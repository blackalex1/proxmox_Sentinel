import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from core.handlers.base import process_terminate_ssh

@pytest.mark.asyncio
async def test_process_terminate_ssh_local_success():
    # Setup mock CallbackQuery and Message
    mock_message = AsyncMock()
    mock_message.html_text = "🖥 <b>Успешная SSH авторизация на Хосте!</b>\n\n🕒 Время: <code>20:19:11</code>"
    mock_message.text = "🖥 Успешная SSH авторизация на Хосте!\n\nВремя: 20:19:11"
    
    mock_callback = AsyncMock()
    mock_callback.data = "termssh:local:98765"
    mock_callback.message = mock_message
    mock_callback.answer = AsyncMock()
    
    # Mock asyncio.create_subprocess_exec
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"")
    mock_proc.returncode = 0
    
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)) as mock_exec:
        await process_terminate_ssh(mock_callback)
        
        # Verify subprocess was called with kill -9
        mock_exec.assert_called_once_with(
            "kill", "-9", "98765",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        # Verify alert response was sent to Telegram
        mock_callback.answer.assert_called_once_with("SSH-сессия успешно сброшена!", show_alert=True)
        # Verify the original message was updated with status and keyboard removed
        mock_message.edit_text.assert_called_once()
        args, kwargs = mock_message.edit_text.call_args
        assert "❌ SSH-сессия сброшена пользователем через Telegram" in kwargs["text"]
        assert kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_process_terminate_ssh_lxc_already_dead():
    # Setup mock CallbackQuery and Message
    mock_message = AsyncMock()
    mock_message.html_text = "🔒 <b>Успешная SSH авторизация в LXC!</b>\n\n🕒 Время: <code>20:19:11</code>"
    mock_message.text = "🔒 Успешная SSH авторизация в LXC!\n\nВремя: 20:19:11"
    
    mock_callback = AsyncMock()
    mock_callback.data = "termssh:lxc_101:54321"
    mock_callback.message = mock_message
    mock_callback.answer = AsyncMock()
    
    # Mock asyncio.create_subprocess_exec to fail with "No such process"
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"kill: kill 54321 failed: No such process")
    mock_proc.returncode = 1
    
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)) as mock_exec:
        await process_terminate_ssh(mock_callback)
        
        # Verify pct exec kill -9 was called
        mock_exec.assert_called_once_with(
            "pct", "exec", "101", "--", "kill", "-9", "54321",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        # Verify alert response says session already closed
        mock_callback.answer.assert_called_once_with("Сессия уже закрыта или не найдена.", show_alert=True)
        # Verify the message was edited
        mock_message.edit_text.assert_called_once()
        args, kwargs = mock_message.edit_text.call_args
        assert "🔒 Сессия уже была закрыта или не найдена" in kwargs["text"]
        assert kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_process_terminate_ssh_remote_vps():
    # Setup mock CallbackQuery and Message
    mock_message = AsyncMock()
    mock_message.html_text = "🖥 <b>[VPS SSH Security: 198.51.100.42] Успешный вход по SSH!</b>"
    mock_message.text = "🖥 [VPS SSH Security: 198.51.100.42] Успешный вход по SSH!"
    
    mock_callback = AsyncMock()
    mock_callback.data = "termssh:198.51.100.42:3322"
    mock_callback.message = mock_message
    mock_callback.answer = AsyncMock()
    
    # Mock settings.remote_servers
    mock_server = {'ip': '198.51.100.42', 'user': 'root', 'key': 'config/id_rsa_remote'}
    
    with patch("core.config.settings.remote_servers", [mock_server]), \
         patch("modules.proxmox.monitor.remote.ssh.run_remote_ssh_cmd", AsyncMock(return_value=(True, "", ""))) as mock_remote_ssh:
         
        await process_terminate_ssh(mock_callback)
        
        # Verify remote ssh command was run
        mock_remote_ssh.assert_called_once_with(mock_server, ["kill", "-9", "3322"])
        # Verify success alerts
        mock_callback.answer.assert_called_once_with("SSH-сессия успешно сброшена!", show_alert=True)
        mock_message.edit_text.assert_called_once()
