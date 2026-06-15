translation = {
    "new_ip_alert": (
        "# 🚨 New IP Connection\n"
        "---\n\n"
        "### 🚨 [{protocol} Security] Обнаружено подключение с нового IP!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **📦 Панель** | `{panel_name}` |\n"
        "| **👤 Пользователь** | `{username}` |\n"
        "| **🌐 Новый IP** | `{client_ip}` ⚠️ [ВНИМАНИЕ] |\n"
        "{geo_row}\n"
        "<details>\n"
        "  <summary>📋 <b>Предыдущие подключения</b></summary>\n"
        "  <pre><code>{history_text}</code></pre>\n"
        "</details>"
    ),
    "session_activity_card": (
        "# 📊 Session Activity\n"
        "---\n\n"
        "### 📊 [{protocol}] Активность сессии на {panel_name}\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **👤 Пользователь** | `{username}` |\n"
        "| **📥 Скачано** | `{download}` |\n"
        "| **📤 Загружено** | `{upload}` |\n\n"
        "<details>\n"
        "  <summary>📋 <b>Хронология событий</b></summary>\n"
        "  <pre><code>{timeline}</code></pre>\n"
        "</details>"
    ),
    "client_disconnected_alert": (
        "# 🔴 Client Disconnected\n"
        "---\n\n"
        "### 🔴 [{protocol}] Клиент отключился от {panel_name}\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **👤 Пользователь** | `{username}` |\n"
        "| **🌐 IP-адрес** | `{client_ip}` |\n"
        "{geo_row}"
    ),
    "ips_autoblock_alert_audit": (
        "# 🛑 Account Auto-Blocked\n"
        "---\n\n"
        "### 🛑 [IPS: Авто-блокировка на {panel_name}]\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **👤 Пользователь** | `{email}` |\n"
        "| **📝 Причина** | **{details}** |\n"
    ),
    "login_success_alert": (
        "# 🔑 Web GUI Access\n"
        "---\n\n"
        "### 🟢 Вход выполнен на {panel_name}\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **👤 Логин** | `{username}` |\n"
        "| **🌐 IP-адрес** | `{ip}` |\n"
        "{geo_row}"
        "| **ℹ️ Детали** | **{details}** |\n"
    ),
    "spectre_2fa_alert": (
        "# 🔑 Spectre 2FA Prompt\n"
        "---\n\n"
        "### 🔑 [Spectre 2FA: Попытка входа]\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🖥 Панель** | **{panel_name}** |\n"
        "| **👤 Пользователь** | `{username}` |\n"
        "| **🌐 IP-адрес** | `{client_ip}` |\n"
        "{geo_row}"
    ),
    "panel_status_message": (
        "# 📊 Server Status: {panel_name}\n"
        "---\n\n"
        "### 📊 Текущее состояние сервера\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🖥️ CPU** | `[{cpu_bar}] {cpu:.1f}%` |\n"
        "| **💾 RAM** | `[{mem_bar}] {mem_curr:.2f} / {mem_tot:.2f} GB` |\n"
        "| **⏱️ Uptime** | `{uptime_str}` |\n"
        "| **🖧 Inbounds** | `{total_inbounds}` |\n"
        "| **👥 Clients** | `{total_clients}` |\n"
        "| **🟢 Active** | `{active_clients}` |\n"
        "| **🔵 Online** | `{online_clients}` |\n"
        "| **🔴 Blocked** | `{blocked_clients}` |\n"
    ),
    
    # Traffic table
    "top_traffic_title": "🏆 Топ потребителей трафика ({period_label})",
    "top_traffic_today": "Сегодня",
    "top_traffic_month": "За месяц",
    "top_traffic_error": "❌ {panel_name}: {error_info}",
    "top_traffic_panel_header": "📌 Панель: {panel_name}",
    "top_traffic_rank": "#",
    "top_traffic_user": "Пользователь",
    "top_traffic_traffic": "Трафик",
    "top_traffic_no_activity": "Нет активности пользователей",
    "top_traffic_no_data": "Нет данных об активности пользователей на панелях.",
    "top_traffic_footer": "\n<i>Для переключения используйте: <code>/top today</code> или <code>/top month</code></i>",
    
    # Misc strings
    "history_unknown": "неизвестно",
    "history_empty": "нет предыдущих подключений",
    "uptime_format": "{days}д {hours}ч {minutes}м",
    "timeline_show_more": "*... показать ещё ...*"
}
