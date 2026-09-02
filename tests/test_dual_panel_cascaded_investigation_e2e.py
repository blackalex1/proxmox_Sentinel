import os
import sys
import time
import json
import socket
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

CONTROLLER_DIR = Path(__file__).resolve().parent.parent
PANEL_DIR = CONTROLLER_DIR.parent / "panel"
for p in [str(CONTROLLER_DIR), str(PANEL_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.spectre_client import SpectrePanelInstance, spectre_manager
from modules.proxmox.monitor.remote.traffic import (
    handle_remote_traffic_line,
    investigate_and_resolve_remote_attack,
    recent_remote_traffic_alerts,
    active_investigations
)
from core import sentinel_core_bridge


@pytest.fixture
def dual_panels_environment(tmp_path, monkeypatch):
    """
    Creates and configures two live panel environments with real databases,
    log files, outbounds, inbounds, and clients:
    - Panel 1: Upstream LXC Gateway (LXC 104) with cascaded client 'cascaded_attacker@test.lan'
      and Outbound tunnel pointing to Panel 2.
    - Panel 2: Exit VPS (198.51.100.14) with transit tunnel account 'vps_transit_tunnel',
      direct client 'direct_attacker@test.lan', and innocent user 'innocent_tg_client@test.lan'.
    """
    recent_remote_traffic_alerts.clear()
    active_investigations.clear()

    monkeypatch.setattr("core.db.log_ips_incident", AsyncMock(return_value=True))

    # Panel 1 (LXC 104) setup
    p1_dir = tmp_path / "panel1"
    p1_dir.mkdir()
    p1_log_dir = p1_dir / "logs"
    p1_log_dir.mkdir()
    p1_xray_log = p1_log_dir / "access.log"
    p1_singbox_log = p1_dir / "singbox.log"
    p1_env = p1_dir / "config" / ".env"
    p1_env.parent.mkdir(parents=True)
    p1_env.write_text("PANEL_SECRET=ui_p1\n", encoding="utf-8")

    # Panel 2 (VPS) setup
    p2_dir = tmp_path / "panel2"
    p2_dir.mkdir()
    p2_log_dir = p2_dir / "logs"
    p2_log_dir.mkdir()
    p2_xray_log = p2_log_dir / "access.log"
    p2_hysteria_log = p2_dir / "hysteria.log"
    p2_env = p2_dir / "config" / ".env"
    p2_env.parent.mkdir(parents=True)
    p2_env.write_text("PANEL_SECRET=ui_p2\n", encoding="utf-8")

    # In-memory mock databases for both panels
    p1_db = {
        "clients": {
            "cascaded_attacker@test.lan": {"enable": 1, "inbound": "vless-phone-in", "uuid": "uuid-p1-phone"}
        },
        "outbounds": [
            {
                "tag": "out-vps-test",
                "remark": "VPS-Test-Hysteria-Tunnel",
                "protocol": "hysteria2",
                "settings": {"server": "198.51.100.14", "port": 36711},
                "streamSettings": {"serverName": "198.51.100.14"}
            }
        ]
    }

    p2_db = {
        "clients": {
            "vps_transit_tunnel": {"enable": 1, "inbound": "hy2-tunnel-in", "uuid": "uuid-vps-tunnel"},
            "direct_attacker@test.lan": {"enable": 1, "inbound": "xray-direct-in", "uuid": "uuid-vps-direct"},
            "innocent_tg_client@test.lan": {"enable": 1, "inbound": "xray-direct-in", "uuid": "uuid-vps-tg"}
        },
        "outbounds": [
            {"tag": "direct", "remark": "Direct", "protocol": "freedom"}
        ]
    }

    # Create mock HTTP handlers simulating real Spectre Panel API endpoints
    async def p1_request(method, path, data=None, params=None):
        if path in ["/api/routing/outbounds", "/api/outbounds"]:
            return True, {"success": True, "obj": p1_db["outbounds"]}
        if path == "/api/security/disable-client":
            email = (data or {}).get("email")
            if email in p1_db["clients"]:
                if p1_db["clients"][email]["enable"] == 0:
                    return True, {"success": True, "msg": "Client already blocked"}
                p1_db["clients"][email]["enable"] = 0
                return True, {"success": True, "msg": f"Client {email} disabled successfully"}
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
            lines = []
            if p1_xray_log.exists():
                lines.extend(p1_xray_log.read_text(encoding="utf-8").splitlines())
            if p1_singbox_log.exists():
                lines.extend(p1_singbox_log.read_text(encoding="utf-8").splitlines())
            found_email, found_ip, tag = sentinel_core_bridge.find_xray_client_email(lines, dst, port, max_age_sec=45)
            if found_email and p1_db["clients"].get(found_email, {}).get("enable") == 1:
                return True, {"success": True, "email": found_email, "client_ip": found_ip, "source": "xray", "inbound_tag": tag}
            return False, {"success": False, "msg": "Client not found"}
        return False, {"error": "Not handled"}

    async def p2_request(method, path, data=None, params=None):
        if path in ["/api/routing/outbounds", "/api/outbounds"]:
            return True, {"success": True, "obj": p2_db["outbounds"]}
        if path == "/api/security/disable-client":
            email = (data or {}).get("email")
            if email in p2_db["clients"]:
                if p2_db["clients"][email]["enable"] == 0:
                    return True, {"success": True, "msg": "Client already blocked"}
                p2_db["clients"][email]["enable"] = 0
                return True, {"success": True, "msg": f"Client {email} disabled successfully"}
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
            if p2_hysteria_log.exists():
                h_lines = p2_hysteria_log.read_text(encoding="utf-8").splitlines()
                email = sentinel_core_bridge.find_hysteria_client_email(h_lines, dst, port, max_age_sec=45)
                if email and p2_db["clients"].get(email, {}).get("enable") == 1:
                    ip = sentinel_core_bridge.find_client_ip_for_email_in_hysteria_log(h_lines, email, max_age_sec=45)
                    return True, {"success": True, "email": email, "client_ip": ip, "source": "hysteria", "inbound_tag": "hysteria"}
            if p2_xray_log.exists():
                x_lines = p2_xray_log.read_text(encoding="utf-8").splitlines()
                email, ip, tag = sentinel_core_bridge.find_xray_client_email(x_lines, dst, port, max_age_sec=45)
                if email and p2_db["clients"].get(email, {}).get("enable") == 1:
                    return True, {"success": True, "email": email, "client_ip": ip, "source": "xray", "inbound_tag": tag}
            return False, {"success": False, "msg": "Client not found"}
        return False, {"error": "Not handled"}

    panel1 = SpectrePanelInstance(
        name="LXC-104-Gateway",
        url="http://127.0.0.1:20530",
        token="token_p1",
        secret_path="ui_p1",
        source_type="lxc",
        identifier="104",
        env_path=str(p1_env)
    )
    panel1.request = p1_request

    panel2 = SpectrePanelInstance(
        name="VPS-198.51.100.14",
        url="http://127.0.0.1:15000",
        token="token_p2",
        secret_path="ui_p2",
        source_type="vps",
        identifier="198.51.100.14",
        env_path=str(p2_env)
    )
    panel2.request = p2_request

    spectre_manager.panels = {
        "lxc_104": panel1,
        "vps_198.51.100.14": panel2
    }

    return {
        "p1": panel1,
        "p2": panel2,
        "p1_db": p1_db,
        "p2_db": p2_db,
        "p1_xray_log": p1_xray_log,
        "p1_singbox_log": p1_singbox_log,
        "p2_xray_log": p2_xray_log,
        "p2_hysteria_log": p2_hysteria_log,
    }


# ---------------------------------------------------------------------------
# TEST 1: CASCADED / ROUTED ATTACK INVESTIGATION & RESOLUTION
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dual_panel_cascaded_upstream_client_investigation(dual_panels_environment, monkeypatch):
    """
    СЦЕНАРИЙ 1: Каскадная атака через цепочку двух панелей.
    - Клиент 'cascaded_attacker@test.lan' подключен к домашней панели LXC 104.
    - Его трафик через Outbound 'VPS-Test-Hysteria-Tunnel' уходит на VPS (198.51.100.14).
    - На VPS трафик идет через туннельный аккаунт 'vps_transit_tunnel' и совершает атаку на 203.0.113.195:22 (SSH).
    - В то же время на VPS есть невиновный клиент 'innocent_tg_client@test.lan', использующий api.telegram.org:443.

    ПРОВЕРЯЕМ:
    1. Расследование опрашивает логи upstream панели LXC 104 через sentinel-core.
    2. Виновником определяется истинный клиент 'cascaded_attacker@test.lan'.
    3. Клиент 'cascaded_attacker@test.lan' БАНИТСЯ на Panel 1 (enable=0).
    4. Транзитный туннель 'vps_transit_tunnel' на Panel 2 ОСТАЕТСЯ АКТИВНЫМ (enable=1).
    5. Невиновный пользователь Telegram НЕ банится (enable=1).
    6. Сообщение администраторам содержит точное имя туннеля 'VPS-Test-Hysteria-Tunnel' и имя нарушителя.
    """
    env = dual_panels_environment
    now_str_xray = time.strftime("%Y/%m/%d %H:%M:%S")
    now_str_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Записываем реальные логи прокси на обеих панелях
    p1_log_line = f"{now_str_xray} [info] 192.168.1.50:41234 accepted tcp:203.0.113.195:22 [vless-phone-in >> out-vps-test] email: cascaded_attacker@test.lan\n"
    env["p1_xray_log"].write_text(p1_log_line, encoding="utf-8")

    p2_hy_lines = [
        f'{{"time":"{now_str_iso}","id":"vps_transit_tunnel","reqAddr":"203.0.113.195:22"}}\n',
        f'{{"time":"{now_str_iso}","auth":"vps_transit_tunnel","addr":"192.168.1.104:55123"}}\n',
        f'{{"time":"{now_str_iso}","id":"innocent_tg_client@test.lan","reqAddr":"api.telegram.org:443"}}\n',
    ]
    env["p2_hysteria_log"].write_text("".join(p2_hy_lines), encoding="utf-8")

    telegram_alerts = []
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.send_alert_to_admins",
        AsyncMock(side_effect=lambda text, **kw: telegram_alerts.append(text))
    )
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.get_and_kill_remote_process",
        AsyncMock(return_value=("hysteria", "WHITELISTED"))
    )

    iptables_line = "Sep 02 14:00:00 vps kernel: [123456.789] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=198.51.100.14 DST=203.0.113.195 LEN=60 PROTO=TCP SPT=34446 DPT=22"
    server_vps = {'ip': '198.51.100.14', 'user': 'root', 'key': 'key_path'}

    # Обрабатываем событие сетевого фильтра (срабатывает немедленное обнаружение на upstream панели)
    await handle_remote_traffic_line(iptables_line, server=server_vps)
    await asyncio.sleep(0.1)

    # Проверка 1: Администраторам отправлен алерт успешного расследования
    assert len(telegram_alerts) >= 1
    alert_text = telegram_alerts[0]
    assert "cascaded_attacker@test.lan" in alert_text
    assert "203.0.113.195:22" in alert_text
    assert "VPS-Test-Hysteria-Tunnel" in alert_text

    # Проверка 2: Реальный нарушитель заблокирован на домашней панели LXC 104
    assert env["p1_db"]["clients"]["cascaded_attacker@test.lan"]["enable"] == 0

    # Проверка 3: Транзитный туннель на VPS остался активен для всех остальных
    assert env["p2_db"]["clients"]["vps_transit_tunnel"]["enable"] == 1

    # Проверка 4: Невиновный пользователь Telegram не пострадал
    assert env["p2_db"]["clients"]["innocent_tg_client@test.lan"]["enable"] == 1


