import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_ssh_run_command_mocked():
    # Создаем моки для asyncssh
    mock_result = AsyncMock()
    mock_result.exit_status = 0
    mock_result.stdout = "mongosh success response"
    mock_result.stderr = ""
    
    mock_conn = AsyncMock()
    mock_conn.run.return_return = mock_result
    mock_conn.run.return_value = mock_result
    mock_conn.is_closed.return_value = False
    
    with patch("asyncssh.connect", AsyncMock(return_value=mock_conn)) as mock_connect:
        from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
        
        server = {
            'ip': '192.168.1.50',
            'user': 'root',
            'key': 'config/dummy_key'
        }
        
        success, stdout, stderr = await run_remote_ssh_cmd(server, ["echo test"])
        
        # Проверяем корректность вызова и возвращаемых значений
        assert success is True
        assert stdout == "mongosh success response"
        assert stderr == ""
        
        mock_connect.assert_called_once_with(
            '192.168.1.50',
            username='root',
            client_keys=['config/dummy_key'],
            known_hosts=None,
            connect_timeout=10,
            keepalive_interval=30,
            keepalive_count_max=3
        )
        mock_conn.run.assert_called_once_with("echo test", check=False)
