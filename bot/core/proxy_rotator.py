import asyncio
import time
import urllib.request
import re
import logging
import aiohttp
from aiohttp_socks import ProxyConnector

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
        
        # Получаем список чувствительных портов для фильтрации
        from core.config import settings
        sensitive_ports = settings.monitor_lxc_ports_sensitive
        if isinstance(sensitive_ports, str):
            try:
                sensitive_ports = [int(x.strip()) for x in sensitive_ports.split(',') if x.strip()]
            except Exception:
                sensitive_ports = []
        elif not isinstance(sensitive_ports, list):
            sensitive_ports = []
        
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
                filtered_count = 0
                for p in found:
                    p_clean = p.strip().replace(" ", "")
                    try:
                        parts = p_clean.split(':')
                        if len(parts) == 2:
                            port = int(parts[1])
                            if port in sensitive_ports:
                                filtered_count += 1
                                continue
                    except Exception:
                        pass
                    unique_proxies.add(p_clean)
                    
                logger.info(f"Успешно загружено {len(found)} прокси из {url} (отфильтровано чувствительных портов: {filtered_count})")
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
