import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_router_ipv6_callbacks():
    from modules.router.handlers import (
        cb_router_allow_port_action,
        cb_router_allow_alert_action,
        cb_router_disallow_port_action,
        cb_router_ban_all_action,
        cb_router_ban_port_action,
        cb_router_unban_port_action,
        handle_router_block_ip,
        handle_router_unblock_ip,
    )
    from core.db import is_router_port_allowed

    cb_mock = AsyncMock()
    cb_mock.message = AsyncMock()
    cb_mock.message.chat.id = 12345
    cb_mock.message.message_id = 99
    cb_mock.message.text = "Router Alert Text"

    with patch("modules.router.router.run_router_ssh_cmd", AsyncMock(return_value=(True, "OK", ""))), \
         patch("modules.router.handlers.render_client_details", AsyncMock(return_value=("text", None))), \
         patch("modules.router.handlers.edit_rich_message", AsyncMock()), \
         patch("modules.router.handlers.send_rich_message", AsyncMock()):

        # 1. Быстрое разрешение из алерта с IPv6:
        cb_mock.data = "r_al_alert:2001:db8::cafe:8006:tcp"
        await cb_router_allow_alert_action(cb_mock)
        assert await is_router_port_allowed("2001:db8::cafe", 8006, "tcp") is True

        # 2. Отзыв разрешения для IPv6:
        cb_mock.data = "r_disallow_port:2001:db8::cafe:8006:tcp"
        await cb_router_disallow_port_action(cb_mock)
        assert await is_router_port_allowed("2001:db8::cafe", 8006, "tcp") is False

        # 3. Разрешение сервиса через меню для IPv6:
        cb_mock.data = "r_allow_act:2001:db8::cafe:80_443:tcp"
        await cb_router_allow_port_action(cb_mock)
        assert await is_router_port_allowed("2001:db8::cafe", 80, "tcp") is True
        assert await is_router_port_allowed("2001:db8::cafe", 443, "tcp") is True

        # 4. Блокировка всех портов IPv6:
        with patch("modules.router.handlers.ban_router_ip", AsyncMock(return_value=(True, "OK"))) as mock_ban_ip:
            cb_mock.data = "r_ban_all:2001:db8::cafe:3600"
            await cb_router_ban_all_action(cb_mock)
            mock_ban_ip.assert_called_once_with("2001:db8::cafe", delay=3600, reason="Вручную из TG")

        # 5. Блокировка порта IPv6:
        with patch("modules.router.handlers.ban_router_port", AsyncMock(return_value=(True, "OK"))) as mock_ban_p:
            cb_mock.data = "r_ban_port:2001:db8::cafe:22:tcp:3600"
            await cb_router_ban_port_action(cb_mock)
            mock_ban_p.assert_called_once_with("2001:db8::cafe", 22, proto="tcp", delay=3600, reason="Вручную из TG")

        # 6. Снятие блокировки порта IPv6:
        with patch("modules.router.handlers.unban_router_port", AsyncMock(return_value=(True, "OK"))) as mock_unban_p, \
             patch("modules.router.handlers.execute_read_one", AsyncMock(return_value=None)), \
             patch("modules.router.handlers.execute_read_all", AsyncMock(return_value=[])), \
             patch("modules.router.handlers.get_router_allowed_ports", AsyncMock(return_value=[])):
            cb_mock.data = "r_unban_port:2001:db8::cafe:22:tcp"
            await cb_router_unban_port_action(cb_mock)
            mock_unban_p.assert_called_once_with("2001:db8::cafe", 22, "tcp")

        # 7. Системные алерты роутера: router_block и router_unblock с IPv6
        with patch("modules.router.handlers.ban_router_ip", AsyncMock(return_value=(True, "OK"))) as mock_sys_ban:
            cb_mock.data = "router_block:2001:db8::cafe"
            await handle_router_block_ip(cb_mock)
            mock_sys_ban.assert_called_once_with("2001:db8::cafe")

        with patch("modules.router.handlers.unban_router_ip", AsyncMock(return_value=(True, "OK"))) as mock_sys_unban:
            cb_mock.data = "router_unblock:2001:db8::cafe"
            await handle_router_unblock_ip(cb_mock)
            mock_sys_unban.assert_called_once_with("2001:db8::cafe")

        # Очистка
        from modules.router.router import disallow_router_port
        await disallow_router_port("2001:db8::cafe", 80, "tcp")
        await disallow_router_port("2001:db8::cafe", 443, "tcp")


