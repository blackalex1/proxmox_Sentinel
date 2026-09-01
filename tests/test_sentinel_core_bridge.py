import pytest
from core import sentinel_core_bridge

def test_bridge_parse_iptables_line():
    line = (
        "May 30 02:47:54 proxmox kernel: [12345.67] HOST_CONN_OUT: "
        "IN= OUT=eth0 SRC=192.168.1.120 DST=192.168.1.1 LEN=60 "
        "TOS=0x00 PREC=0x00 TTL=64 ID=21151 DF PROTO=TCP SPT=56088 DPT=22"
    )
    ev = sentinel_core_bridge.parse_iptables_line(line, vpn_vmid=100)
    assert ev is not None
    assert ev["vmid"] == 0
    assert ev["direction"] == "OUT"
    assert ev["proto"] == "TCP"
    assert ev["src"] == "192.168.1.120"
    assert ev["dst"] == "192.168.1.1"
    assert ev["spt"] == 56088
    assert ev["dpt"] == 22

def test_bridge_classify_connection():
    event = {
        "vmid": 0,
        "direction": "IN",
        "proto": "TCP",
        "src": "203.0.113.5",
        "dst": "192.168.1.120",
        "spt": 45678,
        "dpt": 22
    }
    policy = {
        "trusted_admin_ips": ["198.51.100.1"],
        "sensitive_ports": [22, 8006]
    }
    risk, label, desc = sentinel_core_bridge.classify_connection(event, policy=policy, lang="ru")
    assert risk == "CRITICAL"
    assert "Вход на Хост" in label

def test_bridge_find_real_vpn_client_ip():
    dump = (
        "ipv4     2 tcp      6 431999 ESTABLISHED src=192.168.1.55 dst=1.1.1.1 sport=54321 dport=443 "
        "src=1.1.1.1 dst=10.0.0.100 sport=443 dport=54321 [ASSURED] mark=0 use=1\n"
    )
    res = sentinel_core_bridge.find_real_vpn_client_ip("tcp", "10.0.0.100", "1.1.1.1", 54321, 443, conntrack_dump=dump)
    assert res == "192.168.1.55"

def test_bridge_find_xray_client_email():
    import datetime
    now_str = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    lines = [
        f"{now_str} [info] 192.168.1.100:54321 accepted tcp:13.251.130.193:22 [VLESS-TCP >> direct] email: attacker@xray.com"
    ]
    email, ip, tag = sentinel_core_bridge.find_xray_client_email(lines, dst_ip="13.251.130.193", dst_port=22)
    assert email == "attacker@xray.com"
    assert ip == "192.168.1.100"
    assert tag == "VLESS-TCP >> direct"

def test_bridge_find_hysteria_client_email():
    import datetime
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f'{{"time":"{now_str}","id":"tunnel_user","reqAddr":"13.251.130.193:22"}}'
    ]
    email = sentinel_core_bridge.find_hysteria_client_email(lines, dst_ip="13.251.130.193", dst_port=22)
    assert email == "tunnel_user"

def test_bridge_parse_auth_line():
    ssh_line = "May 30 16:45:10 proxmox sshd[12345]: Accepted publickey for root from 198.51.100.22 port 54321 ssh2: RSA SHA256:abc123xyz"
    ev = sentinel_core_bridge.parse_auth_line(ssh_line)
    assert ev is not None
    assert ev["type"] == "SSH_LOGIN"
    assert ev["user"] == "root"
    assert ev["source_ip"] == "198.51.100.22"
    assert ev["port"] == 54321
    assert ev["pid"] == 12345
    assert ev["auth_method"] == "publickey"
    assert ev["key_fingerprint"] == "SHA256:abc123xyz"

def test_bridge_parse_router():
    ct_line = "[NEW] tcp      6 120 SYN_SENT src=192.168.1.100 dst=5.255.255.242 sport=33296 dport=443 [UNREPLIED]"
    ev = sentinel_core_bridge.parse_router_conntrack_line(ct_line)
    assert ev is not None
    assert ev["src_ip"] == "192.168.1.100"
    assert ev["dst_host"] == "5.255.255.242"
    assert ev["proto"] == "TCP"
    assert ev["src_port"] == 33296
    assert ev["dst_port"] == 443


def test_bridge_configure_router_threat_detector():
    res = sentinel_core_bridge.configure_router_threat_detector(
        scan_limit=5,
        burst_limit_1m=12,
        burst_limit_3m=18,
        target_brute_limit=4,
        window_minutes=15,
        sensitive_ports=[22, 8006, 5432]
    )
    assert res is True

