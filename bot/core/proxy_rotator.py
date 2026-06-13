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
            logger.info("Используем кэшированный список прокси (кулдаун скрапинга активен)")
            return self.cached_proxies
            
        logger.info("Начинаем скрапинг свежих списков бесплатных SOCKS5 прокси...")
        unique_proxies = set()
        
        loop = asyncio.get_running_loop()
        
        for url in PROXY_SOURCES:
            try:
                logger.info(f"Загрузка прокси из источника: {url}")
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
                    
                logger.info(f"Успешно загружено {len(found)} прокси из {url}")
            except Exception as e:
                logger.warning(f"Не удалось загрузить список прокси из {url}: {e}")
                
        self.cached_proxies = list(unique_proxies)
        self.last_scrape_time = now
        logger.info(f"Скрапинг завершен. Всего уникальных прокси найдено: {len(self.cached_proxies)}")
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
                            logger.warning(f"[Proxy Monitor] Неожиданный статус-код {response.status} при проверке {proxy_url}")
        except Exception as e:
            if verbose:
                logger.warning(f"[Proxy Monitor] Сбой проверки прокси {proxy_url}: {e!r}")
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
            logger.error("Списки прокси пусты, невозможно запустить ротатор.")
            return None

        # Перемешиваем или берем первые max_to_check
        proxies_to_check = proxies[:max_to_check]
        logger.info(f"Начинаем проверку первых {len(proxies_to_check)} прокси...")

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(proxies_to_check), batch_size):
                batch = proxies_to_check[i:i+batch_size]
                logger.info(f"Проверка батча прокси #{i//batch_size + 1} ({len(batch)} шт)...")
                
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
                    logger.info(f"Найден рабочий прокси: {best_proxy} (пинг: {best_ping:.1f} мс)")
                    return best_proxy
                    
        logger.error("Все проверенные бесплатные прокси оказались нерабочими.")
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
        logging.info("[Proxy Monitor] Проверяем работоспособность основного прокси на старте...")
        is_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=4.0, verbose=False)
        if not is_alive:
            # Пробуем еще 2 раза быстро с паузой 2 секунды
            for attempt in range(2):
                await asyncio.sleep(2.0)
                is_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=4.0, verbose=False)
                if is_alive:
                    break
                    
        if not is_alive:
            logging.warning("[Proxy Monitor] Потерял соединение с моим прокси и пошел искать доступные бесплатные SOCKS5...")
            new_proxy = await proxy_rotator.get_working_proxy()
            if new_proxy:
                safe_swap_bot_session(bot, AiohttpSession(proxy=new_proxy, **session_kwargs))
                active_proxy = new_proxy
                using_fallback = True
                logging.info(f"[Proxy Monitor] Успешно переключено на бесплатный прокси: {new_proxy}")
                from modules.proxmox.monitor.utils import send_alert_to_admins
                asyncio.create_task(send_alert_to_admins(
                    get_proxy_switch_alert(primary_proxy, new_proxy)
                ))
            else:
                logging.error("[Proxy Monitor] Не удалось найти живой бесплатный прокси. Остаемся на основном в надежде на чудо...")
        else:
            logging.info("[Proxy Monitor] Основной прокси успешно прошел стартовую проверку.")
            
    while True:
        try:
            await asyncio.sleep(10)
            
            # 1. Проверяем работоспособность текущего активного прокси
            if active_proxy:
                is_alive, _ = await proxy_rotator.test_proxy_alive(active_proxy, timeout=4.0, verbose=False)
                if not is_alive:
                    logging.warning(f"[Proxy Monitor] Сбой первой проверки прокси ({active_proxy}). Выполняем повторные проверки...")
                    
                    # Пробуем еще 2 раза быстро с паузой 2 секунды
                    retry_success = False
                    for attempt in range(1, 3):
                        await asyncio.sleep(2.0)
                        is_alive_retry, _ = await proxy_rotator.test_proxy_alive(active_proxy, timeout=4.0, verbose=False)
                        if is_alive_retry:
                            logging.info(f"[Proxy Monitor] Прокси ({active_proxy}) восстановился на попытке {attempt + 1}.")
                            retry_success = True
                            break
                            
                    if not retry_success:
                        logging.warning(f"[Proxy Monitor] Текущий активный прокси ({active_proxy}) окончательно перестал отвечать!")
                        
                        if not using_fallback:
                            logging.warning("[Proxy Monitor] Потерял соединение с моим прокси и пошел искать доступные бесплатные SOCKS5...")
                        else:
                            logging.warning("[Proxy Monitor] Резервный бесплатный прокси отключился, ищу замену...")
                            
                        new_proxy = await proxy_rotator.get_working_proxy()
                        if new_proxy:
                            safe_swap_bot_session(bot, AiohttpSession(proxy=new_proxy, **session_kwargs))
                            active_proxy = new_proxy
                            using_fallback = True
                            logging.info(f"[Proxy Monitor] Успешно переключено на новый бесплатный прокси: {new_proxy}")
                            from modules.proxmox.monitor.utils import send_alert_to_admins
                            await send_alert_to_admins(
                                get_proxy_switch_alert(primary_proxy, new_proxy)
                            )
                        else:
                            logging.error("[Proxy Monitor] Не удалось найти рабочий бесплатный прокси. Попробуем в следующей итерации.")
                            
            # 2. Если мы сейчас на бесплатном прокси, раз в 2 минуты проверяем основной прокси
            if using_fallback and primary_proxy:
                now = time.monotonic()
                if now - last_primary_check >= 120:
                    last_primary_check = now
                    logging.info(f"[Proxy Monitor] Проверяем доступность основного прокси ({primary_proxy})...")
                    primary_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=4.0, verbose=False)
                    if not primary_alive:
                        # Пробуем еще 2 раза быстро с паузой 2 секунды
                        for attempt in range(2):
                            await asyncio.sleep(2.0)
                            primary_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy, timeout=4.0, verbose=False)
                            if primary_alive:
                                break
                                
                    if primary_alive:
                        logging.info("[Proxy Monitor] Мой основной прокси снова доступен! Возвращаюсь на него и разрываю соединение с бесплатным.")
                        safe_swap_bot_session(bot, AiohttpSession(proxy=primary_proxy, **session_kwargs))
                        active_proxy = primary_proxy
                        using_fallback = False
                        logging.info("[Proxy Monitor] Успешно возвращено соединение с основным прокси.")
                        from modules.proxmox.monitor.utils import send_alert_to_admins
                        await send_alert_to_admins(
                            get_proxy_restored_alert(primary_proxy)
                        )
                    else:
                        logging.info("[Proxy Monitor] Основной прокси всё еще недоступен. Продолжаем работу на резервном.")
        except Exception as e:
            logging.error(f"[Proxy Monitor] Исключение в цикле мониторинга: {e}")

