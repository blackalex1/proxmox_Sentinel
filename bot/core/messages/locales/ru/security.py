# Locale bundle: security (ru)

translations = {'auth': {'vps_ssh_login_alert': '# 🖥️ VPS SSH Security: {ip}\n'
                                 '---\n'
                                 '\n'
                                 '### 🟢 Успешный вход по SSH!\n'
                                 '\n'
                                 '| Параметр | Значение |\n'
                                 '| :--- | :--- |\n'
                                 '| **👤 Пользователь** | `{username}` |\n'
                                 '| **🌐 IP-адрес** | `{client_ip}` |\n'
                                 '{geo_row}| **🔑 Метод** | `{auth_method}`{key_info} |\n'
                                 '\n'
                                 '{security_aside}\n'
                                 '<details>\n'
                                 '  <summary>🔍 <b>Показать лог входа</b></summary>\n'
                                 '  <pre><code>{raw_line}</code></pre>\n'
                                 '</details>',
          'pve_web_login_alert': '# 🖥 Web GUI Access\n'
                                 '---\n'
                                 '\n'
                                 '### 🟢 Успешный вход в Proxmox Web GUI!\n'
                                 '\n'
                                 '| Параметр | Значение |\n'
                                 '| :--- | :--- |\n'
                                 '| **📦 Назначение** | {target_str} |\n'
                                 '| **👤 Пользователь** | `{user}` |\n'
                                 '| **🌐 IP-адрес** | `WEB_GUI` |\n'
                                 '\n'
                                 '<details>\n'
                                 '  <summary>🔍 <b>Показать лог входа</b></summary>\n'
                                 '  <pre><code>{line}</code></pre>\n'
                                 '</details>',
          'pve_web_fail_alert': '# 🖥 Web GUI Alert\n'
                                '---\n'
                                '\n'
                                '### ❌ ОШИБКА АВТОРИЗАЦИИ в Proxmox Web GUI!\n'
                                '\n'
                                '| Параметр | Значение |\n'
                                '| :--- | :--- |\n'
                                '| **📦 Назначение** | {target_str} |\n'
                                '| **👤 Попытка входа под** | `{user}` |\n'
                                '| **🌐 IP-адрес** | `{ip}` |\n'
                                '{geo_row}| **📝 Причина** | `{reason}` |\n'
                                '\n'
                                '<details>\n'
                                '  <summary>🔍 <b>Показать лог ошибки</b></summary>\n'
                                '  <pre><code>{line}</code></pre>\n'
                                '</details>',
          'ssh_login_alert': '# {emoji_str} SSH Access Report\n'
                             '---\n'
                             '\n'
                             '### 🟢 {title_str}\n'
                             '\n'
                             '| Параметр | Значение |\n'
                             '| :--- | :--- |\n'
                             '| **📦 Назначение** | {target_str} |\n'
                             '| **👤 Пользователь** | `{user}` |\n'
                             '| **🌐 IP-адрес** | `{ip}` |\n'
                             '{geo_row}| **🔑 Метод** | `{method}` |\n'
                             '{key_row}\n'
                             '<details>\n'
                             '  <summary>🔍 <b>Показать лог входа</b></summary>\n'
                             '  <pre><code>{line}</code></pre>\n'
                             '</details>',
          'ssh_fail_alert': '# {emoji_str} SSH Auth Alert\n'
                            '---\n'
                            '\n'
                            '### ❌ {title_str}\n'
                            '\n'
                            '| Параметр | Значение |\n'
                            '| :--- | :--- |\n'
                            '| **📦 Назначение** | {target_str} |\n'
                            '| **👤 Попытка входа под** | `{user}` |\n'
                            '| **🌐 IP-адрес** | `{ip}` |\n'
                            '{geo_row}| **🔑 Способ** | `{method_ru}` |\n'
                            '\n'
                            '<details>\n'
                            '  <summary>🔍 <b>Показать лог ошибки</b></summary>\n'
                            '  <pre><code>{line}</code></pre>\n'
                            '</details>',
          'sudo_alert': '# {emoji_str} Privileged Execution\n'
                        '---\n'
                        '\n'
                        '### 💻 {title_str}\n'
                        '\n'
                        '| Параметр | Значение |\n'
                        '| :--- | :--- |\n'
                        '| **📦 Назначение** | {target_str} |\n'
                        '| **👤 Пользователь** | `{user}` (от имени `{run_as}`) |\n'
                        '| **💻 Команда** | `{command}` |\n'
                        '\n'
                        '<details>\n'
                        '  <summary>🔍 <b>Показать лог выполнения</b></summary>\n'
                        '  <pre><code>{line}</code></pre>\n'
                        '</details>',
          'ssh_close_alert': '# 🚪 SSH Session Close\n'
                             '---\n'
                             '\n'
                             '### 🚪 SSH сессия завершена\n'
                             '\n'
                             '| Параметр | Значение |\n'
                             '| :--- | :--- |\n'
                             '| **📦 Назначение** | {target_str} |\n'
                             '| **👤 Пользователь** | `{user}` |\n'
                             '{ip_row}\n'
                             '<details>\n'
                             '  <summary>🔍 <b>Показать лог завершения</b></summary>\n'
                             '  <pre><code>{line}</code></pre>\n'
                             '</details>'},
 'ban_center': {'ban_center_title': '🛑 Центр блокировок Sentinel IPS',
                'ban_center_empty': '<tr><td colspan="4" style="padding: 8px; color: #a6adc8; text-align: '
                                    'center;"><i>Активных блокировок в системе нет.<br/>Вся сетевая активность '
                                    'находится под контролем Active IPS Engine.</i></td></tr>',
                'active_bans_header': '👤 Активные временные блокировки IP',
                'banned_keys_header': '🔑 Заблокированные SSH-ключи',
                'banned_login_ips_header': '🛡 Блокировки входа (Failed Logins)',
                'banned_panel_clients_header': '🚫 Заблокированные клиенты панелей',
                'col_panel': 'Панель',
                'col_client': 'Клиент',
                'col_inbound': 'Инбаунд',
                'col_ip': 'IP-адрес',
                'col_node': 'Узел',
                'col_reason': 'Причина',
                'col_expires': 'Истекает',
                'col_user': 'Пользователь',
                'col_banned_at': 'Забанен',
                'reason_manual': 'Вручную',
                'reason_2fa_blocked': '2FA-блокировка (Вход)',
                'remaining_hours': '{hours}ч {minutes}м',
                'remaining_minutes': '{minutes}м {seconds}с',
                'remaining_unknown': 'Неизвестно',
                'btn_unban_ip': '🔓 Разблокировать {ip}',
                'btn_unban_key': '🔓 Восстановить ключ (...{fp})',
                'btn_unban_pclient': '🔓 Разблокировать {email}',
                'load_err': '❌ Ошибка при загрузке Центра блокировок.',
                'open_err': '❌ Ошибка при открытии Центра блокировок.',
                'invalid_callback_err': '❌ Ошибка: Неверный формат callback.',
                'unban_in_progress': '⏳ Снятие блокировки...',
                'vps_not_found_err': 'VPS с IP {ip} не найден в настройках',
                'unban_success_alert': '🟢 Блокировка с IP {ip} успешно снята!',
                'unban_failed_alert': '❌ Ошибка снятия блокировки: {desc}',
                'key_not_found_err': '❌ Ошибка: Ключ не найден в БД или уже разблокирован.',
                'restore_key_in_progress': '⏳ Восстановление ключа...',
                'invalid_lxc_id_err': 'Неверный ID LXC.',
                'restore_key_success_alert': '🟢 SSH-ключ успешно восстановлен!',
                'restore_key_failed_alert': '❌ Ошибка восстановления: {desc}',
                'pclient_unban_in_progress': '⏳ Разблокировка клиента {email}...',
                'pclient_unban_success_alert': '🟢 Клиент {email} успешно разблокирован на панели {panel_name}!',
                'pclient_unban_failed_alert': '❌ Ошибка разблокировки клиента {email}: {desc}',
                'unban_login_ip_help': '🟢 <b>Разблокировка IP входа:</b>\n'
                                       'Используйте команду: <code>/unban_login_ip &lt;ip&gt;</code>',
                'unban_login_ip_in_progress': '⏳ Разблокировка IP <code>{ip}</code> на всех панелях...',
                'unban_login_ip_success_item': '  • {name}: 🟢 Разблокирован',
                'unban_login_ip_failed_item': '  • {name}: 🔴 Ошибка ({error})',
                'unban_login_ip_success': '✅ <b>Результаты разблокировки IP <code>{ip}</code>:</b>\n{details}',
                'unban_login_ip_failed': '❌ <b>Не удалось разблокировать IP <code>{ip}</code>:</b>\n{details}'},
 'threats': {'title': '⚡ Журнал инцидентов безопасности Sentinel IPS',
             'empty': 'Инцидентов безопасности не зафиксировано. Система работает в штатном режиме.',
             'col_time': '📅 Время',
             'col_ip': '🌐 IP атаки',
             'col_user': '👤 Пользователь',
             'col_reaction': '⚡ Реакция'},
 'traffic': {'ips_investigation_success_alert': '# ✅ IPS Investigation Done\n'
                                                '---\n'
                                                '\n'
                                                '### ✅ [IPS: Расследование завершено] Нарушитель найден!\n'
                                                '\n'
                                                '| Параметр | Значение |\n'
                                                '| :--- | :--- |\n'
                                                '| **👤 Нарушитель** | `{xray_client}` (Заблокирован) |\n'
                                                '| **🔓 Транзитный туннель** | `{tunnel_email}` (Активен) |\n'
                                                '| **🌐 Маршрут атаки** | `{target_panel_name}` → `{tunnel_email}` → '
                                                '`{server_ip}` → `{dst_ip}:{dpt}` |\n'
                                                '\n'
                                                '✨ *Все остальные пользователи туннеля снова в сети!*\n'
                                                '\n'
                                                '<details>\n'
                                                '  <summary>📋 <b>Показать детали глобального бана '
                                                'нарушителя</b></summary>\n'
                                                '  <pre><code>{block_details_str}</code></pre>\n'
                                                '</details>\n'
                                                '\n'
                                                '<details>\n'
                                                '  <summary>📋 <b>Показать статус транзитного туннеля</b></summary>\n'
                                                '  <pre><code>{unblock_details_str}</code></pre>\n'
                                                '</details>\n'
                                                '\n'
                                                '*Sentinel Security Guard • Время: {timestamp}*',
             'ips_investigation_failed_alert': '# ⚠️ IPS Investigation Failed\n'
                                               '---\n'
                                               '\n'
                                               '### ⚠️ [IPS: Расследование не удалось] Виновник не обнаружен!\n'
                                               '\n'
                                               '| Параметр | Значение |\n'
                                               '| :--- | :--- |\n'
                                               '| **🚨 Статус туннеля** | `{tunnel_email}` (Оставлен в бане) |\n'
                                               '| **🎯 Цель атаки** | `{dst_ip}:{dpt}` |\n'
                                               '\n'
                                               '<details>\n'
                                               '  <summary>🔍 <b>Показать собранные фрагменты логов</b></summary>\n'
                                               '  <pre><code>{logs_text}</code></pre>\n'
                                               '</details>\n'
                                               '\n'
                                               '*Sentinel Security Guard • Время: {timestamp}*',
             'ips_sensitive_access_alert': '# 🚨 Traffic Security Alert\n'
                                           '---\n'
                                           '\n'
                                           '### 🚨 [VPS Traffic Security] Входящий доступ на sensitive порт!\n'
                                           '\n'
                                           '| Параметр | Значение |\n'
                                           '| :--- | :--- |\n'
                                           '| **🌐 VPS Server** | `{server_ip}` |\n'
                                           '| **🔌 Протокол** | `{proto}` |\n'
                                           '| **👤 Источник** | `{src}:{spt}` |\n'
                                           '| **🎯 Назначение** | `{dst}:{dpt}` |\n'
                                           '\n'
                                           '*Sentinel Security Guard • Время: {timestamp}*',
             'ips_hysteria_attack_alert': '# 🚨 Traffic Attack Detected\n'
                                          '---\n'
                                          '\n'
                                          '### 🚨 [VPS Traffic IPS] Обнаружена атака через Hysteria-туннель!\n'
                                          '\n'
                                          '| Параметр | Значение |\n'
                                          '| :--- | :--- |\n'
                                          '| **🌐 VPS Server** | `{server_ip}` |\n'
                                          '| **🔥 Временный бан** | `{email}` |\n'
                                          '| **🔌 Протокол** | `{proto}` |\n'
                                          '| **👤 Источник** | `{src}:{spt}` |\n'
                                          '| **🎯 Назначение** | `{dst}:{dpt}` |\n'
                                          '\n'
                                          '<details>\n'
                                          '  <summary>📋 <b>Показать статус блокировки туннеля</b></summary>\n'
                                          '  <pre><code>{block_details_str}</code></pre>\n'
                                          '</details>\n'
                                          '\n'
                                          '*Sentinel Security Guard • Время: {timestamp}*',
             'ips_xray_attack_alert': '# 🚨 Traffic Attack Blocked\n'
                                      '---\n'
                                      '\n'
                                      '### 🚨 [VPS Traffic IPS] Блокировка сетевой атаки!\n'
                                      '\n'
                                      '| Параметр | Значение |\n'
                                      '| :--- | :--- |\n'
                                      '| **🌐 VPS Server** | `{server_ip}` |\n'
                                      '| **👤 Нарушитель (Xray)** | `{email}`{inbound_display} |\n'
                                      '| **🔌 Протокол** | `{proto}` |\n'
                                      '| **👤 Источник** | `{src}:{spt}`{proc_info} |\n'
                                      '| **🎯 Назначение** | `{dst}:{dpt}` |\n'
                                      '\n'
                                      '<details>\n'
                                      '  <summary>🚨 <b>Показать статус авто-блокировки аккаунта '
                                      'нарушителя</b></summary>\n'
                                      '  <pre><code>{block_details_str}</code></pre>\n'
                                      '</details>\n'
                                      '\n'
                                      '*Sentinel Security Guard • Время: {timestamp}*',
             'ips_whitelisted_alert': '# ℹ️ Connection Allowed\n'
                                      '---\n'
                                      '\n'
                                      '### ℹ️ [VPS Traffic] Разрешенное соединение\n'
                                      '\n'
                                      '| Параметр | Значение |\n'
                                      '| :--- | :--- |\n'
                                      '| **🌐 VPS Server** | `{server_ip}` |\n'
                                      '| **📁 Процесс** | `{proc_name}` |\n'
                                      '| **🔌 Протокол** | `{proto}` |\n'
                                      '| **👤 Источник** | `{src}:{spt}` |\n'
                                      '| **🎯 Назначение** | `{dst}:{dpt}` |\n'
                                      '\n'
                                      '*Sentinel Security Guard • Время: {timestamp}*',
             'ips_process_killed_alert': '# 🚨 Traffic Attack Blocked\n'
                                         '---\n'
                                         '\n'
                                         '### 🚨 [VPS Traffic IPS] Заблокирована сетевая атака!\n'
                                         '\n'
                                         '| Параметр | Значение |\n'
                                         '| :--- | :--- |\n'
                                         '| **🌐 VPS Server** | `{server_ip}` |\n'
                                         '| **🔥 Действие** | **Процесс уничтожен (kill -9)** |\n'
                                         '| **📁 Процесс** | `{proc_name}` (PID: `{killed_pid}`) |\n'
                                         '| **🔌 Протокол** | `{proto}` |\n'
                                         '| **👤 Источник** | `{src}:{spt}` |\n'
                                         '| **🎯 Назначение** | `{dst}:{dpt}` |\n'
                                         '\n'
                                         '*Sentinel Security Guard • Время: {timestamp}*',
             'ips_process_warning_alert': '# ⚠️ Traffic Sensitive Alert\n'
                                          '---\n'
                                          '\n'
                                          '### ⚠️ [VPS Traffic Warning] Исходящее соединение на sensitive порт!\n'
                                          '\n'
                                          '| Параметр | Значение |\n'
                                          '| :--- | :--- |\n'
                                          '| **🌐 VPS Server** | `{server_ip}` |\n'
                                          '| **🔌 Протокол** | `{proto}` |\n'
                                          '| **👤 Источник** | `{src}:{spt}`{proc_info} |\n'
                                          '| **🎯 Назначение** | `{dst}:{dpt}` |\n'
                                          '\n'
                                          '*Sentinel Security Guard • Время: {timestamp}*',
             'local_traffic_alert': '# {clean_h1}\n'
                                    '---\n'
                                    '\n'
                                    '### {title}\n'
                                    '\n'
                                    '| Параметр | Значение |\n'
                                    '| :--- | :--- |\n'
                                    '| **📦 Контейнер** | {vmid} (`{container_name}`) |\n'
                                    '| **🏷️ Угроза** | {label} |\n'
                                    '| **🔌 Протокол** | `{proto}` |\n'
                                    '| **🧭 Направление** | {direction_text} |\n'
                                    '| **👤 Источник** | `{src}:{spt}` |\n'
                                    '| **🎯 Назначение** | `{dst}:{dpt}` |\n'
                                    '{vpn_ip_row}{vpn_client_row}{vpn_inbound_row}\n'
                                    '\n'
                                    '{block_details_block}\n'
                                    '\n'
                                    '*Sentinel Security Guard • Время: {timestamp}*',
             'local_h1_allowed': 'ℹ️ Connection Allowed',
             'local_h1_blocked': '🚨 Attack Blocked',
             'local_h1_critical': '🚨 Critical Alert',
             'local_h1_warning': '⚠️ Warning Alert',
             'local_h1_default': '⚠️ Traffic Alert',
             'local_direction_in': 'ВХОДЯЩЕЕ',
             'local_direction_out': 'ИСХОДЯЩЕЕ',
             'local_real_ip': '| **👤 Реальный IP** | `{real_client_ip}` |\n',
             'local_vpn_client': '| **👤 Клиент VPN** | `{xray_client_email}` |\n',
             'local_vpn_inbound': '| **🔌 Инбаунд VPN** | `{inbound_tag}` |\n',
             'local_block_status': '\n'
                                   '<details>\n'
                                   '  <summary>🚨 <b>Показать статус авто-блокировки аккаунта</b></summary>\n'
                                   '  <pre><code>{block_details_str}</code></pre>\n'
                                   '</details>',
             'proc_info_tmpl': ' (Процесс: `{proc_name}`)'}}
