import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from core.spectre_client import parse_env_content, SpectrePanelInstance, SpectreClientManager, spectre_manager
from core.handlers.spectre import cmd_panel, cmd_backup, cmd_status_spectre, cmd_my_spectre, cmd_ban_client, cmd_unban_client


def test_parse_env_content():
    content = """
    # This is a comment
    PANEL_PORT=2053
    PANEL_SECRET_PATH="my_secret_path"
    API_TOKEN='some_api_token'
    """
    config = parse_env_content(content)
    assert config["PANEL_PORT"] == "2053"
    assert config["PANEL_SECRET_PATH"] == "my_secret_path"
    assert config["API_TOKEN"] == "some_api_token"

@pytest.mark.asyncio
async def test_spectre_panel_request():
    panel = SpectrePanelInstance("Test", "http://127.0.0.1:2053", "token", "ui", "lxc", "999")
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"success": True, "data": "ok"})
    
    mock_request_ctx = MagicMock()
    mock_request_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_request_ctx.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = MagicMock()
    mock_session.request = MagicMock(return_value=mock_request_ctx)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        success, res = await panel.request("GET", "/api/test")
        assert success is True
        assert res["success"] is True
        assert res["data"] == "ok"

@pytest.mark.asyncio
async def test_discover_panels():
    manager = SpectreClientManager()
    
    # Mock Proxmox API
    mock_proxmox = MagicMock()
    mock_proxmox.get_nodes.return_value = [{'node': 'pve1'}]
    mock_proxmox.get_vms.return_value = [{'type': 'lxc', 'status': 'running', 'vmid': 999, 'name': 'VPN-LXC'}]
    mock_proxmox.get_lxc_ip.return_value = '10.0.0.99'
    
    # Mock subprocess exec (for cat command in LXC)
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (
        b"PANEL_PORT=2053\nAPI_TOKEN=lxc_token\nPANEL_SECRET_PATH=secret",
        b""
    )
    
    # Mock remote VPS discovery
    mock_server = {'ip': '1.1.1.1', 'user': 'root', 'key': 'key_path'}
    
    with patch("modules.proxmox.api.proxmox", mock_proxmox), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
         patch("core.config.settings.proxmox_host", "192.168.1.100:8006"), \
         patch("core.config.settings.remote_servers", [mock_server]), \
         patch("core.spectre_client.manager.probe_panel_url", AsyncMock(side_effect=lambda ip, port: f"http://{ip}:{port}")), \
         patch("modules.proxmox.monitor.remote.ssh.run_remote_ssh_cmd", AsyncMock(return_value=(
             True,
             "PANEL_PORT=15000\nAPI_TOKEN=vps_token\nPANEL_SECRET_PATH=ui",
             ""
         ))):
         
        await manager.discover_panels()
        
        # Verify both LXC and VPS panels were discovered
        assert len(manager.panels) == 2
        assert "lxc_999" in manager.panels
        assert "vps_1.1.1.1" in manager.panels
        
        # Check details
        lxc_p = manager.panels["lxc_999"]
        assert lxc_p.url == "http://10.0.0.99:2053"
        assert lxc_p.token == "lxc_token"
        assert lxc_p.secret_path == "secret"
        
        vps_p = manager.panels["vps_1.1.1.1"]
        assert vps_p.url == "http://1.1.1.1:15000"
        assert vps_p.token == "vps_token"
        assert vps_p.secret_path == "ui"

@pytest.mark.asyncio
async def test_spectre_handlers_panel(monkeypatch):
    mock_message = AsyncMock()
    
    # Setup mock panels
    panel1 = SpectrePanelInstance("Panel 1", "http://10.0.0.99:2053", "token1", "ui", "lxc", "999")
    spectre_manager.panels = {"lxc_999": panel1}
    
    # Test single panel handler
    await cmd_panel(mock_message)
    mock_message.reply.assert_called_once()
    args, kwargs = mock_message.reply.call_args
    assert "Panel 1" in args[0]
    assert kwargs.get("reply_markup") is not None
    
    # Test multiple panels handler
    mock_message.reply.reset_mock()
    panel2 = SpectrePanelInstance("Panel 2", "http://1.1.1.1:15000", "token2", "ui", "vps", "1.1.1.1")
    spectre_manager.panels = {"lxc_999": panel1, "vps_1.1.1.1": panel2}
    
    await cmd_panel(mock_message)
    mock_message.reply.assert_called_once()
    args, kwargs = mock_message.reply.call_args
    assert "Выберите Spectre Panel" in args[0]
    assert kwargs.get("reply_markup") is not None

