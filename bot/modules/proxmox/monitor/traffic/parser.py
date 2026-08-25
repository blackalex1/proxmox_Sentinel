import os
from typing import Optional, Dict, Any, Tuple
from core.config import settings
from core import sentinel_core_bridge

def find_kernel_log_path() -> Optional[str]:
    """Поиск файла системного лога, куда ядро пишет сообщения от iptables."""
    paths = ["/var/log/messages", "/var/log/syslog", "/var/log/kern.log"]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def is_vpn_vmid(vmid: int) -> bool:
    """Проверка, является ли VMID VPN-контейнером."""
    if vmid == settings.vpn_vmid:
        return True
    try:
        from core.spectre_client import spectre_manager
        if spectre_manager.get_panel_by_vmid(int(vmid)) is not None:
            return True
    except Exception:
        pass
    return False

def _build_classifier_policy(event_vmid: Optional[int] = None) -> Dict[str, Any]:
    """Формирует актуальную конфигурацию политики для Go ядра sentinel_core."""
    vpn_vmids = [settings.vpn_vmid] if settings.vpn_vmid else []
    if event_vmid is not None and is_vpn_vmid(event_vmid) and event_vmid not in vpn_vmids:
        vpn_vmids.append(event_vmid)
    try:
        from core.spectre_client import spectre_manager
        for p in spectre_manager.panels.values():
            if p.source_type == "lxc" and p.identifier and str(p.identifier).isdigit():
                v_id = int(p.identifier)
                if v_id not in vpn_vmids:
                    vpn_vmids.append(v_id)
    except Exception:
        pass

    return {
        "vpn_vmid": settings.vpn_vmid or 100,
        "vpn_vmids": vpn_vmids,
        "trusted_admin_ips": settings.trusted_admin_ips or [],
        "proxmox_host": settings.proxmox_host or "",
        "sensitive_ports": settings.monitor_lxc_ports_sensitive or [22, 23, 3389, 3306, 5432, 27017, 6379, 8006],
        "whitelist_ports": settings.monitor_lxc_ports_whitelist or [80, 443, 53, 123],
        "vpn_ports": settings.monitor_lxc_vpn_ports or [443, 8443, 2083, 2087, 2096],
        "lxc_whitelist_vmids": settings.ips_lxc_whitelist or [],
        "alert_vpn_client_unusual_ports": bool(settings.alert_vpn_client_unusual_ports),
    }

def classify_connection(event: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Классифицирует сетевое подключение через Go-ядро sentinel_core.
    Возвращает кортеж: (risk_level, label, description)
    risk_level: 'INFO', 'WARNING', 'CRITICAL'
    """
    policy = _build_classifier_policy(event_vmid=event.get("vmid"))
    return sentinel_core_bridge.classify_connection(event, policy=policy, lang="ru")


def parse_iptables_line(line: str) -> Optional[Dict[str, Any]]:
    """Парсинг лог-линии iptables ядра через Go-ядро sentinel_core."""
    vpn_vmid = settings.vpn_vmid or 100
    return sentinel_core_bridge.parse_iptables_line(line, vpn_vmid=vpn_vmid)
