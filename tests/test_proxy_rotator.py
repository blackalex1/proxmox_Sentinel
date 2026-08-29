import pytest
import asyncio
import json
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


@pytest.mark.asyncio
async def test_proxy_alive_check():
    """
    Проверяет тест-кейс функции проверки прокси test_proxy_alive
    на примере успешного сокетного ответа SOCKS5 и провала.
    """
    rotator = SocksProxyRotator()

    # Сценарий 1: SOCKS5 прокси успешно отвечает (рукопожатие 0x05, 0x00 + CONNECT 0x05 0x00)
    mock_sock_ok = MagicMock()
    mock_sock_ok.recv.side_effect = [b"\x05\x00", b"\x05\x00\x00\x01\x7f\x00\x00\x01\x01\xbb"]
    with patch('socket.socket', return_value=mock_sock_ok):
        is_alive, latency = await rotator.test_proxy_alive("socks5://127.0.0.1:10808", timeout=1.0)
        assert is_alive is True
        assert latency >= 0

    # Сценарий 2: Ошибка подключения сокета (Exception)
    with patch('socket.socket', side_effect=ConnectionRefusedError("Connection refused")):
        is_alive, latency = await rotator.test_proxy_alive("socks5://127.0.0.1:10808", timeout=1.0)
        assert is_alive is False
        assert latency >= 999999


@pytest.mark.asyncio
async def test_3tier_cascade_tier1_success():
    """
    Проверяет, что при наличии рабочих нод в ТИР 1 (Черные списки),
    выбирается ТИР 1, а ТИР 2 и ТИР 3 даже не вызываются.
    """
    rotator = SocksProxyRotator()

    with patch.object(rotator, '_check_vpn_sources', AsyncMock(side_effect=[
        "socks5://127.0.0.1:10818", # Tier 1 success
        None                        # Tier 2 (should not be reached)
    ])) as mock_vpn, patch.object(rotator, '_check_socks5_sources', AsyncMock(return_value=None)) as mock_socks, \
         patch.object(rotator, '_load_cached_nodes_from_disk', return_value=[]):

        proxy = await rotator.get_working_proxy()
        assert proxy == "socks5://127.0.0.1:10818"
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
        "socks5://127.0.0.1:10818"  # Tier 2 success
    ])) as mock_vpn, patch.object(rotator, '_check_socks5_sources', AsyncMock(return_value=None)) as mock_socks, \
         patch.object(rotator, '_load_cached_nodes_from_disk', return_value=[]):

        proxy = await rotator.get_working_proxy()
        assert proxy == "socks5://127.0.0.1:10818"
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
    ])) as mock_vpn, patch.object(rotator, '_check_socks5_sources', AsyncMock(return_value="socks5://198.51.100.1:1080")) as mock_socks, \
         patch.object(rotator, '_load_cached_nodes_from_disk', return_value=[]):

        proxy = await rotator.get_working_proxy()
        assert proxy == "socks5://198.51.100.1:1080"
        assert mock_vpn.call_count == 2
        mock_socks.assert_called_once()


@pytest.mark.asyncio
async def test_passive_refresh_disk_cache():
    """
    Проверяет, что refresh_disk_cache пассивно сохраняет списки с Git на диск
    без вызова активного пакетного сканирования портов.
    """
    rotator = SocksProxyRotator()
    sample_nodes = ["vless://uuid@host:443#sample1", "ss://YWVzLTEyOC1nY206cGFzcw@1.2.3.4:8388#sample2"]

    with patch.object(rotator, '_fetch_single_source', AsyncMock(return_value=sample_nodes)), \
         patch.object(rotator, '_save_working_nodes_to_disk') as mock_save:
        count = await rotator.refresh_disk_cache()
        assert count == 2
        mock_save.assert_called_once_with(sample_nodes)


