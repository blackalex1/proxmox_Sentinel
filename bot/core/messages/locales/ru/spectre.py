translation = {
    "new_ip_alert": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>🚨 [{protocol}] Обнаружено подключение с нового IP</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📦 Панель</b></td>\n'
        '    <td align="left"><code>{panel_name}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>👤 Пользователь</b></td>\n'
        '    <td align="left"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🌐 Новый IP</b></td>\n'
        '    <td align="left"><code>{client_ip}</code> ⚠️</td>\n'
        '  </tr>\n'
        '{geo_row}'
        '</table>\n\n'
        '<details>\n'
        '  <summary>📋 <b>Предыдущие подключения</b></summary>\n'
        '  <pre><code>{history_text}</code></pre>\n'
        '</details>'
    ),
    "btn_approve_ip": "✅ Одобрить IP",
    "ip_approved_success_toast": "✅ IP {ip} успешно одобрен!",
    "ip_approve_failed": "❌ Не удалось одобрить IP.",
    "select_audit_category": "📋 <b>Выберите категорию логов для панели {name}:</b>",
    "audit_cat_all": "📂 Все логи",
    "audit_cat_logins": "🔑 Входы в панель",
    "audit_cat_clients": "👤 Управление клиентами",
    "audit_cat_inbounds": "🔌 Подключения / Протоколы",
    "audit_cat_security": "🛡️ Безопасность / Блокировки",
    "audit_cat_settings": "⚙️ Настройки системы",
    "btn_back_to_categories": "🔙 К категориям",
    "session_activity_card": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>📊 [{protocol}] {panel_name}</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>👤 Пользователь</b></td>\n'
        '    <td align="left"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📥 Скачано</b></td>\n'
        '    <td align="left"><b>{download}</b></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📤 Загружено</b></td>\n'
        '    <td align="left"><b>{upload}</b></td>\n'
        '  </tr>\n'
        '</table>\n\n'
        '<details>\n'
        '  <summary>📋 <b>Хронология событий</b></summary>\n'
        '  <pre><code>{timeline}</code></pre>\n'
        '</details>'
    ),

    "client_disconnected_alert": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>🔴 [{protocol}] Клиент отключился</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📦 Панель</b></td>\n'
        '    <td align="left"><code>{panel_name}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>👤 Пользователь</b></td>\n'
        '    <td align="left"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🌐 IP-адрес</b></td>\n'
        '    <td align="left"><code>{client_ip}</code></td>\n'
        '  </tr>\n'
        '{geo_row}'
        '</table>'
    ),
    "ips_autoblock_alert_audit": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>🛑 [IPS] Авто-блокировка аккаунта</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📦 Панель</b></td>\n'
        '    <td align="left"><code>{panel_name}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>👤 Пользователь</b></td>\n'
        '    <td align="left"><code>{email}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📝 Причина</b></td>\n'
        '    <td align="left"><b>{details}</b></td>\n'
        '  </tr>\n'
        '</table>'
    ),
    "login_success_alert": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>🔑 Web GUI Access • Вход выполнен</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📦 Панель</b></td>\n'
        '    <td align="left"><code>{panel_name}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>👤 Логин</b></td>\n'
        '    <td align="left"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🌐 IP-адрес</b></td>\n'
        '    <td align="left"><code>{ip}</code></td>\n'
        '  </tr>\n'
        '{geo_row}'
        '  <tr>\n'
        '    <td align="left"><b>ℹ️ Детали</b></td>\n'
        '    <td align="left"><code>{details}</code></td>\n'
        '  </tr>\n'
        '</table>'
    ),
    "spectre_2fa_alert": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>🔑 Sentinel 2FA Prompt • Попытка входа</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📦 Панель</b></td>\n'
        '    <td align="left"><code>{panel_name}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>👤 Пользователь</b></td>\n'
        '    <td align="left"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🌐 IP-адрес</b></td>\n'
        '    <td align="left"><code>{client_ip}</code></td>\n'
        '  </tr>\n'
        '{geo_row}'
        '</table>'
    ),
    "panel_status_message": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>📊 Server Status: {panel_name}</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🖥️ CPU</b></td>\n'
        '    <td align="left"><code>[{cpu_bar}] {cpu:.1f}%</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>💾 RAM</b></td>\n'
        '    <td align="left"><code>[{mem_bar}] {mem_curr:.2f} / {mem_tot:.2f} GB</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>⏱️ Uptime</b></td>\n'
        '    <td align="left"><code>{uptime_str}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🖧 Inbounds</b></td>\n'
        '    <td align="left"><code>{total_inbounds}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>👥 Clients</b></td>\n'
        '    <td align="left"><code>{total_clients}</code> (🟢 {active_clients} / 🔵 {online_clients} / 🔴 {blocked_clients})</td>\n'
        '  </tr>\n'
        '</table>'
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
    "timeline_show_more": "*... показать ещё ...*",

    # Panel handler menu strings
    "panel_not_found_err": "❌ <b>Панели Sentinel Panel не обнаружены.</b>\nУбедитесь, что панели запущены и доступны.",
    "open_panel_btn": "📱 Открыть {name}",
    "clients_list_btn": "👥 Список клиентов",
    "status_btn": "⚙️ Статус",
    "add_slave_btn": "➕ Добавить слейв",
    "add_master_btn": "➕ Добавить мастер",
    "add_master_node_btn": "➕ Добавить мастер ноду",
    "spectre_panel_title": "🛡️ <b>Панель управления Sentinel Panel</b>\n\nСервер: <code>{name}</code>",
    "select_panel_title": "🛡️ <b>Выберите Sentinel Panel для управления:</b>",
    "panel_not_found": "❌ Панель не найдена.",
    "open_webapp_btn": "📱 Открыть WebApp",
    "audit_logs_btn": "📋 Логи аудита",
    "backup_btn": "📥 Бэкап",
    "vps_logs_btn": "🔒 Логи входа VPS",
    "back_to_list_btn": "🔙 Назад к списку",
    "manage_panel_title": "🛡️ <b>Управление панелью {name}</b>\n\nВыберите действие:",
    "generating_join_code": "⏳ <b>Генерация кода подключения для слейв-ноды на {name}...</b>",
    "add_slave_title": (
        "➕ <b>Добавление слейв-ноды для {name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 Код подключения (Join Code):\n<code>{join_code}</code>\n"
        "⏱ Истекает: <b>{expiry_str}</b>\n\n"
        "💻 <b>Команда для запуска на слейв-сервере:</b>\n\n"
        "🐳 <b>Вариант А (в Docker-контейнере):</b>\n"
        "<code>docker compose exec -T sentinel-panel python register_node.py --master \"{master_url}\" --join-code \"{join_code}\"</code>\n\n"
        "🐍 <b>Вариант Б (локально на хосте через Virtualenv):</b>\n"
        "<code>.venv/bin/python register_node.py --master \"{master_url}\" --join-code \"{join_code}\"</code>\n\n"
        "<i>Запустите подходящую команду в директории слейв-панели для регистрации публичного ключа.</i>"
    ),
    "back_btn": "🔙 Назад",
    "generating_error": "❌ <b>Ошибка генерации кода подключения для {name}:</b>\n<code>{error_info}</code>",
    "add_master_title": (
        "➕ <b>Добавление новой Мастер-панели в Контроллер</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Чтобы подключить еще одну Мастер-панель к вашему Telegram-боту:\n\n"
        "1️⃣ Откройте конфигурационный файл <code>.env</code> контроллера.\n"
        "2️⃣ Добавьте или отредактируйте переменную <code>SENTINEL_PANELS</code>. Это JSON-список панелей:\n\n"
        "<code>SENTINEL_PANELS='[\n"
        "  {{\"name\": \"Моя Панель\", \"url\": \"https://ip:port\", \"token\": \"api_token_here\", \"secret_path\": \"secret\"}}\n"
        "]'</code>\n\n"
        "3️⃣ Перезапустите бота. Он автоматически обнаружит её и добавит в меню."
    ),

    # Setup slave node command
    "setup_slave_help": (
        "💻 <b>Настройка сервера как слейв-ноды:</b>\n"
        "Используйте формат: <code>/setup_slave &lt;master_url&gt; &lt;join_code&gt;</code>\n\n"
        "<i>Пример:</i>\n<code>/setup_slave https://master.com/secret JOIN-E5A73D1C</code>"
    ),
    "setup_slave_init": "⏳ <b>Инициализация подключения к Мастер-серверу...</b>",
    "setup_slave_rejected": "❌ <b>Регистрация отклонена Мастером (код {status}):</b>\n<code>{error_info}</code>",
    "setup_slave_success": (
        "✅ <b>Сервер успешно настроен как слейв-нода!</b>\n\n"
        "ID Ноды: <code>{node_id}</code>\n"
        "Конфиг сохранен в: <code>{config_path}</code>\n"
        "🔗 Связь с Мастером установлена успешно."
    ),
    "setup_slave_error": "❌ <b>Произошла ошибка при настройке слейв-ноды:</b>\n<code>{error_info}</code>",

    # Admin actions and sessions
    "data_format_err": "Ошибка формата данных",
    "panel_not_found_or_disabled": "Панель не найдена или отключена",
    "sessions_fetch_err": "Не удалось получить сессии с панели",
    "sessions_terminated": "\n\n❌ <b>Сессии пользователя {username} с IP {ip} успешно сброшены ({terminated} сесс.).</b>",
    "sessions_terminated_alert": "Сессии успешно сброшены",
    "no_active_sessions_err": "Активные сессии не найдены на панели",
    "error_alert": "Ошибка: {error}",
    "reset_pwd_manual_unsupported": "Невозможно сбросить пароль для панели с ручной настройкой (.env)",
    "reset_pwd_success": "\n\n🔑 <b>Пароль пользователя {username} успешно изменен!</b>\nНовый пароль: <tg-spoiler><code>{new_pwd}</code></tg-spoiler>",
    "reset_pwd_success_alert": "Пароль успешно изменен",
    "reset_pwd_failed": "Не удалось сбросить пароль: {error_info}",

    # Clients list and pagination
    "loading_clients": "⏳ Загрузка списка клиентов для <b>{name}</b>...",
    "load_clients_err": "❌ <b>Не удалось загрузить клиентов с панели {name}</b>",
    "clients_list_empty": "👥 <b>Список клиентов на панели {name} пуст.</b>",
    "nav_back": "◀️ Назад",
    "nav_start": "⏹️ Начало",
    "nav_forward": "Вперед ▶️",
    "nav_end": "⏹️ Конец",
    "back_to_menu_btn": "🔙 Назад в меню панели",
    "clients_list_title": "👥 <b>Список клиентов на панели {name}</b> (Всего: {total_clients}):",

    # Client view/card
    "client_not_found_err": "❌ <b>Клиент {email} не найден на панели.</b>",
    "no_limit": "Без лимита",
    "status_online": "🟢 Онлайн",
    "status_offline": "⚪ Офлайн",
    "btn_ban_client": "🛑 Заблокировать",
    "btn_unban_client": "🟢 Разблокировать",
    "expiry_never": "Никогда",
    "blocked_by_admin": "Заблокирован администратором",
    "status_blocked": "🔴 Заблокирован ({reason})",
    "client_profile_card": (
        "👤 <b>Client Profile: {email}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🖥️ <b>Панель:</b> <code>{panel_name}</code>\n"
        "🚦 <b>Скачано (DL):</b> <code>{down_gb:.3f} GB</code>\n"
        "📤 <b>Загружено (UL):</b> <code>{up_gb:.3f} GB</code>\n"
        "💾 <b>Лимит:</b> <code>{total_gb_str}</code>\n"
        "⏱️ <b>Истекает:</b> <code>{exp_str}</code>\n"
        "⚡ <b>Статус:</b> {status_str}\n"
    ),
    "btn_conn_history": "📊 История подключений и IP",

    # Action results
    "act_banned_success": "Успешно заблокирован",
    "act_unbanned_success": "Успешно разблокирован",
    "act_panel_error": "Ошибка на стороне панели",
    "act_success_alert": "✅ {success_msg}!",
    "act_failed_alert": "❌ Ошибка: {desc}",

    # System and Backup handler keys
    "no_panels_err": "❌ <b>Панели Sentinel Panel не обнаружены.</b>",
    "select_panel_backup": "📥 <b>Выберите панель для создания бэкапа:</b>",
    "backup_in_progress": "⏳ Создание резервной копии для <b>{name}</b>...",
    "backup_success": "✅ <b>Резервная копия успешно создана!</b>\nСервер: <code>{name}</code>",
    "backup_send_err": "❌ Ошибка отправки бэкапа: {error}",
    "backup_failed": "❌ <b>Не удалось создать бэкап для {name}:</b>\n<code>{error}</code>",
    "unknown_error": "Неизвестная ошибка",
    "select_panel_status": "📊 <b>Выберите панель для проверки статуса:</b>",
    "status_fetching": "⏳ Получение статуса от <b>{name}</b>...",
    "status_failed": "❌ <b>Ошибка получения статуса {name}:</b>\n<code>{error}</code>",
    "traffic_stats_fetching": "📊 Получение статистики по трафику со всех панелей...",
    "select_panel_audit": "📋 <b>Выберите панель для просмотра лога аудита:</b>",
    "audit_logs_fetching": "⏳ Получение логов аудита от <b>{name}</b>...",
    "audit_logs_empty": "📁 <b>{name}</b>: Лог аудита пуст.",
    "audit_logs_title": "📋 <b>Последние действия в панели: {name}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n",
    "audit_logs_failed": "❌ <b>Ошибка получения логов {name}:</b>\n<code>{error}</code>",

    # Client search and actions keys
    "my_subscription_title": "🔑 <b>Поиск подписки клиента:</b>\nИспользуйте команду: <code>/my &lt;email или UUID&gt;</code>",
    "lookup_in_progress": "🔍 Поиск клиента по всем базам данных панелей...",
    "client_not_found_everywhere": "❌ <b>Клиент с таким email или UUID не найден ни на одной панели.</b>",
    "no_traffic_limit": "Без лимита",
    "limit_gb": "{limit:.2f} ГБ",
    "status_active": "🟢 Активен",
    "reason_limit_exceeded": "Превышены лимиты",
    "status_blocked_with_reason": "🔴 Заблокирован ({reason})",
    "expires_never": "Никогда",
    "client_card_sub_title": (
        "🔑 <b>Подписка: {email}</b>\n"
        "📡 Панель/Сервер: <b>{panel_name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 Подключение: <b>{remark} (:{port})</b>\n"
        "📡 Протокол: <b>{protocol}</b>\n"
        "🚦 Скачано (DL): <b>{download_gb:.3f} ГБ</b>\n"
        "📤 Загружено (UL): <b>{upload_gb:.3f} ГБ</b>\n"
        "💾 Лимит трафика: <b>{total_gb_str}</b>\n"
        "⏱ Истекает: <b>{expiry_str}</b>\n"
        "⚡ Статус: <b>{status_str}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 <b>Ссылки для подключения:</b>\n"
    ),
    "copy_link_hint": "\n<i>Нажмите на ссылку, чтобы скопировать её.</i>",
    "btn_conn_history_and_ip": "📊 История подключений и IP",
    "qr_code_caption": "QR-код {protocol} ({index})",
    "lookup_error": "❌ Произошла ошибка при поиске: {error}",
    "unbanning_tunnel_hint": "👇 Вы можете разблокировать туннель вручную в один клик:",
    "unbanning_tunnel_progress": "⏳ <i>Выполняется разблокировка туннеля на всех связанных нодах...</i>",
    "manual_unban_success_details": (
        "{original_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 <b>Туннель успешно разблокирован вручную!</b>\n\n"
        "📋 <b>Детализация по нодам и панелям:</b>\n"
        "{details}\n\n"
        "🕒 <i>Время выполнения:</i> <code>{timestamp}</code> • <i>Статус:</i> 🟢 <b>Активен</b>"
    ),
    "manual_unban_failed_details": (
        "{original_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <b>Туннель разблокирован с предупреждениями:</b>\n\n"
        "📋 <b>Детализация по нодам и панелям:</b>\n"
        "{details}\n\n"
        "🕒 <i>Время выполнения:</i> <code>{timestamp}</code>"
    ),
    "manual_unban_error": (
        "{original_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ <b>Ошибка при разблокировке туннеля:</b>\n"
        "<code>{error}</code>"
    ),
    "ban_help": "🛑 <b>Блокировка клиента:</b>\nИспользуйте команду: <code>/ban &lt;email&gt;</code>",
    "ban_progress": "⏳ <i>Блокировка клиента <code>{email}</code> на всех целевых панелях...</i>",
    "ban_status_success": "🟢 Заблокирован",
    "ban_status_error": "🔴 Ошибка",
    "ban_success_results": (
        "🛑 <b>Клиент <code>{email}</code> успешно заблокирован!</b>\n\n"
        "📋 <b>Детализация по панелям:</b>\n"
        "{details}"
    ),
    "ban_failed_results": (
        "❌ <b>Не удалось заблокировать клиента <code>{email}</code>:</b>\n\n"
        "📋 <b>Детализация по панелям:</b>\n"
        "{details}"
    ),
    "ban_error": "❌ <b>Произошла ошибка при блокировке:</b> <code>{error}</code>",
    "unban_help": "🟢 <b>Разблокировка клиента:</b>\nИспользуйте команду: <code>/unban &lt;email&gt;</code>",
    "unban_progress": "⏳ <i>Разблокировка клиента <code>{email}</code> на всех доступных панелях...</i>",
    "unban_status_success": "🟢 Разблокирован",
    "unban_status_error": "🔴 Ошибка",
    "unban_success_results": (
        "🟢 <b>Клиент <code>{email}</code> успешно разблокирован!</b>\n\n"
        "📋 <b>Детализация по панелям:</b>\n"
        "{details}"
    ),
    "unban_failed_results": (
        "❌ <b>Не удалось разблокировать клиента <code>{email}</code>:</b>\n\n"
        "📋 <b>Детализация по панелям:</b>\n"
        "{details}"
    ),
    "unban_error": "❌ <b>Произошла ошибка при разблокировке:</b> <code>{error}</code>",
    "tg_2fa_approved": "✅ <b>Вход успешно разрешен.</b>",
    "tg_2fa_blocked": "🛑 <b>IP-адрес заблокирован.</b>",
    "tg_2fa_error": "❌ Ошибка: {error}",
    "tg_2fa_unblock_failed": "Не удалось заблокировать ни на одной панели",
    "tg_2fa_approve_failed": "Не удалось подтвердить ни на одной панели",
    "tg_2fa_block_confirm_btn": "🔥 Да, заблокировать IP",
    "tg_2fa_block_cancel_btn": "🔙 Отмена",
    "tg_2fa_block_confirm_text": "{original_text}\n\n⚠️ <b>Вы уверены? Блокировка вашего IP лишит вас доступа к серверу!</b>",
    "tg_2fa_approve_btn": "✅ Да, разрешить",
    "tg_2fa_block_btn": "❌ Заблокировать IP",
    "tg_2fa_block_cancelled_alert": "Блокировка IP отменена",

    # Timeline and Duration strings
    "timeline_connect": "🟢 [{timestamp}] Подключение с {ip}",
    "timeline_disconnect": "🔴 [{timestamp}] Отключение {ip} — {duration}",
    "duration_sec": "{val} сек",
    "duration_min_sec": "{min} мин {sec} сек",
    "duration_hour_min": "{hour} ч {min} мин"
}

