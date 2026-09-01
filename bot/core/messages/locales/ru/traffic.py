translation = {
    "ips_investigation_success_alert": (
        "# ✅ IPS Investigation Done\n"
        "---\n\n"
        "### ✅ [IPS: Расследование завершено] Нарушитель найден!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **👤 Нарушитель** | `{xray_client}` (Заблокирован) |\n"
        "| **🔓 Транзитный туннель** | `{tunnel_email}` (Активен) |\n"
        "| **🌐 Маршрут атаки** | `{target_panel_name}` → `{tunnel_email}` → `{server_ip}` → `{dst_ip}:{dpt}` |\n\n"
        "✨ *Все остальные пользователи туннеля снова в сети!*\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать детали глобального бана нарушителя</b></summary>\n"
        "  <pre><code>{block_details_str}</code></pre>\n"
        "</details>\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать статус транзитного туннеля</b></summary>\n"
        "  <pre><code>{unblock_details_str}</code></pre>\n"
        "</details>\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),

    "ips_investigation_failed_alert": (
        "# ⚠️ IPS Investigation Failed\n"
        "---\n\n"
        "### ⚠️ [IPS: Расследование не удалось] Виновник не обнаружен!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🚨 Статус туннеля** | `{tunnel_email}` (Оставлен в бане) |\n"
        "| **🎯 Цель атаки** | `{dst_ip}:{dpt}` |\n\n"
        "<details>\n"
        "  <summary>🔍 <b>Показать собранные фрагменты логов</b></summary>\n"
        "  <pre><code>{logs_text}</code></pre>\n"
        "</details>\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    "ips_sensitive_access_alert": (
        "# 🚨 Traffic Security Alert\n"
        "---\n\n"
        "### 🚨 [VPS Traffic Security] Входящий доступ на sensitive порт!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src}:{spt}` |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    "ips_hysteria_attack_alert": (
        "# 🚨 Traffic Attack Detected\n"
        "---\n\n"
        "### 🚨 [VPS Traffic IPS] Обнаружена атака через Hysteria-туннель!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **🔥 Временный бан** | `{email}` |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src}:{spt}` |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать статус блокировки туннеля</b></summary>\n"
        "  <pre><code>{block_details_str}</code></pre>\n"
        "</details>\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    "ips_xray_attack_alert": (
        "# 🚨 Traffic Attack Blocked\n"
        "---\n\n"
        "### 🚨 [VPS Traffic IPS] Блокировка сетевой атаки!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **👤 Нарушитель (Xray)** | `{email}`{inbound_display} |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src}:{spt}`{proc_info} |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        "<details>\n"
        "  <summary>🚨 <b>Показать статус авто-блокировки аккаунта нарушителя</b></summary>\n"
        "  <pre><code>{block_details_str}</code></pre>\n"
        "</details>\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    "ips_whitelisted_alert": (
        "# ℹ️ Connection Allowed\n"
        "---\n\n"
        "### ℹ️ [VPS Traffic] Разрешенное соединение\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **📁 Процесс** | `{proc_name}` |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src}:{spt}` |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    "ips_process_killed_alert": (
        "# 🚨 Traffic Attack Blocked\n"
        "---\n\n"
        "### 🚨 [VPS Traffic IPS] Заблокирована сетевая атака!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **🔥 Действие** | **Процесс уничтожен (kill -9)** |\n"
        "| **📁 Процесс** | `{proc_name}` (PID: `{killed_pid}`) |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src}:{spt}` |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    "ips_process_warning_alert": (
        "# ⚠️ Traffic Sensitive Alert\n"
        "---\n\n"
        "### ⚠️ [VPS Traffic Warning] Исходящее соединение на sensitive порт!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src}:{spt}`{proc_info} |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    "local_traffic_alert": (
        "# {clean_h1}\n"
        "---\n\n"
        "### {title}\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **📦 Контейнер** | {vmid} (`{container_name}`) |\n"
        "| **🏷️ Угроза** | {label} |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **🧭 Направление** | {direction_text} |\n"
        "| **👤 Источник** | `{src}:{spt}` |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n"
        "{vpn_ip_row}"
        "{vpn_client_row}"
        "{vpn_inbound_row}\n\n"
        "{block_details_block}\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    
    # helper elements
    "local_h1_allowed": "ℹ️ Connection Allowed",
    "local_h1_blocked": "🚨 Attack Blocked",
    "local_h1_critical": "🚨 Critical Alert",
    "local_h1_warning": "⚠️ Warning Alert",
    "local_h1_default": "⚠️ Traffic Alert",
    "local_direction_in": "ВХОДЯЩЕЕ",
    "local_direction_out": "ИСХОДЯЩЕЕ",
    "local_real_ip": "| **👤 Реальный IP** | `{real_client_ip}` |\n",
    "local_vpn_client": "| **👤 Клиент VPN** | `{xray_client_email}` |\n",
    "local_vpn_inbound": "| **🔌 Инбаунд VPN** | `{inbound_tag}` |\n",
    "local_block_status": "\n<details>\n  <summary>🚨 <b>Показать статус авто-блокировки аккаунта</b></summary>\n  <pre><code>{block_details_str}</code></pre>\n</details>",
    "proc_info_tmpl": " (Процесс: `{proc_name}`)"
}
