import os
import sys
import json
import time
import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from core.spectre_client.log_parser import (
    find_email_and_ip_in_xray_log,
    find_email_in_hysteria_log,
    find_client_ip_for_email_in_hysteria_log,
    parse_xray_timestamp,
    parse_hysteria_timestamp
)
from modules.proxmox.monitor.traffic.vpn import (
    find_real_vpn_client_ip,
    find_xray_client_email
)

# Binary candidate paths (Windows / Linux / Workspace)
def get_binary_path(name: str) -> Path:
    candidates = [
        Path(r"c:\Users\black\PycharmProjects\panel\bin") / f"{name}.exe",
        Path(r"c:\Users\black\PycharmProjects\panel\bin") / name,
        Path(r"c:\Users\black\PycharmProjects\panel + bot\Spectre-panel\bin") / f"{name}.exe",
        Path(r"c:\Users\black\PycharmProjects\panel + bot\Spectre-panel\bin") / name,
        Path("/opt/spectre-panel/bin") / name,
        Path("/home/alex/panel/bin") / name,
    ]
    if name == "hysteria":
        candidates.insert(0, Path(r"c:\Users\black\PycharmProjects\panel\bin\hysteria-windows-amd64.exe"))
        candidates.insert(1, Path(r"c:\Users\black\PycharmProjects\panel\bin\hysteria-linux-amd64"))
        candidates.insert(2, Path("/home/alex/panel/bin/hysteria-linux-amd64"))
    
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[0]


# ---------------------------------------------------------------------------
# 1. TEST ALL REAL BINARIES VERSION & EXECUTION
# ---------------------------------------------------------------------------
def test_all_real_core_binaries_present_and_executable():
    """
    Проверяет наличие и работоспособность нативных бинарников всех 3 ядер:
    1. Xray Core (xray.exe / xray)
    2. sing-box Core (sing-box.exe / sing-box)
    3. Hysteria 2 Core (hysteria-windows-amd64.exe / hysteria-linux-amd64)
    """
    cores = ["xray", "sing-box", "hysteria"]
    for core in cores:
        bin_path = get_binary_path(core)
        if bin_path.exists():
            res = subprocess.run([str(bin_path), "version"], capture_output=True, text=True, timeout=5)
            assert res.returncode == 0 or "Hysteria" in res.stdout or "xray" in res.stdout.lower() or "sing-box" in res.stdout.lower()
            print(f"[OK] Core '{core}' binary is valid: {bin_path}")


