import logging
import os
from typing import Optional, Dict, Any, Tuple
from core.config import settings
from core import sentinel_core_bridge
from modules.proxmox.monitor.trusted_vmids import (
    get_trusted_vpn_vmids_cache,
    init_trusted_vpn_vmids_cache,
    update_trusted_vpn_vmids_cache,
    get_trusted_vpn_vmids_sync,
    is_vpn_vmid,
)

logger = logging.getLogger(__name__)


def find_kernel_log_path() -> Optional[str]:
    """Поиск файла системного лога, куда ядро пишет сообщения от iptables."""
    paths = ["/var/log/messages", "/var/log/syslog", "/var/log/kern.log"]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def _build_classifier_policy(event_vmid: Optional[int] = None) -> Dict[str, Any]:
    """Формирует актуальную конфигурацию политики для Go ядра sentinel_core."""
    vpn_vmids = get_trusted_vpn_vmids_sync()
    if event_vmid is not None and is_vpn_vmid(event_vmid) and event_vmid not in vpn_vmids:
        vpn_vmids.append(event_vmid)

    primary_vmid = vpn_vmids[0] if vpn_vmids else 0

    return {
        "vpn_vmid": primary_vmid,
        "vpn_vmids": vpn_vmids,
        **settings.get_classifier_policy_defaults(),
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
    vpn_vmids = get_trusted_vpn_vmids_sync()
    primary_vmid = vpn_vmids[0] if vpn_vmids else 0
    return sentinel_core_bridge.parse_iptables_line(line, vpn_vmid=primary_vmid)
