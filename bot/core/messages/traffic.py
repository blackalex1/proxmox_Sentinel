# bot/core/messages/traffic.py
"""Шаблоны сообщений для IPS, сетевых атак и трафика на GFM Markdown."""

def get_ips_investigation_success_alert(xray_client, tunnel_email, target_panel_name, server_ip, dst_ip, dpt, block_details_str, unblock_details_str, timestamp):
    return (
        f"# ✅ IPS Investigation Done\n"
        f"---\n\n"
        f"### ✅ [IPS: Расследование завершено] Нарушитель найден!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **👤 Нарушитель (Xray)** | `{xray_client}` (Заблокирован) |\n"
        f"| **🔓 Hysteria туннель** | `{tunnel_email}` (Разблокирован) |\n"
        f"| **🌐 Маршрут атаки** | Вход: `{target_panel_name}` (Xray)<br/>Транзит: `{tunnel_email}` (Hysteria2)<br/>Выход: VPS `{server_ip}` → `{dst_ip}:{dpt}` |\n\n"
        f"✨ *Все остальные пользователи туннеля снова в сети!*\n\n"
        f"<details>\n"
        f"  <summary>📋 <b>Показать детали глобального бана нарушителя</b></summary>\n"
        f"  <pre><code>{block_details_str}</code></pre>\n"
        f"</details>\n\n"
        f"<details>\n"
        f"  <summary>📋 <b>Показать детали разблокировки туннеля Hysteria</b></summary>\n"
        f"  <pre><code>{unblock_details_str}</code></pre>\n"
        f"</details>\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )

def get_ips_investigation_failed_alert(tunnel_email, dst_ip, dpt, logs_text, timestamp):
    return (
        f"# ⚠️ IPS Investigation Failed\n"
        f"---\n\n"
        f"### ⚠️ [IPS: Расследование не удалось] Виновник не обнаружен!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🚨 Статус туннеля** | `{tunnel_email}` (Оставлен в бане) |\n"
        f"| **🎯 Цель атаки** | `{dst_ip}:{dpt}` |\n\n"
        f"<details>\n"
        f"  <summary>🔍 <b>Показать собранные фрагменты логов</b></summary>\n"
        f"  <pre><code>{logs_text}</code></pre>\n"
        f"</details>\n\n"
        f"👇 Вы можете разблокировать туннель вручную в один клик:\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )

def get_ips_sensitive_access_alert(server_ip, proto, src, spt, dst, dpt, timestamp):
    return (
        f"# 🚨 Traffic Security Alert\n"
        f"---\n\n"
        f"### 🚨 [VPS Traffic Security] Входящий доступ на sensitive порт!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 VPS Server** | `{server_ip}` |\n"
        f"| **🔌 Протокол** | `{proto}` |\n"
        f"| **👤 Источник** | `{src}:{spt}` |\n"
        f"| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )

def get_ips_hysteria_attack_alert(server_ip, email, proto, src, spt, dst, dpt, block_details_str, timestamp):
    return (
        f"# 🚨 Traffic Attack Detected\n"
        f"---\n\n"
        f"### 🚨 [VPS Traffic IPS] Обнаружена атака через Hysteria-туннель!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 VPS Server** | `{server_ip}` |\n"
        f"| **🔥 Временный бан** | `{email}` |\n"
        f"| **🔌 Протокол** | `{proto}` |\n"
        f"| **👤 Источник** | `{src}:{spt}` |\n"
        f"| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        f"🔍 *Запущено асинхронное расследование для поиска конкретного виновника внутри туннеля...*\n\n"
        f"<details>\n"
        f"  <summary>📋 <b>Показать статус блокировки туннеля</b></summary>\n"
        f"  <pre><code>{block_details_str}</code></pre>\n"
        f"</details>\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )

def get_ips_xray_attack_alert(server_ip, email, proto, src, spt, dst, dpt, block_details_str, proc_info, timestamp):
    return (
        f"# 🚨 Traffic Attack Blocked\n"
        f"---\n\n"
        f"### 🚨 [VPS Traffic IPS] Блокировка сетевой атаки!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 VPS Server** | `{server_ip}` |\n"
        f"| **👤 Нарушитель (Xray)** | `{email}` |\n"
        f"| **🔌 Протокол** | `{proto}` |\n"
        f"| **👤 Источник** | `{src}:{spt}`{proc_info} |\n"
        f"| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        f"<details>\n"
        f"  <summary>🚨 <b>Показать статус авто-блокировки аккаунта нарушителя</b></summary>\n"
        f"  <pre><code>{block_details_str}</code></pre>\n"
        f"</details>\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )

def get_ips_whitelisted_alert(server_ip, proc_name, proto, src, spt, dst, dpt, timestamp):
    return (
        f"# ℹ️ Connection Allowed\n"
        f"---\n\n"
        f"### ℹ️ [VPS Traffic] Разрешенное соединение (в белом списке IPS)\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 VPS Server** | `{server_ip}` |\n"
        f"| **📁 Процесс** | `{proc_name}` |\n"
        f"| **🔌 Протокол** | `{proto}` |\n"
        f"| **👤 Источник** | `{src}:{spt}` |\n"
        f"| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )

def get_ips_process_killed_alert(server_ip, proc_name, killed_pid, proto, src, spt, dst, dpt, timestamp):
    return (
        f"# 🚨 Traffic Attack Blocked\n"
        f"---\n\n"
        f"### 🚨 [VPS Traffic IPS] Заблокирована сетевая атака!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 VPS Server** | `{server_ip}` |\n"
        f"| **🔥 Действие** | **Процесс автоматически уничтожен (kill -9)** |\n"
        f"| **📁 Процесс** | `{proc_name}` (PID: `{killed_pid}`) |\n"
        f"| **🔌 Протокол** | `{proto}` |\n"
        f"| **👤 Источник** | `{src}:{spt}` |\n"
        f"| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )

def get_ips_process_warning_alert(server_ip, proc_name, proto, src, spt, dst, dpt, timestamp):
    proc_info = f" (Процесс: `{proc_name}`)" if proc_name else ""
    return (
        f"# ⚠️ Traffic Sensitive Alert\n"
        f"---\n\n"
        f"### ⚠️ [VPS Traffic Warning] Исходящее соединение на sensitive порт!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 VPS Server** | `{server_ip}` |\n"
        f"| **🔌 Протокол** | `{proto}` |\n"
        f"| **👤 Источник** | `{src}:{spt}`{proc_info} |\n"
        f"| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        f"*Примечание: Процесс уже завершил работу или не найден. • Время: {timestamp}*"
    )

def get_local_traffic_alert(clean_h1, title, desc_with_client, vmid, container_name, label, proto, direction, src, spt, dst, dpt, vpn_ip_row, vpn_client_row, block_details_block, timestamp):
    vpn_ip_row = vpn_ip_row.strip()
    if vpn_ip_row:
        vpn_ip_row = "\n" + vpn_ip_row
    vpn_client_row = vpn_client_row.strip()
    if vpn_client_row:
        vpn_client_row = "\n" + vpn_client_row
        
    return (
        f"# {clean_h1}\n"
        f"---\n\n"
        f"### {title}\n\n"
        f"ℹ️ Описание: *{desc_with_client}*\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 Контейнер** | {vmid} (`{container_name}`) |\n"
        f"| **🏷 Угроза** | {label} |\n"
        f"| **🔌 Протокол** | `{proto}` |\n"
        f"| **🧭 Направление** | {'ВХОДЯЩЕЕ' if direction == 'IN' else 'ИСХОДЯЩЕЕ'} |\n"
        f"| **👤 Источник** | `{src}:{spt}` |\n"
        f"| **🎯 Назначение** | `{dst}:{dpt}` |"
        f"{vpn_ip_row}"
        f"{vpn_client_row}\n\n"
        f"{block_details_block}\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )
