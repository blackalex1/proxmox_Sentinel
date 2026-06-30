translation = {
    "ban_center_title": "🛑 Центр блокировок Aegis IPS",
    "ban_center_empty": "<tr><td colspan=\"4\" style=\"padding: 8px; color: #a6adc8; text-align: center;\"><i>Активных блокировок в системе нет.<br/>Вся сетевая активность находится под контролем Active IPS Engine.</i></td></tr>",
    "active_bans_header": "👤 Активные временные блокировки IP",
    "banned_keys_header": "🔑 Заблокированные SSH-ключи",
    "banned_login_ips_header": "🛡 Блокировки входа (Failed Logins)",
    "col_panel": "Панель",
    
    # Active IP table headers
    "col_ip": "IP-адрес",
    "col_node": "Узел",
    "col_reason": "Причина",
    "col_expires": "Истекает",
    
    # Banned keys table headers
    "col_user": "Пользователь",
    "col_banned_at": "Забанен",
    
    "reason_manual": "Вручную",
    "reason_2fa_blocked": "2FA-блокировка (Вход)",

    # Remaining time formatting
    "remaining_hours": "{hours}ч {minutes}м",
    "remaining_minutes": "{minutes}м {seconds}с",
    "remaining_unknown": "Неизвестно",

    # Buttons
    "btn_unban_ip": "🔓 Разблокировать {ip}",
    "btn_unban_key": "🔓 Восстановить ключ (...{fp})",

    # Alerts and error messages
    "load_err": "❌ Ошибка при загрузке Центра блокировок.",
    "open_err": "❌ Ошибка при открытии Центра блокировок.",
    "invalid_callback_err": "❌ Ошибка: Неверный формат callback.",
    "unban_in_progress": "⏳ Снятие блокировки...",
    "vps_not_found_err": "VPS с IP {ip} не найден в настройках",
    "unban_success_alert": "🟢 Блокировка с IP {ip} успешно снята!",
    "unban_failed_alert": "❌ Ошибка снятия блокировки: {desc}",
    "key_not_found_err": "❌ Ошибка: Ключ не найден в БД или уже разблокирован.",
    "restore_key_in_progress": "⏳ Восстановление ключа...",
    "invalid_lxc_id_err": "Неверный ID LXC.",
    "restore_key_success_alert": "🟢 SSH-ключ успешно восстановлен!",
    "restore_key_failed_alert": "❌ Ошибка восстановления: {desc}",

    # CLI / Slash commands
    "unban_login_ip_help": "🟢 <b>Разблокировка IP входа:</b>\nИспользуйте команду: <code>/unban_login_ip &lt;ip&gt;</code>",
    "unban_login_ip_in_progress": "⏳ Разблокировка IP <code>{ip}</code> на всех панелях...",
    "unban_login_ip_success_item": "  • {name}: 🟢 Разблокирован",
    "unban_login_ip_failed_item": "  • {name}: 🔴 Ошибка ({error})",
    "unban_login_ip_success": "✅ <b>Результаты разблокировки IP <code>{ip}</code>:</b>\n{details}",
    "unban_login_ip_failed": "❌ <b>Не удалось разблокировать IP <code>{ip}</code>:</b>\n{details}"
}
