import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from core.handlers.status import is_task_running, get_system_status_text, cmd_status, callback_status_check

@pytest.mark.asyncio
async def test_is_task_running():
    # 1. Create a dummy coroutine and task with a specific name
    async def dummy_coro():
        await asyncio.sleep(0.5)

    task = asyncio.create_task(dummy_coro(), name="test_dummy_task_name")
    
    try:
        # Check that it detects the task running
        assert is_task_running("test_dummy_task_name") is True
        assert is_task_running("non_existent_task") is False
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Now that the task is finished/cancelled, it shouldn't be active
    assert is_task_running("test_dummy_task_name") is False


@pytest.mark.asyncio
async def test_get_system_status_text():
    # We will mock the task check and the Proxmox APIs to test text construction
    with patch("core.handlers.status.is_task_running") as mock_is_running, \
         patch("modules.proxmox.api.proxmox.proxmox", True), \
         patch("modules.proxmox.api.proxmox.get_nodes") as mock_nodes:
        
        # Setup mocks
        mock_is_running.side_effect = lambda name: name in ["monitor_lxc_resources", "monitor_lxc_traffic"]
        mock_nodes.return_value = [
            {'node': 'pve-node1', 'status': 'online', 'cpu': 0.12, 'mem': 4 * 1024**3, 'maxmem': 8 * 1024**3},
            {'node': 'pve-node2', 'status': 'offline'}
        ]
        
        status_text = await get_system_status_text()
        
        # Verify Proxmox text representation
        assert "pve-node1" in status_text
        assert "online" in status_text
        assert "offline" in status_text
        assert "pve-node2" in status_text
        
        # Verify background service status checks (resource and traffic running, others stopped)
        assert "LXC Resource Monitor" in status_text
        assert "LXC Auth Watcher" in status_text
        assert "Active IPS Engine" in status_text


@pytest.mark.asyncio
async def test_cmd_status():
    mock_message = AsyncMock()
    mock_status_msg = AsyncMock()
    mock_status_msg.message_id = 12345
    mock_message.answer.return_value = mock_status_msg
    mock_message.chat.id = 67890

    with patch("core.handlers.status.get_system_status_text", AsyncMock(return_value="Dummy Status Text")), \
         patch("modules.proxmox.monitor.utils.edit_rich_message", AsyncMock()) as mock_edit_rich:
        await cmd_status(mock_message)
        
        # Verify initial answer was sent
        mock_message.answer.assert_called_once_with("⏳ <i>Сбор информации о состоянии систем...</i>", parse_mode="HTML")
        
        # Verify edit_rich_message was called
        mock_edit_rich.assert_called_once()
        args, kwargs = mock_edit_rich.call_args
        assert kwargs.get("chat_id") == 67890
        assert kwargs.get("message_id") == 12345
        assert kwargs.get("text") == "Dummy Status Text"
        assert kwargs.get("parse_mode") == "HTML"
        assert kwargs.get("reply_markup") is not None


@pytest.mark.asyncio
async def test_callback_status_check():
    mock_callback = AsyncMock()
    mock_callback.message = AsyncMock()
    mock_callback.message.chat.id = 67890
    mock_callback.message.message_id = 12345
    
    with patch("core.handlers.status.get_system_status_text", AsyncMock(return_value="Dummy Status Text Callback")), \
         patch("modules.proxmox.monitor.utils.edit_rich_message", AsyncMock()) as mock_edit_rich:
        await callback_status_check(mock_callback)
        
        # Verify edit_rich_message was called twice (first loading, then final status)
        assert mock_edit_rich.call_count == 2
        
        # Check first call (loading status)
        first_args, first_kwargs = mock_edit_rich.call_args_list[0]
        assert first_kwargs.get("chat_id") == 67890
        assert first_kwargs.get("message_id") == 12345
        assert "Сбор информации" in first_kwargs.get("text")
        
        # Check second call (final status)
        second_args, second_kwargs = mock_edit_rich.call_args_list[1]
        assert second_kwargs.get("chat_id") == 67890
        assert second_kwargs.get("message_id") == 12345
        assert second_kwargs.get("text") == "Dummy Status Text Callback"
        assert second_kwargs.get("reply_markup") is not None
        
        # Verify callback.answer() was called at the end
        mock_callback.answer.assert_called_once()
