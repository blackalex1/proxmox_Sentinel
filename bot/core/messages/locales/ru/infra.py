# Locale bundle: infra (ru)

translations = {'ansible': {'missing_dir': '🛠 <b>Управление Ansible:</b>\n'
                            '❌ Папка <code>{playbooks_dir}</code> не найдена.\n'
                            'Создайте эту папку во время запуска или проверьте настройки '
                            '<code>ANSIBLE_PLAYBOOKS_DIR</code> в .env',
             'playbooks_menu': '🛠 <b>Управление Ansible:</b>\nВыберите плейбук для запуска:',
             'ask_host': '🛠 Плейбук: <b>{filename}</b>\n'
                         '\n'
                         'На каких хостах (или группах) вы хотите его запустить?\n'
                         '<i>✏️ Выберите цель из списка (прочитано из вашего hosts.ini)\n'
                         'или напишите свой вариант вручную прямо в чат:</i>',
             'setup_loading': '🔍 <b>Настройка окружения Ansible</b>\n'
                              '\n'
                              '⌛ <i>Опрашиваю состояние LXC контейнеров и удаленных серверов, пожалуйста, '
                              'подождите...</i>',
             'setup_menu': '🔑 <b>Настройка окружения Ansible</b>\n'
                           '\n'
                           'Я могу автоматически создать пользователя <code>ansible</code> с беспарольным доступом '
                           '<code>sudo</code> и установить сгенерированный публичный SSH-ключ:\n'
                           '• На самом <b>Хосте Proxmox VE</b>.\n'
                           '• Во все <b>активные LXC контейнеры</b> на хосте Proxmox.\n'
                           '• На все <b>удаленные VPS сервера</b>, добавленные в конфигурацию.\n'
                           '\n'
                           '📋 <b>Текущий статус готовности хостов:</b>\n'
                           '{status_text}<i>🟢 — настроен для работы с Ansible\n'
                           '🔴 — не настроен (или недоступен)</i>\n'
                           '\n'
                           'Выберите область настройки:',
             'setup_host_start': '⏳ Начинаю настройку на хосте Proxmox VE. Это может занять несколько секунд...',
             'setup_lxc_start': '⏳ Начинаю настройку во всех активных LXC контейнерах. Это может занять несколько '
                                'секунд...',
             'setup_vps_start': '⏳ Начинаю настройку на всех удаленных VPS серверах. Пожалуйста, подождите...',
             'setup_success': '✅ Настройка SSH-доступа для Ansible успешно завершена: <b>{target_name}</b>',
             'setup_failed': '❌ Ошибка при настройке {target_name}: <code>{error_msg}</code>',
             'run_start': '⏳ Запускаю <b>{filename}</b> {target_text}...\nОжидайте результата.',
             'run_success': '✅ Плейбук <b>{filename}</b> успешно выполнен!',
             'run_failed': '❌ Ошибка выполнения плейбука <b>{filename}</b>:\n<pre><code>{error_msg}</code></pre>',
             'reboot_start': '⏳ Перезагружаю хосты <b>{host_name}</b> через Ansible...',
             'reboot_success': '✅ Хосты <b>{host_name}</b> успешно отправлены в перезагрузку!',
             'reboot_failed': '❌ Ошибка перезагрузки хостов <b>{host_name}</b>:\n<pre><code>{error_msg}</code></pre>',
             'target_all_hosts': 'на <b>всех хостах</b>',
             'target_host': 'на хосте: <b>{host}</b>'},
 'nodes': {'vps_offline_alert': '# ⚠️ VPS Offline\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [Remote Monitor] Удаленный VPS-сервер отключен!\n'
                                '\n'
                                '| Параметр | Значение |\n'
                                '| :--- | :--- |\n'
                                '| **🌐 IP-адрес** | `{ip}` |\n'
                                '| **🔌 Статус** | 🔴 Недоступен (SSH порт закрыт) |\n',
           'vps_online_alert': '# ✅ VPS Online\n'
                               '---\n'
                               '\n'
                               '### ✅ [Remote Monitor] Связь с VPS восстановлена!\n'
                               '\n'
                               '| Параметр | Значение |\n'
                               '| :--- | :--- |\n'
                               '| **🌐 IP-адрес** | `{ip}` |\n'
                               '| **🔌 Статус** | 🟢 Доступен (Связь восстановлена) |\n',
           'node_offline_alert': '# ⚠️ Node Offline\n'
                                 '---\n'
                                 '\n'
                                 '### ⚠️ [Cluster Monitor] Сервер недоступен!\n'
                                 '\n'
                                 '| Параметр | Значение |\n'
                                 '| :--- | :--- |\n'
                                 '| **🖥 Сервер** | **{node_name}** |\n'
                                 '| **🔌 Статус** | 🔴 {status} |\n',
           'node_online_alert': '# ✅ Node Online\n'
                                '---\n'
                                '\n'
                                '### ✅ [Cluster Monitor] Сервер снова в сети!\n'
                                '\n'
                                '| Параметр | Значение |\n'
                                '| :--- | :--- |\n'
                                '| **🖥 Сервер** | **{node_name}** |\n'
                                '| **🔌 Статус** | 🟢 Доступен |\n',
           'status_audit_title': '📊 Аудит статуса систем Proxmox Sentinel',
           'hypervisor_header': '🖥 Hypervisor (Proxmox VE)',
           'pve_not_configured': '⚪ <b>Proxmox VE:</b> Не настроен',
           'pve_error': '🔴 <b>Proxmox VE:</b> Ошибка: <code>{error}</code>',
           'pve_nodes_not_found': '🔴 <b>Proxmox VE:</b> Ноды не найдены',
           'pve_online_detail': '🟢 online (CPU: {cpu:.1f}% | RAM: {mem:.1f}/{maxmem:.1f} GB)',
           'pve_offline_detail': '🔴 offline',
           'security_services_header': '🛡 Фоновые службы безопасности',
           'service_active': '🟢 Активен',
           'service_stopped': '🔴 Остановлен',
           'ips_enabled': '🟢 Защита включена',
           'ips_disabled': '🔴 Защита выключена',
           'remote_vps_disabled_env': '⚪ Выключен в .env',
           'panels_header': '🛡️ Панели Sentinel Panel',
           'panels_not_found': '⚪ <i>Подключенные панели не найдены</i>',
           'panel_online_detail': '🟢 online (Клиенты: {online}/{total} | CPU: {cpu:.1f}%)',
           'panel_online_simple': '🟢 online',
           'panel_offline_detail': '🔴 offline ({error})'},
 'proxmox': {'title': '👨\u200d💻 <b>Панель управления Proxmox:</b>\nВыберите сервер из списка ниже:',
             'error_connect': '❌ Ошибка подключения: {err_msg}',
             'error': 'Ошибка: {err_msg}',
             'vms_title': '<b>Виртуальные машины на сервере {node_name}:</b>',
             'host_label': '💻 [Хост] Proxmox VE',
             'back_to_nodes': '🔙 Назад к серверам',
             'host_logs_btn': '🔒 Логи входа Хоста',
             'host_traffic_btn': '🌐 Трафик Хоста',
             'wl_ips_btn': '⚙️ Белый список IPS',
             'refresh_status_btn': '🔄 Обновить статус',
             'back_to_vms_btn': '🔙 Назад к списку ВМ',
             'shutdown_btn': '🔌 Мягко выключить',
             'stop_btn': '🛑 Убить (Stop)',
             'reboot_btn': '🔄 Перезагрузить',
             'reboot_host_btn': '🔄 Перезагрузить Хост',
             'start_btn': '▶️ Запустить',
             'auth_logs_btn': '🔒 Логи входа',
             'ports_traffic_btn': '🌐 Трафик портов',
             'clone_btn': '👯 Клонировать',
             'refresh_log_btn': '🔄 Обновить лог',
             'back_to_vm_btn': '🔙 Назад к ВМ',
             'refresh_traffic_btn': '🔄 Обновить активность',
             'back_to_panel_btn': '🔙 Назад к панели',
             'confirm_host_reboot_title': '⚠️ <b>ВНИМАНИЕ! Перезагрузка хоста {node_name}</b>\n'
                                          '\n'
                                          'Вы действительно хотите перезагрузить гипервизор <b>{node_name}</b>?\n'
                                          '<i>Это приведет к остановке всех запущенных на нем виртуальных машин и '
                                          'контейнеров!</i>',
             'confirm_host_reboot_yes': '⚠️ Да, перезагрузить хост!',
             'confirm_host_reboot_cancel': '❌ Отмена',
             'host_reboot_initiated': '⏳ Запрос на перезагрузку хоста {node_name} отправлен!',
             'status_host_title': '💻 <b>Хост Proxmox VE ({node_name})</b>\n\n',
             'status_vm_title': '🖥 <b>ВМ {vmid} ({name})</b>\n\n',
             'status_label': 'Статус',
             'status_online_vm': '🟢 Включена',
             'status_online_host': '🟢 Включен',
             'status_offline_vm': '🔴 Выключена',
             'version_label': 'Версия PVE',
             'cpu_cores_label': 'Ядер CPU',
             'cpu_load_label': 'Нагрузка CPU',
             'ram_usage_label': 'Потребление RAM',
             'uptime_label': 'Uptime',
             'type_label': 'Тип',
             'host_data_actual': 'Данные хоста актуальны',
             'vm_data_actual': 'Данные ВМ актуальны',
             'error_vm_load': 'Ошибка загрузки ВМ: {err_msg}',
             'exec_cmd': '⏳ Выполняю команду {action}...',
             'error_cmd': '❌ Ошибка команды:\n{err_msg}',
             'uptime_format': '{hours}ч {minutes}м {seconds}с',
             'clone_title': '📝 <b>Клонирование {vm_type} {vmid} ({node_name})</b>\n'
                            '\n'
                            'Введите <b>ID</b> для новой машины (например, 105):',
             'clone_id_nan': '❌ ID должен быть числом! Попробуйте еще раз:',
             'clone_name_prompt': 'Введите <b>имя</b> для новой машины (например, my-new-server):',
             'clone_starting': '⏳ Начинаю клонирование...',
             'clone_success': '✅ Клонирование успешно запущено!\nНовая машина ID: {new_id}, Имя: {new_name}',
             'clone_error': '❌ Ошибка клонирования: {error}',
             'host_label_default': 'Хост Proxmox VE',
             'auth_logs_host_title': '🔒 <b>Логи авторизации Хоста {node_name}:</b>\n\n',
             'auth_logs_lxc_title': '🔒 <b>Логи авторизации LXC {vmid} ({name}):</b>\n\n',
             'auth_logs_vps_title': '🔒 <b>Логи авторизации VPS ({server_ip}):</b>\n\n',
             'logs_empty': '<i>История пуста или бот был недавно перезапущен. Логи появятся при новых попытках '
                           'входа.</i>',
             'logs_truncated': '\n\n<i>... [Часть логов обрезана из-за лимитов Telegram] ...</i>',
             'log_actual': 'Лог актуален',
             'log_error': 'Ошибка получения логов: {err_msg}',
             'log_vps_error': 'Ошибка получения логов VPS: {err_msg}',
             'traffic_host_title': '🌐 <b>Сетевая активность Хоста {node_name}:</b>\n',
             'traffic_lxc_title': '🌐 <b>Сетевая активность LXC {vmid} ({name}):</b>\n',
             'traffic_subtitle': '<i>(Последние соединения и уровень их безопасности)</i>\n\n',
             'traffic_empty': '<i>Соединений не зафиксировано. Сетевая активность появится при прохождении нового '
                              'трафика.</i>',
             'traffic_direction_in_label': 'Входящее соединение',
             'traffic_direction_out_label': 'Исходящее соединение',
             'traffic_truncated': '\n\n<i>... [Часть активности обрезана из-за лимитов Telegram] ...</i>',
             'traffic_actual': 'Активность актуальна',
             'traffic_error': 'Ошибка получения сетевой активности: {err_msg}'},
 'resources': {'vps_cpu_alert': '# ⚠️ CPU High Load\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [VPS Monitor] Высокая нагрузка CPU (более 5 минут)!\n'
                                '\n'
                                '| Параметр | Значение |\n'
                                '| :--- | :--- |\n'
                                '| **🌐 VPS IP** | `{ip}` |\n'
                                '| **🔴 CPU load** | **{cpu:.1f}%** (Порог: {threshold}%) |\n',
               'vps_ram_alert': '# ⚠️ RAM High Usage\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [VPS Monitor] Высокое потребление RAM (более 5 минут)!\n'
                                '\n'
                                '| Параметр | Значение |\n'
                                '| :--- | :--- |\n'
                                '| **🌐 VPS IP** | `{ip}` |\n'
                                '| **🔴 ОЗУ load** | **{ram_pct:.1f}%** (Порог: {threshold}%) |\n',
               'vps_disk_alert': '# ⚠️ Disk Full Alert\n'
                                 '---\n'
                                 '\n'
                                 '### ⚠️ [VPS Monitor] Переполнение Диска VPS!\n'
                                 '\n'
                                 '| Параметр | Значение |\n'
                                 '| :--- | :--- |\n'
                                 '| **🌐 VPS IP** | `{ip}` |\n'
                                 '| **🔴 Диск usage** | **{disk_pct:.1f}%** (Порог: {threshold}%) |\n',
               'lxc_state_alert': '# {emoji} VM Status Alert\n'
                                  '---\n'
                                  '\n'
                                  '### {emoji} Изменение статуса LXC контейнера!\n'
                                  '\n'
                                  '| Параметр | Значение |\n'
                                  '| :--- | :--- |\n'
                                  '| **📦 ID** | `{vmid}` |\n'
                                  '| **🏷 Имя** | `{name}` |\n'
                                  '| **⚡️ Сервер** | `{node_name}` |\n'
                                  '| **ℹ️ Статус** | **{status_text}** |\n',
               'lxc_cpu_alert': '# ⚠️ CPU Load Alert\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [LXC Monitor] Высокая нагрузка CPU (более 5 минут)!\n'
                                '\n'
                                '| Параметр | Значение |\n'
                                '| :--- | :--- |\n'
                                '| **📦 LXC Container** | {vmid} (`{name}`) |\n'
                                '| **🔴 CPU load** | **{cpu:.1f}%** (Порог: {threshold}%) |\n',
               'lxc_ram_alert': '# ⚠️ RAM Load Alert\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [LXC Monitor] Высокое потребление RAM (более 5 минут)!\n'
                                '\n'
                                '| Параметр | Значение |\n'
                                '| :--- | :--- |\n'
                                '| **📦 LXC Container** | {vmid} (`{name}`) |\n'
                                '| **🔴 ОЗУ usage** | **{mem_pct:.1f}%** ({mem:.1f} / {maxmem:.1f} GB) (Порог: '
                                '{threshold}%) |\n',
               'lxc_disk_alert': '# ⚠️ Disk Full Alert\n'
                                 '---\n'
                                 '\n'
                                 '### ⚠️ [LXC Monitor] Переполнение Диска LXC!\n'
                                 '\n'
                                 '| Параметр | Значение |\n'
                                 '| :--- | :--- |\n'
                                 '| **📦 LXC Container** | {vmid} (`{name}`) |\n'
                                 '| **🔴 Диск usage** | **{disk_pct:.1f}%** ({disk:.1f} / {maxdisk:.1f} GB) (Порог: '
                                 '{threshold}%) |\n'}}