@pytest.mark.asyncio
async def test_start_or_reload_singbox_tunnel_passthrough(tmp_path):
    """
    Проверяет, что start_or_reload_singbox_tunnel напрямую и без искажений
    записывает JSON-конфиг ядра в singbox_failover.json и запускает процесс.
    """
    rotator = SocksProxyRotator()

    raw_cfg = {
        "dns": {
            "servers": [
                {
                    "tag": "dns-remote",
                    "address": "https://1.1.1.1/dns-query",
                    "detour": "proxy"
                }
            ]
        },
        "inbounds": [{"type": "socks", "tag": "socks-in", "listen_port": 10818}]
    }
    raw_cfg_str = json.dumps(raw_cfg)

    written_content = None
    def mock_open_file(path, mode="r", *args, **kwargs):
        nonlocal written_content
        m = MagicMock()
        def write_side(data):
            nonlocal written_content
            written_content = data
        m.__enter__.return_value.write.side_effect = write_side
        return m

    with patch.object(rotator, '_find_proxy_engine_bin', return_value=("sing-box", "singbox")), \
         patch('builtins.open', side_effect=mock_open_file), \
         patch('subprocess.Popen') as mock_popen, \
         patch.object(rotator, 'test_proxy_alive', AsyncMock(return_value=(True, 20.0))):

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdout.readline.return_value = ""
        mock_popen.return_value = mock_proc

        ok = await rotator.start_or_reload_singbox_tunnel(raw_cfg_str, port=10818)
        assert ok is True
        assert written_content == raw_cfg_str


@pytest.mark.asyncio
async def test_node_testing_and_activation_with_core():
    """
    Проверяет связку _test_and_activate_nodes с sentinel_core_bridge:
    передачу списка URI в check_proxies, проверку success и запуск sing-box.
    """
    rotator = SocksProxyRotator()
    sample_uris = ["vless://uuid@1.2.3.4:443?type=tcp&security=reality#Node1"]

    mock_check_results = [
        {
            "proxyUrl": sample_uris[0],
            "protocol": "vless",
            "name": "Node1",
            "success": True,
            "latencyMs": 45.0
        }
    ]

    mock_parsed_profile = {
        "protocol": "vless",
        "address": "1.2.3.4",
        "port": 443,
        "name": "Node1"
    }

    with patch('core.sentinel_core_bridge.check_proxies', return_value=mock_check_results) as mock_check, \
         patch('core.proxy_rotator.parse_vpn_uri', return_value=mock_parsed_profile), \
         patch('core.sentinel_core_bridge.build_failover_client_config', return_value='{"dns":{}}'), \
         patch.object(rotator, 'start_or_reload_singbox_tunnel', AsyncMock(return_value=True)) as mock_tunnel, \
         patch.object(rotator, '_save_working_nodes_to_disk'):

        proxy_url = await rotator._test_and_activate_nodes(sample_uris, tier_name="TestTier")
        assert proxy_url == "socks5://127.0.0.1:10818"
        mock_check.assert_called_once()
        # Проверяем, что в check_proxies передан список URI
        passed_uris = mock_check.call_args[0][0]
        assert passed_uris == sample_uris
        mock_tunnel.assert_called_once()


@pytest.mark.asyncio
async def test_proxy_selection_scope_and_router_bypass():
    """
    Проверяет, что proxy_selection_scope активирует временное окно игнорирования,
    и check_is_bot_or_admin распознает трафик хоста как легитимный во время подбора.
    """
    from modules.proxmox.monitor.state import proxy_selection_scope, is_proxy_selection_in_progress
    from modules.router.monitor.helpers import check_is_bot_or_admin

    # До входа в scope
    assert is_proxy_selection_in_progress() is False

    async with proxy_selection_scope(duration=10.0):
        assert is_proxy_selection_in_progress() is True
        # Локальный хост во время подбора прокси признается легитимным
        is_trusted = await check_is_bot_or_admin("127.0.0.1", 54321, "8.8.8.8", 443)
        assert is_trusted is True

