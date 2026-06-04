import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from core.handlers.base import process_terminate_ssh, process_ban_ssh_key, get_kill_tree_cmd, get_ban_key_tree_cmd

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
        
        # Verify subprocess was called with kill tree script
        mock_exec.assert_called_once_with(
            "sh", "-c", get_kill_tree_cmd(98765),
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
        
        # Verify pct exec kill tree script was called
        mock_exec.assert_called_once_with(
            "pct", "exec", "101", "--", "sh", "-c", get_kill_tree_cmd(54321),
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
    mock_message.html_text = "🖥 <b>[VPS SSH Security: 194.87.29.14] Успешный вход по SSH!</b>"
    mock_message.text = "🖥 [VPS SSH Security: 194.87.29.14] Успешный вход по SSH!"
    
    mock_callback = AsyncMock()
    mock_callback.data = "termssh:194.87.29.14:3322"
    mock_callback.message = mock_message
    mock_callback.answer = AsyncMock()
    
    # Mock settings.remote_servers
    mock_server = {'ip': '194.87.29.14', 'user': 'root', 'key': 'config/id_rsa_remote'}
    
    with patch("core.config.settings.remote_servers", [mock_server]), \
         patch("modules.proxmox.monitor.remote.ssh.run_remote_ssh_cmd", AsyncMock(return_value=(True, "", ""))) as mock_remote_ssh:
         
        await process_terminate_ssh(mock_callback)
        
        # Verify remote ssh command was run with kill tree script
        mock_remote_ssh.assert_called_once_with(mock_server, [get_kill_tree_cmd(3322)])
        # Verify success alerts
        mock_callback.answer.assert_called_once_with("SSH-сессия успешно сброшена!", show_alert=True)
        mock_message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_process_ban_ssh_key_local_success():
    # Setup mock CallbackQuery and Message
    mock_message = AsyncMock()
    mock_message.html_text = "🖥 <b>Успешная SSH авторизация на Хосте!</b>"
    mock_message.text = "🖥 Успешная SSH авторизация на Хосте!"
    
    mock_callback = AsyncMock()
    mock_callback.data = "bankey:local:98765"
    mock_callback.message = mock_message
    mock_callback.answer = AsyncMock()
    
    # Mock cache in database
    mock_db_cache = {"local:98765": ["SHA256:targetfingerprint", "root"]}
    
    # Mock subprocess runs (first kill, then ban script)
    mock_proc_kill = AsyncMock()
    mock_proc_kill.wait = AsyncMock(return_value=0)
    
    mock_proc_ban = AsyncMock()
    mock_proc_ban.communicate.return_value = (b"DELETED_KEY:/root/.ssh/authorized_keys:ssh-rsa AAA...\nSUCCESS", b"")
    mock_proc_ban.returncode = 0
    
    with patch("core.db.get_state", AsyncMock(return_value=mock_db_cache)), \
         patch("asyncio.create_subprocess_exec") as mock_exec:
         
        mock_exec.side_effect = [mock_proc_kill, mock_proc_ban]
        
        await process_ban_ssh_key(mock_callback)
        
        # Verify it called kill first
        mock_exec.assert_any_call("sh", "-c", get_kill_tree_cmd(98765))
        
        # Verify it called ban shell command on the host
        mock_exec.assert_any_call(
            "sh", "-c", get_ban_key_tree_cmd("SHA256:targetfingerprint"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Verify success alert and text edits
        mock_callback.answer.assert_called_once_with("SSH-ключ успешно заблокирован и удален!", show_alert=True)
        mock_message.edit_text.assert_called_once()
        args, kwargs = mock_message.edit_text.call_args
        assert "🚫 SSH-ключ (...tfingerprint) удален из authorized_keys и сессия сброшена" in kwargs["text"]
        assert kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_process_ban_ssh_key_remote_vps():
    # Setup mock CallbackQuery and Message
    mock_message = AsyncMock()
    mock_message.html_text = "🖥 <b>[VPS SSH Security: 194.87.29.14] Успешный вход по SSH!</b>"
    mock_message.text = "🖥 [VPS SSH Security: 194.87.29.14] Успешный вход по SSH!"
    
    mock_callback = AsyncMock()
    mock_callback.data = "bankey:194.87.29.14:3322"
    mock_callback.message = mock_message
    mock_callback.answer = AsyncMock()
    
    # Mock cache in database
    mock_db_cache = {"194.87.29.14:3322": ["SHA256:targetfingerprint", "root"]}
    mock_server = {'ip': '194.87.29.14', 'user': 'root', 'key': 'config/id_rsa_remote'}
    
    with patch("core.db.get_state", AsyncMock(return_value=mock_db_cache)), \
         patch("core.config.settings.remote_servers", [mock_server]), \
         patch("modules.proxmox.monitor.remote.ssh.run_remote_ssh_cmd") as mock_remote_ssh:
         
        mock_remote_ssh.side_effect = [
            (True, "", ""),  # Result of kill
            (True, "DELETED_KEY:/root/.ssh/authorized_keys:ssh-rsa AAA...\nSUCCESS", "")  # Result of ban script
        ]
        
        await process_ban_ssh_key(mock_callback)
        
        # Verify remote ssh command run
        mock_remote_ssh.assert_any_call(mock_server, [get_kill_tree_cmd(3322)])
        # Verify ban script was run remotely
        mock_remote_ssh.assert_any_call(
            mock_server,
            [get_ban_key_tree_cmd("SHA256:targetfingerprint")]
        )
        
        # Verify success notifications
        mock_callback.answer.assert_called_once_with("SSH-ключ успешно заблокирован и удален!", show_alert=True)
        mock_message.edit_text.assert_called_once()
