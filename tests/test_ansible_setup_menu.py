import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import CallbackQuery
from modules.ansible.handlers.setup import process_ansible_setup_menu
from modules.ansible.keyboards import get_ansible_main_keyboard

@pytest.mark.asyncio
async def test_ansible_setup_menu_callback():
    mock_message = AsyncMock()
    mock_callback = AsyncMock(spec=CallbackQuery)
    mock_callback.data = "ansible_setup_env"
    mock_callback.message = mock_message
    mock_callback.answer = AsyncMock()

    with patch("modules.ansible.handlers.setup.check_and_generate_ansible_keys"), \
         patch("modules.ansible.handlers.setup.check_host_ansible_status", AsyncMock(return_value=True)), \
         patch("modules.ansible.handlers.setup.check_lxc_ansible_status", AsyncMock(return_value=True)), \
         patch("modules.proxmox.api.proxmox.proxmox") as mock_pve:
        
        mock_pve.cluster.resources.get.return_value = [
            {'type': 'lxc', 'status': 'running', 'vmid': 102, 'name': 'torserver', 'node': 'proxmox'}
        ]
        
        await process_ansible_setup_menu(mock_callback)
        
        mock_callback.answer.assert_called_once_with("Проверяю статус хостов...")
        assert mock_message.edit_text.call_count >= 1

def test_ansible_main_keyboard_has_setup_env():
    kb = get_ansible_main_keyboard()
    button_callbacks = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "ansible_setup_env" in button_callbacks
