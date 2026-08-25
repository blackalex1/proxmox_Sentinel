import datetime
import re
from typing import Optional, List, Tuple
from core import sentinel_core_bridge

def parse_xray_timestamp(line: str) -> Optional[datetime.datetime]:
    """Парсинг временной метки Xray/Sing-box."""
    try:
        match = re.search(r"(\d{4}[/-]\d{2}[/-]\d{2}[ T]\d{2}:\d{2}:\d{2})", line)
        if match:
            t_str = match.group(1).replace("/", "-").replace("T", " ")
            return datetime.datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None

def parse_hysteria_timestamp(line: str) -> Optional[datetime.datetime]:
    """Парсинг временной метки Hysteria 2."""
    try:
        match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
        if match:
            return datetime.datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%S")
    except Exception:
        pass
    return None

def find_email_in_hysteria_log(
    lines: List[str],
    dst_ip: Optional[str],
    dst_port: int,
    max_age_sec: int = 300
) -> Optional[str]:
    """Поиск пользователя/email в логах Hysteria 2 через Go-ядро sentinel_core."""
    return sentinel_core_bridge.find_hysteria_client_email(
        lines=lines,
        dst_ip=dst_ip,
        dst_port=dst_port,
        max_age_sec=max_age_sec
    )

def find_client_ip_for_email_in_hysteria_log(
    lines: List[str],
    email: str,
    max_age_sec: int = 600
) -> Optional[str]:
    """Поиск последнего IP пользователя Hysteria 2 через Go-ядро sentinel_core."""
    return sentinel_core_bridge.find_client_ip_for_email_in_hysteria_log(
        lines=lines,
        email=email,
        max_age_sec=max_age_sec
    )

def find_email_and_ip_in_xray_log(
    lines: List[str],
    client_ip: Optional[str],
    dst_ip: Optional[str],
    dst_port: int,
    max_age_sec: int = 300
) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    """Поиск пользователя, IP и тега инбаунда в логах Xray/Sing-box через Go-ядро sentinel_core."""
    email, ip, tag = sentinel_core_bridge.find_xray_client_email(
        lines=lines,
        dst_ip=dst_ip,
        dst_port=dst_port,
        client_ip=client_ip,
        max_age_sec=max_age_sec
    )
    if email:
        return email, ip, tag
    return None