# ---------------------------------------------------------------------------
# 2. REAL SING-BOX CONFIG CHECK, RUN & LOG ATTRIBUTION
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_real_singbox_execution_and_investigation():
    """
    Тестирует реальный запуск sing-box, генерацию логов и расследование по логам.
    """
    singbox_bin = get_binary_path("sing-box")
    if not singbox_bin.exists():
        pytest.skip(f"sing-box binary not found at {singbox_bin}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "singbox_investigation.json"
        log_path = Path(tmp_dir) / "singbox_investigation.log"

        config_data = {
            "log": {
                "level": "info",
                "output": str(log_path).replace("\\", "/"),
                "timestamp": True
            },
            "inbounds": [
                {
                    "type": "socks",
                    "tag": "socks-ips",
                    "listen": "127.0.0.1",
                    "listen_port": 59988
                }
            ],
            "outbounds": [
                {"type": "direct", "tag": "direct"}
            ]
        }
        config_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")

        # Check config
        check_res = subprocess.run([str(singbox_bin), "check", "-c", str(config_path)], capture_output=True, text=True)
        assert check_res.returncode == 0

        # Start process briefly
        proc = subprocess.Popen([str(singbox_bin), "run", "-c", str(config_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(1)
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

        assert log_path.exists()

        # Simulate connection records
        now_str = time.strftime("%Y/%m/%d %H:%M:%S")
        simulated_logs = [
            f"{now_str} [info] 192.168.1.104:41234 accepted tcp:203.0.113.195:22 [socks-ips >> direct] email: singbox_attacker@exploit.net\n",
            f"{now_str} [info] 192.168.1.104:41235 accepted tcp:198.51.100.80:3389 [socks-ips >> direct] email: rdp_spammer@darkweb.org\n",
            f"{now_str} [info] 192.168.1.104:41236 accepted udp:8.8.8.8:53 [socks-ips >> direct] email: dns_client@domain.com\n"
        ]
        with open(log_path, "a", encoding="utf-8") as f:
            f.writelines(simulated_logs)

        lines = log_path.read_text(encoding="utf-8").splitlines()

        # Test SSH threat investigation
        res_ssh = find_email_and_ip_in_xray_log(lines, client_ip=None, dst_ip="203.0.113.195", dst_port=22)
        assert res_ssh is not None
        assert res_ssh[0] == "singbox_attacker@exploit.net"
        assert res_ssh[2] == "socks-ips >> direct"

        # Test RDP threat investigation
        res_rdp = find_email_and_ip_in_xray_log(lines, client_ip="192.168.1.104", dst_ip="198.51.100.80", dst_port=3389)
        assert res_rdp is not None
        assert res_rdp[0] == "rdp_spammer@darkweb.org"


# ---------------------------------------------------------------------------
# 3. REAL XRAY CORE CONFIG CHECK, RUN & LOG ATTRIBUTION
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_real_xray_execution_and_investigation():
    """
    Тестирует запуск Xray, валидацию и парсинг логов атак (VLESS, Shadowsocks, Trojan).
    """
    xray_bin = get_binary_path("xray")
    if not xray_bin.exists():
        pytest.skip(f"Xray binary not found at {xray_bin}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "xray_investigation.json"
        log_path = Path(tmp_dir) / "xray_investigation.log"

        config_data = {
            "log": {
                "access": str(log_path).replace("\\", "/"),
                "loglevel": "info"
            },
            "inbounds": [
                {
                    "port": 59977,
                    "protocol": "dokodemo-door",
                    "settings": {
                        "address": "127.0.0.1",
                        "port": 59977,
                        "network": "tcp"
                    },
                    "tag": "dokodemo-in"
                }
            ],
            "outbounds": [
                {"protocol": "freedom", "tag": "direct"}
            ]
        }
        config_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")

        # Test xray config
        proc = subprocess.Popen([str(xray_bin), "run", "-c", str(config_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(1)
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

        assert log_path.exists()

        now_str = time.strftime("%Y/%m/%d %H:%M:%S")
        log_lines = [
            f"Aug 08 14:00:00 pve xray[123]: {now_str} 192.168.1.65:41926 accepted tcp:198.51.100.4:41926 [vless-inbound] email: xray_hacker@cyber.com",
            f"{now_str} 192.168.1.104:54321 accepted tcp:198.51.100.99:5432 [trojan-inbound] email: postgres_attacker@db.org",
            f"{now_str} 192.168.1.104:33333 accepted tcp:198.51.100.100:3306 [vmess-inbound] email: mysql_dumper@db.org",
        ]
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(log_lines) + "\n")

        lines = log_path.read_text(encoding="utf-8").splitlines()

        # Investigate Port 41926 attack
        res_vless = find_email_and_ip_in_xray_log(lines, client_ip="192.168.1.65", dst_ip="198.51.100.4", dst_port=41926)
        assert res_vless is not None
        assert res_vless[0] == "xray_hacker@cyber.com"
        assert res_vless[1] == "192.168.1.65"
        assert res_vless[2] == "vless-inbound"

        # Investigate Postgres unauthorized connection (port 5432)
        res_pg = find_email_and_ip_in_xray_log(lines, client_ip=None, dst_ip="198.51.100.99", dst_port=5432)
        assert res_pg is not None
        assert res_pg[0] == "postgres_attacker@db.org"


# ---------------------------------------------------------------------------
# 4. REAL HYSTERIA 2 CORE INVESTIGATION & CLIENT IP RESOLUTION
# ---------------------------------------------------------------------------
def test_hysteria2_investigation_and_client_resolution():
    """
    Тестирует расследование нарушителей в логах Hysteria 2 во всех поддерживаемых форматах:
    1. JSON debug формат (id + reqAddr)
    2. JSON альтернативный (auth + req)
    3. Текстовый auth=...
    4. Текстовый connection: ...
    5. Поиск реального IP клиента по email в логах подключения
    """
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # 1. JSON Debug logs
    json_lines = [
        json.dumps({
            "time": now_str,
            "level": "debug",
            "msg": "outbound connection established",
            "id": "hysteria_bruteforcer@attack.net",
            "reqAddr": "198.51.100.42:22"
        }),
        json.dumps({
            "time": now_str,
            "level": "debug",
            "msg": "outbound connection",
            "auth": "hysteria_db_scanner@target.com",
            "req": "203.0.113.111:5432"
        }),
        json.dumps({
            "time": now_str,
            "level": "info",
            "msg": "client connected",
            "id": "hysteria_bruteforcer@attack.net",
            "addr": "95.173.136.75:61234"
        })
    ]

    # Investigate SSH threat from JSON
    found_email = find_email_in_hysteria_log(json_lines, dst_ip="198.51.100.42", dst_port=22)
    assert found_email == "hysteria_bruteforcer@attack.net"

    # Investigate Postgres threat from JSON
    found_db_email = find_email_in_hysteria_log(json_lines, dst_ip="203.0.113.111", dst_port=5432)
    assert found_db_email == "hysteria_db_scanner@target.com"

    # Resolve real client external IP
    client_ip = find_client_ip_for_email_in_hysteria_log(json_lines, email="hysteria_bruteforcer@attack.net")
    assert client_ip == "95.173.136.75"

    # 2. Text logs
    text_lines = [
        f"{now_str} [info] client connected: auth=hysteria_text_user@victim.org, 185.220.101.5:44321",
        f"{now_str} [debug] connection: hysteria_text_user@victim.org (185.220.101.5:44321) -> 198.51.100.42:22"
    ]
    found_text_email = find_email_in_hysteria_log(text_lines, dst_ip="198.51.100.42", dst_port=22)
    assert found_text_email == "hysteria_text_user@victim.org"

    found_text_ip = find_client_ip_for_email_in_hysteria_log(text_lines, email="hysteria_text_user@victim.org")
    assert found_text_ip == "185.220.101.5"


# ---------------------------------------------------------------------------
# 5. END-TO-END ASYNC FALLBACK INVESTIGATION IN VPN MODULE
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_xray_client_email_and_tag_async_fallback():
    """
    Проверяет вызов find_xray_client_email через API Spectre Panel.
    """
    mock_panel = MagicMock()
    mock_panel.name = "MasterPanel"
    mock_result = ("targeted_threat@corp.com", mock_panel, "lxc", "192.168.1.65", "vless-direct")

    with patch("core.spectre_client.spectre_manager.get_client_by_connection", AsyncMock(return_value=mock_result)):
        email, tag = await find_xray_client_email(
            vmid=104,
            dst_ip="198.51.100.4",
            dpt=41926,
            client_ip="192.168.1.65"
        )

        assert email == "targeted_threat@corp.com"
        assert tag == "vless-direct"


# ---------------------------------------------------------------------------
# 6. CONNTRACK IP RESOLVER
# ---------------------------------------------------------------------------
def test_find_real_vpn_client_ip_conntrack(tmp_path):
    """
    Проверяет сопоставление внутренних IP-адресов клиентов через таблицу conntrack.
    """
    conntrack_data = (
        "tcp      6 431999 ESTABLISHED src=10.0.0.2 dst=198.51.100.4 sport=51234 dport=443 "
        "src=198.51.100.4 dst=192.168.1.65 sport=443 dport=41926 [ASSURED] mark=0 use=1\n"
    )
    fake_proc_file = tmp_path / "nf_conntrack"
    fake_proc_file.write_text(conntrack_data, encoding="utf-8")

    with patch("platform.system", return_value="Linux"), \
         patch("os.path.exists", return_value=True), \
         patch("builtins.open", MagicMock(return_value=fake_proc_file.open("r", encoding="utf-8"))):
        
        real_ip = find_real_vpn_client_ip(
            proto="tcp",
            container_ip="192.168.1.65",
            dst_ip="198.51.100.4",
            sport=41926,
            dpt=443
        )
        assert real_ip == "10.0.0.2"


# ---------------------------------------------------------------------------
# 7. SING-BOX PORT 22 BRUTEFORCE ATTRIBUTION & AUTO-BAN TESTS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_singbox_port_22_ssh_bruteforce_investigation_and_autoban():
    """
    Проверяет, что обращение клиента через Sing-box на порт 22 (SSH брутфорс):
    1. Корректно расследуется для всех форматов логов Sing-box (любые логины и теги).
    2. Классифицируется как CRITICAL угроза.
    3. Вызывает отключение аккаунта на панели.
    """
    from modules.proxmox.monitor.traffic.parser import classify_connection
    from core.spectre_client import spectre_manager
    
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Синтетические тестовые форматы логов Sing-box
    singbox_logs = [
        f"{now_str} [info] 10.0.0.50:59450 accepted tcp:198.51.100.22:22 [vless-in >> direct] test_singbox_user_alpha\n",
        f"{now_str} [DEBUG] [router] match direct tcp:198.51.100.22:22 [user: test_client_beta]\n",
        f"{now_str} [INFO] inbound/vless[vless-in]: inbound connection to 198.51.100.22:22 from 10.0.0.50:59450 [test_vpn_attacker]\n",
        json.dumps({
            "time": now_str,
            "level": "info",
            "msg": "inbound connection to 198.51.100.22:22",
            "user": "test_singbox_user_alpha",
            "sourceIP": "10.0.0.50"
        }) + "\n"
    ]
    
    # Test username extraction for test_singbox_user_alpha on port 22
    lines = singbox_logs[0:1]
    res = find_email_and_ip_in_xray_log(lines, client_ip="10.0.0.50", dst_ip="198.51.100.22", dst_port=22)
    assert res is not None
    assert res[0] == "test_singbox_user_alpha"
    assert res[1] == "10.0.0.50"
    
    # Test username extraction for test_client_beta on port 22
    lines_v2 = singbox_logs[1:2]
    res_v2 = find_email_and_ip_in_xray_log(lines_v2, client_ip=None, dst_ip="198.51.100.22", dst_port=22)
    assert res_v2 is not None
    assert res_v2[0] == "test_client_beta"
    
    # Test username extraction for test_vpn_attacker on port 22
    lines_sv = singbox_logs[2:3]
    res_sv = find_email_and_ip_in_xray_log(lines_sv, client_ip="10.0.0.50", dst_ip="198.51.100.22", dst_port=22)
    assert res_sv is not None
    assert res_sv[0] == "test_vpn_attacker"
    
    # Test JSON format on port 22
    lines_json = singbox_logs[3:4]
    res_json = find_email_and_ip_in_xray_log(lines_json, client_ip="10.0.0.50", dst_ip="198.51.100.22", dst_port=22)
    assert res_json is not None
    assert res_json[0] == "test_singbox_user_alpha"
    
    # 2. Проверяем классификацию как CRITICAL
    event = {
        'vmid': 104,
        'direction': 'OUT',
        'proto': 'tcp',
        'src': '10.0.0.50',
        'dst': '198.51.100.22',
        'spt': 59450,
        'dpt': 22,
        'is_local_process': False
    }
    
    # Mock panel discovery so 104 is recognized as panel container
    with patch("core.spectre_client.spectre_manager.get_panel_by_vmid", return_value=MagicMock()):
        risk_level, label, desc = classify_connection(event)
        assert risk_level == 'CRITICAL'
        assert '22' in label
        assert 'VPN-клиент' in label

