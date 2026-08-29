import asyncio
import json
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from typing import Optional, List, Dict, Any, Tuple

# Ensure bot root directory is always present in sys.path for direct CLI execution
_bot_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _bot_root not in sys.path:
    sys.path.insert(0, _bot_root)

from core import sentinel_core_bridge

logger = logging.getLogger(__name__)

# ТИР 1: Черные списки (Hysteria 2 / Trojan / VLESS Reality / Shadowsocks)
BLACK_LIST_SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
]

# ТИР 2: Белые списки (VLESS Reality CIDR/SNI)
WHITE_LIST_SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
]

# ТИР 3: Открытые SOCKS5 прокси (Крайний случай)
SOCKS5_FALLBACK_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all"
]


def _free_port(port: int):
    """Освобождает указанный локальный порт на Linux/Unix."""
    if sys.platform == "win32":
        return
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def parse_vpn_uri(uri: str) -> Optional[Dict[str, Any]]:
    """Парсит URI подписки через Go-ядро sentinel-core."""
    try:
        res = sentinel_core_bridge.parse_subscription(uri)
        if res and isinstance(res, list) and len(res) > 0:
            return res[0]
    except Exception as e:
        logger.debug("Failed to parse URI %s via core: %s", uri[:30], e)
    return None


class SocksProxyRotator:
    def __init__(self):
        self.cached_proxies = []
        self.last_scrape_time = 0
        self.scrape_cooldown = 300
        self._singbox_proc: Optional[subprocess.Popen] = None
        self._last_working_source_tier: str = ""
        self._current_engine: str = "singbox"

    def _find_proxy_engine_bin(self) -> Tuple[Optional[str], str]:
        """Ищет бинарник sing-box или xray на сервере."""
        bin_dir = os.path.join(_bot_root, "bin")

        singbox_candidates = [
            os.path.join(bin_dir, "sing-box.exe" if sys.platform == "win32" else "sing-box"),
            os.path.join(bin_dir, "singbox.exe" if sys.platform == "win32" else "singbox"),
            shutil.which("sing-box"),
            shutil.which("singbox"),
            "/usr/local/bin/sing-box",
            "/usr/bin/sing-box"
        ]
        for c in singbox_candidates:
            if c and os.path.isfile(c) and (sys.platform == "win32" or os.access(c, os.X_OK)):
                return c, "singbox"

        xray_candidates = [
            os.path.join(bin_dir, "xray.exe" if sys.platform == "win32" else "xray"),
            shutil.which("xray"),
            "/usr/local/bin/xray",
            "/usr/bin/xray"
        ]
        for c in xray_candidates:
            if c and os.path.isfile(c) and (sys.platform == "win32" or os.access(c, os.X_OK)):
                return c, "xray"

        return None, ""

    def stop_tunnel(self):
        """Останавливает запущенный фоновый процесс прокси и всю его группу процессов."""
        if self._singbox_proc:
            try:
                if sys.platform != "win32":
                    try:
                        os.killpg(os.getpgid(self._singbox_proc.pid), signal.SIGTERM)
                    except Exception:
                        self._singbox_proc.terminate()
                else:
                    self._singbox_proc.terminate()
                self._singbox_proc.wait(timeout=1.5)
            except Exception:
                try:
                    if sys.platform != "win32":
                        try:
                            os.killpg(os.getpgid(self._singbox_proc.pid), signal.SIGKILL)
                        except Exception:
                            self._singbox_proc.kill()
                    else:
                        self._singbox_proc.kill()
                except Exception:
                    pass
            self._singbox_proc = None

        try:
            if sys.platform != "win32":
                subprocess.run(["pkill", "-9", "-f", "singbox_failover.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-9", "-f", "xray_failover.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        _free_port(10818)
        _free_port(10819)

    def _get_cache_file_path(self) -> str:
        """Путь к локальному дисковому кэшу рабочих VPN-нод."""
        config_dir = os.path.join(_bot_root, "config")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "cached_vpn_nodes.json")

    def _load_cached_nodes_from_disk(self) -> List[str]:
        cache_file = self._get_cache_file_path()
        if os.path.isfile(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [str(x) for x in data if x]
            except Exception as e:
                logger.debug("Failed to read cached VPN nodes: %s", e)
        return []

    def _save_working_nodes_to_disk(self, uris: List[str]):
        if not uris:
            return
        cache_file = self._get_cache_file_path()
        try:
            existing = self._load_cached_nodes_from_disk()
            combined = []
            seen = set()
            for u in uris + existing:
                if u and u not in seen:
                    seen.add(u)
                    combined.append(u)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(combined[:50], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug("Failed to write cached VPN nodes: %s", e)

    async def start_or_reload_singbox_tunnel(self, config_json: str, port: int = 10818) -> bool:
        """Запускает клиентский процесс Sing-box с failover-группой."""
        self.stop_tunnel()
        _free_port(port)
        _free_port(port + 1)

        engine_bin, engine_type = self._find_proxy_engine_bin()
        if not engine_bin:
            logger.error("Бинарник sing-box/xray не найден в %s/bin", _bot_root)
            return False

        cfg_path = os.path.join(_bot_root, "bin", f"{engine_type}_failover.json")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)

        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(config_json)

            env = os.environ.copy()
            env["ENABLE_DEPRECATED_LEGACY_DNS_SERVERS"] = "true"

            extra_kwargs = {}
            if sys.platform != "win32":
                extra_kwargs["preexec_fn"] = os.setsid

            log_path = os.path.join(_bot_root, "bin", f"{engine_type}_rotator.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            log_file = open(log_path, "w", encoding="utf-8", errors="ignore")

            cmd = [engine_bin, "run", "-c", cfg_path] if engine_type == "singbox" else [engine_bin, "run", "-config", cfg_path]

            self._singbox_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                bufsize=1,
                env=env,
                **extra_kwargs
            )
            self._current_engine = engine_type

            # Background thread to stream and log Sing-box engine lines live in real time
            import threading
            def _stream_logs():
                try:
                    for line in iter(self._singbox_proc.stdout.readline, ''):
                        clean_line = line.strip()
                        if clean_line:
                            log_file.write(clean_line + "\n")
                            log_file.flush()
                            logger.info("    [%s] %s", engine_type, clean_line)
                except Exception:
                    pass
                finally:
                    try:
                        log_file.close()
                    except Exception:
                        pass

            log_thread = threading.Thread(target=_stream_logs, daemon=True)
            log_thread.start()

            for _ in range(16):
                await asyncio.sleep(0.6)
                if self._singbox_proc.poll() is not None:
                    logger.warning("%s process terminated with exit code %d (see %s)", engine_type, self._singbox_proc.returncode, log_path)
                    self._singbox_proc = None
                    return False

                ok, lat = await self.test_proxy_alive(f"socks5://127.0.0.1:{port}", timeout=2.5)
                if ok:
                    logger.info("Started local %s failover tunnel on port %d (latency: %.1f ms)", engine_type, port, lat)
                    return True

            logger.warning("%s started on port %d but failed health probe.", engine_type, port)
            self.stop_tunnel()
            return False
        except Exception as e:
            logger.exception("Failed to launch %s client process: %s", engine_type, e)
            self.stop_tunnel()
            return False

    async def _test_and_activate_nodes(self, uris: List[str], tier_name: str = "Tier") -> Optional[str]:
        """Тестирует список нод через ядро и поднимает отказоустойчивую группу Sing-box."""
        if not uris:
            return None

        logger.info("[Failover] Parsing %d nodes via sentinel-core...", len(uris[:50]))
        profiles = []
        for u in uris[:50]:
            p = parse_vpn_uri(u)
            if p:
                p["proxyUrl"] = u
                profiles.append(p)

        if not profiles:
            return None

        # Проверяем живые ноды параллельно через сокетный пинг ядра
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None,
            lambda: sentinel_core_bridge.check_proxies(profiles[:25], timeout_ms=3000)
        )

        working = [r for r in results if r.get("isAlive")]
        if not working:
            return None

        working.sort(key=lambda x: x.get("latencyMs", 999999))
        best = working[0]
        logger.info("%s: %d / %d nodes alive. Best: %s (%.1f ms)", tier_name, len(working), len(profiles[:25]), best.get("name") or best.get("address"), best.get("latencyMs", 0))

        logger.info("[Failover] Compiling Sing-box multi-node client config for %d alive nodes...", len(working[:10]))
        client_cfg = None
        try:
            client_cfg = sentinel_core_bridge.build_failover_client_config(
                working[:10],
                socks_port=10818,
                http_port=10819,
                health_url="https://www.gstatic.com/generate_204"
            )
        except Exception as e:
            logger.error("Core build_failover_client_config exception: %s", e)

        if not client_cfg:
            logger.error("Не удалось скомпилировать Sing-box конфиг через sentinel-core.")
            return None

        logger.info("[Tunnel] Launching Sing-box client process and activating fastest route...")
        ok = await self.start_or_reload_singbox_tunnel(client_cfg, port=10818)
        if ok:
            working_uris = [p["proxyUrl"] for p in working if p.get("proxyUrl")]
            if working_uris:
                self._save_working_nodes_to_disk(working_uris)
            return "socks5://127.0.0.1:10818"

        return None

    async def _fetch_single_source(self, base_url: str) -> List[str]:
        """Скачивает файл подписки через быстрые CDN-зеркала с таймаутом 3.5с."""
        loop = asyncio.get_running_loop()
        mirror_prefixes = [
            "https://ghfast.top/",
            "https://gh-proxy.com/",
            "https://gh.ddlc.top/",
            "",
        ]

        def _fetch_url(target_url: str) -> str:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SentinelController/1.0"}
            )
            with urllib.request.urlopen(req, timeout=2.0, context=ctx) as response:
                return response.read().decode("utf-8", errors="ignore")

        for prefix in mirror_prefixes:
            full_url = f"{prefix}{base_url}" if prefix else base_url
            try:
                content = await loop.run_in_executor(None, _fetch_url, full_url)
                if content and len(content) > 10:
                    return [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
            except Exception:
                continue
        return []

    async def _check_vpn_sources(self, sources: List[str], tier_name: str = "Tier") -> Optional[str]:
        """Параллельно скачивает подписки и активирует лучший Sing-box туннель."""
        tasks = [self._fetch_single_source(url) for url in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        uris = []
        for r in results:
            if isinstance(r, list):
                uris.extend(r)

        return await self._test_and_activate_nodes(uris, tier_name=tier_name)

    async def start_tunnel_for_node(self, node_uri: str, port: int = 10818) -> bool:
        """Запускает туннель для конкретной VPN ссылки через ядро sentinel-core."""
        parsed = parse_vpn_uri(node_uri)
        if parsed:
            try:
                cfg_json = sentinel_core_bridge.build_failover_client_config([parsed], socks_port=port, http_port=port+1, health_url="https://www.gstatic.com/generate_204")
                if cfg_json:
                    ok = await self.start_or_reload_singbox_tunnel(cfg_json, port=port)
                    if ok:
                        self._save_working_nodes_to_disk([node_uri])
                        return True
            except Exception as e:
                logger.error("start_tunnel_for_node error: %s", e)
        return False

    async def test_proxy_alive(self, proxy_url: str, timeout: float = 3.0) -> Tuple[bool, float]:
        """Проверяет доступность SOCKS5/HTTP прокси сокетным рукопожатием и сквозным соединением (E2E)."""
        loop = asyncio.get_running_loop()

        def _socket_probe():
            start = time.monotonic()
            try:
                parsed = urllib.parse.urlparse(proxy_url)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or 1080
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((host, port))
                if proxy_url.startswith("socks5://") or proxy_url.startswith("socks5h://"):
                    # 1. SOCKS5 greeting: VER=5, NMETHODS=1, NO_AUTH=0
                    s.sendall(b"\x05\x01\x00")
                    resp = s.recv(2)
                    if resp != b"\x05\x00":
                        s.close()
                        return False, 999999.0

                    # 2. SOCKS5 CONNECT to 1.1.1.1:443 (HTTPS) to verify real internet connectivity through VPN!
                    ip_bytes = socket.inet_aton("1.1.1.1")
                    port_bytes = (443).to_bytes(2, byteorder="big")
                    req = b"\x05\x01\x00\x01" + ip_bytes + port_bytes
                    s.sendall(req)
                    connect_resp = s.recv(10)
                    s.close()
                    if len(connect_resp) >= 2 and connect_resp[1] == 0:
                        lat = (time.monotonic() - start) * 1000.0
                        return True, lat
                    return False, 999999.0
                elif proxy_url.startswith("socks4://"):
                    s.close()
                    lat = (time.monotonic() - start) * 1000.0
                    return True, lat
                else:
                    # HTTP proxy probe
                    s.sendall(b"CONNECT 1.1.1.1:443 HTTP/1.1\r\nHost: 1.1.1.1:443\r\n\r\n")
                    resp = s.recv(12)
                    s.close()
                    lat = (time.monotonic() - start) * 1000.0
                    return b"200" in resp or b"HTTP" in resp, lat
            except Exception:
                return False, 999999.0

        return await loop.run_in_executor(None, _socket_probe)

    async def get_working_proxy(self) -> Optional[str]:
        """4-Уровневый каскадный поиск рабочего соединения."""
        # ТИР 0: Дисковый кэш
        cached = self._load_cached_nodes_from_disk()
        if cached:
            logger.info("[Failover] Checking %d local cached VPN nodes...", len(cached))
            cached_res = await self._test_and_activate_nodes(cached, tier_name="Disk Cache")
            if cached_res:
                logger.info("[Failover] Successfully activated cached VPN node: %s", cached_res)
                return cached_res

        # ТИР 1: Черные списки
        logger.info("[Failover] Checking Tier 1: Black lists (Hysteria 2 / Trojan / VLESS Reality)...")
        t1_proxy = await self._check_vpn_sources(BLACK_LIST_SOURCES, tier_name="Tier 1")
        if t1_proxy:
            return t1_proxy

        # ТИР 2: Белые списки
        logger.info("[Failover] Checking Tier 2: White lists (VLESS Reality)...")
        t2_proxy = await self._check_vpn_sources(WHITE_LIST_SOURCES, tier_name="Tier 2")
        if t2_proxy:
            return t2_proxy

        return None


proxy_rotator = SocksProxyRotator()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sentinel Controller Proxy Rotator CLI Bridge")
    parser.add_argument("--find-and-start", action="store_true", help="Find best working VPN node and start local Sing-box tunnel")
    parser.add_argument("--node", type=str, default="", help="Specific VPN node URI (ss://, vless://, etc.) to start tunnel for")
    parser.add_argument("--port", type=int, default=10818, help="Local SOCKS5 port to bind (default 10818)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    async def _cli_main():
        if args.node:
            print(f"[Rotator] Starting local tunnel for node on port {args.port}...", file=sys.stderr, flush=True)
            ok = await proxy_rotator.start_tunnel_for_node(args.node, port=args.port)
            if ok:
                print(f"PROXY_READY:socks5://127.0.0.1:{args.port}", flush=True)
                while True:
                    await asyncio.sleep(1)
            else:
                print(f"[Rotator] Failed to start tunnel for node, falling back to rotation...", file=sys.stderr, flush=True)

        if args.find_and_start or args.node:
            print(f"[Rotator] Searching for working VPN node on port {args.port}...", file=sys.stderr, flush=True)
            proxy = await proxy_rotator.get_working_proxy()
            if proxy:
                print(f"PROXY_READY:{proxy}", flush=True)
                while True:
                    await asyncio.sleep(1)
            else:
                print(f"[Rotator] No responsive VPN nodes found", file=sys.stderr, flush=True)
                sys.exit(1)

    try:
        asyncio.run(_cli_main())
    except KeyboardInterrupt:
        proxy_rotator.stop_tunnel()