@pytest.mark.asyncio
async def test_two_phase_ips_success(monkeypatch):
    """
    Интеграционный тест успешного сценария двухфазного IPS:
    1. Обнаружение атаки на VPS по порту 22.
    2. Временная блокировка туннеля Hysteria.
    3. Асинхронное расследование, которое находит конкретного Xray-клиента на LXC.
    4. Перманентный бан Xray-клиента.
    5. Снятие блокировки с туннеля Hysteria.
    """
    from core.spectre_client import SpectrePanelInstance, spectre_manager
    from modules.proxmox.monitor.remote.traffic import handle_remote_traffic_line, recent_remote_traffic_alerts
    
    # Сбрасываем кэш троттлинга
    recent_remote_traffic_alerts.clear()
    
    from core.config import settings
    monkeypatch.setattr(settings, "transit_tunnels", ["bot", "tunnel@hysteria.com"])
    
    # 1. Настраиваем фейковые панели
    lxc_panel = SpectrePanelInstance("LXC Panel", "http://127.0.0.1:20530", "lxc_token", "ui", "lxc", "999")
    vps_panel = SpectrePanelInstance("VPS Panel", "http://127.0.0.1:15000", "vps_token", "ui", "vps", "1.1.1.1")
    
    spectre_manager.panels = {
        "lxc_999": lxc_panel,
        "vps_1.1.1.1": vps_panel
    }
    
    api_calls = []
    
    async def mock_request(self, method, path, **kwargs):
        api_calls.append((self.name, method, path, kwargs))
        if path == "/api/security/disable-client":
            email = kwargs.get("data", {}).get("email")
            return True, {"success": True, "msg": f"Client {email} blocked"}
        elif path == "/api/security/enable-client":
            email = kwargs.get("data", {}).get("email")
            return True, {"success": True, "msg": f"Client {email} unblocked"}
        return False, {"error": "Not mocked"}
        
    monkeypatch.setattr(SpectrePanelInstance, "request", mock_request)

    async def mock_get_client_by_connection(client_ip, dst_ip, port, source_type, source_id):
        if source_type == 'vps':
            return "tunnel@hysteria.com", vps_panel, "hysteria", "1.2.3.4"
        elif source_type == 'lxc':
            return "attacker@xray.com", lxc_panel, "xray", "1.2.3.4"
        return None
    monkeypatch.setattr(spectre_manager, "get_client_by_connection", mock_get_client_by_connection)
    
    # Замокаем отправку алертов в Telegram
    telegram_alerts = []
    async def mock_send_alert(text, parse_mode="HTML", reply_markup=None):
        telegram_alerts.append((text, reply_markup))
        
    monkeypatch.setattr("modules.proxmox.monitor.remote.traffic.send_alert_to_admins", mock_send_alert)
    
    # Замокаем ss kill-process
    monkeypatch.setattr("modules.proxmox.monitor.remote.traffic.get_and_kill_remote_process", AsyncMock(return_value=("hysteria", "WHITELISTED")))
    
    # Уменьшим время паузы в расследовании для быстроты тестов, но сохраним реальное переключение контекста
    orig_sleep = asyncio.sleep
    async def mock_sleep(delay, *args, **kwargs):
        await orig_sleep(0.001)
    monkeypatch.setattr("modules.proxmox.monitor.remote.traffic.asyncio.sleep", mock_sleep)
    
    # Эмулируем исходящую строку iptables о исходящей атаке с VPS на порт 22
    line = "Jun 07 00:30:05 vps kernel: [123456.789] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=1.1.1.1 DST=8.8.8.8 LEN=60 PROTO=TCP SPT=12345 DPT=22"
    server_vps = {'ip': '1.1.1.1', 'user': 'root', 'key': 'key_path'}
    
    # Вызываем обработчик трафика
    await handle_remote_traffic_line(line, server=server_vps)
    
    # Даем асинхронным задачам выполниться (с использованием реального sleep)
    await orig_sleep(0.05)
    
    # Проверяем, что были отправлены алерты в Telegram
    assert len(telegram_alerts) >= 2
    alert_1, _ = telegram_alerts[0]
    alert_2, _ = telegram_alerts[1]
    
    assert "Обнаружена атака через Hysteria-туннель" in alert_1
    assert "tunnel@hysteria.com" in alert_1
    assert "Нарушитель найден" in alert_2
    assert "attacker@xray.com" in alert_2
    assert "Разблокирован" in alert_2
    
    disabled_emails = [call[3].get("data", {}).get("email") for call in api_calls if call[2] == "/api/security/disable-client"]
    enabled_emails = [call[3].get("data", {}).get("email") for call in api_calls if call[2] == "/api/security/enable-client"]
    
    assert "tunnel@hysteria.com" in disabled_emails
    assert "attacker@xray.com" in disabled_emails
    assert "tunnel@hysteria.com" in enabled_emails

