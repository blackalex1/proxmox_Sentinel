from typing import Optional, Dict, Any
from core import sentinel_core_bridge

def parse_router_conntrack_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Разбор строки событий conntrack роутера через Go-ядро sentinel_core.
    Пример: "[NEW] tcp      6 120 SYN_SENT src=192.168.1.100 dst=5.255.255.242 sport=33296 dport=443 ..."
    """
    return sentinel_core_bridge.parse_router_conntrack_line(line)

def parse_router_iptables_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Разбор лог-строки iptables/nftables роутера через Go-ядро sentinel_core.
    Пример: "ROUTER-IPS: IN=br-lan OUT= SRC=192.168.1.150 DST=203.0.113.100 PROTO=TCP SPT=54321 DPT=22"
    """
    return sentinel_core_bridge.parse_router_iptables_line(line)