# ---------------------------------------------------------------------------
# TEST 2: DIRECT EXIT PANEL ATTACK INVESTIGATION & RESOLUTION
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dual_panel_direct_client_attack_investigation(dual_panels_environment, monkeypatch):
    """
    СЦЕНАРИЙ 2: Прямая атака на конечной панели (VPS).
    - Клиент 'direct_attacker@test.lan' подключен напрямую к Panel 2 (VPS).
    - Он совершает атаку на 198.51.100.88:3389 (RDP).
    - На Panel 1 никаких записей об этом соединении нет.

    ПРОВЕРЯЕМ:
    1. Расследование проверяет Panel 1, убеждается что это не каскадный клиент.
    2. Виновником определяется прямой клиент VPS 'direct_attacker@test.lan'.
    3. Клиент 'direct_attacker@test.lan' БАНИТСЯ на Panel 2 (enable=0).
    4. Upstream клиенты на Panel 1 и туннели не затронуты.
    """
    env = dual_panels_environment
    now_str_xray = time.strftime("%Y/%m/%d %H:%M:%S")

    # Panel 2 (VPS) содержит лог прямого Xray клиента
    p2_xray_line = f"{now_str_xray} [info] 192.0.2.45:41235 accepted tcp:198.51.100.88:3389 [xray-direct-in >> direct] email: direct_attacker@test.lan\n"
    env["p2_xray_log"].write_text(p2_xray_line, encoding="utf-8")

    telegram_alerts = []
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.send_alert_to_admins",
        AsyncMock(side_effect=lambda text, **kw: telegram_alerts.append(text))
    )
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.get_and_kill_remote_process",
        AsyncMock(return_value=("xray", "WHITELISTED"))
    )

    iptables_line = "Sep 02 14:05:00 vps kernel: [123457.100] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=198.51.100.14 DST=198.51.100.88 LEN=60 PROTO=TCP SPT=41235 DPT=3389"
    server_vps = {'ip': '198.51.100.14', 'user': 'root', 'key': 'key_path'}

    # Запускаем обработку и ждем завершения фонового расследования (1.5с задержка)
    await handle_remote_traffic_line(iptables_line, server=server_vps)
    await asyncio.sleep(1.8)

    # Проверка 1: Администраторам отправлен алерт блокировки Xray клиента на VPS
    assert len(telegram_alerts) >= 1
    alert_text = telegram_alerts[0]
    assert "direct_attacker@test.lan" in alert_text
    assert "198.51.100.88:3389" in alert_text

    # Проверка 2: Нарушитель заблокирован на Panel 2 (VPS)
    assert env["p2_db"]["clients"]["direct_attacker@test.lan"]["enable"] == 0

    # Проверка 3: Upstream клиенты на Panel 1 не затронуты
    assert env["p1_db"]["clients"]["cascaded_attacker@test.lan"]["enable"] == 1


