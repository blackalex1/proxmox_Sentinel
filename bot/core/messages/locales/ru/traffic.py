translation = {
    "ips_investigation_success_alert": (
        "# ✅ IPS Investigation Done\n"
        "---\n\n"
        "### ✅ [IPS: Расследование завершено] Нарушитель найден!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **👤 Нарушитель (Xray)** | `{xray_client}` (Заблокирован) |\n"
        "| **🔓 Hysteria туннель** | `{tunnel_email}` (Разблокирован) |\n"
        "| **🌐 Маршрут атаки** | Вход: `{target_panel_name}` (Xray)<br/>Транзит: `{tunnel_email}` (Hysteria2)<br/>Выход: VPS `{server_ip}` → `{dst_ip}:{dpt}` |\n\n"
        "✨ *Все остальные пользователи туннеля снова в сети!*\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать детали глобального бана нарушителя</b></summary>\n"
        "  <pre><code>{block_details_str}</code></pre>\n"
        "</details>\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать детали разблокировки туннеля Hysteria</b></summary>\n"
        "  <pre><code>{unblock_details_str}</code></pre>\n"
        "</details>\n\n"
        "*Aegis Security Guard • Время: {timestamp}*"
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
        "👇 Вы можете разблокировать туннель вручную в один клик:\n\n"
        "*Aegis Security Guard • Время: {timestamp}*"
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
        "*Aegis Security Guard • Время: {timestamp}*"
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
        "🔍 *Запущено асинхронное расследование для поиска конкретного виновника внутри туннеля...*\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать статус блокировки туннеля</b></summary>\n"
        "  <pre><code>{block_details_str}</code></pre>\n"
        "</details>\n\n"
        "*Aegis Security Guard • Время: {timestamp}*"
    ),
    "ips_xray_attack_alert": (
        "# 🚨 Traffic Attack Blocked\n"
        "---\n\n"
        "### 🚨 [VPS Traffic IPS] Блокировка сетевой атаки!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **👤 Нарушитель (Xray)** | `{email}` |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src}:{spt}`{proc_info} |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        "<details>\n"
        "  <summary>🚨 <b>Показать статус авто-блокировки аккаунта нарушителя</b></summary>\n"
        "  <pre><code>{block_details_str}</code></pre>\n"
        "</details>\n\n"
        "*Aegis Security Guard • Время: {timestamp}*"
    ),
    "ips_whitelisted_alert": (
        "# ℹ️ Connection Allowed\n"
        "---\n\n"
        "### ℹ️ [VPS Traffic] Разрешенное соединение (в белом списке IPS)\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **📁 Процесс** | `{proc_name}` |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src}:{spt}` |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        "*Aegis Security Guard • Время: {timestamp}*"
    ),
    "ips_process_killed_alert": (
        "# 🚨 Traffic Attack Blocked\n"
        "---\n\n"
        "### 🚨 [VPS Traffic IPS] Заблокирована сетевая атака!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **🔥 Действие** | **Процесс автоматически уничтожен (kill -9)** |\n"
        "| **📁 Процесс** | `{proc_name}` (PID: `{killed_pid}`) |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src}:{spt}` |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |\n\n"
        "*Aegis Security Guard • Время: {timestamp}*"
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
        "*Примечание: Процесс уже завершил работу или не найден. • Время: {timestamp}*"
    ),
    "local_traffic_alert": (
        "# {clean_h1}\n"
        "---\n\n"
        "### {title}\n\n"
        "ℹ️ Описание: *{desc_with_client}*\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **📦 Контейнер** | {vmid} (`{container_name}`) |\n"
        "| **🏷 Угроза** | {label} |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **🧭 Направление** | {direction_text} |\n"
        "| **👤 Источник** | `{src}:{spt}` |\n"
        "| **🎯 Назначение** | `{dst}:{dpt}` |"
        "{vpn_ip_row}"
        "{vpn_client_row}\n\n"
        "{block_details_block}\n\n"
        "*Aegis Security Guard • Время: {timestamp}*"
    ),
    
    # helper elements
    "local_h1_allowed": "ℹ️ Connection Allowed",
    "local_h1_blocked": "🚨 Attack Blocked",
    "local_h1_critical": "🚨 Critical Alert",
    "local_h1_warning": "⚠️ Warning Alert",
    "local_h1_default": "⚠️ Traffic Alert",
    "local_direction_in": "ВХОДЯЩЕЕ",
    "local_direction_out": "ИСХОДЯЩЕЕ",
    "local_real_ip": "\n| **👤 Реальный IP** | `{real_client_ip}` |",
    "local_vpn_client": "\n| **👤 Клиент VPN** | `{xray_client_email}` |",
    "local_block_status": "\n\n<details>\n  <summary>🚨 <b>Показать статус авто-блокировки аккаунта</b></summary>\n  <pre><code>{block_details_str}</code></pre>\n</details>",
    "proc_info_tmpl": " (Процесс: `{proc_name}`)"
}
