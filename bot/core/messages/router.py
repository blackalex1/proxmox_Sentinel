# bot/core/messages/router.py
"""Шаблоны сообщений для роутера и управления клиентами с поддержкой Rich Bot API и i18n."""

import html
from typing import List, Dict, Any, Optional
from core.config import settings
from core.messages.i18n import _

def get_router_recovery_alert(ip, rules_str):
    return _(
        "router", "router_recovery_alert",
        ip=ip, rules_str=rules_str
    )

def get_router_unknown_block_alert(ip, rules_str):
    return _(
        "router", "router_unknown_block_alert",
        ip=ip, rules_str=rules_str
    )

def get_router_autoblock_alert(src_ip, dst_host, dst_port, proto, timestamp):
    return _(
        "router", "router_autoblock_alert",
        src_ip=src_ip, dst_host=dst_host, dst_port=dst_port,
        proto=proto, timestamp=timestamp, threshold=settings.router_max_violations
    )

def get_router_port_alert(type_str, proto, src_ip, src_port, dst_host, dst_port, timestamp):
    return _(
        "router", "router_port_alert",
        type_str=type_str, proto=proto, src_ip=src_ip,
        src_port=src_port, dst_host=dst_host, dst_port=dst_port,
        timestamp=timestamp
    )

def get_router_clients_list_text(has_clients: bool) -> str:
    if not has_clients:
        return _("router", "clients_list_empty")
    return _("router", "clients_list_header")

def get_router_client_details_card(
    hostname: str,
    ip: str,
    mac: str,
    active: bool,
    full_ban: Optional[Dict[str, Any]],
    port_bans: List[Dict[str, Any]]
) -> str:
    status_emoji = _("router", "status_active") if active else _("router", "status_offline")
    port_bans_list = port_bans if isinstance(port_bans, list) else []
    if full_ban:
        ban_status = _("router", "ban_status_full")
    elif port_bans_list:
        ban_status = _("router", "ban_status_ports")
    else:
        ban_status = _("router", "ban_status_none")
        
    bans_count = (1 if full_ban else 0) + len(port_bans_list)
    
    rows = []
    rows.append('<table bordered striped compact>')
    rows.append('  <tr>')
    rows.append(f'    <th colspan="2" align="center"><b>{_("router", "client_details_title")}</b></th>')
    rows.append('  </tr>')
    rows.append('  <tr>')
    rows.append(f'    <td align="left"><b>{_("router", "col_device_name")}</b></td>')
    rows.append(f'    <td align="left"><code>{html.escape(hostname)}</code></td>')
    rows.append('  </tr>')
    rows.append('  <tr>')
    rows.append(f'    <td align="left"><b>{_("router", "col_ip")}</b></td>')
    rows.append(f'    <td align="left"><code>{html.escape(ip)}</code></td>')
    rows.append('  </tr>')
    rows.append('  <tr>')
    rows.append(f'    <td align="left"><b>{_("router", "col_mac")}</b></td>')
    rows.append(f'    <td align="left"><code>{html.escape(mac)}</code></td>')
    rows.append('  </tr>')
    rows.append('  <tr>')
    rows.append(f'    <td align="left"><b>{_("router", "col_net_status")}</b></td>')
    rows.append(f'    <td align="left">{status_emoji}</td>')
    rows.append('  </tr>')
    rows.append('  <tr>')
    rows.append(f'    <td align="left"><b>{_("router", "col_ban_status")}</b></td>')
    rows.append(f'    <td align="left">{ban_status}</td>')
    rows.append('  </tr>')
    rows.append('</table>\n')
    
    rows.append(_("router", "client_active_rules_footer", count=bans_count))
    return "\n".join(rows)

def get_router_ban_all_menu_text(ip: str) -> str:
    return _("router", "prompt_ban_all_duration", ip=ip)

def get_router_ban_port_menu_text(ip: str) -> str:
    return _("router", "prompt_ban_port_service", ip=ip)

def get_router_ban_port_duration_text(ip: str, port_label: str, proto: str) -> str:
    return _("router", "prompt_ban_port_duration", ip=ip, port=port_label, proto=proto)

def get_router_custom_port_prompt_text(ip: str) -> str:
    return _("router", "prompt_custom_port_input", ip=ip)

def get_router_active_bans_text(ip: str, full_ban: Optional[Dict[str, Any]], port_bans: List[Dict[str, Any]]) -> str:
    text = _("router", "active_bans_header", ip=ip)
    if full_ban:
        expire = full_ban.get('expire_time')
        expire_label = expire.split(".")[0].replace("T", " ") if expire else _("router", "dur_forever")
        text += _("router", "active_ban_ip_item", expire=expire_label)
        
    for pb in port_bans:
        p = pb.get('port')
        proto = pb.get('protocol')
        expire = pb.get('expire_time')
        expire_label = expire.split(".")[0].replace("T", " ") if expire and expire != "never" else _("router", "dur_forever")
        text += _("router", "active_ban_port_item", port=p, proto=proto, expire=expire_label)
        
    if not full_ban and not port_bans:
        text += _("router", "active_bans_empty")
        
    return text
