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
    "timeline_show_more": "*... показать ещё ...*",

    # Panel handler menu strings
    "panel_not_found_err": "❌ <b>Панели Spectre Panel не обнаружены.</b>\nУбедитесь, что панели запущены и доступны.",
    "open_panel_btn": "📱 Открыть {name}",
    "clients_list_btn": "👥 Список клиентов",
    "status_btn": "⚙️ Статус",
    "add_slave_btn": "➕ Добавить слейв",
    "add_master_btn": "➕ Добавить мастер",
    "add_master_node_btn": "➕ Добавить мастер ноду",
    "spectre_panel_title": "🚀 <b>Панель управления Spectre Panel</b>\n\nСервер: <code>{name}</code>",
    "select_panel_title": "🚀 <b>Выберите Spectre Panel для управления:</b>",
    "panel_not_found": "❌ Панель не найдена.",
    "open_webapp_btn": "📱 Открыть WebApp",
    "audit_logs_btn": "📋 Логи аудита",
    "backup_btn": "📥 Бэкап",
    "vps_logs_btn": "🔒 Логи входа VPS",
    "back_to_list_btn": "🔙 Назад к списку",
    "manage_panel_title": "🚀 <b>Управление панелью {name}</b>\n\nВыберите действие:",
    "generating_join_code": "⏳ <b>Генерация кода подключения для слейв-ноды на {name}...</b>",
    "add_slave_title": (
        "➕ <b>Добавление слейв-ноды для {name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 Код подключения (Join Code):\n<code>{join_code}</code>\n"
        "⏱ Истекает: <b>{expiry_str}</b>\n\n"
        "💻 <b>Команда для запуска на слейв-сервере:</b>\n\n"
        "🐳 <b>Вариант А (в Docker-контейнере):</b>\n"
        "<code>docker compose exec -T spectre-panel python register_node.py --master \"{master_url}\" --join-code \"{join_code}\"</code>\n\n"
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
        "2️⃣ Добавьте или отредактируйте переменную <code>SPECTRE_PANELS</code>. Это JSON-список панелей:\n\n"
        "<code>SPECTRE_PANELS='[\n"
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
        "# 👤 Client Profile: {email}\n"
        "---\n\n"
        "### 👤 Информация о клиенте VPN\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🖥️ Панель** | `{panel_name}` |\n"
        "| **🚦 Скачано (DL)** | `{down_gb:.3f} GB` |\n"
        "| **📤 Загружено (UL)** | `{up_gb:.3f} GB` |\n"
        "| **💾 Лимит трафика** | `{total_gb_str}` |\n"
        "| **⏱️ Истекает** | `{exp_str}` |\n"
        "| **⚡ Статус** | **{status_str}** |\n"
    ),
    "btn_conn_history": "📊 История подключений и IP",

    # Action results
    "act_banned_success": "Успешно заблокирован",
    "act_unbanned_success": "Успешно разблокирован",
    "act_panel_error": "Ошибка на стороне панели",
    "act_success_alert": "✅ {success_msg}!",
    "act_failed_alert": "❌ Ошибка: {desc}"
}
