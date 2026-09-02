translation = {
    "router_recovery_alert": (
        "# 🚨 Security Recovery\n"
        "---\n\n"
        "### 🚨 КРИТИЧЕСКАЯ УГРОЗА: Восстановлен доступ для доверенного узла!\n\n"
        "Бот обнаружил, что доверенный IP-адрес (хост Proxmox VE или телефон администратора) был заблокирован на роутере! Блокировка была **автоматически снята** ботом.\n\n"
        "🌐 **Доверенный IP:** `{ip}`\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n"
        "  <pre><code>{rules_str}</code></pre>\n"
        "</details>"
    ),
    "router_unknown_block_alert": (
        "# ⚠️ Router Reconciliation\n"
        "---\n\n"
        "### ⚠️ Обнаружена неизвестная блокировка на роутере!\n\n"
        "Бот обнаружил правила блокировки для IP, которых нет в базе данных временных банов бота. В целях безопасности и синхронизации блокировка была автоматически снята.\n\n"
        "🌐 **IP-адрес:** `{ip}`\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n"
        "  <pre><code>{rules_str}</code></pre>\n"
        "</details>"
    ),
    "router_autoblock_alert": (
        "# 🛑 Router Auto-Block\n"
        "---\n\n"
        "### 🛑 [Router Security] Устройство заблокировано автоматически!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🎯 Причина** | Лимит нарушений ({threshold}+ попыток за 10 мин) |\n"
        "| **👤 Заблокированный IP** | `{src_ip}` |\n"
        "| **🧭 Последняя цель** | `{dst_host}:{dst_port}` (`{proto}`) |\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    "router_port_alert": (
        "# 🚨 Router {type_str} Alert\n"
        "---\n\n"
        "### 🚨 [Router Security: {type_str}] Доступ к чувствительному порту!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src_ip}:{src_port}` |\n"
        "| **🎯 Назначение** | `{dst_host}:{dst_port}` |\n\n"
        "*Sentinel Security Guard • Время: {timestamp}*"
    ),
    "btn_unblock_ip_router": "🟢 Разблокировать IP на роутере",
    "btn_block_ip_router": "🛑 Заблокировать IP на роутере",
    "btn_ban_all_full": "🛑 Заблокировать полностью",
    "btn_unban_all_full": "🟢 Разблокировать полностью",
    "btn_ban_port_menu": "🔒 Заблокировать порт/сервис",
    "btn_manage_bans": "🔎 Управление блокировками ({count})",
    "btn_back_to_clients": "🔙 Назад к списку клиентов",
    "btn_web_service": "🌐 Web-браузер (80, 443)",
    "btn_ssh_service": "💻 SSH консоль (22)",
    "btn_dns_service": "👥 DNS запросы (53)",
    "btn_custom_port": "✏️ Ввести порт вручную...",
    "btn_unban_port_action": "❌ Снять блок {port}/{proto}",
    "btn_unban_all_action": "🟢 Снять полную блокировку",
    
    "dur_1_hour": "1 час",
    "dur_1_day": "1 день",
    "dur_1_week": "1 неделя",
    "dur_forever": "Навсегда",
    
    "prompt_ban_all_duration": "⌛️ <b>Выберите длительность полной блокировки для устройства {ip}:</b>",
    "prompt_ban_port_service": "🔒 <b>Выберите порт или сервис для блокировки устройства {ip}:</b>",
    "prompt_ban_port_duration": "⌛️ <b>Выберите длительность блокировки портов {port}/{proto} для устройства {ip}:</b>",
    "prompt_custom_port_input": (
        "✏️ <b>Блокировка порта для устройства {ip}</b>\n\n"
        "Введите номер порта или порт/протокол (например: <code>80</code>, <code>53/udp</code>, <code>8080/tcp</code>):"
    ),
    "active_bans_header": "🔎 <b>Активные блокировки для устройства {ip}:</b>\n\n",
    "active_ban_ip_item": " • <b>Полная блокировка IP</b> (Истекает: {expire})\n",
    "active_ban_port_item": " • <b>Порт {port}/{proto}</b> (Истекает: {expire})\n",
    "active_bans_empty": "Нет активных блокировок для этого устройства.",
    
    "err_session_lost": "❌ Ошибка: сессия утеряна. Начните заново с команды /router",
    "err_invalid_proto": "❌ Неверный протокол. Укажите tcp или udp (например, 80/tcp или 53/udp)",
    "err_invalid_port": "❌ Порт должен быть числом от 1 до 65535.",
    "action_applying_ssh": "Выполняю блокировку по SSH...",
    "action_unbanning_ssh": "Снимаю блокировку по SSH...",
    "action_unbanning_port_ssh": "Снимаю блокировку порта {port}/{proto} по SSH...",
    "action_banning_port_ssh": "Добавляю правила блокировки порта по SSH...",
    "port_blocked_success": "Порт {port}/{proto} успешно заблокирован!",
    "port_unblocked_success": "Блокировка порта {port}/{proto} снята!",
    
    "ip_blocked_successfully": "🛑 IP {ip} успешно заблокирован на роутере!",
    "ip_block_failed": "❌ Ошибка блокировки: {desc}",
    "ip_block_error": "Ошибка при блокировке: {e}",
    "ip_unblocked_successfully": "🟢 Блокировка с IP {ip} снята!",
    "ip_unblock_failed": "❌ Ошибка снятия блокировки: {desc}",
    "ip_unblock_error": "Ошибка при разблокировке: {e}",
    "device_blocked_text": "\n\n🛑 <b>УСТРОЙСТВО {ip} ЗАБЛОКИРОВАНО НА РОУТЕРЕ!</b>",
    "invalid_data_format": "Ошибка: неверный формат данных.",
    
    # UI and Client Details
    "clients_list_empty": "⚠️ Устройства не найдены или мониторинг роутера отключен в конфигурации.",
    "clients_list_header": "🖥 <b>Клиенты вашего роутера:</b>\nВыберите устройство из списка ниже для управления блокировками.\n",
    "client_details_title": "🖥 Управление клиентом роутера",
    "col_device_name": "Имя устройства",
    "col_ip": "IP-адрес",
    "col_mac": "MAC-адрес",
    "col_net_status": "Статус сети",
    "col_ban_status": "Статус блокировки",
    "status_active": "🟢 Активен",
    "status_offline": "⚪ Офлайн",
    "ban_status_full": "🛑 Заблокирован полностью",
    "ban_status_ports": "🔒 Есть блокировки портов",
    "ban_status_none": "🟢 Доступ разрешен",
    "client_active_rules_footer": "🔒 Всего активных правил блокировки: <b>{count}</b>",
}
