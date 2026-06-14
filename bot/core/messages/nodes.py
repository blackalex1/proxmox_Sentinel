# bot/core/messages/nodes.py
"""Шаблоны сообщений для мониторинга доступности серверов и узлов Proxmox VE на GFM Markdown."""

def get_vps_offline_alert(ip):
    return (
        f"# ⚠️ VPS Offline\n"
        f"---\n\n"
        f"### ⚠️ [Remote Monitor] Удаленный VPS-сервер отключен!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 IP-адрес** | `{ip}` |\n"
        f"| **🔌 Статус** | 🔴 Недоступен (SSH порт закрыт) |\n"
    )

def get_vps_online_alert(ip):
    return (
        f"# ✅ VPS Online\n"
        f"---\n\n"
        f"### ✅ [Remote Monitor] Связь с VPS восстановлена!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 IP-адрес** | `{ip}` |\n"
        f"| **🔌 Статус** | 🟢 Доступен (Связь восстановлена) |\n"
    )

def get_node_offline_alert(node_name, status):
    return (
        f"# ⚠️ Node Offline\n"
        f"---\n\n"
        f"### ⚠️ [Cluster Monitor] Сервер недоступен!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🖥 Сервер** | **{node_name}** |\n"
        f"| **🔌 Статус** | 🔴 {status} |\n"
    )

def get_node_online_alert(node_name):
    return (
        f"# ✅ Node Online\n"
        f"---\n\n"
        f"### ✅ [Cluster Monitor] Сервер снова в сети!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🖥 Сервер** | **{node_name}** |\n"
        f"| **🔌 Статус** | 🟢 Доступен |\n"
    )

def get_system_status_table(pve_nodes=None, pve_error=None, pve_configured=True, services=None):
    import html
    
    rows = []
    rows.append('<table border="1" style="border-collapse: collapse; width: 100%;">')
    rows.append('  <tr style="background-color: #1e1e2e; color: #ffffff;">')
    rows.append('    <th colspan="2" style="padding: 8px; text-align: center;"><b>📊 Аудит статуса систем PVE Aegis</b></th>')
    rows.append('  </tr>')
    
    # 1. Hypervisor section
    rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
    rows.append('    <td colspan="2" style="padding: 6px;"><b>🖥 Hypervisor (Proxmox VE)</b></td>')
    rows.append('  </tr>')
    
    if not pve_configured:
        rows.append('  <tr>')
        rows.append('    <td colspan="2" style="padding: 8px;">⚪ <b>Proxmox VE:</b> Не настроен</td>')
        rows.append('  </tr>')
    elif pve_error:
        escaped_err = html.escape(str(pve_error))
        rows.append('  <tr>')
        rows.append('    <td colspan="2" style="padding: 8px; color: #f38ba8;">🔴 <b>Proxmox VE:</b> Ошибка: <code>{}</code></td>'.format(escaped_err))
        rows.append('  </tr>')
    elif not pve_nodes:
        rows.append('  <tr>')
        rows.append('    <td colspan="2" style="padding: 8px; color: #f38ba8;">🔴 <b>Proxmox VE:</b> Ноды не найдены</td>')
        rows.append('  </tr>')
    else:
        for node in pve_nodes:
            name = node.get('node', 'unknown')
            status = node.get('status', 'offline')
            if status == 'online':
                cpu = node.get('cpu', 0) * 100
                mem = node.get('mem', 0) / (1024**3)
                maxmem = node.get('maxmem', 1) / (1024**3)
                detail = f"🟢 online (CPU: {cpu:.1f}% | RAM: {mem:.1f}/{maxmem:.1f} GB)"
            else:
                detail = "🔴 offline"
            rows.append('  <tr>')
            rows.append(f'    <td style="padding: 8px; width: 35%;"><code>{html.escape(name)}</code></td>')
            rows.append(f'    <td style="padding: 8px;">{detail}</td>')
            rows.append('  </tr>')
            
    # 2. Security Services section
    rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
    rows.append('    <td colspan="2" style="padding: 6px;"><b>🛡 Фоновые службы безопасности</b></td>')
    rows.append('  </tr>')
    
    if not services:
        services = {}
        
    # LXC Resource Monitor
    resource_running = services.get("resource_monitor")
    resource_status = "🟢 Активен" if resource_running else "🔴 Остановлен"
    rows.append('  <tr>')
    rows.append('    <td style="padding: 8px; width: 35%;"><b>LXC Resource Monitor</b></td>')
    rows.append(f'    <td style="padding: 8px;">{resource_status}</td>')
    rows.append('  </tr>')
    
    # LXC Auth Watcher
    auth_running = services.get("auth_watcher")
    auth_status = "🟢 Активен" if auth_running else "🔴 Остановлен"
    rows.append('  <tr>')
    rows.append('    <td style="padding: 8px;"><b>LXC Auth Watcher</b></td>')
    rows.append(f'    <td style="padding: 8px;">{auth_status} (auth.log)</td>')
    rows.append('  </tr>')
    
    # Active IPS Engine
    ips_running = services.get("ips_engine")
    ips_status = "🟢 Защита включена" if ips_running else "🔴 Защита выключена"
    rows.append('  <tr>')
    rows.append('    <td style="padding: 8px;"><b>Active IPS Engine</b></td>')
    rows.append(f'    <td style="padding: 8px;">{ips_status} (iptables)</td>')
    rows.append('  </tr>')
    
    # Remote VPS Monitor
    remote_val = services.get("remote_monitor")
    if remote_val is None:
        remote_status = "⚪ Выключен в .env"
    else:
        remote_status = "🟢 Активен" if remote_val else "🔴 Остановлен"
    rows.append('  <tr>')
    rows.append('    <td style="padding: 8px;"><b>Remote VPS Monitor</b></td>')
    rows.append(f'    <td style="padding: 8px;">{remote_status}</td>')
    rows.append('  </tr>')
    
    rows.append('</table>')
    return "\n".join(rows)

