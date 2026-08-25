import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from typing import Optional, List, Dict, Any

import aiohttp
from aiohttp_socks import ProxyConnector

from core.messages import get_proxy_switch_alert, get_proxy_restored_alert
from core import sentinel_core_bridge

logger = logging.getLogger(__name__)

# ТИР 1: Черные списки (Hysteria2, Trojan, VLESS, Shadowsocks)
BLACK_LIST_SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt",
]

# ТИР 2: Белые списки (VLESS Reality CIDR/SNI)
WHITE_LIST_SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile-2.txt",
]

# ТИР 3: Открытые SOCKS5 прокси (Крайний случай)
SOCKS5_FALLBACK_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all"
]


class SocksProxyRotator:
    def __init__(self):
        self.cached_proxies = []
        self.last_scrape_time = 0
        self.scrape_cooldown = 300  # 5 минут кулдауна между скрапингом
        self._singbox_proc: Optional[subprocess.Popen] = None
        self._last_working_source_tier: str = ""

    async def test_proxy_alive(self, proxy_url: str, timeout: float = 5.0, verbose: bool = False) -> tuple[bool, float]:
        """
        Проверяет доступность api.telegram.org или резервного эндпоинта через указанный прокси.
        Возвращает (is_alive, latency_ms)
        """
        proxy_key = None
        try:
            from urllib.parse import urlparse
            import socket
            parsed = urlparse(proxy_url)
            netloc = parsed.netloc
            if '@' in netloc:
                netloc = netloc.split('@')[1]
            if ':' in netloc:
                proxy_host, proxy_port = netloc.split(':')
                proxy_port = int(proxy_port)
            else:
                proxy_host = netloc
                proxy_port = 1080 if parsed.scheme == 'socks5' else 80
            if proxy_host and proxy_port:
                try:
                    proxy_host_ip = socket.gethostbyname(proxy_host)
                    proxy_key = (proxy_host_ip, proxy_port)
                except Exception:
                    proxy_key = (proxy_host, proxy_port)
        except Exception:
            pass

        if proxy_key:
            try:
                from modules.proxmox.monitor.state import active_proxy_checks
                active_proxy_checks[proxy_key] += 1
            except Exception:
                pass

        test_urls = ["https://api.telegram.org", "https://cp.cloudflare.com/generate_204"]
        start = time.monotonic()

        try:
            connector = ProxyConnector.from_url(proxy_url, rdns=True)
            client_timeout = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(connector=connector, timeout=client_timeout) as session:
                for test_url in test_urls:
                    try:
                        async with session.get(test_url) as response:
                            if response.status in (200, 204):
                                latency = (time.monotonic() - start) * 1000
                                return True, latency
                    except Exception as err:
                        if verbose:
                            logger.warning("proxy_monitor_check_failed", proxy_url, err)
                        continue
        except Exception as e:
            if verbose:
                logger.warning("proxy_monitor_check_failed", proxy_url, e)
        finally:
            if proxy_key:
                try:
                    from modules.proxmox.monitor.state import active_proxy_checks
                    active_proxy_checks[proxy_key] -= 1
                    if active_proxy_checks[proxy_key] <= 0:
                        active_proxy_checks.pop(proxy_key, None)
                except Exception:
                    pass
        return False, 0.0

    def _find_proxy_engine_bin(self) -> tuple[Optional[str], str]:
        """Finds sing-box or xray binary across host and bot/bin paths."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 1. Check sing-box
        sb_bin = shutil.which("sing-box") or shutil.which("singbox")
        if not sb_bin:
            for candidate in [
                os.path.join(base_dir, "bin", "sing-box.exe" if sys.platform == "win32" else "sing-box"),
                "/usr/local/bin/sing-box",
                "/usr/bin/sing-box"
            ]:
                if os.path.isfile(candidate):
                    sb_bin = candidate
                    break
        if sb_bin:
            return sb_bin, "singbox"

        # 2. Check xray
        xray_bin = shutil.which("xray") or shutil.which("xray-core")
        if not xray_bin:
            for candidate in [
                os.path.join(base_dir, "bin", "xray.exe" if sys.platform == "win32" else "xray"),
                "/usr/local/bin/xray",
                "/usr/bin/xray"
            ]:
                if os.path.isfile(candidate):
                    xray_bin = candidate
                    break
        if xray_bin:
            return xray_bin, "xray"

        return None, ""

    async def start_or_reload_singbox_tunnel(self, config_json: str, port: int = 10818) -> bool:
        """
        Запускает или обновляет локальный клиентский процесс Sing-box / Xray с failover конфигом.
        """
        engine_bin, engine_type = self._find_proxy_engine_bin()
        if not engine_bin:
            logger.debug("Neither sing-box nor xray binary found on host, using direct node connections")
            return False

        # Terminate previous process if alive
        if self._singbox_proc is not None:
            try:
                self._singbox_proc.terminate()
                self._singbox_proc.wait(timeout=2)
            except Exception:
                try:
                    self._singbox_proc.kill()
                except Exception:
                    pass
            self._singbox_proc = None

        cfg_name = f"{engine_type}_failover.json"
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), cfg_name)
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(config_json)

            self._singbox_proc = subprocess.Popen(
                [engine_bin, "run", "-c", cfg_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            # Wait 0.8s for socket binding
            await asyncio.sleep(0.8)

            # Test local proxy
            local_url = f"socks5://127.0.0.1:{port}"
            ok, lat = await self.test_proxy_alive(local_url, timeout=4.0)
            if ok:
                logger.info("Started local %s failover tunnel on port %d (latency: %.1f ms)", engine_type, port, lat)
                return True
            else:
                stderr_output = ""
                if self._singbox_proc and self._singbox_proc.poll() is not None:
                    try:
                        _, stderr_bytes = self._singbox_proc.communicate(timeout=1)
                        stderr_output = stderr_bytes.decode('utf-8', errors='ignore').strip()
                    except Exception:
                        pass
                logger.warning("%s started on port %d but failed health probe. Details: %s", engine_type, port, stderr_output or "timeout")
        except Exception as e:
            logger.error("Failed to start %s tunnel: %s", engine_type, e)

        return False

    async def _check_vpn_sources(self, sources: List[str], tier_name: str) -> Optional[str]:
        """Загружает и проверяет через ядро список VPN-конфигураций."""
        loop = asyncio.get_running_loop()
        uris = []

        for url in sources:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                content = await loop.run_in_executor(
                    None,
                    lambda: urllib.request.urlopen(req, timeout=6).read().decode('utf-8', errors='ignore')
                )
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('//'):
                        uris.append(line)
            except Exception as e:
                logger.warning("Failed to fetch %s source %s: %s", tier_name, url, e)

        if not uris:
            return None

        # Пакетная проверка всех нод через высокопроизводительное Go ядро
        results = await loop.run_in_executor(
            None,
            lambda: sentinel_core_bridge.check_proxies(uris, target_host="api.telegram.org", timeout_ms=2500, concurrency=64)
        )
        working = [r for r in results if r.get("success")]
        if not working:
            logger.info("%s: checked %d nodes, none responsive", tier_name, len(uris))
            return None

        working.sort(key=lambda x: x.get("latencyMs", 99999))
        best = working[0]
        logger.info("%s: %d / %d nodes alive. Best: %s (%.1f ms)", tier_name, len(working), len(uris), best.get("name") or best.get("proxyUrl"), best.get("latencyMs", 0))

        # Формируем ТОП-4 профилей для отказоустойчивой группы Sing-box на выделенном порту 10818
        top_profiles = []
        for w in working[:4]:
            uri = w.get("proxyUrl")
            if uri:
                parsed_list = sentinel_core_bridge.parse_subscription(uri)
                if parsed_list:
                    top_profiles.append(parsed_list[0])

        if top_profiles:
            cfg_json = sentinel_core_bridge.build_failover_client_config(top_profiles, socks_port=10818, http_port=10819)
            if cfg_json:
                tunnel_ok = await self.start_or_reload_singbox_tunnel(cfg_json, port=10818)
                if tunnel_ok:
                    self._last_working_source_tier = tier_name
                    return "socks5://127.0.0.1:10818"

        # Если локальный бинарник sing-box не установлен, но среди лучших есть SOCKS5
        for w in working:
            if w.get("protocol") == "socks5" or "socks5://" in w.get("proxyUrl", ""):
                self._last_working_source_tier = tier_name
                return w.get("proxyUrl")

        return None

    async def _check_socks5_sources(self) -> Optional[str]:
        """Крайний случай: скрапинг и проверка открытых SOCKS5 списков."""
        loop = asyncio.get_running_loop()
        unique_proxies = set()

        for url in SOCKS5_FALLBACK_SOURCES:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                content = await loop.run_in_executor(
                    None,
                    lambda: urllib.request.urlopen(req, timeout=6).read().decode('utf-8', errors='ignore')
                )
                found = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s*:\s*\d{2,5}\b', content)
                for p in found:
                    unique_proxies.add(f"socks5://{p.strip().replace(' ', '')}")
            except Exception as e:
                logger.warning("failed_load_proxy_list", url, e)

        if not unique_proxies:
            return None

        proxies_list = list(unique_proxies)[:200]
        results = await loop.run_in_executor(
            None,
            lambda: sentinel_core_bridge.check_proxies(proxies_list, target_host="api.telegram.org", timeout_ms=3000, concurrency=64)
        )
        working = [r for r in results if r.get("success")]
        if not working:
            return None

        working.sort(key=lambda x: x.get("latencyMs", 99999))
        best_proxy = working[0]["proxyUrl"]
        self._last_working_source_tier = "Tier 3 (SOCKS5 Public)"
        logger.info("Tier 3 SOCKS5: found %d working proxies, best: %s (%.1f ms)", len(working), best_proxy, working[0]["latencyMs"])
        return best_proxy

    async def get_working_proxy(self) -> Optional[str]:
        """
        3-Уровневый каскадный поиск рабочего соединения:
        1. ТИР 1: Черные списки (Hysteria2, Trojan, VLESS, Shadowsocks).
        2. ТИР 2 (если ТИР 1 пуст): Белые списки (VLESS Reality).
        3. ТИР 3 (Крайний случай): Парсинг открытых SOCKS5 прокси.
        """
        # ТИР 1: Проверяем черные списки
        logger.info("starting_checking_tier1_black_lists")
        t1_proxy = await self._check_vpn_sources(BLACK_LIST_SOURCES, tier_name="Tier 1 (Black List)")
        if t1_proxy:
            return t1_proxy

        # ТИР 2: Проверяем белые списки
        logger.info("starting_checking_tier2_white_lists")
        t2_proxy = await self._check_vpn_sources(WHITE_LIST_SOURCES, tier_name="Tier 2 (White List)")
        if t2_proxy:
            return t2_proxy

        # ТИР 3: Крайний случай - парсинг открытых SOCKS5
        logger.info("starting_checking_tier3_socks5_public")
        t3_proxy = await self._check_socks5_sources()
        if t3_proxy:
            return t3_proxy

        logger.error("all_checked_free_proxies_non_working")
        return None


# Глобальный экземпляр ротатора
proxy_rotator = SocksProxyRotator()


def safe_swap_bot_session(bot, new_session):
    """Безопасно заменяет bot.session на новую сессию и асинхронно закрывает старую."""
    old_session = bot.session
    bot.session = new_session
    if old_session:
        try:
            asyncio.create_task(old_session.close())
        except Exception:
            pass


async def proxy_monitor_loop(bot, primary_proxy, session_kwargs, start_active_proxy=None, start_using_fallback=False):
    """
    Фоновый мониторинг прокси.
    Каждые 10 секунд проверяет текущий активный прокси.
    Каждые 15 секунд проверяет доступность основного прокси, если сейчас активен fallback.
    При необходимости производит бесшовное горячее переключение bot.session.
    """
    from aiogram.client.session.aiohttp import AiohttpSession

    active_proxy = start_active_proxy if start_active_proxy is not None else primary_proxy
    using_fallback = start_using_fallback
    last_primary_check = time.monotonic()

    # Если на старте основной прокси не проверен, делаем это здесь
    if start_active_proxy is None and primary_proxy:
        logging.info("proxy_monitor_checking_functionality_of_the_main")
        is_local = "127.0.0.1" in primary_proxy or "localhost" in primary_proxy
        initial_timeout = 8.0 if is_local else 5.0
        initial_retries = 5 if is_local else 2

        is_alive = False
        for attempt in range(initial_retries):
            if attempt > 0:
                await asyncio.sleep(2.0)
            is_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=initial_timeout, verbose=False)
            if is_alive:
                break

        if not is_alive:
            logging.warning("proxy_monitor_lost_connection_to_my_proxy")
            new_proxy = await proxy_rotator.get_working_proxy()
            if new_proxy:
                safe_swap_bot_session(bot, AiohttpSession(proxy=new_proxy, **session_kwargs))
                active_proxy = new_proxy
                using_fallback = True
                last_primary_check = time.monotonic() - 15
                logging.info("proxy_monitor_successfully_switched_to_free_proxy", new_proxy)
                from modules.proxmox.monitor.utils import send_alert_to_admins
                asyncio.create_task(send_alert_to_admins(
                    get_proxy_switch_alert(primary_proxy, new_proxy, tier_info=proxy_rotator._last_working_source_tier or "Failover")
                ))
            else:
                logging.error("proxy_monitor_failed_to_find_a_live")
        else:
            logging.info("proxy_monitor_main_proxy_successfully_passed_the")

    while True:
        try:
            await asyncio.sleep(10)

            # 1. Проверяем работоспособность текущего активного прокси
            if active_proxy:
                is_alive, _ = await proxy_rotator.test_proxy_alive(active_proxy, timeout=6.0, verbose=False)
                if not is_alive:
                    logging.warning("proxy_monitor_first_check_proxy_failed_performing_retries", active_proxy)

                    is_local = "127.0.0.1" in active_proxy or "localhost" in active_proxy
                    retry_count = 5 if is_local else 3
                    retry_success = False
                    for attempt in range(1, retry_count):
                        await asyncio.sleep(3.0)
                        is_alive_retry, _ = await proxy_rotator.test_proxy_alive(active_proxy, timeout=6.0, verbose=False)
                        if is_alive_retry:
                            logging.info("proxy_monitor_recovered_attempt", active_proxy, attempt + 1)
                            retry_success = True
                            break

                    if not retry_success:
                        logging.warning("proxy_monitor_current_active_proxy_has_completely_stopped", active_proxy)

                        if not using_fallback and primary_proxy:
                            logging.info("proxy_monitor_waiting_2_seconds_to_reconnect")
                            await asyncio.sleep(5.0)
                            is_alive_last_chance, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=6.0, verbose=False)
                            if is_alive_last_chance:
                                logging.info("proxy_monitor_main_proxy_recovered_after_a")
                                continue

                        if not using_fallback:
                            logging.warning("proxy_monitor_lost_connection_to_my_proxy")
                        else:
                            logging.warning("proxy_monitor_backup_free_proxy_disconnected_searching")

                        new_proxy = await proxy_rotator.get_working_proxy()
                        if new_proxy:
                            safe_swap_bot_session(bot, AiohttpSession(proxy=new_proxy, **session_kwargs))
                            active_proxy = new_proxy
                            using_fallback = True
                            last_primary_check = time.monotonic() - 15
                            logging.info("proxy_monitor_successfully_switched_to_new_free", new_proxy)
                            from modules.proxmox.monitor.utils import send_alert_to_admins
                            await send_alert_to_admins(
                                get_proxy_switch_alert(primary_proxy, new_proxy, tier_info=proxy_rotator._last_working_source_tier or "Failover")
                            )
                        else:
                            logging.error("proxy_monitor_failed_to_find_a_working")

            # 2. Если мы сейчас на fallback, проверяем доступность основного прокси
            if using_fallback and primary_proxy:
                now = time.monotonic()
                if now - last_primary_check >= 15:
                    last_primary_check = now
                    logging.info("proxy_monitor_checking_availability_main_proxy", primary_proxy)
                    primary_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=6.0, verbose=False)
                    if not primary_alive:
                        for attempt in range(2):
                            await asyncio.sleep(2.0)
                            primary_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=6.0, verbose=False)
                            if primary_alive:
                                break

                    if primary_alive:
                        logging.info("proxy_monitor_my_main_proxy_is_available")
                        safe_swap_bot_session(bot, AiohttpSession(proxy=primary_proxy, **session_kwargs))
                        active_proxy = primary_proxy
                        using_fallback = False
                        logging.info("proxy_monitor_connection_to_the_main_proxy")
                        from modules.proxmox.monitor.utils import send_alert_to_admins
                        await send_alert_to_admins(
                            get_proxy_restored_alert(primary_proxy)
                        )
                    else:
                        logging.info("proxy_monitor_main_proxy_is_still_unavailable")
        except Exception as e:
            logging.error("proxy_monitor_exception_in_monitoring_loop", e)
