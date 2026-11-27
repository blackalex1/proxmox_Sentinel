# Locale bundle: infra (en)

translations = {'ansible': {'missing_dir': '🛠 <b>Ansible Control:</b>\n'
                            '❌ Folder <code>{playbooks_dir}</code> not found.\n'
                            'Please create this directory or check <code>ANSIBLE_PLAYBOOKS_DIR</code> in your .env',
             'playbooks_menu': '🛠 <b>Ansible Control:</b>\nSelect a playbook to run:',
             'ask_host': '🛠 Playbook: <b>{filename}</b>\n'
                         '\n'
                         'Which hosts (or groups) do you want to run it on?\n'
                         '<i>✏️ Select a target from the list (read from hosts.ini)\n'
                         'or type a custom target in chat:</i>',
             'setup_loading': '🔍 <b>Ansible Setup</b>\n'
                              '\n'
                              '⌛ <i>Checking LXC containers and remote servers status, please wait...</i>',
             'setup_menu': '🔑 <b>Ansible Environment Setup</b>\n'
                           '\n'
                           'I can automatically create the <code>ansible</code> user with passwordless '
                           '<code>sudo</code> and configure the generated public SSH key on:\n'
                           '• The <b>Proxmox VE Host</b>.\n'
                           '• All <b>active LXC containers</b> on Proxmox.\n'
                           '• All <b>remote VPS servers</b> in configuration.\n'
                           '\n'
                           '📋 <b>Current Host Readiness:</b>\n'
                           '{status_text}<i>🟢 — configured for Ansible\n'
                           '🔴 — not configured (or offline)</i>\n'
                           '\n'
                           'Select setup target:',
             'setup_host_start': '⏳ Starting setup on Proxmox VE host. This may take a few seconds...',
             'setup_lxc_start': '⏳ Starting setup on all active LXC containers. This may take a few seconds...',
             'setup_vps_start': '⏳ Starting setup on all remote VPS servers. Please wait...',
             'setup_success': '✅ SSH access for Ansible successfully configured: <b>{target_name}</b>',
             'setup_failed': '❌ Error setting up {target_name}: <code>{error_msg}</code>',
             'run_start': '⏳ Running <b>{filename}</b> {target_text}...\nPlease wait.',
             'run_success': '✅ Playbook <b>{filename}</b> executed successfully!',
             'run_failed': '❌ Playbook <b>{filename}</b> failed:\n<pre><code>{error_msg}</code></pre>',
             'reboot_start': '⏳ Rebooting hosts <b>{host_name}</b> via Ansible...',
             'reboot_success': '✅ Reboot command sent successfully to <b>{host_name}</b>!',
             'reboot_failed': '❌ Failed to reboot hosts <b>{host_name}</b>:\n<pre><code>{error_msg}</code></pre>',
             'target_all_hosts': 'on <b>all hosts</b>',
             'target_host': 'on host: <b>{host}</b>'},
 'nodes': {'vps_offline_alert': '# ⚠️ VPS Offline\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [Remote Monitor] Remote VPS server is offline!\n'
                                '\n'
                                '| Parameter | Value |\n'
                                '| :--- | :--- |\n'
                                '| **🌐 IP Address** | `{ip}` |\n'
                                '| **🔌 Status** | 🔴 Offline (SSH port closed) |\n',
           'vps_online_alert': '# ✅ VPS Online\n'
                               '---\n'
                               '\n'
                               '### ✅ [Remote Monitor] Connection with VPS restored!\n'
                               '\n'
                               '| Parameter | Value |\n'
                               '| :--- | :--- |\n'
                               '| **🌐 IP Address** | `{ip}` |\n'
                               '| **🔌 Status** | 🟢 Online (Connection restored) |\n',
           'node_offline_alert': '# ⚠️ Node Offline\n'
                                 '---\n'
                                 '\n'
                                 '### ⚠️ [Cluster Monitor] Server is offline!\n'
                                 '\n'
                                 '| Parameter | Value |\n'
                                 '| :--- | :--- |\n'
                                 '| **🖥 Server** | **{node_name}** |\n'
                                 '| **🔌 Status** | 🔴 {status} |\n',
           'node_online_alert': '# ✅ Node Online\n'
                                '---\n'
                                '\n'
                                '### ✅ [Cluster Monitor] Server is back online!\n'
                                '\n'
                                '| Parameter | Value |\n'
                                '| :--- | :--- |\n'
                                '| **🖥 Server** | **{node_name}** |\n'
                                '| **🔌 Status** | 🟢 Online |\n',
           'status_audit_title': '📊 Proxmox Sentinel System Status Audit',
           'hypervisor_header': '🖥 Hypervisor (Proxmox VE)',
           'pve_not_configured': '⚪ <b>Proxmox VE:</b> Not configured',
           'pve_error': '🔴 <b>Proxmox VE:</b> Error: <code>{error}</code>',
           'pve_nodes_not_found': '🔴 <b>Proxmox VE:</b> Nodes not found',
           'pve_online_detail': '🟢 online (CPU: {cpu:.1f}% | RAM: {mem:.1f}/{maxmem:.1f} GB)',
           'pve_offline_detail': '🔴 offline',
           'security_services_header': '🛡 Background Security Services',
           'service_active': '🟢 Active',
           'service_stopped': '🔴 Stopped',
           'ips_enabled': '🟢 Protection enabled',
           'ips_disabled': '🔴 Protection disabled',
           'remote_vps_disabled_env': '⚪ Disabled in .env',
           'panels_header': '🛡️ Sentinel Panels',
           'panels_not_found': '⚪ <i>No connected panels found</i>',
           'panel_online_detail': '🟢 online (Clients: {online}/{total} | CPU: {cpu:.1f}%)',
           'panel_online_simple': '🟢 online',
           'panel_offline_detail': '🔴 offline ({error})'},
 'proxmox': {'title': '👨\u200d💻 <b>Proxmox Control Panel:</b>\nSelect a server from the list below:',
             'error_connect': '❌ Connection error: {err_msg}',
             'error': 'Error: {err_msg}',
             'vms_title': '<b>Virtual Machines on server {node_name}:</b>',
             'host_label': '💻 [Host] Proxmox VE',
             'back_to_nodes': '🔙 Back to Servers',
             'host_logs_btn': '🔒 Host Login Logs',
             'host_traffic_btn': '🌐 Host Traffic',
             'wl_ips_btn': '⚙️ IPS Whitelist',
             'refresh_status_btn': '🔄 Refresh Status',
             'back_to_vms_btn': '🔙 Back to VM List',
             'shutdown_btn': '🔌 Graceful Shutdown',
             'stop_btn': '🛑 Stop VM',
             'reboot_btn': '🔄 Reboot VM',
             'reboot_host_btn': '🔄 Reboot Host',
             'start_btn': '▶️ Start VM',
             'auth_logs_btn': '🔒 Login Logs',
             'ports_traffic_btn': '🌐 Port Traffic',
             'clone_btn': '👯 Clone VM',
             'refresh_log_btn': '🔄 Refresh Log',
             'back_to_vm_btn': '🔙 Back to VM',
             'refresh_traffic_btn': '🔄 Refresh Activity',
             'back_to_panel_btn': '🔙 Back to Panel',
             'confirm_host_reboot_title': '⚠️ <b>WARNING! Host Reboot ({node_name})</b>\n'
                                          '\n'
                                          'Are you sure you want to reboot hypervisor <b>{node_name}</b>?\n'
                                          '<i>This will stop all running VMs and LXC containers on this host!</i>',
             'confirm_host_reboot_yes': '⚠️ Yes, Reboot Host!',
             'confirm_host_reboot_cancel': '❌ Cancel',
             'host_reboot_initiated': '⏳ Host reboot request sent for {node_name}!',
             'status_host_title': '💻 <b>Proxmox VE Host ({node_name})</b>\n\n',
             'status_vm_title': '🖥 <b>VM {vmid} ({name})</b>\n\n',
             'status_label': 'Status',
             'status_online_vm': '🟢 Running',
             'status_online_host': '🟢 Online',
             'status_offline_vm': '🔴 Stopped',
             'version_label': 'PVE Version',
             'cpu_cores_label': 'CPU Cores',
             'cpu_load_label': 'CPU Load',
             'ram_usage_label': 'RAM Usage',
             'uptime_label': 'Uptime',
             'type_label': 'Type',
             'host_data_actual': 'Host data is up to date',
             'vm_data_actual': 'VM data is up to date',
             'error_vm_load': 'Error loading VM: {err_msg}',
             'exec_cmd': '⏳ Executing command {action}...',
             'error_cmd': '❌ Command error:\n{err_msg}',
             'uptime_format': '{hours}h {minutes}m {seconds}s',
             'clone_title': '📝 <b>Cloning {vm_type} {vmid} ({node_name})</b>\n'
                            '\n'
                            'Enter <b>ID</b> for the new machine (e.g., 105):',
             'clone_id_nan': '❌ ID must be a number! Please try again:',
             'clone_name_prompt': 'Enter a <b>name</b> for the new machine (e.g., my-new-server):',
             'clone_starting': '⏳ Starting cloning...',
             'clone_success': '✅ Cloning successfully started!\nNew VM ID: {new_id}, Name: {new_name}',
             'clone_error': '❌ Cloning error: {error}',
             'host_label_default': 'Proxmox VE Host',
             'auth_logs_host_title': '🔒 <b>Authorization logs for Host {node_name}:</b>\n\n',
             'auth_logs_lxc_title': '🔒 <b>Authorization logs for LXC {vmid} ({name}):</b>\n\n',
             'auth_logs_vps_title': '🔒 <b>Authorization logs for VPS ({server_ip}):</b>\n\n',
             'logs_empty': '<i>History is empty or the bot was recently restarted. Logs will appear upon new login '
                           'attempts.</i>',
             'logs_truncated': '\n\n<i>... [Part of logs truncated due to Telegram size limits] ...</i>',
             'log_actual': 'Log is up to date',
             'log_error': 'Error retrieving logs: {err_msg}',
             'log_vps_error': 'Error retrieving VPS logs: {err_msg}',
             'traffic_host_title': '🌐 <b>Network activity for Host {node_name}:</b>\n',
             'traffic_lxc_title': '🌐 <b>Network activity for LXC {vmid} ({name}):</b>\n',
             'traffic_subtitle': '<i>(Recent connections and their threat level)</i>\n\n',
             'traffic_empty': '<i>No connections recorded. Network activity will appear when new traffic passes.</i>',
             'traffic_direction_in_label': 'Inbound connection',
             'traffic_direction_out_label': 'Outbound connection',
             'traffic_truncated': '\n\n<i>... [Part of activity truncated due to Telegram size limits] ...</i>',
             'traffic_actual': 'Activity is up to date',
             'traffic_error': 'Error retrieving network activity: {err_msg}'},
 'resources': {'vps_cpu_alert': '# ⚠️ CPU High Load\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [VPS Monitor] High CPU load (more than 5 minutes)!\n'
                                '\n'
                                '| Parameter | Value |\n'
                                '| :--- | :--- |\n'
                                '| **🌐 VPS IP** | `{ip}` |\n'
                                '| **🔴 CPU load** | **{cpu:.1f}%** (Threshold: {threshold}%) |\n',
               'vps_ram_alert': '# ⚠️ RAM High Usage\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [VPS Monitor] High RAM usage (more than 5 minutes)!\n'
                                '\n'
                                '| Parameter | Value |\n'
                                '| :--- | :--- |\n'
                                '| **🌐 VPS IP** | `{ip}` |\n'
                                '| **🔴 RAM load** | **{ram_pct:.1f}%** (Threshold: {threshold}%) |\n',
               'vps_disk_alert': '# ⚠️ Disk Full Alert\n'
                                 '---\n'
                                 '\n'
                                 '### ⚠️ [VPS Monitor] VPS Disk space running low!\n'
                                 '\n'
                                 '| Parameter | Value |\n'
                                 '| :--- | :--- |\n'
                                 '| **🌐 VPS IP** | `{ip}` |\n'
                                 '| **🔴 Disk usage** | **{disk_pct:.1f}%** (Threshold: {threshold}%) |\n',
               'lxc_state_alert': '# {emoji} VM Status Alert\n'
                                  '---\n'
                                  '\n'
                                  '### {emoji} LXC Container status changed!\n'
                                  '\n'
                                  '| Parameter | Value |\n'
                                  '| :--- | :--- |\n'
                                  '| **📦 ID** | `{vmid}` |\n'
                                  '| **🏷 Name** | `{name}` |\n'
                                  '| **⚡️ Server** | `{node_name}` |\n'
                                  '| **ℹ️ Status** | **{status_text}** |\n',
               'lxc_cpu_alert': '# ⚠️ CPU Load Alert\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [LXC Monitor] High CPU load (more than 5 minutes)!\n'
                                '\n'
                                '| Parameter | Value |\n'
                                '| :--- | :--- |\n'
                                '| **📦 LXC Container** | {vmid} (`{name}`) |\n'
                                '| **🔴 CPU load** | **{cpu:.1f}%** (Threshold: {threshold}%) |\n',
               'lxc_ram_alert': '# ⚠️ RAM Load Alert\n'
                                '---\n'
                                '\n'
                                '### ⚠️ [LXC Monitor] High RAM usage (more than 5 minutes)!\n'
                                '\n'
                                '| Parameter | Value |\n'
                                '| :--- | :--- |\n'
                                '| **📦 LXC Container** | {vmid} (`{name}`) |\n'
                                '| **🔴 RAM usage** | **{mem_pct:.1f}%** ({mem:.1f} / {maxmem:.1f} GB) (Threshold: '
                                '{threshold}%) |\n',
               'lxc_disk_alert': '# ⚠️ Disk Full Alert\n'
                                 '---\n'
                                 '\n'
                                 '### ⚠️ [LXC Monitor] LXC Disk space running low!\n'
                                 '\n'
                                 '| Parameter | Value |\n'
                                 '| :--- | :--- |\n'
                                 '| **📦 LXC Container** | {vmid} (`{name}`) |\n'
                                 '| **🔴 Disk usage** | **{disk_pct:.1f}%** ({disk:.1f} / {maxdisk:.1f} GB) (Threshold: '
                                 '{threshold}%) |\n'}}
