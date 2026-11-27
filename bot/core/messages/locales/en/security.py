# Locale bundle: security (en)

translations = {'auth': {'vps_ssh_login_alert': '# 🖥️ VPS SSH Security: {ip}\n'
                                 '---\n'
                                 '\n'
                                 '### 🟢 Successful SSH Login!\n'
                                 '\n'
                                 '| Parameter | Value |\n'
                                 '| :--- | :--- |\n'
                                 '| **👤 User** | `{username}` |\n'
                                 '| **🌐 IP Address** | `{client_ip}` |\n'
                                 '{geo_row}| **🔑 Method** | `{auth_method}`{key_info} |\n'
                                 '\n'
                                 '{security_aside}\n'
                                 '<details>\n'
                                 '  <summary>🔍 <b>Show Login Log</b></summary>\n'
                                 '  <pre><code>{raw_line}</code></pre>\n'
                                 '</details>',
          'pve_web_login_alert': '# 🖥 Web GUI Access\n'
                                 '---\n'
                                 '\n'
                                 '### 🟢 Successful Proxmox Web GUI Login!\n'
                                 '\n'
                                 '| Parameter | Value |\n'
                                 '| :--- | :--- |\n'
                                 '| **📦 Target** | {target_str} |\n'
                                 '| **👤 User** | `{user}` |\n'
                                 '| **🌐 IP Address** | `WEB_GUI` |\n'
                                 '\n'
                                 '<details>\n'
                                 '  <summary>🔍 <b>Show Login Log</b></summary>\n'
                                 '  <pre><code>{line}</code></pre>\n'
                                 '</details>',
          'pve_web_fail_alert': '# 🖥 Web GUI Alert\n'
                                '---\n'
                                '\n'
                                '### ❌ AUTHENTICATION FAILED in Proxmox Web GUI!\n'
                                '\n'
                                '| Parameter | Value |\n'
                                '| :--- | :--- |\n'
                                '| **📦 Target** | {target_str} |\n'
                                '| **👤 Login Attempt As** | `{user}` |\n'
                                '| **🌐 IP Address** | `{ip}` |\n'
                                '{geo_row}| **📝 Reason** | `{reason}` |\n'
                                '\n'
                                '<details>\n'
                                '  <summary>🔍 <b>Show Error Log</b></summary>\n'
                                '  <pre><code>{line}</code></pre>\n'
                                '</details>',
          'ssh_login_alert': '# {emoji_str} SSH Access Report\n'
                             '---\n'
                             '\n'
                             '### 🟢 {title_str}\n'
                             '\n'
                             '| Parameter | Value |\n'
                             '| :--- | :--- |\n'
                             '| **📦 Target** | {target_str} |\n'
                             '| **👤 User** | `{user}` |\n'
                             '| **🌐 IP Address** | `{ip}` |\n'
                             '{geo_row}| **🔑 Method** | `{method}` |\n'
                             '{key_row}\n'
                             '<details>\n'
                             '  <summary>🔍 <b>Show Login Log</b></summary>\n'
                             '  <pre><code>{line}</code></pre>\n'
                             '</details>',
          'ssh_fail_alert': '# {emoji_str} SSH Auth Alert\n'
                            '---\n'
                            '\n'
                            '### ❌ {title_str}\n'
                            '\n'
                            '| Parameter | Value |\n'
                            '| :--- | :--- |\n'
                            '| **📦 Target** | {target_str} |\n'
                            '| **👤 Attempted User** | `{user}` |\n'
                            '| **🌐 IP Address** | `{ip}` |\n'
                            '{geo_row}| **🔑 Method** | `{method_ru}` |\n'
                            '\n'
                            '<details>\n'
                            '  <summary>🔍 <b>Show Error Log</b></summary>\n'
                            '  <pre><code>{line}</code></pre>\n'
                            '</details>',
          'sudo_alert': '# {emoji_str} Privileged Execution\n'
                        '---\n'
                        '\n'
                        '### 💻 {title_str}\n'
                        '\n'
                        '| Parameter | Value |\n'
                        '| :--- | :--- |\n'
                        '| **📦 Target** | {target_str} |\n'
                        '| **👤 User** | `{user}` (as `{run_as}`) |\n'
                        '| **💻 Command** | `{command}` |\n'
                        '\n'
                        '<details>\n'
                        '  <summary>🔍 <b>Show Execution Log</b></summary>\n'
                        '  <pre><code>{line}</code></pre>\n'
                        '</details>',
          'ssh_close_alert': '# 🚪 SSH Session Close\n'
                             '---\n'
                             '\n'
                             '### 🚪 SSH session closed\n'
                             '\n'
                             '| Parameter | Value |\n'
                             '| :--- | :--- |\n'
                             '| **📦 Target** | {target_str} |\n'
                             '| **👤 User** | `{user}` |\n'
                             '{ip_row}\n'
                             '<details>\n'
                             '  <summary>🔍 <b>Show Close Log</b></summary>\n'
                             '  <pre><code>{line}</code></pre>\n'
                             '</details>'},
 'ban_center': {'ban_center_title': '🛑 Sentinel IPS Ban Center',
                'ban_center_empty': '<tr><td colspan="4" style="padding: 8px; color: #a6adc8; text-align: '
                                    'center;"><i>No active blocks in the system.<br/>All network activity is monitored '
                                    'by the Active IPS Engine.</i></td></tr>',
                'active_bans_header': '👤 Active Temporary IP Blocks',
                'banned_keys_header': '🔑 Banned SSH Keys',
                'banned_login_ips_header': '🛡 Failed Login Blocks',
                'banned_panel_clients_header': '🚫 Banned Panel Clients',
                'col_panel': 'Panel',
                'col_client': 'Client',
                'col_inbound': 'Inbound',
                'col_ip': 'IP Address',
                'col_node': 'Node',
                'col_reason': 'Reason',
                'col_expires': 'Expires',
                'col_user': 'User',
                'col_banned_at': 'Banned At',
                'reason_manual': 'Manual',
                'reason_2fa_blocked': '2FA Block (Login)',
                'remaining_hours': '{hours}h {minutes}m',
                'remaining_minutes': '{minutes}m {seconds}s',
                'remaining_unknown': 'Unknown',
                'btn_unban_ip': '🔓 Unblock {ip}',
                'btn_unban_key': '🔓 Restore key (...{fp})',
                'btn_unban_pclient': '🔓 Unban {email}',
                'load_err': '❌ Error loading Ban Center.',
                'open_err': '❌ Error opening Ban Center.',
                'invalid_callback_err': '❌ Error: Invalid callback format.',
                'unban_in_progress': '⏳ Removing block...',
                'vps_not_found_err': 'VPS with IP {ip} was not found in settings',
                'unban_success_alert': '🟢 Block on IP {ip} successfully removed!',
                'unban_failed_alert': '❌ Error removing block: {desc}',
                'key_not_found_err': '❌ Error: Key not found in DB or already restored.',
                'restore_key_in_progress': '⏳ Restoring key...',
                'invalid_lxc_id_err': 'Invalid LXC ID.',
                'restore_key_success_alert': '🟢 SSH key successfully restored!',
                'restore_key_failed_alert': '❌ Error restoring key: {desc}',
                'pclient_unban_in_progress': '⏳ Unbanning client {email}...',
                'pclient_unban_success_alert': '🟢 Client {email} successfully unbanned on panel {panel_name}!',
                'pclient_unban_failed_alert': '❌ Error unbanning client {email}: {desc}',
                'unban_login_ip_help': '🟢 <b>Unban Login IP:</b>\nUse command: <code>/unban_login_ip &lt;ip&gt;</code>',
                'unban_login_ip_in_progress': '⏳ Unbanning IP <code>{ip}</code> on all panels...',
                'unban_login_ip_success_item': '  • {name}: 🟢 Unbanned',
                'unban_login_ip_failed_item': '  • {name}: 🔴 Error ({error})',
                'unban_login_ip_success': '✅ <b>IP <code>{ip}</code> unban results:</b>\n{details}',
                'unban_login_ip_failed': '❌ <b>Failed to unban IP <code>{ip}</code>:</b>\n{details}'},
 'threats': {'title': '⚡ Sentinel IPS Security Incident Log',
             'empty': 'No security incidents recorded. System running normally.',
             'col_time': '📅 Time',
             'col_ip': '🌐 Attack IP',
             'col_user': '👤 User',
             'col_reaction': '⚡ Reaction'},
 'traffic': {'ips_investigation_success_alert': '# ✅ IPS Investigation Done\n'
                                                '---\n'
                                                '\n'
                                                '### ✅ [IPS: Investigation Complete] Violator found!\n'
                                                '\n'
                                                '| Parameter | Value |\n'
                                                '| :--- | :--- |\n'
                                                '| **👤 Violator** | `{xray_client}` (Blocked) |\n'
                                                '| **🔓 Transit Tunnel** | `{tunnel_email}` (Active) |\n'
                                                '| **🌐 Attack Route** | `{target_panel_name}` → `{tunnel_email}` → '
                                                '`{server_ip}` → `{dst_ip}:{dpt}` |\n'
                                                '\n'
                                                '✨ *All other tunnel users are back online!*\n'
                                                '\n'
                                                '<details>\n'
                                                '  <summary>📋 <b>Show global block details of the '
                                                'violator</b></summary>\n'
                                                '  <pre><code>{block_details_str}</code></pre>\n'
                                                '</details>\n'
                                                '\n'
                                                '<details>\n'
                                                '  <summary>📋 <b>Show status of the transit tunnel</b></summary>\n'
                                                '  <pre><code>{unblock_details_str}</code></pre>\n'
                                                '</details>\n'
                                                '\n'
                                                '*Sentinel Security Guard • Time: {timestamp}*',
             'ips_investigation_failed_alert': '# ⚠️ IPS Investigation Failed\n'
                                               '---\n'
                                               '\n'
                                               '### ⚠️ [IPS: Investigation Failed] Violator not detected!\n'
                                               '\n'
                                               '| Parameter | Value |\n'
                                               '| :--- | :--- |\n'
                                               '| **🚨 Tunnel Status** | `{tunnel_email}` (Left in ban) |\n'
                                               '| **🎯 Attack Target** | `{dst_ip}:{dpt}` |\n'
                                               '\n'
                                               '<details>\n'
                                               '  <summary>🔍 <b>Show gathered log fragments</b></summary>\n'
                                               '  <pre><code>{logs_text}</code></pre>\n'
                                               '</details>\n'
                                               '\n'
                                               '*Sentinel Security Guard • Time: {timestamp}*',
             'ips_sensitive_access_alert': '# 🚨 Traffic Security Alert\n'
                                           '---\n'
                                           '\n'
                                           '### 🚨 [VPS Traffic Security] Ingress access to sensitive port!\n'
                                           '\n'
                                           '| Parameter | Value |\n'
                                           '| :--- | :--- |\n'
                                           '| **🌐 VPS Server** | `{server_ip}` |\n'
                                           '| **🔌 Protocol** | `{proto}` |\n'
                                           '| **👤 Source** | `{src}:{spt}` |\n'
                                           '| **🎯 Target** | `{dst}:{dpt}` |\n'
                                           '\n'
                                           '*Sentinel Security Guard • Time: {timestamp}*',
             'ips_hysteria_attack_alert': '# 🚨 Traffic Attack Detected\n'
                                          '---\n'
                                          '\n'
                                          '### 🚨 [VPS Traffic IPS] Attack detected through Hysteria tunnel!\n'
                                          '\n'
                                          '| Parameter | Value |\n'
                                          '| :--- | :--- |\n'
                                          '| **🌐 VPS Server** | `{server_ip}` |\n'
                                          '| **🔥 Temporary Ban** | `{email}` |\n'
                                          '| **🔌 Protocol** | `{proto}` |\n'
                                          '| **👤 Source** | `{src}:{spt}` |\n'
                                          '| **🎯 Target** | `{dst}:{dpt}` |\n'
                                          '\n'
                                          '<details>\n'
                                          '  <summary>📋 <b>Show tunnel block status</b></summary>\n'
                                          '  <pre><code>{block_details_str}</code></pre>\n'
                                          '</details>\n'
                                          '\n'
                                          '*Sentinel Security Guard • Time: {timestamp}*',
             'ips_xray_attack_alert': '# 🚨 Traffic Attack Blocked\n'
                                      '---\n'
                                      '\n'
                                      '### 🚨 [VPS Traffic IPS] Network attack blocked!\n'
                                      '\n'
                                      '| Parameter | Value |\n'
                                      '| :--- | :--- |\n'
                                      '| **🌐 VPS Server** | `{server_ip}` |\n'
                                      '| **👤 Violator (Xray)** | `{email}`{inbound_display} |\n'
                                      '| **🔌 Protocol** | `{proto}` |\n'
                                      '| **👤 Source** | `{src}:{spt}`{proc_info} |\n'
                                      '| **🎯 Target** | `{dst}:{dpt}` |\n'
                                      '\n'
                                      '<details>\n'
                                      '  <summary>🚨 <b>Show auto-block status of the violator account</b></summary>\n'
                                      '  <pre><code>{block_details_str}</code></pre>\n'
                                      '</details>\n'
                                      '\n'
                                      '*Sentinel Security Guard • Time: {timestamp}*',
             'ips_whitelisted_alert': '# ℹ️ Connection Allowed\n'
                                      '---\n'
                                      '\n'
                                      '### ℹ️ [VPS Traffic] Connection allowed\n'
                                      '\n'
                                      '| Parameter | Value |\n'
                                      '| :--- | :--- |\n'
                                      '| **🌐 VPS Server** | `{server_ip}` |\n'
                                      '| **📁 Process** | `{proc_name}` |\n'
                                      '| **🔌 Protocol** | `{proto}` |\n'
                                      '| **👤 Source** | `{src}:{spt}` |\n'
                                      '| **🎯 Target** | `{dst}:{dpt}` |\n'
                                      '\n'
                                      '*Sentinel Security Guard • Time: {timestamp}*',
             'ips_process_killed_alert': '# 🚨 Traffic Attack Blocked\n'
                                         '---\n'
                                         '\n'
                                         '### 🚨 [VPS Traffic IPS] Network attack blocked!\n'
                                         '\n'
                                         '| Parameter | Value |\n'
                                         '| :--- | :--- |\n'
                                         '| **🌐 VPS Server** | `{server_ip}` |\n'
                                         '| **🔥 Action** | **Process terminated (kill -9)** |\n'
                                         '| **📁 Process** | `{proc_name}` (PID: `{killed_pid}`) |\n'
                                         '| **🔌 Protocol** | `{proto}` |\n'
                                         '| **👤 Source** | `{src}:{spt}` |\n'
                                         '| **🎯 Target** | `{dst}:{dpt}` |\n'
                                         '\n'
                                         '*Sentinel Security Guard • Time: {timestamp}*',
             'ips_process_warning_alert': '# ⚠️ Traffic Sensitive Alert\n'
                                          '---\n'
                                          '\n'
                                          '### ⚠️ [VPS Traffic Warning] Outgoing connection to sensitive port!\n'
                                          '\n'
                                          '| Parameter | Value |\n'
                                          '| :--- | :--- |\n'
                                          '| **🌐 VPS Server** | `{server_ip}` |\n'
                                          '| **🔌 Protocol** | `{proto}` |\n'
                                          '| **👤 Source** | `{src}:{spt}`{proc_info} |\n'
                                          '| **🎯 Target** | `{dst}:{dpt}` |\n'
                                          '\n'
                                          '*Sentinel Security Guard • Time: {timestamp}*',
             'local_traffic_alert': '# {clean_h1}\n'
                                    '---\n'
                                    '\n'
                                    '### {title}\n'
                                    '\n'
                                    '| Parameter | Value |\n'
                                    '| :--- | :--- |\n'
                                    '| **📦 Container** | {vmid} (`{container_name}`) |\n'
                                    '| **🏷️ Threat** | {label} |\n'
                                    '| **🔌 Protocol** | `{proto}` |\n'
                                    '| **🧭 Direction** | {direction_text} |\n'
                                    '| **👤 Source** | `{src}:{spt}` |\n'
                                    '| **🎯 Destination** | `{dst}:{dpt}` |\n'
                                    '{vpn_ip_row}{vpn_client_row}{vpn_inbound_row}\n'
                                    '\n'
                                    '{block_details_block}\n'
                                    '\n'
                                    '*Sentinel Security Guard • Time: {timestamp}*',
             'local_h1_allowed': 'ℹ️ Connection Allowed',
             'local_h1_blocked': '🚨 Attack Blocked',
             'local_h1_critical': '🚨 Critical Alert',
             'local_h1_warning': '⚠️ Warning Alert',
             'local_h1_default': '⚠️ Traffic Alert',
             'local_direction_in': 'INBOUND',
             'local_direction_out': 'OUTBOUND',
             'local_real_ip': '| **👤 Real IP** | `{real_client_ip}` |\n',
             'local_vpn_client': '| **👤 VPN Client** | `{xray_client_email}` |\n',
             'local_vpn_inbound': '| **🔌 VPN Inbound** | `{inbound_tag}` |\n',
             'local_block_status': '\n'
                                   '<details>\n'
                                   '  <summary>🚨 <b>Show auto-block status of the account</b></summary>\n'
                                   '  <pre><code>{block_details_str}</code></pre>\n'
                                   '</details>',
             'proc_info_tmpl': ' (Process: `{proc_name}`)'}}
