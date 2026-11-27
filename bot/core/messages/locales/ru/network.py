# Locale bundle: network (ru)

translations = {'proxy': {'proxy_switch_alert': '# ⚠️ Proxy Switch Alert\n'
                                 '---\n'
                                 '\n'
                                 '### ⚠️ [Proxy Monitor] Основной прокси не отвечает!\n'
                                 '\n'
                                 '🔄 Бот автоматически переключился на резервный канал связи.\n'
                                 '\n'
                                 '| Параметр | Значение |\n'
                                 '| :--- | :--- |\n'
                                 '| **❌ Основной прокси** | `{primary_proxy}` |\n'
                                 '| **🔄 Резервный канал** | `{new_proxy}` |\n'
                                 '| **🛡 Уровень резерва** | {tier_info} |\n',
           'proxy_restored_alert': '# ✅ Proxy Restored\n'
                                   '---\n'
                                   '\n'
                                   '### ✅ [Proxy Monitor] Основной прокси снова доступен!\n'
                                   '\n'
                                   '🔄 Успешно вернулись на основное подключение.\n'
                                   '\n'
                                   '| Параметр | Значение |\n'
                                   '| :--- | :--- |\n'
                                   '| **🔌 Подключение** | `{primary_proxy}` |\n'
                                   '| **ℹ️ Статус** | 🟢 В сети (Основной прокси) |\n'},
 'router': {'router_recovery_alert': '# 🚨 Security Recovery\n'
                                     '---\n'
                                     '\n'
                                     '### 🚨 КРИТИЧЕСКАЯ УГРОЗА: Восстановлен доступ для доверенного узла!\n'
                                     '\n'
                                     'Бот обнаружил, что доверенный IP-адрес (хост Proxmox VE или телефон '
                                     'администратора) был заблокирован на роутере! Блокировка была **автоматически '
                                     'снята** ботом.\n'
                                     '\n'
                                     '🌐 **Доверенный IP:** `{ip}`\n'
                                     '\n'
                                     '<details>\n'
                                     '  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n'
                                     '  <pre><code>{rules_str}</code></pre>\n'
                                     '</details>',
            'router_unknown_block_alert': '# ⚠️ Router Reconciliation\n'
                                          '---\n'
                                          '\n'
                                          '### ⚠️ Обнаружена неизвестная блокировка на роутере!\n'
                                          '\n'
                                          'Бот обнаружил правила блокировки для IP, которых нет в базе данных '
                                          'временных банов бота. В целях безопасности и синхронизации блокировка была '
                                          'автоматически снята.\n'
                                          '\n'
                                          '🌐 **IP-адрес:** `{ip}`\n'
                                          '\n'
                                          '<details>\n'
                                          '  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n'
                                          '  <pre><code>{rules_str}</code></pre>\n'
                                          '</details>',
            'router_autoblock_alert': '# 🛑 Router Auto-Block\n'
                                      '---\n'
                                      '\n'
                                      '### 🛑 [Router Security] Устройство заблокировано автоматически!\n'
                                      '\n'
                                      '| Параметр | Значение |\n'
                                      '| :--- | :--- |\n'
                                      '| **🎯 Причина** | Лимит нарушений ({threshold}+ попыток за 10 мин) |\n'
                                      '| **👤 Заблокированный IP** | `{src_ip}` |\n'
                                      '| **🧭 Последняя цель** | `{dst_host}:{dst_port}` (`{proto}`) |\n'
                                      '\n'
                                      '*Sentinel Security Guard • Время: {timestamp}*',
            'router_port_alert': '# 🚨 Router {type_str} Alert\n'
                                 '---\n'
                                 '\n'
                                 '### 🚨 [Router Security: {type_str}] Доступ к чувствительному порту!\n'
                                 '\n'
                                 '| Параметр | Значение |\n'
                                 '| :--- | :--- |\n'
                                 '| **🔌 Протокол** | `{proto}` |\n'
                                 '| **👤 Источник** | `{src_ip}:{src_port}` |\n'
                                 '| **🎯 Назначение** | `{dst_host}:{dst_port}` |\n'
                                 '\n'
                                 '*Sentinel Security Guard • Время: {timestamp}*',
            'btn_unblock_ip_router': '🟢 Разблокировать IP на роутере',
            'btn_block_ip_router': '🛑 Заблокировать IP на роутере',
            'btn_allow_port_alert': '🟢 Разрешить {port}',
            'btn_allow_all_alert': '🌐 Разрешить все порты',
            'btn_ban_all_full': '🛑 Заблокировать полностью',
            'btn_unban_all_full': '🟢 Разблокировать полностью',
            'btn_ban_port_menu': '🔒 Заблокировать порт/сервис',
            'btn_allow_port_menu': '🟢 Разрешить порт/сервис',
            'btn_allow_all_ports': '🌐 Разрешить все порты (Доверенный)',
            'btn_manage_bans': '🔎 Управление блокировками ({count})',
            'btn_manage_rules': '🔎 Управление правилами ({count})',
            'btn_back_to_clients': '🔙 Назад к списку клиентов',
            'btn_web_service': '🌐 Web-браузер (80, 443)',
            'btn_ssh_service': '💻 SSH консоль (22)',
            'btn_dns_service': '👥 DNS запросы (53)',
            'btn_db_service': '🗄 Базы данных (3306, 5432)',
            'btn_proxmox_rdp_service': '🖥 Proxmox / RDP (8006, 3389)',
            'btn_custom_port': '✏️ Ввести порт вручную...',
            'btn_unban_port_action': '❌ Снять блок {port}/{proto}',
            'btn_disallow_port_action': '❌ Запретить {port}/{proto}',
            'btn_unban_all_action': '🟢 Снять полную блокировку',
            'dur_1_hour': '1 час',
            'dur_1_day': '1 день',
            'dur_1_week': '1 неделя',
            'dur_forever': 'Навсегда',
            'prompt_ban_all_duration': '⌛️ <b>Выберите длительность полной блокировки для устройства {ip}:</b>',
            'prompt_ban_port_service': '🔒 <b>Выберите порт или сервис для блокировки устройства {ip}:</b>',
            'prompt_ban_port_duration': '⌛️ <b>Выберите длительность блокировки портов {port}/{proto} для устройства '
                                        '{ip}:</b>',
            'prompt_custom_port_input': '✏️ <b>Блокировка порта для устройства {ip}</b>\n'
                                        '\n'
                                        'Введите номер порта или порт/протокол (например: <code>80</code>, '
                                        '<code>53/udp</code>, <code>8080/tcp</code>):',
            'prompt_allow_port_service': '🟢 <b>Разрешение портов для устройства {ip}</b>\n'
                                         '\n'
                                         'Выберите сервис или порт для постоянного разрешения (трафик не будет '
                                         'блокироваться и вызывать алерты):',
            'prompt_custom_allow_port_input': '🟢 <b>Разрешение порта для устройства {ip}</b>\n'
                                              '\n'
                                              'Введите номер порта (1-65535) или порт/протокол (например: '
                                              '<code>8080</code>, <code>8080/tcp</code>, <code>53/udp</code> или '
                                              '<code>0</code> для всех портов):',
            'active_bans_header': '🔎 <b>Активные правила для устройства {ip}:</b>\n\n',
            'active_ban_ip_item': ' • <b>Полная блокировка IP</b> (Истекает: {expire})\n',
            'active_ban_port_item': ' • <b>Порт {port}/{proto}</b> (Истекает: {expire})\n',
            'active_bans_empty': 'Нет активных правил для этого устройства.',
            'err_session_lost': '❌ Ошибка: сессия утеряна. Начните заново с команды /router',
            'err_invalid_proto': '❌ Неверный протокол. Укажите tcp или udp (например, 80/tcp или 53/udp)',
            'err_invalid_port': '❌ Порт должен быть числом от 1 до 65535 (или 0 для всех портов).',
            'action_applying_ssh': 'Выполняю блокировку по SSH...',
            'action_unbanning_ssh': 'Снимаю блокировку по SSH...',
            'action_unbanning_port_ssh': 'Снимаю блокировку порта {port}/{proto} по SSH...',
            'action_banning_port_ssh': 'Добавляю правила блокировки порта по SSH...',
            'action_allowing_port_ssh': 'Добавляю правила разрешения порта по SSH...',
            'action_disallowing_port_ssh': 'Удаляю правила разрешения порта по SSH...',
            'port_blocked_success': 'Порт {port}/{proto} успешно заблокирован!',
            'port_unblocked_success': 'Блокировка порта {port}/{proto} снята!',
            'port_allowed_success': '🟢 Порт {port}/{proto} успешно разрешен для {ip}!',
            'port_disallowed_success': 'Разрешение для порта {port}/{proto} снято!',
            'ip_blocked_successfully': '🛑 IP {ip} успешно заблокирован на роутере!',
            'ip_block_failed': '❌ Ошибка блокировки: {desc}',
            'ip_block_error': 'Ошибка при блокировке: {e}',
            'ip_unblocked_successfully': '🟢 Блокировка с IP {ip} снята!',
            'ip_unblock_failed': '❌ Ошибка снятия блокировки: {desc}',
            'ip_unblock_error': 'Ошибка при разблокировке: {e}',
            'device_blocked_text': '\n\n🛑 <b>УСТРОЙСТВО {ip} ЗАБЛОКИРОВАНО НА РОУТЕРЕ!</b>',
            'invalid_data_format': 'Ошибка: неверный формат данных.',
            'clients_list_empty': '⚠️ Устройства не найдены или мониторинг роутера отключен в конфигурации.',
            'clients_list_header': '🖥 <b>Клиенты вашего роутера:</b>\n'
                                   'Выберите устройство из списка ниже для управления блокировками и разрешениями '
                                   'портов.\n',
            'client_details_title': '🖥 Управление клиентом роутера',
            'col_device_name': 'Имя устройства',
            'col_ip': 'IP-адрес',
            'col_mac': 'MAC-адрес',
            'col_net_status': 'Статус сети',
            'col_ban_status': 'Статус блокировки',
            'col_allowed_ports': 'Разрешенные порты',
            'allowed_ports_all': '🌐 Все порты (Доверенный)',
            'allowed_ports_none': 'По умолчанию',
            'status_active': '🟢 Активен',
            'status_offline': '⚪ Офлайн',
            'ban_status_full': '🛑 Заблокирован полностью',
            'ban_status_ports': '🔒 Есть блокировки портов',
            'ban_status_none': '🟢 Доступ разрешен',
            'client_active_rules_footer': '🔒 Всего активных правил: <b>{count}</b>'},
 'whitelist': {'whitelist_view_title': '📁 Белый список: {node_label}',
               'whitelist_empty': '<tr><td colspan="2" style="padding: 8px; color: #a6adc8; text-align: '
                                  'center;"><i>Правил в белом списке для этого узла нет. Все соединения проверяются '
                                  'стандартными правилами IPS.</i></td></tr>',
               'whitelist_type_header': 'Тип правила',
               'whitelist_value_header': 'Значение',
               'whitelist_rule_ip_port': '🌐 IP / Порт',
               'whitelist_rule_process': '⚙️ Процесс',
               'whitelist_view_all_title': '📋 Все правила белых списков Sentinel IPS',
               'whitelist_view_all_empty': '<tr><td colspan="2" style="padding: 8px; color: #bf616a; text-align: '
                                           'center;">❌ Нет настроенных правил ни для одного узла.</td></tr>',
               'global_node': '🌍 Глобально (Везде)',
               'router_node': '🔌 Роутер',
               'pve_node': '🖥️ Proxmox Host',
               'lxc_node': '📦 LXC {vmid} ({name})',
               'vps_node': '🌐 VPS {ip}',
               'offline_label': '{label} (офлайн)',
               'btn_show_all': '📋 Показать все правила',
               'btn_back_to_nodes': '🔙 К выбору узла',
               'btn_add_ip_port': '➕ Добавить IP/Порт',
               'btn_add_proc': '➕ Добавить Процесс',
               'btn_delete_rule': '🗑️ Удалить правило',
               'btn_back_to_nodes_list': '🔙 Назад к списку узлов',
               'btn_cancel': '❌ Отмена',
               'btn_del_ip': '🗑️ IP: {item}',
               'btn_del_proc': '🗑️ Proc: {item}',
               'btn_back_to_view': '🔙 Назад к просмотру',
               'manage_title': '⚙️ <b>Управление белыми списками Sentinel IPS</b>\n'
                               '\n'
                               'Выберите узел (ноду) для просмотра и настройки правил безопасности:',
               'add_ip_port_title': '➕ <b>Добавление IP/Порта в белый список</b>\n'
                                    'Узел: {node_label}\n'
                                    '\n'
                                    'Отправьте сообщением IP-адрес или связку IP:Порт (например: <code>1.2.3.4</code> '
                                    'или <code>1.2.3.4:22</code>, или <code>1.2.3.4:*</code> для любого порта):',
               'invalid_input': 'Неверный ввод. Попробуйте еще раз или нажмите Отмена.',
               'invalid_ip_port_format': '❌ Неверный формат IP/Порта. Примеры: <code>192.168.1.100</code> или '
                                         '<code>192.168.1.100:22</code> или <code>192.168.1.100:*</code>.',
               'rule_added_success': '🟢 <b>Правило успешно добавлено!</b>\n'
                                     '\n'
                                     '📁 <b>Белый список для узла: {node_label}</b>\n'
                                     '━━━━━━━━━━━━━━━━━━━━━━━━\n',
               'allowed_ip_ports': '<b>Разрешенные IP / IP:Порты:</b>\n',
               'allowed_processes': '<b>Разрешенные процессы:</b>\n',
               'add_proc_title': '➕ <b>Добавление процесса в белый список</b>\n'
                                 'Узел: {node_label}\n'
                                 '\n'
                                 'Отправьте сообщением имя процесса (например: <code>caddy</code>, <code>nginx</code> '
                                 'или <code>sshd</code>):',
               'invalid_proc_name': '❌ Неверное имя процесса (разрешены только латинские буквы и цифры). Попробуйте '
                                    'еще раз.',
               'proc_added_success': '🟢 <b>Процесс успешно добавлен!</b>\n'
                                     '\n'
                                     '📁 <b>Белый список для узла: {node_label}</b>\n'
                                     '━━━━━━━━━━━━━━━━━━━━━━━━\n',
               'empty_whitelist_err': '❌ Белый список этого узла пуст. Нечего удалять.',
               'del_rule_title': '🗑️ <b>Удаление правил белого списка</b>\n'
                                 'Узел: {node_label}\n'
                                 '\n'
                                 'Выберите правило, которое хотите удалить:',
               'del_success_alert': '🟢 Успешно удалено: {item}',
               'cli_add_help': '❌ Использование: <code>/whitelist_add &lt;IP или IP:Port&gt; [node]</code>\n'
                               'Пример: <code>/whitelist_add 1.2.3.4:22 router</code>',
               'cli_invalid_ip_port': '❌ Неверный формат IP/Порта.',
               'cli_added_ip_port': '🟢 Добавлено <code>{val}</code> в белый список узла <b>{label}</b>.',
               'cli_rule_exists': 'ℹ️ Правило <code>{val}</code> уже существует для узла <b>{label}</b>.',
               'cli_proc_help': '❌ Использование: <code>/whitelist_process &lt;имя процесса&gt; [node]</code>\n'
                                'Пример: <code>/whitelist_process openvpn global</code>',
               'cli_invalid_proc': '❌ Неверное имя процесса.',
               'cli_added_proc': '🟢 Добавлен процесс <code>{val}</code> в белый список узла <b>{label}</b>.',
               'cli_proc_exists': 'ℹ️ Процесс <code>{val}</code> уже находится в белом списке узла <b>{label}</b>.',
               'qwl_invalid_callback': '❌ Неверный формат callback-данных.',
               'qwl_added_success': '🟢 Успешно добавлено в белый список {label}: {val}',
               'qwl_added_msg': '\n\n✅ <b>Добавлено в белый список ({label}):</b> <code>{val}</code>',
               'qwl_already_whitelisted': 'ℹ️ Уже находится в белом списке {label}.',
               'qwl_save_error': '❌ Произошла ошибка при сохранении.'}}