@pytest.mark.asyncio
async def test_spectre_ipv6_panel_callbacks():
    from core.spectre_client import spectre_manager
    from core.spectre_client.client import SpectrePanelInstance
    from bot.core.handlers.spectre.panel import (
        cb_spectre_clients,
        cb_spectre_client_view,
        cb_spectre_client_act,
        cb_ctrl_term_sess,
        cb_ctrl_reset_pwd,
    )
    from bot.core.handlers.spectre.system import cb_audit_category

    panel_key = "vps_2001:db8::1"
    mock_instance = MagicMock(spec=SpectrePanelInstance)
    mock_instance.name = "VPS 2001:db8::1"
    mock_instance.request = AsyncMock(return_value=(True, {"success": True, "clients": []}))
    mock_instance.get_audit_logs = AsyncMock(return_value=(True, {"logs": []}))
    spectre_manager.panels[panel_key] = mock_instance

    cb_mock = AsyncMock()
    cb_mock.message = AsyncMock()
    cb_mock.message.chat.id = 12345
    cb_mock.message.message_id = 100
    cb_mock.message.html_text = "Orig Text"

    try:
        # 1. cb_spectre_clients with IPv6 panel_key and page 2:
        cb_mock.data = f"spectre_clients:{panel_key}:2"
        await cb_spectre_clients(cb_mock)
        mock_instance.request.assert_called()

        # 2. cb_spectre_client_view with IPv6 panel_key and email:
        mock_instance.request = AsyncMock(return_value=(True, {
            "success": True,
            "clients": [{"client": {"email": "user@example.com", "up": 1024, "down": 2048, "total": 0, "enable": 1, "expiry_time": 0}}]
        }))
        with patch("modules.proxmox.monitor.utils.edit_rich_message", AsyncMock()):
            cb_mock.data = f"spectre_client_view:{panel_key}:user@example.com"
            await cb_spectre_client_view(cb_mock)

        # 3. cb_spectre_client_act with IPv6 panel_key, email and action:
        mock_instance.request = AsyncMock(return_value=(True, {"success": True}))
        with patch("bot.core.handlers.spectre.panel.cb_spectre_client_view", AsyncMock()) as mock_view:
            cb_mock.data = f"spectre_client_act:{panel_key}:user@example.com:ban"
            await cb_spectre_client_act(cb_mock)
            mock_instance.request.assert_called_with("POST", "/api/security/disable-client", data={"email": "user@example.com"})
            mock_view.assert_called_once()

        # 4. cb_audit_category with IPv6 panel_key:
        with patch("bot.core.handlers.spectre.system.run_audit_for_panel", AsyncMock()) as mock_audit:
            cb_mock.data = f"spectre_audit_cat:{panel_key}:login"
            await cb_audit_category(cb_mock)
            mock_audit.assert_called_once_with(cb_mock.message, panel_key, search="login")

        # 5. cb_ctrl_term_sess with IPv6 panel_key and IPv6 client IP:
        mock_instance.request = AsyncMock(side_effect=[
            (True, {"success": True, "sessions": [{"session_id": "sess-1", "username": "admin", "ip_address": "2001:db8::cafe"}]}),
            (True, {"success": True})
        ])
        cb_mock.data = f"ctrl_term_sess:{panel_key}:admin:2001:db8::cafe"
        await cb_ctrl_term_sess(cb_mock)
        assert mock_instance.request.call_count == 2
        mock_instance.request.assert_called_with("POST", "/api/security/sessions/terminate", json={"session_id": "sess-1"})

        # 6. cb_ctrl_reset_pwd with IPv6 panel_key:
        mock_instance.source_type = "manual"
        cb_mock.data = f"ctrl_reset_pwd:{panel_key}:admin"
        await cb_ctrl_reset_pwd(cb_mock)
        cb_mock.answer.assert_called()

    finally:
        spectre_manager.panels.pop(panel_key, None)