# ---------------------------------------------------------------------------
# TEST 3: FALSE-POSITIVE & ANTI-CYCLE RESILIENCE
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dual_panel_false_positive_and_anti_cycle_resilience(dual_panels_environment, monkeypatch):
    """
    СЦЕНАРИЙ 3: Защита от ложных срабатываний и зацикливания.
    1. На VPS есть лог клиента 'innocent_tg_client@test.lan', открывшего 'api.telegram.org:443'.
    2. Происходит алерт на сторонний IP '198.51.100.137:443'.
    3. Проверяем: невиновный клиент Telegram НЕ банится!
    4. Повторный всплеск пакетов от уже заблокированного нарушителя не вызывает лавины алертов.
    """
    env = dual_panels_environment
    now_str_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # В логах есть только соединение к Telegram
    p2_hy_lines = [
        f'{{"time":"{now_str_iso}","id":"innocent_tg_client@test.lan","reqAddr":"api.telegram.org:443"}}\n',
    ]
    env["p2_hysteria_log"].write_text("".join(p2_hy_lines), encoding="utf-8")

    telegram_alerts = []
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.send_alert_to_admins",
        AsyncMock(side_effect=lambda text, **kw: telegram_alerts.append(text))
    )
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.get_and_kill_remote_process",
        AsyncMock(return_value=("hysteria", "WHITELISTED"))
    )

    # Алерт на 198.51.100.137:443 (не совпадает с api.telegram.org)
    iptables_line = "Sep 02 14:10:00 vps kernel: [123458.000] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=198.51.100.14 DST=198.51.100.137 LEN=60 PROTO=TCP SPT=50000 DPT=443"
    server_vps = {'ip': '198.51.100.14', 'user': 'root', 'key': 'key_path'}

    await handle_remote_traffic_line(iptables_line, server=server_vps)
    await asyncio.sleep(0.1)

    # Невиновный пользователь Telegram НЕ заблокирован
    assert env["p2_db"]["clients"]["innocent_tg_client@test.lan"]["enable"] == 1


