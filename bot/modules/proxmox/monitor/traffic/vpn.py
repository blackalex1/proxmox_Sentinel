import logging
from typing import Optional, Tuple
from core import sentinel_core_bridge

def find_real_vpn_client_ip(proto: str, container_ip: str, dst_ip: str, sport: int, dpt: int) -> Optional[str]:
    """
    Поиск реального внутреннего IP-адреса VPN-клиента из таблицы conntrack хоста через Go-ядро sentinel_core.
    """
    return sentinel_core_bridge.find_real_vpn_client_ip(
        proto=proto,
        container_ip=str(container_ip),
        dst_ip=str(dst_ip),
        sport=int(sport),
        dpt=int(dpt)
    )

async def find_xray_client_email(vmid: int, dst_ip: Optional[str], dpt: int, client_ip: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Ищет email клиента Xray / Sing-box / Hysteria 2 через API Spectre Panel или сессионный трекер ядра.
    Весь парсинг и сбор логов вынесены в Go-ядро sentinel_core.
    """
    try:
        from core.spectre_client import spectre_manager
        res = await spectre_manager.get_client_by_connection(
            client_ip=client_ip,
            dst_ip=dst_ip,
            port=dpt,
            source_type='lxc',
            source_id=str(vmid)
        )
        if res:
            email, panel, source, real_client_ip, inbound_tag = res
            panel_name = getattr(panel, "name", str(panel))
            logging.info("vpn_ips_successfully_found_client_email_via", email, panel_name)
            return email, inbound_tag
    except Exception as e:
        logging.error("error_calling_spectre_panel_api", e)

    return None, None
