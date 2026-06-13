# bot/core/messages/spectre.py
"""Шаблоны сообщений для Spectre VPN панели (входы, 2FA, сессии, новые IP) на GFM Markdown."""

def get_new_ip_alert(protocol, panel_name, username, client_ip, timestamp_str, history_list, geoip_info=None):
    import datetime
    history_lines = []
    for h in history_list:
        try:
            time_formatted = datetime.datetime.fromtimestamp(h["timestamp"]).strftime("%d.%m %H:%M")
        except Exception:
            time_formatted = "неизвестно"
        history_lines.append(f"• `{h['ip']}` ({time_formatted}) — {h['duration']}")
    history_text = "\n".join(history_lines) if history_lines else "нет предыдущих подключений"

    geo_row = ""
    if geoip_info:
        geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
    return (
        f"# 🚨 New IP Connection\n"
        f"---\n\n"
        f"### 🚨 [{protocol} Security] Обнаружено подключение с нового IP!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 Панель** | `{panel_name}` |\n"
        f"| **👤 Пользователь** | `{username}` |\n"
        f"| **🌐 Новый IP** | `{client_ip}` ⚠️ [ВНИМАНИЕ] |\n"
        f"{geo_row}\n"
        f"<details>\n"
        f"  <summary>📋 <b>Предыдущие подключения</b></summary>\n"
        f"  <pre><code>{history_text.strip()}</code></pre>\n"
        f"</details>"
    )

def get_session_activity_card(protocol, panel_name, username, download_bytes, upload_bytes, timeline_lines):
    def format_bytes(b):
        if b < 1024:
            return f"{b} B"
        elif b < 1024 * 1024:
            return f"{b / 1024:.2f} KB"
        elif b < 1024 * 1024 * 1024:
            return f"{b / (1024 * 1024):.2f} MB"
        else:
            return f"{b / (1024 * 1024 * 1024):.2f} GB"

    download = format_bytes(download_bytes)
    upload = format_bytes(upload_bytes)
    
    displayed_lines = timeline_lines[-15:]
    timeline = "\n".join(displayed_lines)
    if len(timeline_lines) > 15:
        timeline = "*... показать ещё ...*\n" + timeline

    return (
        f"# 📊 Session Activity\n"
        f"---\n\n"
        f"### 📊 [{protocol}] Активность сессии на {panel_name}\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **👤 Пользователь** | `{username}` |\n"
        f"| **📥 Скачано** | `{download}` |\n"
        f"| **📤 Загружено** | `{upload}` |\n\n"
        f"<details>\n"
        f"  <summary>📋 <b>Хронология событий</b></summary>\n"
        f"  <pre><code>{timeline.strip()}</code></pre>\n"
        f"</details>"
    )

def get_client_disconnected_alert(protocol, panel_name, username, client_ip, timestamp_str, geoip_info=None):
    geo_row = ""
    if geoip_info:
        geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
    return (
        f"# 🔴 Client Disconnected\n"
        f"---\n\n"
        f"### 🔴 [{protocol}] Клиент отключился от {panel_name}\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **👤 Пользователь** | `{username}` |\n"
        f"| **🌐 IP-адрес** | `{client_ip}` |\n"
        f"{geo_row}"
    )

def get_ips_autoblock_alert_audit(panel_name, email, details, time_str):
    return (
        f"# 🛑 Account Auto-Blocked\n"
        f"---\n\n"
        f"### 🛑 [IPS: Авто-блокировка на {panel_name}]\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **👤 Пользователь** | `{email}` |\n"
        f"| **📝 Причина** | **{details}** |\n"
    )

def get_login_success_alert(panel_name, username, ip, details, time_str, geoip_info=None):
    geo_row = ""
    if geoip_info:
        geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
    return (
        f"# 🔑 Web GUI Access\n"
        f"---\n\n"
        f"### 🟢 Вход выполнен на {panel_name}\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **👤 Логин** | `{username}` |\n"
        f"| **🌐 IP-адрес** | `{ip}` |\n"
        f"{geo_row}"
        f"| **ℹ️ Детали** | **{details}** |\n"
    )

def get_spectre_2fa_alert(panel_name, username, client_ip, time_str, geoip_info=None):
    geo_row = ""
    if geoip_info:
        geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
    return (
        f"# 🔑 Spectre 2FA Prompt\n"
        f"---\n\n"
        f"### 🔑 [Spectre 2FA: Попытка входа]\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🖥 Панель** | **{panel_name}** |\n"
        f"| **👤 Пользователь** | `{username}` |\n"
        f"| **🌐 IP-адрес** | `{client_ip}` |\n"
        f"{geo_row}"
    )

def get_panel_status_message(panel_name, cpu, mem_curr, mem_tot, mem_pct, uptime, total_inbounds, total_clients, active_clients, online_clients, blocked_clients):
    def make_bar(pct, length=10):
        pct = max(0.0, min(100.0, pct))
        filled_length = int(round(length * pct / 100))
        return "■" * filled_length + "□" * (length - filled_length)
        
    cpu_bar = make_bar(cpu)
    mem_bar = make_bar(mem_pct)
    
    days = uptime // 86400
    hours = (uptime % 86400) // 3600
    minutes = (uptime % 3600) // 60
    uptime_str = f"{days}д {hours}ч {minutes}м"

    return (
        f"# 📊 Server Status: {panel_name}\n"
        f"---\n\n"
        f"### 📊 Текущее состояние сервера\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🖥️ CPU** | `[{cpu_bar}] {cpu:.1f}%` |\n"
        f"| **💾 RAM** | `[{mem_bar}] {mem_curr:.2f} / {mem_tot:.2f} GB` |\n"
        f"| **⏱️ Uptime** | `{uptime_str}` |\n"
        f"| **🖧 Inbounds** | `{total_inbounds}` |\n"
        f"| **👥 Clients** | `{total_clients}` |\n"
        f"| **🟢 Active** | `{active_clients}` |\n"
        f"| **🔵 Online** | `{online_clients}` |\n"
        f"| **🔴 Blocked** | `{blocked_clients}` |\n"
    )

