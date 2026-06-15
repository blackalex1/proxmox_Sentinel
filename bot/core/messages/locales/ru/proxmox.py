translation = {
    "title": "👨‍💻 <b>Панель управления Proxmox:</b>\nВыберите сервер из списка ниже:",
    "error_connect": "❌ Ошибка подключения: {err_msg}",
    "error": "Ошибка: {err_msg}",
    "vms_title": "<b>Виртуальные машины на сервере {node_name}:</b>",
    
    # Keyboard button labels
    "host_label": "💻 [Хост] Proxmox VE",
    "back_to_nodes": "🔙 Назад к серверам",
    "host_logs_btn": "🔒 Логи входа Хоста",
    "host_traffic_btn": "🌐 Трафик Хоста",
    "wl_ips_btn": "⚙️ Белый список IPS",
    "refresh_status_btn": "🔄 Обновить статус",
    "back_to_vms_btn": "🔙 Назад к списку ВМ",
    "shutdown_btn": "🔌 Мягко выключить",
    "stop_btn": "🛑 Убить (Stop)",
    "reboot_btn": "🔄 Перезагрузить",
    "start_btn": "▶️ Запустить",
    "auth_logs_btn": "🔒 Логи входа",
    "ports_traffic_btn": "🌐 Трафик портов",
    "clone_btn": "👯 Клонировать",
    "refresh_log_btn": "🔄 Обновить лог",
    "back_to_vm_btn": "🔙 Назад к ВМ",
    "refresh_traffic_btn": "🔄 Обновить активность",
    "back_to_panel_btn": "🔙 Назад к панели",
    
    # VM / Node status cards
    "status_host_title": "💻 <b>Хост Proxmox VE ({node_name})</b>\n\n",
    "status_vm_title": "🖥 <b>ВМ {vmid} ({name})</b>\n\n",
    "status_label": "Статус",
    "status_online_vm": "🟢 Включена",
    "status_online_host": "🟢 Включен",
    "status_offline_vm": "🔴 Выключена",
    "version_label": "Версия PVE",
    "cpu_cores_label": "Ядер CPU",
    "cpu_load_label": "Нагрузка CPU",
    "ram_usage_label": "Потребление RAM",
    "uptime_label": "Uptime",
    "type_label": "Тип",
    
    # Alert notifications
    "host_data_actual": "Данные хоста актуальны",
    "vm_data_actual": "Данные ВМ актуальны",
    "error_vm_load": "Ошибка загрузки ВМ: {err_msg}",
    "exec_cmd": "⏳ Выполняю команду {action}...",
    "error_cmd": "❌ Ошибка команды:\n{err_msg}",
    "uptime_format": "{hours}ч {minutes}м {seconds}с",

    # Clone module
    "clone_title": "📝 <b>Клонирование {vm_type} {vmid} ({node_name})</b>\n\nВведите <b>ID</b> для новой машины (например, 105):",
    "clone_id_nan": "❌ ID должен быть числом! Попробуйте еще раз:",
    "clone_name_prompt": "Введите <b>имя</b> для новой машины (например, my-new-server):",
    "clone_starting": "⏳ Начинаю клонирование...",
    "clone_success": "✅ Клонирование успешно запущено!\nНовая машина ID: {new_id}, Имя: {new_name}",
    "clone_error": "❌ Ошибка клонирования: {error}",

    # Logs module
    "host_label_default": "Хост Proxmox VE",
    "auth_logs_host_title": "🔒 <b>Логи авторизации Хоста {node_name}:</b>\n\n",
    "auth_logs_lxc_title": "🔒 <b>Логи авторизации LXC {vmid} ({name}):</b>\n\n",
    "auth_logs_vps_title": "🔒 <b>Логи авторизации VPS ({server_ip}):</b>\n\n",
    "logs_empty": "<i>История пуста или бот был недавно перезапущен. Логи появятся при новых попытках входа.</i>",
    "logs_truncated": "\n\n<i>... [Часть логов обрезана из-за лимитов Telegram] ...</i>",
    "log_actual": "Лог актуален",
    "log_error": "Ошибка получения логов: {err_msg}",
    "log_vps_error": "Ошибка получения логов VPS: {err_msg}",

    # Traffic logs module
    "traffic_host_title": "🌐 <b>Сетевая активность Хоста {node_name}:</b>\n",
    "traffic_lxc_title": "🌐 <b>Сетевая активность LXC {vmid} ({name}):</b>\n",
    "traffic_subtitle": "<i>(Последние соединения и уровень их безопасности)</i>\n\n",
    "traffic_empty": "<i>Соединений не зафиксировано. Сетевая активность появится при прохождении нового трафика.</i>",
    "traffic_direction_in_label": "Входящее соединение",
    "traffic_direction_out_label": "Исходящее соединение",
    "traffic_truncated": "\n\n<i>... [Часть активности обрезана из-за лимитов Telegram] ...</i>",
    "traffic_actual": "Активность актуальна",
    "traffic_error": "Ошибка получения сетевой активности: {err_msg}"
}