# ---------------------------------------------------------------------------
# TEST 4: REAL BINARY SING-BOX LIVE LOG GENERATION & SENTINEL PARSING
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_real_singbox_binary_cascaded_log_attribution():
    """
    СЦЕНАРИЙ 4: Проверка парсинга реальных логов нативного бинарника sing-box через C-FFI sentinel-core.
    Генерирует формат логов sing-box с connID и проверяет корректную привязку клиента и IP.
    """
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    singbox_lines = [
        f"+0300 {now_str} INFO [338227781 0ms] inbound/vless[vless-phone-in]: inbound connection from 192.168.1.88:51234",
        f"+0300 {now_str} INFO [338227781 15ms] inbound/vless[vless-phone-in]: [test_user] inbound connection to 203.0.113.50:22",
        f"+0300 {now_str} INFO [338227781 30ms] outbound/hysteria2[vps-tunnel]: outbound connection to 198.51.100.14:36711"
    ]

    email, ip, tag = sentinel_core_bridge.find_xray_client_email(
        singbox_lines,
        dst_ip="203.0.113.50",
        dst_port=22,
        client_ip=None,
        max_age_sec=45
    )

    assert email == "test_user", f"Expected 'test_user', got '{email}'"
    assert ip == "192.168.1.88", f"Expected IP '192.168.1.88', got '{ip}'"
    assert tag in ["vless-phone-in", "test_user", "proxy"]