@pytest.mark.asyncio
async def test_history_special_username_callback():
    from bot.core.handlers.history import callback_vpn_history_view
    cb_mock = AsyncMock()
    cb_mock.message = AsyncMock()

    with patch("bot.core.handlers.history.execute_read_one", AsyncMock(return_value={'cnt': 0})):
        cb_mock.data = "vpn_hist:special:username:with:colons:3"
        await callback_vpn_history_view(cb_mock)
        # Should not raise exception, extracted username "special:username:with:colons" and page 3
        cb_mock.message.edit_text.assert_called_once()
        text = cb_mock.message.edit_text.call_args[0][0]
        assert "special:username:with:colons" in text


@pytest.mark.asyncio
async def test_whitelist_ipv6_callbacks():
    from bot.core.handlers.whitelist import (
        cb_whitelist_del_item,
        cb_quick_whitelist,
        cb_quick_block_ip,
        cb_copy_ip,
    )

    cb_mock = AsyncMock()
    cb_mock.message = AsyncMock()
    cb_mock.message.html_text = "Orig"
    cb_mock.message.text = "Orig"

    # 1. cb_whitelist_del_item with IPv6 node:
    with patch("bot.core.handlers.whitelist.get_node_whitelists", AsyncMock(return_value={"vps_2001:db8::1": {"ip_ports": ["2001:db8::cafe:80"], "processes": []}})), \
         patch("bot.core.handlers.whitelist.save_node_whitelists", AsyncMock()) as mock_save, \
         patch("bot.core.handlers.whitelist.sync_whitelists_to_panels", AsyncMock()), \
         patch("bot.core.handlers.whitelist.cb_whitelist_del_select", AsyncMock()):
        cb_mock.data = "wl_del_item:vps_2001:db8::1:ip_ports:2001:db8::cafe:80"
        await cb_whitelist_del_item(cb_mock)
        mock_save.assert_called_once_with({"vps_2001:db8::1": {"ip_ports": [], "processes": []}})

    # 2. cb_quick_whitelist with IPv6 node and IPv6 target ip:port:
    with patch("bot.core.handlers.whitelist.get_node_whitelists", AsyncMock(return_value={})), \
         patch("bot.core.handlers.whitelist.save_node_whitelists", AsyncMock()) as mock_save, \
         patch("bot.core.handlers.whitelist.sync_whitelists_to_panels", AsyncMock()):
        cb_mock.data = "qwl:vps_2001:db8::1:ipport:2001:db8::cafe:80"
        await cb_quick_whitelist(cb_mock)
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert "2001:db8::cafe:80" in saved["vps_2001:db8::1"]["ip_ports"]

    # 3. cb_quick_block_ip with IPv6:
    with patch("modules.proxmox.monitor.traffic.firewall.block_local_ip", AsyncMock()) as mock_block:
        cb_mock.data = "qblock:ip:2001:db8::cafe"
        await cb_quick_block_ip(cb_mock)
        mock_block.assert_called_once_with("2001:db8::cafe", delay=3600, reason="Быстрая блокировка из алерта")

    # 4. cb_copy_ip with IPv6:
    cb_mock.data = "copy:ip:2001:db8::cafe"
    await cb_copy_ip(cb_mock)
    cb_mock.answer.assert_called_with("2001:db8::cafe", show_alert=True)