@pytest.mark.asyncio
async def test_two_phase_ips_failure(monkeypatch):
    """
    Интеграционный тест сценария с неудачным расследованием:
    1. Обнаружение атаки на VPS по порту 22.
    2. Временный бан туннеля Hysteria.
    3. Асинхронное расследование не находит виновника в Xray на LXC.
    4. Туннель остается заблокированным.
    5. Админу отсылается сообщение с логами и кнопкой ручной разблокировки.
    """
    from core.spectre_client import SpectrePanelInstance, spectre_manager
    from modules.proxmox.monitor.remote.traffic import handle_remote_traffic_line, recent_remote_traffic_alerts
    
    # Сбрасываем кэш троттлинга
    recent_remote_traffic_alerts.clear()
    
    from core.config import settings
    monkeypatch.setattr(settings, "transit_tunnels", ["bot", "tunnel@hysteria.com"])
    
    lxc_panel = SpectrePanelInstance("LXC Panel", "http://127.0.0.1:20530", "lxc-token", "ui", "lxc", "999")
    vps_panel = SpectrePanelInstance("VPS Panel", "http://127.0.0.1:15000", "vps-token", "ui", "vps", "1.1.1.1")
    
    spectre_manager.panels = {
        "lxc_999": lxc_panel,
        "vps_1.1.1.1": vps_panel
    }
    
    api_calls = []
    
    async def mock_request(self, method, path, **kwargs):
        api_calls.append((self.name, method, path, kwargs))
        if path == "/api/security/disable-client":
            return True, {"success": True, "msg": "Blocked"}
        return False, {"error": "Not mocked"}
        
    monkeypatch.setattr(SpectrePanelInstance, "request", mock_request)

    async def mock_get_client_by_connection(client_ip, dst_ip, port, source_type, source_id):
        if source_type == 'vps':
            return "tunnel@hysteria.com", vps_panel, "hysteria", "1.2.3.4"
        return None
    monkeypatch.setattr(spectre_manager, "get_client_by_connection", mock_get_client_by_connection)
    
    telegram_alerts = []
    async def mock_send_alert(text, parse_mode="HTML", reply_markup=None):
        telegram_alerts.append((text, reply_markup))
        
    monkeypatch.setattr("modules.proxmox.monitor.remote.traffic.send_alert_to_admins", mock_send_alert)
    monkeypatch.setattr("modules.proxmox.monitor.remote.traffic.get_and_kill_remote_process", AsyncMock(return_value=("hysteria", "WHITELISTED")))
    
    orig_sleep = asyncio.sleep
    async def mock_sleep(delay, *args, **kwargs):
        await orig_sleep(0.001)
    monkeypatch.setattr("modules.proxmox.monitor.remote.traffic.asyncio.sleep", mock_sleep)
    
    # Мокаем сбор логов по pct exec и ssh
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"mock xray logs", b"")
    monkeypatch.setattr("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc))
    monkeypatch.setattr("modules.proxmox.monitor.remote.traffic.run_remote_ssh_cmd", AsyncMock(return_value=(True, "mock hysteria logs", "")))
    
    line = "Jun 07 00:30:05 vps kernel: [123456.789] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=1.1.1.1 DST=8.8.8.8 LEN=60 PROTO=TCP SPT=12345 DPT=22"
    server_vps = {'ip': '1.1.1.1', 'user': 'root', 'key': 'key_path'}
    
    await handle_remote_traffic_line(line, server=server_vps)
    await orig_sleep(0.05)
    
    assert len(telegram_alerts) >= 2
    alert_1, kb_1 = telegram_alerts[0]
    alert_2, kb_2 = telegram_alerts[1]
    
    assert "Обнаружена атака через Hysteria-туннель" in alert_1
    assert "Виновник не обнаружен" in alert_2
    assert "Оставлен в бане" in alert_2
    assert "mock xray logs" in alert_2
    assert "mock hysteria logs" in alert_2
    
    assert kb_2 is not None
    assert kb_2.inline_keyboard[0][0].text == "🔓 Разблокировать туннель"
    assert kb_2.inline_keyboard[0][0].callback_data == "unban_tunnel:tunnel@hysteria.com"

@pytest.mark.asyncio
async def test_callback_unban_tunnel(monkeypatch):
    """
    Тестирование callback хэндлера unban_tunnel.
    """
    from core.handlers.spectre import cb_unban_tunnel
    from core.spectre_client import spectre_manager, SpectrePanelInstance
    
    panel = SpectrePanelInstance("Panel", "http://127.0.0.1:15000", "token", "ui", "vps", "1.1.1.1")
    spectre_manager.panels = {"vps_1.1.1.1": panel}
    
    async def mock_request(self, method, path, **kwargs):
        if path == "/api/security/enable-client":
            return True, {"success": True, "msg": "Client unblocked"}
        return False, {}
    monkeypatch.setattr(SpectrePanelInstance, "request", mock_request)
    
    mock_callback = AsyncMock()
    mock_callback.data = "unban_tunnel:tunnel@hysteria.com"
    mock_callback.message.html_text = "🚨 Текст алерта\n👇 Вы можете разблокировать туннель вручную в один клик:"
    mock_callback.message.reply_markup = MagicMock()
    
    await cb_unban_tunnel(mock_callback)
    
    mock_callback.message.edit_text.assert_called()
    called_args = mock_callback.message.edit_text.call_args_list
    assert any("Туннель успешно разблокирован вручную!" in call[0][0] for call in called_args)
    mock_callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_spectre_handlers_ban_client(monkeypatch):
    from core.spectre_client import spectre_manager, SpectrePanelInstance
    
    panel = SpectrePanelInstance("Panel", "http://127.0.0.1:15000", "token", "ui", "vps", "1.1.1.1")
    spectre_manager.panels = {"vps_1.1.1.1": panel}
    
    async def mock_request(self, method, path, **kwargs):
        if path == "/api/security/disable-client":
            email = kwargs.get("data", {}).get("email")
            return True, {"success": True, "msg": f"Client {email} blocked"}
        return False, {}
    monkeypatch.setattr(SpectrePanelInstance, "request", mock_request)
    
    mock_status_msg = AsyncMock()
    mock_message = AsyncMock()
    mock_message.text = "/ban attacker@xray.com"
    mock_message.reply = AsyncMock(return_value=mock_status_msg)
    
    await cmd_ban_client(mock_message)
    
    mock_message.reply.assert_called_once()
    assert "attacker@xray.com" in mock_message.reply.call_args[0][0]
    
    mock_status_msg.edit_text.assert_called_once()
    assert "Результаты блокировки" in mock_status_msg.edit_text.call_args[0][0]
    assert "🟢 Заблокирован" in mock_status_msg.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_spectre_handlers_unban_client(monkeypatch):
    from core.spectre_client import spectre_manager, SpectrePanelInstance
    
    panel = SpectrePanelInstance("Panel", "http://127.0.0.1:15000", "token", "ui", "vps", "1.1.1.1")
    spectre_manager.panels = {"vps_1.1.1.1": panel}
    
    async def mock_request(self, method, path, **kwargs):
        if path == "/api/security/enable-client":
            email = kwargs.get("data", {}).get("email")
            return True, {"success": True, "msg": f"Client {email} unblocked"}
        return False, {}
    monkeypatch.setattr(SpectrePanelInstance, "request", mock_request)
    
    mock_status_msg = AsyncMock()
    mock_message = AsyncMock()
    mock_message.text = "/unban attacker@xray.com"
    mock_message.reply = AsyncMock(return_value=mock_status_msg)
    
    await cmd_unban_client(mock_message)
    
    mock_message.reply.assert_called_once()
    assert "attacker@xray.com" in mock_message.reply.call_args[0][0]
    
    mock_status_msg.edit_text.assert_called_once()
    assert "Результаты разблокировки" in mock_status_msg.edit_text.call_args[0][0]
    assert "🟢 Разблокирован" in mock_status_msg.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_spectre_panel_get_audit_logs():
    panel = SpectrePanelInstance("Test", "http://127.0.0.1:2053", "token", "ui", "lxc", "999")
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"success": True, "logs": []})
    
    mock_request_ctx = MagicMock()
    mock_request_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_request_ctx.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = MagicMock()
    mock_session.request = MagicMock(return_value=mock_request_ctx)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        success, res = await panel.get_audit_logs()
        assert success is True
        assert res["success"] is True
        assert "logs" in res


