# bot/core/messages/traffic.py
"""Шаблоны сообщений для IPS, сетевых атак и трафика на GFM Markdown с поддержкой i18n."""

from core.messages.i18n import _

def get_ips_investigation_success_alert(xray_client, tunnel_email, target_panel_name, server_ip, dst_ip, dpt, block_details_str, unblock_details_str, timestamp):
    return _(
        "traffic", "ips_investigation_success_alert",
        xray_client=xray_client, tunnel_email=tunnel_email,
        target_panel_name=target_panel_name, server_ip=server_ip,
        dst_ip=dst_ip, dpt=dpt, block_details_str=block_details_str,
        unblock_details_str=unblock_details_str, timestamp=timestamp
    )

def get_ips_investigation_failed_alert(tunnel_email, dst_ip, dpt, logs_text, timestamp):
    return _(
        "traffic", "ips_investigation_failed_alert",
        tunnel_email=tunnel_email, dst_ip=dst_ip, dpt=dpt,
        logs_text=logs_text, timestamp=timestamp
    )

def get_ips_sensitive_access_alert(server_ip, proto, src, spt, dst, dpt, timestamp):
    return _(
        "traffic", "ips_sensitive_access_alert",
        server_ip=server_ip, proto=proto, src=src, spt=spt,
        dst=dst, dpt=dpt, timestamp=timestamp
    )

def get_ips_hysteria_attack_alert(server_ip, email, proto, src, spt, dst, dpt, block_details_str, timestamp):
    return _(
        "traffic", "ips_hysteria_attack_alert",
        server_ip=server_ip, email=email, proto=proto,
        src=src, spt=spt, dst=dst, dpt=dpt,
        block_details_str=block_details_str, timestamp=timestamp
    )

def get_ips_xray_attack_alert(server_ip, email, proto, src, spt, dst, dpt, block_details_str, proc_info, timestamp):
    return _(
        "traffic", "ips_xray_attack_alert",
        server_ip=server_ip, email=email, proto=proto,
        src=src, spt=spt, dst=dst, dpt=dpt,
        block_details_str=block_details_str, proc_info=proc_info,
        timestamp=timestamp
    )

def get_ips_whitelisted_alert(server_ip, proc_name, proto, src, spt, dst, dpt, timestamp):
    return _(
        "traffic", "ips_whitelisted_alert",
        server_ip=server_ip, proc_name=proc_name, proto=proto,
        src=src, spt=spt, dst=dst, dpt=dpt, timestamp=timestamp
    )

def get_ips_process_killed_alert(server_ip, proc_name, killed_pid, proto, src, spt, dst, dpt, timestamp):
    return _(
        "traffic", "ips_process_killed_alert",
        server_ip=server_ip, proc_name=proc_name, killed_pid=killed_pid,
        proto=proto, src=src, spt=spt, dst=dst, dpt=dpt,
        timestamp=timestamp
    )

def get_ips_process_warning_alert(server_ip, proc_name, proto, src, spt, dst, dpt, timestamp):
    proc_info = _("traffic", "proc_info_tmpl", proc_name=proc_name) if proc_name else ""
    return _(
        "traffic", "ips_process_warning_alert",
        server_ip=server_ip, proto=proto, src=src, spt=spt,
        dst=dst, dpt=dpt, proc_info=proc_info, timestamp=timestamp
    )

def get_local_traffic_alert(title, desc_with_client, vmid, container_name, label, proto, direction, src, spt, dst, dpt, real_client_ip, xray_client_email, block_details_list, timestamp):
    clean_h1 = _("traffic", "local_h1_default")
    if "Разрешенное соединение" in title or "Allowed Connection" in title or "Connection Allowed" in title:
        clean_h1 = _("traffic", "local_h1_allowed")
    elif "Атака заблокирована" in title or "Attack Blocked" in title:
        clean_h1 = _("traffic", "local_h1_blocked")
    elif "КРИТИЧЕСКАЯ УГРОЗА" in title or "CRITICAL" in title:
        clean_h1 = _("traffic", "local_h1_critical")
    elif "ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ" in title or "SUSPICIOUS" in title or "Warning" in title:
        clean_h1 = _("traffic", "local_h1_warning")

    vpn_ip_row = ""
    if real_client_ip and real_client_ip != src:
        vpn_ip_row = _("traffic", "local_real_ip", real_client_ip=real_client_ip)
    
    vpn_client_row = ""
    if xray_client_email:
        vpn_client_row = _("traffic", "local_vpn_client", xray_client_email=xray_client_email)
        
    block_details_block = ""
    if block_details_list:
        block_details_str = "\n".join(block_details_list)
        block_details_block = _("traffic", "local_block_status", block_details_str=block_details_str)

    direction_text = _("traffic", "local_direction_in") if direction == 'IN' else _("traffic", "local_direction_out")

    return _(
        "traffic", "local_traffic_alert",
        clean_h1=clean_h1, title=title, desc_with_client=desc_with_client,
        vmid=vmid, container_name=container_name, label=label,
        proto=proto, direction_text=direction_text, src=src, spt=spt,
        dst=dst, dpt=dpt, vpn_ip_row=vpn_ip_row, vpn_client_row=vpn_client_row,
        block_details_block=block_details_block, timestamp=timestamp
    )
