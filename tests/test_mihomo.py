import pytest
from unittest.mock import AsyncMock, patch
import datetime

@pytest.mark.asyncio
async def test_handle_mihomo_log_line_sensitive_ipv4():
    from modules.mihomo.monitor import handle_mihomo_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    
    lxc_alert_throttle.clear()
    
    # TCP-соединение на sensitive порт 22
    payload = "[TCP] 192.168.1.150:54321 --> 203.0.113.100:22 match Direct"
    
    with patch("modules.mihomo.monitor.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_mihomo_log_line(payload)
        
        # Проверяем, что алерт безопасности БЫЛ вызван
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Router Security: Mihomo" in alert_text
        assert "192.168.1.150:54321" in alert_text
        assert "203.0.113.100:22" in alert_text

@pytest.mark.asyncio
async def test_handle_mihomo_log_line_sensitive_ipv6():
    from modules.mihomo.monitor import handle_mihomo_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    
    lxc_alert_throttle.clear()
    
    # UDP-соединение на sensitive порт 8006 (Proxmox VE)
    payload = "[UDP] [2001:db8::1]:12345 --> [2001:db8::2]:8006 match Rule"
    
    with patch("modules.mihomo.monitor.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_mihomo_log_line(payload)
        
        # Проверяем, что IPv6 адрес корректно распарсен и алерт отправлен
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Router Security: Mihomo" in alert_text
        assert "2001:db8::1:12345" in alert_text
        assert "2001:db8::2:8006" in alert_text

@pytest.mark.asyncio
async def test_handle_mihomo_log_line_safe_port():
    from modules.mihomo.monitor import handle_mihomo_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    
    lxc_alert_throttle.clear()
    
    # Соединение на безопасный порт 443
    payload = "[TCP] 192.168.1.150:54321 --> 1.1.1.1:443 match Proxy"
    
    with patch("modules.mihomo.monitor.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_mihomo_log_line(payload)
        
        # Проверяем, что алерт не отправлялся для безопасных портов
        mock_alert.assert_not_called()
    
@pytest.mark.asyncio
async def test_handle_mihomo_kill_connection_success():
    from modules.mihomo.handlers import handle_mihomo_kill_connection
    from unittest.mock import MagicMock
    
    # Мокаем CallbackQuery
    mock_callback = AsyncMock()
    mock_callback.data = "mihomo_kill:dummy-uuid-12345"
    
    mock_msg = MagicMock()
    mock_msg.text = "🚨 [Router Security: Mihomo] Обнаружен доступ к чувствительному порту!"
    mock_msg.edit_text = AsyncMock()
    mock_callback.message = mock_msg
    
    # Мокаем close_mihomo_connection, возвращающий True
    with patch("modules.mihomo.handlers.close_mihomo_connection", AsyncMock(return_value=True)) as mock_close:
        await handle_mihomo_kill_connection(mock_callback)
        
        # Проверяем успешный вызов разрыва
        mock_close.assert_called_once_with("dummy-uuid-12345")
        # Проверяем, что callback-запрос был успешно отвечен
        mock_callback.answer.assert_called_once_with("✅ Соединение успешно разорвано!", show_alert=True)
        # Проверяем, что текст сообщения был обновлен
        mock_msg.edit_text.assert_called_once()
        new_text = mock_msg.edit_text.call_args[0][0]
        assert "СОЕДИНЕНИЕ РАЗОРВАНО АДМИНИСТРАТОРОМ" in new_text


@pytest.mark.asyncio
async def test_handle_mihomo_block_ip_success():
    from modules.mihomo.handlers import handle_mihomo_block_ip
    from unittest.mock import MagicMock
    
    mock_callback = AsyncMock()
    mock_callback.data = "mihomo_block:192.0.2.99"
    
    mock_msg = MagicMock()
    mock_msg.text = "🚨 [Router Security: Mihomo] Обнаружен доступ к чувствительному порту!"
    mock_msg.edit_text = AsyncMock()
    mock_callback.message = mock_msg
    
    with patch("modules.mihomo.handlers.ban_router_ip", AsyncMock(return_value=(True, "Success"))) as mock_ban:
        await handle_mihomo_block_ip(mock_callback)
        
        mock_ban.assert_called_once_with("192.0.2.99")
        mock_callback.answer.assert_called_once_with("🛑 IP 192.0.2.99 успешно заблокирован на роутере!", show_alert=True)
        mock_msg.edit_text.assert_called_once()
        new_text = mock_msg.edit_text.call_args[0][0]
        assert "УСТРОЙСТВО 192.0.2.99 ЗАБЛОКИРОВАНО НА РОУТЕРЕ" in new_text
 
 
@pytest.mark.asyncio
async def test_handle_mihomo_unblock_ip_success():
    from modules.mihomo.handlers import handle_mihomo_unblock_ip
    from unittest.mock import MagicMock
    
    mock_callback = AsyncMock()
    mock_callback.data = "mihomo_unblock:192.0.2.99"
    
    mock_msg = MagicMock()
    mock_msg.text = "🚨 [Router Security: Mihomo] Обнаружен доступ к чувствительному порту!\n\n🛑 <b>УСТРОЙСТВО 192.0.2.99 ЗАБЛОКИРОВАНО НА РОУТЕРЕ!</b>"
    mock_msg.edit_text = AsyncMock()
    mock_callback.message = mock_msg
    
    with patch("modules.mihomo.handlers.unban_router_ip", AsyncMock(return_value=(True, "Success"))) as mock_unban:
        await handle_mihomo_unblock_ip(mock_callback)
        
        mock_unban.assert_called_once_with("192.0.2.99")
        mock_callback.answer.assert_called_once_with("🟢 Блокировка с IP 192.0.2.99 снята!", show_alert=True)
        mock_msg.edit_text.assert_called_once()
        new_text = mock_msg.edit_text.call_args[0][0]
        assert "ЗАБЛОКИРОВАНО" not in new_text


@pytest.mark.asyncio
async def test_handle_mihomo_log_line_auto_ban():
    from modules.mihomo.monitor import handle_mihomo_log_line, recent_mihomo_violations
    from core.config import settings
    
    # Включаем auto-ban и SSH в моке настроек
    original_ssh = settings.router_ssh_enable
    original_auto = settings.mihomo_auto_ban
    original_max = settings.mihomo_max_violations
    
    settings.router_ssh_enable = True
    settings.mihomo_auto_ban = True
    settings.mihomo_max_violations = 3
    
    recent_mihomo_violations.clear()
    
    payload = "[TCP] 192.168.1.150:54321 --> 203.0.113.100:22 match Direct"
    
    try:
        with patch("modules.mihomo.router.ban_router_ip", AsyncMock(return_value=(True, "Blocked"))) as mock_ban, \
             patch("modules.mihomo.monitor.send_alert_to_admins", AsyncMock()) as mock_alert:
             
            # Попытка 1: Просто предупреждение
            await handle_mihomo_log_line(payload)
            assert len(recent_mihomo_violations["192.168.1.150"]) == 1
            mock_ban.assert_not_called()
            
            # Попытка 2: Предупреждение (но троттлинг алертов сработает на повторные вызовы одного хоста, счетчик нарушений увеличится)
            # Вручную добавим в violations для симуляции
            import time
            recent_mihomo_violations["192.168.1.150"].append(time.time())
            
            # Попытка 3: Автобан срабатывает!
            await handle_mihomo_log_line(payload)
            
            # Проверяем, что бан был вызван автоматически для этого IP
            mock_ban.assert_called_once_with("192.168.1.150")
            assert mock_alert.call_count == 2
            alert_text = mock_alert.call_args[0][0]
            assert "Auto-Block" in alert_text
            assert "Устройство заблокировано автоматически" in alert_text
            
            # Нарушения сброшены после бана
            assert len(recent_mihomo_violations.get("192.168.1.150", [])) == 0
    finally:
        settings.router_ssh_enable = original_ssh
        settings.mihomo_auto_ban = original_auto
        settings.mihomo_max_violations = original_max