@pytest.mark.asyncio
async def test_spectre_handlers_audit(monkeypatch):
    from core.handlers.spectre import cmd_audit
    from core.spectre_client import spectre_manager, SpectrePanelInstance
    
    panel = SpectrePanelInstance("Panel", "http://127.0.0.1:15000", "token", "ui", "vps", "1.1.1.1")
    spectre_manager.panels = {"vps_1.1.1.1": panel}
    
    async def mock_get_audit_logs(self, limit=10):
        import time
        return True, {
            "success": True,
            "logs": [
                {
                    "timestamp": int(time.time()),
                    "username": "admin",
                    "action": "login_success",
                    "target": "1.2.3.4",
                    "details": "Details"
                }
            ]
        }
    monkeypatch.setattr(SpectrePanelInstance, "get_audit_logs", mock_get_audit_logs)
    
    mock_status_msg = AsyncMock()
    mock_message = AsyncMock()
    mock_message.answer = AsyncMock(return_value=mock_status_msg)
    
    await cmd_audit(mock_message)
    
    # Сначала отправляется статус-сообщение о загрузке, затем оно удаляется, и отправляется результат
    assert mock_message.answer.call_count == 2
    mock_status_msg.delete.assert_called_once()
    
    # Проверяем, что во втором вызове answer был передан текст с логом
    second_call_text = mock_message.answer.call_args_list[1][0][0]
    assert "Последние действия в панели" in second_call_text


