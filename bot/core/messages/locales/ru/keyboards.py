translation = {
    # Inline buttons
    "btn_proxmox": "🖥️ Proxmox VE",
    "btn_spectre": "🚀 Spectre VPN Panel",
    "btn_ansible": "🛠️ Ansible Playbooks",
    "btn_vpn_history": "📋 История VPN-подключений",
    "btn_ban_center": "🛑 Центр блокировок",
    "btn_whitelist": "⚙️ Белые списки Aegis IPS",
    "btn_status": "📊 Статус систем",
    "btn_help": "ℹ️ Справка",
    "btn_back_to_menu": "🔙 В главное меню",
    "btn_refresh_status": "🔄 Обновить статус",
    "status_loading": "⏳ <i>Сбор информации о состоянии систем...</i>",
    
    # Reply buttons
    "reply_control_panel": "🛡️ Панель управления",
    "reply_system_status": "📊 Статус систем",
    "reply_help": "ℹ️ Справка",
    
    # Menu and help texts
    "main_menu_text": (
        "🛡️ <b>PVE Aegis IPS • Панель управления</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <b>Система защиты:</b> <code>🟢 АКТИВНА</code>\n"
        "🖥️ <b>Proxmox Host:</b> <code>{pve_ip}</code>\n"
        "🌐 <b>Удаленный VPS:</b> <code>{vps_ip}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите раздел для мониторинга и администрирования:"
    ),
    "help_text": (
        "ℹ️ <b>Справка по командам PVE Aegis:</b>\n\n"
        "• /start — Показать интерактивную панель управления (Главное меню)\n"
        "• /status — Быстрый аудит и статус всех систем (Proxmox, фоновые службы)\n"
        "• /bans — Центр управления активными временными блокировками IP\n"
        "• /whitelist — Управление белыми списками Aegis IPS (IP, порты, процессы)\n"
        "• /whitelist_add &lt;IP или IP:Port&gt; [node] — Быстрое добавление IP в белый список\n"
        "• /whitelist_process &lt;процесс&gt; [node] — Быстрое добавление процесса в белый список\n"
        "• /help — Показать это справочное сообщение\n"
        "• /id — Показать ваш Telegram ID / ID чата\n\n"
        "🛡️ <i>Бот автоматически отслеживает попытки авторизации (SSH Auth Monitor) и несанкционированную сетевую активность (Active IPS Engine) в реальном времени. Все алерты приходят напрямую в этот чат.</i>"
    ),
    
    # Base command responses
    "welcome_message": (
        "👋 <b>Добро пожаловать в систему мониторинга PVE Aegis!</b>\n"
        "<i>Ниже активирована постоянная панель быстрого доступа к главным командам.</i>"
    ),
    "id_message": (
        "👤 <b>Ваш Telegram ID:</b> <code>{user_id}</code>\n"
        "💬 <b>ID этого чата:</b> <code>{chat_id}</code>"
    )
}