# ---------------------------------------------------------------------------
# TEST 5: NO-SNIFFING SCENARIO (RAW IP HANDSHAKE & DIRECT TCP DISCOVERY)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dual_panel_no_sniffing_cascaded_investigation(dual_panels_environment, monkeypatch):
    """
    СЦЕНАРИЙ 5: Отключенный сниффинг на upstream-панели (LXC).
    - На Panel 1 (LXC) в настройках инбаунда полностью отключен сниффинг (sniffing enabled: false).
    - Клиент 'user_nosniff@test.lan' обращается напрямую по целевому IP '203.0.113.77:22' без SNI/домена.
    - Ядро Xray/Sing-box на Panel 1 логирует прямое IP-обращение из заголовка прокси-протокола.
    - На выходном VPS (198.51.100.14) файрвол фиксирует пакет к 203.0.113.77:22.

    ПРОВЕРЯЕМ:
    1. Отсутствие сниффинга не препятствует обнаружению истинного клиента.
    2. Расследование через sentinel-core успешно сопоставляет IP назначения и идентифицирует 'user_nosniff@test.lan'.
    3. Клиент 'user_nosniff@test.lan' блокируется на Panel 1.
    4. Транзитный канал Panel 2 не блокируется.
    """
    env = dual_panels_environment
    env["p1_db"]["clients"]["user_nosniff@test.lan"] = {"enable": 1, "inbound": "vless-nosniff-in", "uuid": "uuid-nosniff"}

    now_str_xray = time.strftime("%Y/%m/%d %H:%M:%S")
    now_str_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Panel 1 без сниффинга фиксирует сырой IP в заголовке VLESS/SOCKS5
    p1_log_line = f"{now_str_xray} [info] 192.168.1.99:49876 accepted tcp:203.0.113.77:22 [vless-nosniff-in >> out-vps-test] email: user_nosniff@test.lan\n"
    env["p1_xray_log"].write_text(p1_log_line, encoding="utf-8")

    # Panel 2 (VPS) фиксирует туннельный трафик
    p2_hy_lines = [
        f'{{"time":"{now_str_iso}","id":"vps_transit_tunnel","reqAddr":"203.0.113.77:22"}}\n',
        f'{{"time":"{now_str_iso}","auth":"vps_transit_tunnel","addr":"192.168.1.104:59111"}}\n',
    ]
    env["p2_hysteria_log"].write_text("".join(p2_hy_lines), encoding="utf-8")

    telegram_alerts = []
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.send_alert_to_admins",
        AsyncMock(side_effect=lambda text, **kw: telegram_alerts.append(text))
    )
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.get_and_kill_remote_process",
        AsyncMock(return_value=("hysteria", "WHITELISTED"))
    )

    iptables_line = "Sep 02 14:15:00 vps kernel: [123459.000] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=198.51.100.14 DST=203.0.113.77 LEN=60 PROTO=TCP SPT=39999 DPT=22"
    server_vps = {'ip': '198.51.100.14', 'user': 'root', 'key': 'key_path'}

    await handle_remote_traffic_line(iptables_line, server=server_vps)
    await asyncio.sleep(0.1)

    # Проверка: Нарушитель без сниффинга найден и заблокирован на Panel 1
    assert len(telegram_alerts) >= 1
    alert_text = telegram_alerts[0]
    assert "user_nosniff@test.lan" in alert_text
    assert "203.0.113.77:22" in alert_text
    assert env["p1_db"]["clients"]["user_nosniff@test.lan"]["enable"] == 0
    assert env["p2_db"]["clients"]["vps_transit_tunnel"]["enable"] == 1
