# bot/core/messages/nodes.py
"""Шаблоны сообщений для мониторинга доступности серверов и узлов Proxmox VE на GFM Markdown с поддержкой i18n."""

import html
from core.messages.i18n import _

def get_vps_offline_alert(ip):
    return _("nodes", "vps_offline_alert", ip=ip)

def get_vps_online_alert(ip):
    return _("nodes", "vps_online_alert", ip=ip)

def get_node_offline_alert(node_name, status):
    return _("nodes", "node_offline_alert", node_name=node_name, status=status)

def get_node_online_alert(node_name):
    return _("nodes", "node_online_alert", node_name=node_name)

def get_system_status_table(pve_nodes=None, pve_error=None, pve_configured=True, services=None):
    rows = []
    rows.append('<table border="1" style="border-collapse: collapse; width: 100%;">')
    rows.append('  <tr style="background-color: #1e1e2e; color: #ffffff;">')
    rows.append(f'    <th colspan="2" style="padding: 8px; text-align: center;"><b>{_("nodes", "status_audit_title")}</b></th>')
    rows.append('  </tr>')
    
    # 1. Hypervisor section
    rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
    rows.append(f'    <td colspan="2" style="padding: 6px;"><b>{_("nodes", "hypervisor_header")}</b></td>')
    rows.append('  </tr>')
    
    if not pve_configured:
        rows.append('  <tr>')
        rows.append(f'    <td colspan="2" style="padding: 8px;">{_("nodes", "pve_not_configured")}</td>')
        rows.append('  </tr>')
    elif pve_error:
        escaped_err = html.escape(str(pve_error))
        rows.append('  <tr>')
        rows.append(f'    <td colspan="2" style="padding: 8px; color: #f38ba8;">{_("nodes", "pve_error", error=escaped_err)}</td>')
        rows.append('  </tr>')
    elif not pve_nodes:
        rows.append('  <tr>')
        rows.append(f'    <td colspan="2" style="padding: 8px; color: #f38ba8;">{_("nodes", "pve_nodes_not_found")}</td>')
        rows.append('  </tr>')
    else:
        for node in pve_nodes:
            name = node.get('node', 'unknown')
            status = node.get('status', 'offline')
            if status == 'online':
                cpu = node.get('cpu', 0) * 100
                mem = node.get('mem', 0) / (1024**3)
                maxmem = node.get('maxmem', 1) / (1024**3)
                detail = _("nodes", "pve_online_detail", cpu=cpu, mem=mem, maxmem=maxmem)
            else:
                detail = _("nodes", "pve_offline_detail")
            rows.append('  <tr>')
            rows.append(f'    <td style="padding: 8px; width: 35%;"><code>{html.escape(name)}</code></td>')
            rows.append(f'    <td style="padding: 8px;">{detail}</td>')
            rows.append('  </tr>')
            
    # 2. Security Services section
    rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
    rows.append(f'    <td colspan="2" style="padding: 6px;"><b>{_("nodes", "security_services_header")}</b></td>')
    rows.append('  </tr>')
    
    if not services:
        services = {}
        
    # LXC Resource Monitor
    resource_running = services.get("resource_monitor")
    resource_status = _("nodes", "service_active") if resource_running else _("nodes", "service_stopped")
    rows.append('  <tr>')
    rows.append('    <td style="padding: 8px; width: 35%;"><b>LXC Resource Monitor</b></td>')
    rows.append(f'    <td style="padding: 8px;">{resource_status}</td>')
    rows.append('  </tr>')
    
    # LXC Auth Watcher
    auth_running = services.get("auth_watcher")
    auth_status = _("nodes", "service_active") if auth_running else _("nodes", "service_stopped")
    rows.append('  <tr>')
    rows.append('    <td style="padding: 8px;"><b>LXC Auth Watcher</b></td>')
    rows.append(f'    <td style="padding: 8px;">{auth_status} (auth.log)</td>')
    rows.append('  </tr>')
    
    # Active IPS Engine
    ips_running = services.get("ips_engine")
    ips_status = _("nodes", "ips_enabled") if ips_running else _("nodes", "ips_disabled")
    rows.append('  <tr>')
    rows.append('    <td style="padding: 8px;"><b>Active IPS Engine</b></td>')
    rows.append(f'    <td style="padding: 8px;">{ips_status} (iptables)</td>')
    rows.append('  </tr>')
    
    # Remote VPS Monitor
    remote_val = services.get("remote_monitor")
    if remote_val is None:
        remote_status = _("nodes", "remote_vps_disabled_env")
    else:
        remote_status = _("nodes", "service_active") if remote_val else _("nodes", "service_stopped")
    rows.append('  <tr>')
    rows.append('    <td style="padding: 8px;"><b>Remote VPS Monitor</b></td>')
    rows.append(f'    <td style="padding: 8px;">{remote_status}</td>')
    rows.append('  </tr>')
    
    rows.append('</table>')
    return "\n".join(rows)
