# bot/core/messages/spectre.py
"""Шаблоны сообщений для Spectre VPN панели (входы, 2FA, сессии, новые IP) с использованием Rich Telegram HTML."""

def get_new_ip_alert(protocol, panel_name, username, client_ip, timestamp_str, history_text, geoip_info=None):
    geo_row = f"\n🗺️ <b>Гео:</b> <code>{geoip_info}</code>" if geoip_info else ""
    return (
        f"🚨 <b>[{protocol} Security] Обнаружено подключение с нового IP!</b>\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"📦 <b>Панель:</b> <code>{panel_name}</code>\n"
        f"👤 <b>Пользователь:</b> <code>{username}</code>\n"
        f"🌐 <b>Новый IP:</b> <code>{client_ip}</code> ⚠️ [ВНИМАНИЕ]{geo_row}\n\n"
        f"📋 <b>Предыдущие подключения:</b>\n"
        f"<blockquote expandable>{history_text.strip()}</blockquote>"
    )

def get_session_activity_card(protocol, panel_name, username, download, upload, timeline):
    return (
        f"📊 <b>[{protocol}] Активность сессии на {panel_name}</b>\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"👤 <b>Пользователь:</b> <code>{username}</code>\n"
        f"📥 <b>Скачано:</b> <code>{download}</code>\n"
        f"📤 <b>Загружено:</b> <code>{upload}</code>\n\n"
        f"📋 <b>Хронология событий:</b>\n"
        f"<blockquote expandable>{timeline.strip()}</blockquote>"
    )

def get_client_disconnected_alert(protocol, panel_name, username, client_ip, timestamp_str, geoip_info=None):
    geo_row = f"\n🗺️ <b>Гео:</b> <code>{geoip_info}</code>" if geoip_info else ""
    return (
        f"🔴 <b>[{protocol}] Клиент отключился от {panel_name}</b>\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"👤 <b>Пользователь:</b> <code>{username}</code>\n"
        f"🌐 <b>IP-адрес:</b> <code>{client_ip}</code>{geo_row}"
    )

def get_ips_autoblock_alert_audit(panel_name, email, details, time_str):
    return (
        f"🛑 <b>[IPS: Авто-блокировка на {panel_name}]</b>\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"👤 <b>Пользователь:</b> <code>{email}</code>\n"
        f"📝 <b>Причина:</b> <b>{details}</b>"
    )

def get_login_success_alert(panel_name, username, ip, details, time_str, geoip_info=None):
    geo_row = f"\n🗺️ <b>Гео:</b> <code>{geoip_info}</code>" if geoip_info else ""
    return (
        f"🟢 <b>Вход выполнен на {panel_name}</b>\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"👤 <b>Логин:</b> <code>{username}</code>\n"
        f"🌐 <b>IP-адрес:</b> <code>{ip}</code>{geo_row}\n"
        f"ℹ️ <b>Детали:</b> <b>{details}</b>"
    )

def get_spectre_2fa_alert(panel_name, username, client_ip, time_str, geoip_info=None):
    geo_row = f"\n🗺️ <b>Гео:</b> <code>{geoip_info}</code>" if geoip_info else ""
    return (
        f"🔑 <b>[Spectre 2FA: Попытка входа]</b>\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"🖥 <b>Панель:</b> <b>{panel_name}</b>\n"
        f"👤 <b>Пользователь:</b> <code>{username}</code>\n"
        f"🌐 <b>IP-адрес:</b> <code>{client_ip}</code>{geo_row}"
    )

def get_panel_status_message(panel_name, cpu, mem_curr, mem_tot, mem_pct, cpu_bar, mem_bar, uptime_str, total_inbounds, total_clients, active_clients, online_clients, blocked_clients):
    return (
        f"📊 <b>Текущее состояние сервера: {panel_name}</b>\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"🖥️ <b>CPU:</b> <code>[{cpu_bar}] {cpu:.1f}%</code>\n"
        f"💾 <b>RAM:</b> <code>[{mem_bar}] {mem_curr:.2f} / {mem_tot:.2f} GB</code>\n"
        f"⏱️ <b>Uptime:</b> <code>{uptime_str}</code>\n"
        f"🖧 <b>Inbounds:</b> <code>{total_inbounds}</code>\n"
        f"👥 <b>Clients:</b> <code>{total_clients}</code>\n"
        f"🟢 <b>Active:</b> <code>{active_clients}</code>\n"
        f"🔵 <b>Online:</b> <code>{online_clients}</code>\n"
        f"🔴 <b>Blocked:</b> <code>{blocked_clients}</code>"
    )

