import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch

# Подтягиваем модули
from core.config import settings
from core.proxy_rotator import SocksProxyRotator

def test_proxy_rotation_config():
    """
    Проверяет, что настройки ротации прокси добавлены в Pydantic Settings
    и имеют корректный логический тип (bool).
    """
    assert hasattr(settings, 'enable_free_proxy_rotation')
    assert isinstance(settings.enable_free_proxy_rotation, bool)

@pytest.mark.asyncio
async def test_scrape_proxies_parsing():
    """
    Проверяет, что SocksProxyRotator правильно загружает и парсит
    IP:Port адреса из контента списков.
    """
    rotator = SocksProxyRotator()
    
    mock_response_1 = "127.0.0.1:1080\n192.168.1.5:8080\n# некорректная строка\n8.8.8.8:80"
    mock_response_2 = "200.200.200.200:3128\n127.0.0.1:1080" # дубликат
    
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_read_1 = MagicMock()
        mock_read_1.read.return_value.decode.return_value = mock_response_1
        
        mock_read_2 = MagicMock()
        mock_read_2.read.return_value.decode.return_value = mock_response_2
        
        mock_urlopen.side_effect = [mock_read_1, mock_read_2]
        
        proxies = await rotator.scrape_proxies()
        
        assert len(proxies) == 4
        assert "127.0.0.1:1080" in proxies
        assert "192.168.1.5:8080" in proxies
        assert "8.8.8.8:80" in proxies
        assert "200.200.200.200:3128" in proxies

# Создаем простые и надежные мок-классы для aiohttp сессии и ответа
class MockResponse:
    def __init__(self, status):
        self.status = status
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class MockSession:
    def __init__(self, response):
        self.response = response
    def get(self, url):
        return self.response
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.mark.asyncio
async def test_proxy_alive_check():
    """
    Проверяет тест-кейс функции проверки прокси test_proxy_alive
    на примере успешного и провального запроса.
    """
    rotator = SocksProxyRotator()
    
    # Сценарий 1: Прокси успешно работает (status = 200)
    mock_session_ok = MockSession(MockResponse(200))
    with patch('aiohttp.ClientSession', return_value=mock_session_ok):
        is_alive, latency = await rotator.test_proxy_alive("socks5://1.2.3.4:1080")
        assert is_alive is True
        assert latency >= 0

    # Сценарий 2: Прокси возвращает ошибку (status = 500)
    mock_session_err = MockSession(MockResponse(500))
    with patch('aiohttp.ClientSession', return_value=mock_session_err):
        is_alive, latency = await rotator.test_proxy_alive("socks5://5.6.7.8:1080")
        assert is_alive is False

    # Сценарий 3: Возникает исключение при подключении (таймаут)
    class MockSessionException:
        async def __aenter__(self):
            raise asyncio.TimeoutError()
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    with patch('aiohttp.ClientSession', return_value=MockSessionException()):
        is_alive, latency = await rotator.test_proxy_alive("socks5://9.9.9.9:1080")
        assert is_alive is False

@pytest.mark.asyncio
async def test_get_working_proxy_selection():
    """
    Проверяет, что get_working_proxy правильно выбирает прокси с наименьшей задержкой.
    """
    rotator = SocksProxyRotator()
    rotator.cached_proxies = ["1.1.1.1:1080", "2.2.2.2:1080", "3.3.3.3:1080"]
    rotator.last_scrape_time = time.monotonic()
    
    async def mock_test(proxy_url, timeout=3.0):
        if "1.1.1.1" in proxy_url:
            return False, 0
        if "2.2.2.2" in proxy_url:
            return True, 100.0
        if "3.3.3.3" in proxy_url:
            return True, 20.0
        return False, 0
        
    with patch.object(rotator, 'test_proxy_alive', side_effect=mock_test):
        best_proxy = await rotator.get_working_proxy(max_to_check=3, batch_size=3)
        assert best_proxy == "socks5://3.3.3.3:1080"
