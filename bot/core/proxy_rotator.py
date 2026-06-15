import asyncio
import time
import urllib.request
import re
import logging
import aiohttp
from aiohttp_socks import ProxyConnector
from core.messages import get_proxy_switch_alert, get_proxy_restored_alert

logger = logging.getLogger(__name__)

# Источники бесплатных списков SOCKS5 прокси
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all"
]

class SocksProxyRotator:
    def __init__(self):
        self.cached_proxies = []
        self.last_scrape_time = 0
        self.scrape_cooldown = 300  # 5 минут кулдауна между скрапингом
        
    async def scrape_proxies(self):
        """
        Асинхронно скачивает списки SOCKS5 прокси из различных источников.
        Сливает их в один уникальный список.
        """
        now = time.monotonic()
        if self.cached_proxies and (now - self.last_scrape_time < self.scrape_cooldown):
            logger.info("using_cached_proxy_list_scraping_cooldown")
            return self.cached_proxies
            
        logger.info("starting_scraping_fresh_free_socks5_proxy")
        unique_proxies = set()
        
        loop = asyncio.get_running_loop()
        
        for url in PROXY_SOURCES:
            try:
                logger.info("loading_proxies_source", url)
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                
                # Запускаем блокирующее скачивание urllib в пуле потоков
                content = await loop.run_in_executor(
                    None, 
                    lambda: urllib.request.urlopen(req, timeout=8).read().decode('utf-8', errors='ignore')
                )
                
                # Ищем паттерны IP:Port
                found = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s*:\s*\d{2,5}\b', content)
                for p in found:
                    unique_proxies.add(p.strip().replace(" ", ""))
                    
                logger.info("successfully_loaded_proxies", len(found), url)
            except Exception as e:
                logger.warning("failed_load_proxy_list", url, e)
                
        self.cached_proxies = list(unique_proxies)
        self.last_scrape_time = now
        logger.info("scraping_completed_total_unique_proxies_found", len(self.cached_proxies))
        return self.cached_proxies

    async def test_proxy_alive(self, proxy_url, timeout=3.0, verbose=False):
        """
        Проверяет доступность api.telegram.org через указанный прокси.
        Возвращает (is_alive, latency)
        """
        # Извлекаем хост и порт прокси для динамического белого списка
        proxy_key = None
        try:
            from urllib.parse import urlparse
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
                proxy_key = (proxy_host, proxy_port)
        except Exception:
            pass

        if proxy_key:
            try:
                from modules.proxmox.monitor.state import active_proxy_checks
                active_proxy_checks[proxy_key] += 1
            except Exception:
                pass

        url = "https://api.telegram.org"
        start = time.monotonic()
        try:
            connector = ProxyConnector.from_url(proxy_url, rdns=True)
            # Настраиваем короткий таймаут для быстрой проверки
            client_timeout = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(connector=connector, timeout=client_timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        latency = (time.monotonic() - start) * 1000
                        return True, latency
                    else:
                        if verbose:
                            logger.warning("proxy_monitor_neozhidannyy_status-kod_pri_proverke", response.status, proxy_url)
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
        return False, 0

    async def get_working_proxy(self, max_to_check=200, batch_size=40):
        """
        Скачивает списки прокси, проверяет их параллельными батчами
        и возвращает первый найденный рабочий прокси с минимальной задержкой.
        """
        proxies = await self.scrape_proxies()
        if not proxies:
            logger.error("proxy_lists_empty_cannot_start_rotation")
            return None

        # Перемешиваем или берем первые max_to_check
        proxies_to_check = proxies[:max_to_check]
        logger.info("starting_check_first_proxies", len(proxies_to_check))

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(proxies_to_check), batch_size):
                batch = proxies_to_check[i:i+batch_size]
                logger.info("checking_proxy_batch_items", i // batch_size + 1, len(batch))
                
                tasks = []
                for p in batch:
                    p_url = f"socks5://{p}"
                    tasks.append(self.test_proxy_alive(p_url))
                    
                results = await asyncio.gather(*tasks)
                
                working_batch = []
                for idx, (is_working, latency) in enumerate(results):
                    if is_working:
                        p_url = f"socks5://{batch[idx]}"
                        working_batch.append((p_url, latency))
                        
                if working_batch:
                    # Сортируем рабочие прокси по пингу
                    working_batch.sort(key=lambda x: x[1])
                    best_proxy, best_ping = working_batch[0]
                    logger.info("found_working_proxy_ping_ms", best_proxy, best_ping)
                    return best_proxy
                    
        logger.error("all_checked_free_proxies_non_working")
        return None

# Глобальный экземпляр ротатора
proxy_rotator = SocksProxyRotator()


def safe_swap_bot_session(bot, new_session):
    """
    Безопасно заменяет bot.session на новую сессию и асинхронно закрывает старую,
    предотвращая утечки ресурсов и предупреждения asyncio о незакрытых коннекторах и сессиях.
    """
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
    Каждые 2 минуты проверяет доступность основного прокси, если сейчас активен бесплатный (fallback).
    При необходимости производит бесшовное горячее переключение bot.session.
    """
    from aiogram.client.session.aiohttp import AiohttpSession
    import logging
    
    # Исходное состояние
    active_proxy = start_active_proxy if start_active_proxy is not None else primary_proxy
    using_fallback = start_using_fallback
    last_primary_check = time.monotonic()
    
    # Если на старте основной прокси не проверен, делаем это здесь
    if start_active_proxy is None and primary_proxy:
        logging.info("proxy_monitor_checking_functionality_of_the_main")
        is_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=4.0, verbose=False)
        if not is_alive:
            # Пробуем еще 2 раза быстро с паузой 2 секунды
            for attempt in range(2):
                await asyncio.sleep(2.0)
                is_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=4.0, verbose=False)
                if is_alive:
                    break
                    
        if not is_alive:
            logging.warning("proxy_monitor_lost_connection_to_my_proxy")
            new_proxy = await proxy_rotator.get_working_proxy()
            if new_proxy:
                safe_swap_bot_session(bot, AiohttpSession(proxy=new_proxy, **session_kwargs))
                active_proxy = new_proxy
                using_fallback = True
                last_primary_check = time.monotonic() - 15 # Проверить основной при первом шаге цикла
                logging.info("proxy_monitor_successfully_switched_to_free_proxy", new_proxy)
                from modules.proxmox.monitor.utils import send_alert_to_admins
                asyncio.create_task(send_alert_to_admins(
                    get_proxy_switch_alert(primary_proxy, new_proxy)
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
                is_alive, _ = await proxy_rotator.test_proxy_alive(active_proxy, timeout=4.0, verbose=False)
                if not is_alive:
                    logging.warning("proxy_monitor_first_check_proxy_failed_performing_retries", active_proxy)
                    
                    # Пробуем еще 2 раза быстро с паузой 2 секунды
                    retry_success = False
                    for attempt in range(1, 3):
                        await asyncio.sleep(2.0)
                        is_alive_retry, _ = await proxy_rotator.test_proxy_alive(active_proxy, timeout=4.0, verbose=False)
                        if is_alive_retry:
                            logging.info("proxy_monitor_recovered_attempt", active_proxy, attempt + 1)
                            retry_success = True
                            break
                            
                    if not retry_success:
                        logging.warning("proxy_monitor_current_active_proxy_has_completely_stopped", active_proxy)
                        
                        # Перед началом поиска резервных прокси пробуем подождать еще 2 секунды и проверить основной —
                        # вдруг это был очень короткий сбой
                        if not using_fallback and primary_proxy:
                            logging.info("proxy_monitor_waiting_2_seconds_to_reconnect")
                            await asyncio.sleep(2.0)
                            is_alive_last_chance, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=4.0, verbose=False)
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
                            last_primary_check = time.monotonic() - 15 # Проверить основной при следующем шаге цикла
                            logging.info("proxy_monitor_successfully_switched_to_new_free", new_proxy)
                            from modules.proxmox.monitor.utils import send_alert_to_admins
                            await send_alert_to_admins(
                                get_proxy_switch_alert(primary_proxy, new_proxy)
                            )
                        else:
                            logging.error("proxy_monitor_failed_to_find_a_working")
                            
            # 2. Если мы сейчас на бесплатном прокси, раз в 15 секунд проверяем основной прокси
            if using_fallback and primary_proxy:
                now = time.monotonic()
                if now - last_primary_check >= 15:
                    last_primary_check = now
                    logging.info("proxy_monitor_checking_availability_main_proxy", primary_proxy)
                    primary_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=4.0, verbose=False)
                    if not primary_alive:
                        # Пробуем еще 2 раза быстро с паузой 2 секунды
                        for attempt in range(2):
                            await asyncio.sleep(2.0)
                            primary_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=4.0, verbose=False)
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

