import re
import logging
import aiohttp
from core.config import settings

async def find_mihomo_connection_id(src_ip, src_port, dst_port):
    """Ищет ID активного соединения в Mihomo по IP/порту источника и порту назначения."""
    try:
        api_url = settings.mihomo_api_url
        headers = {}
        if settings.mihomo_api_secret:
            headers["Authorization"] = f"Bearer {settings.mihomo_api_secret}"
            
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/connections", headers=headers, timeout=2) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    connections = data.get("connections", [])
                    for conn in connections:
                        metadata = conn.get("metadata", {})
                        conn_src_ip = metadata.get("sourceIP", "")
                        conn_src_port = int(metadata.get("sourcePort", 0)) if str(metadata.get("sourcePort", "")).isdigit() else 0
                        conn_dst_port = int(metadata.get("destinationPort", 0)) if str(metadata.get("destinationPort", "")).isdigit() else 0
                        
                        if conn_src_ip == src_ip and conn_src_port == src_port and conn_dst_port == dst_port:
                            return conn.get("id")
    except Exception as e:
        logging.error(f"Ошибка при поиске ID соединения в Mihomo: {e}")
    return None

async def close_mihomo_connection(conn_id):
    """Разрывает активное соединение в Mihomo по его ID."""
    try:
        api_url = settings.mihomo_api_url
        headers = {}
        if settings.mihomo_api_secret:
            headers["Authorization"] = f"Bearer {settings.mihomo_api_secret}"
            
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{api_url}/connections/{conn_id}", headers=headers, timeout=2) as resp:
                if resp.status in (200, 204):
                    return True
    except Exception as e:
        logging.error(f"Ошибка при разрыве соединения {conn_id} в Mihomo: {e}")
    return False

def parse_router_conntrack_line(line):
    """
    Разбор строки событий conntrack роутера.
    Пример: "[NEW] tcp      6 120 SYN_SENT src=192.168.1.69 dst=5.255.255.242 sport=33296 dport=443 ..."
    """
    try:
        if "[NEW]" not in line:
            return None
            
        src_match = re.search(r"src=([^\s]+)", line)
        dst_match = re.search(r"dst=([^\s]+)", line)
        proto_match = re.search(r"(\btcp\b|\budp\b)", line.lower())
        spt_match = re.search(r"sport=(\d+)", line)
        dpt_match = re.search(r"dport=(\d+)", line)
        
        if not (src_match and dst_match and proto_match and spt_match and dpt_match):
            return None
            
        return {
            'src_ip': src_match.group(1),
            'dst_host': dst_match.group(1),
            'proto': proto_match.group(1).upper(),
            'src_port': int(spt_match.group(1)),
            'dst_port': int(dpt_match.group(1))
        }
    except Exception as e:
        logging.error(f"Ошибка парсинга строки conntrack роутера: {e}")
        return None

def parse_router_iptables_line(line):
    """
    Разбор лог-строки iptables/nftables роутера.
    Пример: "ROUTER-IPS: IN=br-lan OUT= SRC=192.168.1.150 DST=203.0.113.100 PROTO=TCP SPT=54321 DPT=22"
    """
    try:
        if "ROUTER-IPS:" not in line:
            return None
            
        src_match = re.search(r"SRC=([^\s]+)", line)
        dst_match = re.search(r"DST=([^\s]+)", line)
        proto_match = re.search(r"PROTO=([^\s]+)", line)
        spt_match = re.search(r"SPT=(\d+)", line)
        dpt_match = re.search(r"DPT=(\d+)", line)
        
        if not (src_match and dst_match and proto_match and spt_match and dpt_match):
            return None
            
        return {
            'src_ip': src_match.group(1),
            'dst_host': dst_match.group(1),
            'proto': proto_match.group(1).upper(),
            'src_port': int(spt_match.group(1)),
            'dst_port': int(dpt_match.group(1))
        }
    except Exception as e:
        logging.error(f"Ошибка парсинга строки лога роутера: {e}")
        return None
