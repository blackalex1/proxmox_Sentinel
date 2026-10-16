import logging
import os
from typing import Optional, Dict, Any, Tuple, Set, List
from core.config import settings
from core import sentinel_core_bridge

logger = logging.getLogger(__name__)

# Кэш доверенных VPN/транзитных VMID в памяти
_trusted_vpn_vmids_cache: Set[int] = set()
_cache_initialized: bool = False

def get_trusted_vpn_vmids_cache() -> Set[int]:
    global _trusted_vpn_vmids_cache, _cache_initialized
    if not _cache_initialized:
        try:
            from core.db import get_trusted_vpn_vmids_sync_from_db
            db_vmids = get_trusted_vpn_vmids_sync_from_db()
            _trusted_vpn_vmids_cache.update(db_vmids)
            _cache_initialized = True
        except Exception as e:
            logger.debug("Failed to sync load trusted vpn vmids: %s", e)
    return _trusted_vpn_vmids_cache

async def init_trusted_vpn_vmids_cache():
    global _trusted_vpn_vmids_cache, _cache_initialized
    try:
        from core.db import get_trusted_vpn_vmids
        db_vmids = await get_trusted_vpn_vmids()
        _trusted_vpn_vmids_cache = set(db_vmids)
        _cache_initialized = True
    except Exception as e:
        logger.error("Error initializing trusted vpn vmids cache: %s", e)

async def update_trusted_vpn_vmids_cache():
    await init_trusted_vpn_vmids_cache()

def get_trusted_vpn_vmids_sync() -> List[int]:
    cached = set(get_trusted_vpn_vmids_cache())
    try:
        from core.spectre_client import spectre_manager
        for p in spectre_manager.panels.values():
            if p.source_type == "lxc" and p.identifier and str(p.identifier).isdigit():
                cached.add(int(p.identifier))
    except Exception:
        pass
    return sorted(list(cached))

def find_kernel_log_path() -> Optional[str]:
    """Поиск файла системного лога, куда ядро пишет сообщения от iptables."""
    paths = ["/var/log/messages", "/var/log/syslog", "/var/log/kern.log"]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def is_vpn_vmid(vmid: int) -> bool:
    """Проверка, является ли VMID доверенным VPN/транзитным контейнером."""
    if vmid in get_trusted_vpn_vmids_cache():
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
    vpn_vmids = get_trusted_vpn_vmids_sync()
    if event_vmid is not None and is_vpn_vmid(event_vmid) and event_vmid not in vpn_vmids:
        vpn_vmids.append(event_vmid)

    primary_vmid = vpn_vmids[0] if vpn_vmids else 0

    return {
        "vpn_vmid": primary_vmid,
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
    vpn_vmids = get_trusted_vpn_vmids_sync()
    primary_vmid = vpn_vmids[0] if vpn_vmids else 0
    return sentinel_core_bridge.parse_iptables_line(line, vpn_vmid=primary_vmid)
