import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch, AsyncMock

from core.config import settings
from core.proxy_rotator import SocksProxyRotator

def test_proxy_rotation_config():
    """
    Проверяет, что настройки ротации прокси добавлены в Pydantic Settings
    и имеют корректный логический тип (bool).
    """
    assert hasattr(settings, 'enable_free_proxy_rotation')
    assert isinstance(settings.enable_free_proxy_rotation, bool)

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
async def test_3tier_cascade_tier1_success():
    """
    Проверяет, что при наличии рабочих нод в ТИР 1 (Черные списки),
    выбирается ТИР 1, а ТИР 2 и ТИР 3 даже не вызываются.
    """
    rotator = SocksProxyRotator()

    with patch.object(rotator, '_check_vpn_sources', AsyncMock(side_effect=[
        "socks5://127.0.0.1:10808", # Tier 1 success
        None                        # Tier 2 (should not be reached)
    ])) as mock_vpn, patch.object(rotator, '_check_socks5_sources', AsyncMock(return_value=None)) as mock_socks:

        proxy = await rotator.get_working_proxy()
        assert proxy == "socks5://127.0.0.1:10808"
        assert mock_vpn.call_count == 1
        mock_socks.assert_not_called()

@pytest.mark.asyncio
async def test_3tier_cascade_tier2_fallback():
    """
    Проверяет, что если ТИР 1 пуст, срабатывает ТИР 2 (Белые списки),
    а ТИР 3 (SOCKS5) не вызывается.
    """
    rotator = SocksProxyRotator()

    with patch.object(rotator, '_check_vpn_sources', AsyncMock(side_effect=[
        None,                        # Tier 1 failed
        "socks5://127.0.0.1:10808"  # Tier 2 success
    ])) as mock_vpn, patch.object(rotator, '_check_socks5_sources', AsyncMock(return_value=None)) as mock_socks:

        proxy = await rotator.get_working_proxy()
        assert proxy == "socks5://127.0.0.1:10808"
        assert mock_vpn.call_count == 2
        mock_socks.assert_not_called()

@pytest.mark.asyncio
async def test_3tier_cascade_tier3_lazy_socks_fallback():
    """
    Проверяет, что только если и ТИР 1, и ТИР 2 недоступны,
    запускается парсинг и проверка ТИР 3 (SOCKS5).
    """
    rotator = SocksProxyRotator()

    with patch.object(rotator, '_check_vpn_sources', AsyncMock(side_effect=[
        None, # Tier 1 failed
        None  # Tier 2 failed
    ])) as mock_vpn, patch.object(rotator, '_check_socks5_sources', AsyncMock(return_value="socks5://198.51.100.1:1080")) as mock_socks:

        proxy = await rotator.get_working_proxy()
        assert proxy == "socks5://198.51.100.1:1080"
        assert mock_vpn.call_count == 2
        mock_socks.assert_called_once()
