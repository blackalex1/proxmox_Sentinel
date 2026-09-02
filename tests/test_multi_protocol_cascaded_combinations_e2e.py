import os
import sys
import time
import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

CONTROLLER_DIR = Path(__file__).resolve().parent.parent
PANEL_DIR = CONTROLLER_DIR.parent / "panel"
for p in [str(CONTROLLER_DIR), str(PANEL_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.spectre_client import SpectrePanelInstance, spectre_manager
from modules.proxmox.monitor.remote.traffic import (
    handle_remote_traffic_line,
    recent_remote_traffic_alerts,
    active_investigations
)
from core import sentinel_core_bridge


@pytest.mark.asyncio
@pytest.mark.parametrize("p1_proto, p1_core, p1_user, p1_log_pattern, out_tunnel_proto, out_tunnel_tag, p2_proto, p2_core, p2_user, p2_log_pattern, target_ip, target_port", [
    # 1. Xray VLESS Reality -> Hysteria 2 Outbound -> Panel 2 Hysteria 2 (Port 22 SSH)
    (
        "vless", "xray", "alice_vless@test.lan",
        "{time} [info] 192.168.1.101:50001 accepted tcp:{dst_ip}:{dst_port} [vless-reality-in >> out-hy2-tunnel] email: alice_vless@test.lan\n",
        "hysteria2", "out-hy2-tunnel",
        "hysteria2", "hysteria", "transit_hy2_tunnel",
        '{{"time":"{iso_time}","id":"transit_hy2_tunnel","reqAddr":"{dst_ip}:{dst_port}"}}\n{{"time":"{iso_time}","auth":"transit_hy2_tunnel","addr":"192.168.1.104:50001"}}\n',
        "203.0.113.51", 22
    ),
    # 2. Sing-box TUIC v5 -> Shadowsocks 2022 Outbound -> Panel 2 Sing-box Shadowsocks (Port 3389 RDP)
    (
        "tuic", "singbox", "bob_tuic@test.lan",
        "+0300 {time} INFO [3001 0ms] inbound/tuic[tuic-in]: inbound connection from 192.168.1.102:50002\n+0300 {time} INFO [3001 10ms] inbound/tuic[tuic-in]: [bob_tuic@test.lan] inbound connection to {dst_ip}:{dst_port}\n",
        "shadowsocks", "out-ss2022-tunnel",
        "shadowsocks", "singbox", "transit_ss_tunnel",
        "+0300 {time} INFO [4001 0ms] inbound/shadowsocks[ss-in]: inbound connection from 192.168.1.104:50002\n+0300 {time} INFO [4001 10ms] inbound/shadowsocks[ss-in]: [transit_ss_tunnel] inbound connection to {dst_ip}:{dst_port}\n",
        "203.0.113.52", 3389
    ),
    # 3. Xray Trojan gRPC -> VLESS Reality Outbound -> Panel 2 Sing-box VLESS (Port 3306 MySQL)
    (
        "trojan", "xray", "carol_trojan@test.lan",
        "{time} [info] 192.168.1.103:50003 accepted tcp:{dst_ip}:{dst_port} [trojan-grpc-in >> out-vless-reality] email: carol_trojan@test.lan\n",
        "vless", "out-vless-reality",
        "vless", "singbox", "transit_vless_tunnel",
        "+0300 {time} INFO [5001 0ms] inbound/vless[vless-in]: inbound connection from 192.168.1.104:50003\n+0300 {time} INFO [5001 12ms] inbound/vless[vless-in]: [transit_vless_tunnel] inbound connection to {dst_ip}:{dst_port}\n",
        "203.0.113.53", 3306
    ),
    # 4. Sing-box Shadowsocks 2022 -> Hysteria 2 Outbound -> Panel 2 Hysteria 2 (Port 5432 PostgreSQL)
    (
        "shadowsocks", "singbox", "dave_ss@test.lan",
        "+0300 {time} INFO [6001 0ms] inbound/shadowsocks[ss-in]: inbound connection from 192.168.1.104:50004\n+0300 {time} INFO [6001 14ms] inbound/shadowsocks[ss-in]: [dave_ss@test.lan] inbound connection to {dst_ip}:{dst_port}\n",
        "hysteria2", "out-hy2-tunnel",
        "hysteria2", "hysteria", "transit_hy2_tunnel",
        '{{"time":"{iso_time}","id":"transit_hy2_tunnel","reqAddr":"{dst_ip}:{dst_port}"}}\n{{"time":"{iso_time}","auth":"transit_hy2_tunnel","addr":"192.168.1.104:50004"}}\n',
        "203.0.113.54", 5432
    ),
    # 5. Xray VMess WebSocket -> VMess gRPC Outbound -> Panel 2 Xray VMess (Port 27017 MongoDB)
    (
        "vmess", "xray", "eve_vmess@test.lan",
        "{time} [info] 192.168.1.105:50005 accepted tcp:{dst_ip}:{dst_port} [vmess-ws-in >> out-vmess-grpc] email: eve_vmess@test.lan\n",
        "vmess", "out-vmess-grpc",
        "vmess", "xray", "transit_vmess_tunnel",
        "{time} [info] 192.168.1.104:50005 accepted tcp:{dst_ip}:{dst_port} [vmess-in >> direct] email: transit_vmess_tunnel\n",
        "203.0.113.55", 27017
    ),
    # 6. Sing-box Mixed / SOCKS5 -> Shadowsocks Outbound -> Panel 2 Xray Shadowsocks (Port 8006 Proxmox)
    (
        "mixed", "singbox", "frank_socks@test.lan",
        "+0300 {time} INFO [7001 0ms] inbound/mixed[mixed-in]: inbound connection from 192.168.1.106:50006\n+0300 {time} INFO [7001 8ms] inbound/mixed[mixed-in]: [frank_socks@test.lan] inbound connection to {dst_ip}:{dst_port}\n",
        "shadowsocks", "out-ss-tunnel",
        "shadowsocks", "xray", "transit_ss_tunnel",
        "{time} [info] 192.168.1.104:50006 accepted tcp:{dst_ip}:{dst_port} [ss-in >> direct] email: transit_ss_tunnel\n",
        "203.0.113.56", 8006
    ),
    # 7. Hysteria 2 Standalone -> Hysteria 2 Outbound -> Panel 2 Sing-box Hysteria 2 (Port 22 SSH)
    (
        "hysteria2", "hysteria", "grace_hy2@test.lan",
        '{{"time":"{iso_time}","id":"grace_hy2@test.lan","reqAddr":"{dst_ip}:{dst_port}"}}\n{{"time":"{iso_time}","auth":"grace_hy2@test.lan","addr":"192.168.1.107:50007"}}\n',
        "hysteria2", "out-hy2-tunnel",
        "hysteria2", "singbox", "transit_hy2_tunnel",
        "+0300 {time} INFO [8001 0ms] inbound/hysteria2[hy2-in]: inbound connection from 192.168.1.104:50007\n+0300 {time} INFO [8001 10ms] inbound/hysteria2[hy2-in]: [transit_hy2_tunnel] inbound connection to {dst_ip}:{dst_port}\n",
        "203.0.113.57", 22
    )
])
async def test_cascaded_protocol_combinations_matrix(
    tmp_path, monkeypatch,
    p1_proto, p1_core, p1_user, p1_log_pattern,
    out_tunnel_proto, out_tunnel_tag,
    p2_proto, p2_core, p2_user, p2_log_pattern,
    target_ip, target_port
):
    """
    Тестирует матрицу произвольных комбинаций протоколов и ядер между двумя панелями:
    Panel 1 (Inbound: p1_proto/p1_core) -> Outbound (out_tunnel_proto) -> Panel 2 (Inbound: p2_proto/p2_core).
    Проверяет успешное расследование, обнаружение истинного upstream-клиента p1_user и блокировку на Panel 1.
    """
    recent_remote_traffic_alerts.clear()
    active_investigations.clear()

    monkeypatch.setattr("core.db.log_ips_incident", AsyncMock(return_value=True))

    p1_dir = tmp_path / f"p1_{p1_proto}"
    p1_dir.mkdir(parents=True, exist_ok=True)
    p1_log = p1_dir / "proxy.log"

    p2_dir = tmp_path / f"p2_{p2_proto}"
    p2_dir.mkdir(parents=True, exist_ok=True)
    p2_log = p2_dir / "proxy.log"

    now_str = time.strftime("%Y/%m/%d %H:%M:%S")
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Форматируем логи
    p1_content = p1_log_pattern.format(time=now_str, iso_time=now_iso, dst_ip=target_ip, dst_port=target_port)
    p1_log.write_text(p1_content, encoding="utf-8")

    p2_content = p2_log_pattern.format(time=now_str, iso_time=now_iso, dst_ip=target_ip, dst_port=target_port)
    p2_log.write_text(p2_content, encoding="utf-8")

    p1_db = {
        "clients": {p1_user: {"enable": 1, "inbound": f"{p1_proto}-in", "uuid": "uuid-p1"}},
        "outbounds": [{"tag": out_tunnel_tag, "remark": f"Tunnel-{out_tunnel_proto.upper()}", "protocol": out_tunnel_proto, "settings": {"server": "198.51.100.14"}}]
    }
    p2_db = {
        "clients": {p2_user: {"enable": 1, "inbound": f"{p2_proto}-in", "uuid": "uuid-p2"}},
        "outbounds": [{"tag": "direct", "remark": "Direct", "protocol": "freedom"}]
    }

    async def p1_request(method, path, data=None, params=None):
        if path in ["/api/routing/outbounds", "/api/outbounds"]:
            return True, {"success": True, "obj": p1_db["outbounds"]}
        if path == "/api/security/disable-client":
            email = (data or {}).get("email")
            if email in p1_db["clients"]:
                p1_db["clients"][email]["enable"] = 0
                return True, {"success": True, "msg": f"Client {email} disabled"}
            return False, {"success": False, "msg": "Client not found"}
        if path == "/api/security/enable-client":
            email = (data or {}).get("email")
            if email in p1_db["clients"]:
                p1_db["clients"][email]["enable"] = 1
                return True, {"success": True, "msg": f"Client {email} enabled"}
            return False, {"success": False, "msg": "Client not found"}
        if path == "/api/security/client-by-connection":
            dst = (params or {}).get("dst_ip")
            port = int((params or {}).get("port", 0))
            lines = p1_log.read_text(encoding="utf-8").splitlines() if p1_log.exists() else []
            if p1_core == "hysteria":
                email = sentinel_core_bridge.find_hysteria_client_email(lines, dst, port, max_age_sec=45)
                ip = sentinel_core_bridge.find_client_ip_for_email_in_hysteria_log(lines, email, max_age_sec=45) if email else None
                tag = "hysteria"
            else:
                email, ip, tag = sentinel_core_bridge.find_xray_client_email(lines, dst, port, max_age_sec=45)

            if email and p1_db["clients"].get(email, {}).get("enable") == 1:
                return True, {"success": True, "email": email, "client_ip": ip, "source": p1_core, "inbound_tag": tag}
            return False, {"success": False, "msg": "Client not found"}
        return False, {"error": "Not handled"}

    async def p2_request(method, path, data=None, params=None):
        if path in ["/api/routing/outbounds", "/api/outbounds"]:
            return True, {"success": True, "obj": p2_db["outbounds"]}
        if path == "/api/security/disable-client":
            email = (data or {}).get("email")
            if email in p2_db["clients"]:
                p2_db["clients"][email]["enable"] = 0
                return True, {"success": True, "msg": f"Client {email} disabled"}
            return False, {"success": False, "msg": "Client not found"}
        if path == "/api/security/enable-client":
            email = (data or {}).get("email")
            if email in p2_db["clients"]:
                p2_db["clients"][email]["enable"] = 1
                return True, {"success": True, "msg": f"Client {email} enabled"}
            return False, {"success": False, "msg": "Client not found"}
        if path == "/api/security/client-by-connection":
            dst = (params or {}).get("dst_ip")
            port = int((params or {}).get("port", 0))
            lines = p2_log.read_text(encoding="utf-8").splitlines() if p2_log.exists() else []
            if p2_core == "hysteria":
                email = sentinel_core_bridge.find_hysteria_client_email(lines, dst, port, max_age_sec=45)
                ip = sentinel_core_bridge.find_client_ip_for_email_in_hysteria_log(lines, email, max_age_sec=45) if email else None
                tag = "hysteria"
            else:
                email, ip, tag = sentinel_core_bridge.find_xray_client_email(lines, dst, port, max_age_sec=45)

            if email and p2_db["clients"].get(email, {}).get("enable") == 1:
                return True, {"success": True, "email": email, "client_ip": ip, "source": p2_core, "inbound_tag": tag}
            return False, {"success": False, "msg": "Client not found"}
        return False, {"error": "Not handled"}

    p1_instance = SpectrePanelInstance(
        name="LXC-Edge-Panel",
        url="http://127.0.0.1:20530",
        token="token_p1",
        secret_path="ui_p1",
        source_type="lxc",
        identifier="104",
        env_path=str(p1_dir / ".env")
    )
    p1_instance.request = p1_request

    p2_instance = SpectrePanelInstance(
        name="VPS-Exit-Panel",
        url="http://127.0.0.1:15000",
        token="token_p2",
        secret_path="ui_p2",
        source_type="vps",
        identifier="198.51.100.14",
        env_path=str(p2_dir / ".env")
    )
    p2_instance.request = p2_request

    spectre_manager.panels = {
        "lxc_104": p1_instance,
        "vps_198.51.100.14": p2_instance
    }

    telegram_alerts = []
    monkeypatch.setattr("modules.proxmox.monitor.remote.traffic.send_alert_to_admins", AsyncMock(side_effect=lambda text, **kw: telegram_alerts.append(text)))
    monkeypatch.setattr("modules.proxmox.monitor.remote.traffic.get_and_kill_remote_process", AsyncMock(return_value=(p2_core, "WHITELISTED")))

    iptables_line = f"Sep 02 14:30:00 vps kernel: [999999.000] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=198.51.100.14 DST={target_ip} LEN=60 PROTO=TCP SPT=48888 DPT={target_port}"
    server_vps = {'ip': '198.51.100.14', 'user': 'root', 'key': 'key_path'}

    await handle_remote_traffic_line(iptables_line, server=server_vps)
    await asyncio.sleep(0.1)

    # 1. Проверяем отправку алерта с найденным клиентом
    assert len(telegram_alerts) >= 1
    alert_text = telegram_alerts[0]
    assert p1_user in alert_text, f"Expected user {p1_user} in alert, got: {alert_text}"
    assert f"{target_ip}:{target_port}" in alert_text

    # 2. Проверяем блокировку на Panel 1
    assert p1_db["clients"][p1_user]["enable"] == 0, f"Expected {p1_user} to be disabled on Panel 1"

    # 3. Проверяем что транзитный канал на Panel 2 не отключен
    assert p2_db["clients"][p2_user]["enable"] == 1, f"Expected transit account {p2_user} to remain enabled on Panel 2"
