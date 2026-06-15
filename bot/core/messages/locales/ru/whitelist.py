translation = {
    "whitelist_view_title": "📁 Белый список: {node_label}",
    "whitelist_empty": "<tr><td colspan=\"2\" style=\"padding: 8px; color: #a6adc8; text-align: center;\"><i>Правил в белом списке для этого узла нет. Все соединения проверяются стандартными правилами IPS.</i></td></tr>",
    "whitelist_type_header": "Тип правила",
    "whitelist_value_header": "Значение",
    "whitelist_rule_ip_port": "🌐 IP / Порт",
    "whitelist_rule_process": "⚙️ Процесс",
    
    "whitelist_view_all_title": "📋 Все правила белых списков Aegis IPS",
    "whitelist_view_all_empty": "<tr><td colspan=\"2\" style=\"padding: 8px; color: #bf616a; text-align: center;\">❌ Нет настроенных правил ни для одного узла.</td></tr>",

    # Whitelist nodes labels
    "global_node": "🌍 Глобально (Везде)",
    "router_node": "🔌 Роутер",
    "pve_node": "🖥️ Proxmox Host",
    "lxc_node": "📦 LXC {vmid} ({name})",
    "vps_node": "🌐 VPS {ip}",
    "offline_label": "{label} (офлайн)",

    # Button texts
    "btn_show_all": "📋 Показать все правила",
    "btn_back_to_nodes": "🔙 К выбору узла",
    "btn_add_ip_port": "➕ Добавить IP/Порт",
    "btn_add_proc": "➕ Добавить Процесс",
    "btn_delete_rule": "🗑️ Удалить правило",
    "btn_back_to_nodes_list": "🔙 Назад к списку узлов",
    "btn_cancel": "❌ Отмена",
    "btn_del_ip": "🗑️ IP: {item}",
    "btn_del_proc": "🗑️ Proc: {item}",
    "btn_back_to_view": "🔙 Назад к просмотру",

    # Messages / Inputs
    "manage_title": "⚙️ <b>Управление белыми списками Aegis IPS</b>\n\nВыберите узел (ноду) для просмотра и настройки правил безопасности:",
    "add_ip_port_title": "➕ <b>Добавление IP/Порта в белый список</b>\nУзел: {node_label}\n\nОтправьте сообщением IP-адрес или связку IP:Порт (например: <code>1.2.3.4</code> или <code>1.2.3.4:22</code>, или <code>1.2.3.4:*</code> для любого порта):",
    "invalid_input": "Неверный ввод. Попробуйте еще раз или нажмите Отмена.",
    "invalid_ip_port_format": "❌ Неверный формат IP/Порта. Примеры: <code>192.168.1.100</code> или <code>192.168.1.100:22</code> или <code>192.168.1.100:*</code>.",
    "rule_added_success": "🟢 <b>Правило успешно добавлено!</b>\n\n📁 <b>Белый список для узла: {node_label}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n",
    "allowed_ip_ports": "<b>Разрешенные IP / IP:Порты:</b>\n",
    "allowed_processes": "<b>Разрешенные процессы:</b>\n",
    "add_proc_title": "➕ <b>Добавление процесса в белый список</b>\nУзел: {node_label}\n\nОтправьте сообщением имя процесса (например: <code>caddy</code>, <code>nginx</code> или <code>sshd</code>):",
    "invalid_proc_name": "❌ Неверное имя процесса (разрешены только латинские буквы и цифры). Попробуйте еще раз.",
    "proc_added_success": "🟢 <b>Процесс успешно добавлен!</b>\n\n📁 <b>Белый список для узла: {node_label}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n",
    "empty_whitelist_err": "❌ Белый список этого узла пуст. Нечего удалять.",
    "del_rule_title": "🗑️ <b>Удаление правил белого списка</b>\nУзел: {node_label}\n\nВыберите правило, которое хотите удалить:",
    "del_success_alert": "🟢 Успешно удалено: {item}",

    # CLI / Slash commands
    "cli_add_help": "❌ Использование: <code>/whitelist_add &lt;IP или IP:Port&gt; [node]</code>\nПример: <code>/whitelist_add 1.2.3.4:22 router</code>",
    "cli_invalid_ip_port": "❌ Неверный формат IP/Порта.",
    "cli_added_ip_port": "🟢 Добавлено <code>{val}</code> в белый список узла <b>{label}</b>.",
    "cli_rule_exists": "ℹ️ Правило <code>{val}</code> уже существует для узла <b>{label}</b>.",
    "cli_proc_help": "❌ Использование: <code>/whitelist_process &lt;имя процесса&gt; [node]</code>\nПример: <code>/whitelist_process openvpn global</code>",
    "cli_invalid_proc": "❌ Неверное имя процесса.",
    "cli_added_proc": "🟢 Добавлен процесс <code>{val}</code> в белый список узла <b>{label}</b>.",
    "cli_proc_exists": "ℹ️ Процесс <code>{val}</code> уже находится в белом списке узла <b>{label}</b>.",

    # Quick Whitelist callbacks
    "qwl_invalid_callback": "❌ Неверный формат callback-данных.",
    "qwl_added_success": "🟢 Успешно добавлено в белый список {label}: {val}",
    "qwl_added_msg": "\n\n✅ <b>Добавлено в белый список ({label}):</b> <code>{val}</code>",
    "qwl_already_whitelisted": "ℹ️ Уже находится в белом списке {label}.",
    "qwl_save_error": "❌ Произошла ошибка при сохранении."
}
