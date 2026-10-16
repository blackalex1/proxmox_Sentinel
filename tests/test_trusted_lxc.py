import pytest
from unittest.mock import AsyncMock, MagicMock
from core.db import add_trusted_vpn_vmid, remove_trusted_vpn_vmid, get_trusted_vpn_vmids
from modules.proxmox.monitor.traffic.parser import (
    is_vpn_vmid,
    classify_connection,
    init_trusted_vpn_vmids_cache,
    update_trusted_vpn_vmids_cache,
)

@pytest.mark.asyncio
async def test_trusted_vpn_vmid_db_and_cache():
    # Изначально очищаем
    await remove_trusted_vpn_vmid(110)
    await update_trusted_vpn_vmids_cache()
    assert not is_vpn_vmid(110)

    # Добавляем 110
    await add_trusted_vpn_vmid(110)
    await update_trusted_vpn_vmids_cache()
    assert is_vpn_vmid(110)
    vmids = await get_trusted_vpn_vmids()
    assert 110 in vmids

    # Удаляем 110
    await remove_trusted_vpn_vmid(110)
    await update_trusted_vpn_vmids_cache()
    assert not is_vpn_vmid(110)
    vmids = await get_trusted_vpn_vmids()
    assert 110 not in vmids

@pytest.mark.asyncio
async def test_trusted_lxc_traffic_classification():
    # 1. Когда 110 НЕ в доверенных:
    await remove_trusted_vpn_vmid(110)
    await update_trusted_vpn_vmids_cache()

    event_p2p = {
        'vmid': 110,
        'direction': 'OUT',
        'proto': 'TCP',
        'src': '192.168.1.110',
        'dst': '198.51.100.55',
        'spt': 41234,
        'dpt': 52777
    }
    risk, label, desc = classify_connection(event_p2p)
    # Для обычного контейнера нетипичный исходящий порт — WARNING
    assert risk == 'WARNING'
    assert 'Нетипичный исходящий порт' in label

    # 2. Добавляем 110 в доверенные узлы (VPN/P2P режим):
    await add_trusted_vpn_vmid(110)
    await update_trusted_vpn_vmids_cache()

    # Тот же P2P запрос на 52777 теперь классифицируется как безопасный INFO (нет алертов)
    risk_trusted, label_trusted, _ = classify_connection(event_p2p)
    assert risk_trusted == 'INFO'

    # 3. Но если из 110 пойдет запрос на sensitive порт (22 SSH):
    event_sensitive = {
        'vmid': 110,
        'direction': 'OUT',
        'proto': 'TCP',
        'src': '192.168.1.110',
        'dst': '198.51.100.55',
        'spt': 41234,
        'dpt': 22
    }
    risk_sensitive, label_sensitive, _ = classify_connection(event_sensitive)
    # Чувствительные порты по-прежнему строго защищены (CRITICAL)
    assert risk_sensitive == 'CRITICAL'
    assert 'sensitive' in label_sensitive.lower()

    # Очистка
    await remove_trusted_vpn_vmid(110)
    await update_trusted_vpn_vmids_cache()

@pytest.mark.asyncio
async def test_alert_callbacks():
    from core.handlers.whitelist import cb_trust_lxc, cb_untrust_lxc, cb_quick_block_ip, cb_copy_ip
    
    # Тест trust_lxc
    cb_mock = MagicMock()
    cb_mock.data = "trust_lxc:110"
    cb_mock.message = MagicMock()
    cb_mock.message.html_text = "Alert"
    cb_mock.message.text = "Alert"
    cb_mock.message.edit_text = AsyncMock()
    cb_mock.answer = AsyncMock()

    await cb_trust_lxc(cb_mock)
    assert is_vpn_vmid(110)
    cb_mock.answer.assert_called_once()
    assert "добавлен в доверенные" in cb_mock.answer.call_args[0][0]

    # Тест untrust_lxc
    cb_mock.data = "untrust_lxc:110"
    cb_mock.answer.reset_mock()
    await cb_untrust_lxc(cb_mock)
    assert not is_vpn_vmid(110)
    cb_mock.answer.assert_called_once()
    assert "удален из доверенных" in cb_mock.answer.call_args[0][0]

    # Тест copy:ip
    cb_mock.data = "copy:ip:198.51.100.55"
    cb_mock.answer.reset_mock()
    await cb_copy_ip(cb_mock)
    cb_mock.answer.assert_called_once_with("198.51.100.55", show_alert=True)


def test_find_kernel_log_path():
    from modules.proxmox.monitor.traffic.parser import find_kernel_log_path
    from unittest.mock import patch

    with patch("os.path.exists", side_effect=lambda p: p == "/var/log/syslog"):
        assert find_kernel_log_path() == "/var/log/syslog"

    with patch("os.path.exists", return_value=False):
        assert find_kernel_log_path() is None
