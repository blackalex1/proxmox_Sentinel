import logging
from typing import List, Set

from core.db import get_trusted_vpn_vmids, get_trusted_vpn_vmids_sync_from_db
from core.spectre_client import spectre_manager

logger = logging.getLogger(__name__)

# Кэш доверенных VPN/транзитных VMID в памяти
_trusted_vpn_vmids_cache: Set[int] = set()
_cache_initialized: bool = False


def get_trusted_vpn_vmids_cache() -> Set[int]:
    global _trusted_vpn_vmids_cache, _cache_initialized
    if not _cache_initialized:
        try:
            db_vmids = get_trusted_vpn_vmids_sync_from_db()
            _trusted_vpn_vmids_cache.update(db_vmids)
            _cache_initialized = True
        except Exception as e:
            logger.debug("Failed to sync load trusted vpn vmids: %s", e)
    return _trusted_vpn_vmids_cache


async def init_trusted_vpn_vmids_cache():
    global _trusted_vpn_vmids_cache, _cache_initialized
    try:
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
        for p in spectre_manager.get_lxc_panels():
            if p.identifier and str(p.identifier).isdigit():
                cached.add(int(p.identifier))
    except Exception:
        pass
    return sorted(list(cached))


def is_vpn_vmid(vmid: int) -> bool:
    """Проверка, является ли VMID доверенным VPN/транзитным контейнером."""
    if vmid in get_trusted_vpn_vmids_cache():
        return True
    try:
        if spectre_manager.get_panel_by_vmid(int(vmid)) is not None:
            return True
    except Exception:
        pass
    return False
