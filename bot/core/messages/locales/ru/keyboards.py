translation = {
    # Inline buttons
    "btn_proxmox": "🖥️ Proxmox VE",
    "btn_spectre": "🛡️ Sentinel Panel",
    "btn_ansible": "🛠️ Ansible Playbooks",
    "btn_vpn_history": "📋 История VPN-подключений",
    "btn_ban_center": "🛑 Центр блокировок",
    "btn_whitelist": "⚙️ Белые списки Sentinel IPS",
    "btn_router_clients": "🖥️ Клиенты роутера",
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
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>🛡️ Proxmox Sentinel • Панель управления</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>⚡ Система защиты</b></td>\n'
        '    <td align="left"><code>🟢 АКТИВНА</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🖥️ Proxmox Host</b></td>\n'
        '    <td align="left"><code>{pve_ip}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🌐 Удаленный VPS</b></td>\n'
        '    <td align="left"><code>{vps_ip}</code></td>\n'
        '  </tr>\n'
        '</table>\n\n'
        '<i>Выберите раздел для мониторинга и администрирования:</i>'
    ),
    "help_text": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>ℹ️ Proxmox Sentinel • Справка по командам</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <th colspan="2" align="left"><b>🎛️ Основное управление</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/start</code></td>\n'
        '    <td align="left">Интерактивная панель управления</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/status</code></td>\n'
        '    <td align="left">Аудит и состояние всех систем</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/id</code></td>\n'
        '    <td align="left">Telegram ID и ID текущего чата</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <th colspan="2" align="left"><b>🛡️ Безопасность и Sentinel IPS</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/threats</code></td>\n'
        '    <td align="left">Журнал инцидентов и сетевых атак</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/bans</code></td>\n'
        '    <td align="left">Центр временных блокировок IP</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/whitelist</code></td>\n'
        '    <td align="left">Белые списки (IP, порты, процессы)</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <th colspan="2" align="left"><b>🌐 Мониторинг и Сеть</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/router</code></td>\n'
        '    <td align="left">Клиенты и сетевой трафик роутера</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/panel</code></td>\n'
        '    <td align="left">Управление узлами Sentinel Panel</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/top</code></td>\n'
        '    <td align="left">Статистика активного трафика</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/backup</code></td>\n'
        '    <td align="left">Резервная копия базы данных</td>\n'
        '  </tr>\n'
        '</table>\n\n'
        '<details>\n'
        '  <summary>⚡ <b>Быстрые команды добавления и снятия банов</b></summary>\n'
        '  • <code>/whitelist_add &lt;IP[:Port]&gt; [node]</code> — быстрое добавление IP в белый список<br/>\n'
        '  • <code>/whitelist_process &lt;процесс&gt; [node]</code> — добавление процесса в белый список<br/>\n'
        '  • <code>/unban_login_ip &lt;IP&gt;</code> — разблокировка IP-адреса входа<br/>\n'
        '  • <code>/audit</code> или <code>/logs</code> — системный журнал аудита\n'
        '</details>\n\n'
        '<blockquote>🛡️ <b>Автономная защита:</b> бот непрерывно отслеживает попытки входа (SSH Auth Monitor) и несанкционированную сетевую активность (Active IPS Engine) в реальном времени. Все алерты приходят в этот чат.</blockquote>'
    ),

    
    # Base command responses
    "welcome_message": (
        "👋 <b>Добро пожаловать в систему мониторинга Proxmox Sentinel!</b>\n"
        "<i>Ниже активирована постоянная панель быстрого доступа к главным командам.</i>"
    ),
    "id_message": (
        "👤 <b>Ваш Telegram ID:</b> <code>{user_id}</code>\n"
        "💬 <b>ID этого чата:</b> <code>{chat_id}</code>"
    )
}