@pytest.mark.asyncio
async def test_spectre_handlers_add_slave(monkeypatch):
    from core.handlers.spectre import cb_add_slave
    from core.spectre_client import spectre_manager, SpectrePanelInstance
    
    panel = SpectrePanelInstance("Panel", "http://127.0.0.1:15000", "token", "ui", "vps", "1.1.1.1")
    spectre_manager.panels = {"vps_1.1.1.1": panel}
    
    async def mock_request(self, method, path, **kwargs):
        if path == "/api/nodes/join-code":
            return True, {"success": True, "code": "JOIN-12345", "expires_at": 1780847253}
        return False, {}
    monkeypatch.setattr(SpectrePanelInstance, "request", mock_request)
    
    mock_callback = AsyncMock()
    mock_callback.data = "spectre_add_slave:vps_1.1.1.1"
    
    await cb_add_slave(mock_callback)
    
    mock_callback.message.edit_text.assert_called()
    called_args = mock_callback.message.edit_text.call_args_list
    assert any("JOIN-12345" in call[0][0] for call in called_args)
    assert any("python register_node.py" in call[0][0] for call in called_args)
    mock_callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_spectre_handlers_add_master(monkeypatch):
    from core.handlers.spectre import cb_add_master
    
    mock_callback = AsyncMock()
    mock_callback.data = "spectre_add_master"
    
    await cb_add_master(mock_callback)
    
    mock_callback.message.edit_text.assert_called_once()
    assert "Добавление новой Мастер-панели" in mock_callback.message.edit_text.call_args[0][0]
    mock_callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_spectre_handlers_setup_slave(monkeypatch):
    from core.handlers.spectre import cmd_setup_slave
    
    # Mock aiohttp client session post
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "node_id": "node-mock-123",
        "node_api_token": "token-mock-123",
        "master_public_key": "pub-mock-123"
    })
    
    mock_post_ctx = MagicMock()
    mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_post_ctx)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    # Mock file writing
    patch("builtins.open", MagicMock()).start()
    
    mock_status_msg = AsyncMock()
    mock_message = AsyncMock()
    mock_message.text = "/setup_slave https://master-server.com/secret JOIN-12345"
    mock_message.reply = AsyncMock(return_value=mock_status_msg)
    
    with patch("aiohttp.ClientSession", return_value=mock_session), \
         patch("os.path.exists", return_value=True), \
         patch("os.chmod", return_value=True):
         
        await cmd_setup_slave(mock_message)
        
        mock_message.reply.assert_called_once()
        mock_status_msg.edit_text.assert_called_once()
        assert "Сервер успешно настроен" in mock_status_msg.edit_text.call_args[0][0]
        assert "node-mock-123" in mock_status_msg.edit_text.call_args[0][0]
        
    patch.stopall()




