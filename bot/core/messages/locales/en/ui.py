# Locale bundle: ui (en)

translations = {'history': {'title_main': '📋 <b>VPN Connection History</b>',
             'empty_history': '❌ <i>Connection history is empty. Events will appear after the first client '
                              'connections.</i>',
             'user_btn_label': '👤 {username} ({total_sessions} sess.)',
             'select_user_desc': 'Select a user to view detailed session history:',
             'btn_back_to_select': '🔙 To User Selection',
             'user_title': '👤 <b>User {username}</b>',
             'empty_user_history': '❌ <i>Session history for this user is empty.</i>',
             'used_ips_header': '🌐 <b>Used IP Addresses:</b>',
             'used_ips_line': '   {char} <code>{ip}</code> ({count} sess.)',
             'session_history_title': '📋 <b>Session History: {username}</b>',
             'label_user': '👤 <b>User:</b> <code>{username}</code>',
             'label_page': '📄 <b>Page:</b> <code>{page} / {total}</code>',
             'label_total_sessions': '📊 <b>Total Sessions:</b> <code>{total}</code>',
             'status_active': 'active',
             'ip_warning_new': ' ⚠️ <b>[NEW IP]</b>',
             'session_header': '<b>Session #{session_num}</b>',
             'session_ip': 'IP:',
             'session_login': 'In:',
             'session_logout': 'Out:',
             'session_traffic': 'Traffic:',
             'session_duration': 'Duration:',
             'btn_prev': '◀️ Back',
             'btn_start': '⏹️ Start',
             'btn_page_info': 'Page {current}/{total}',
             'btn_next': 'Next ▶️',
             'btn_end': '⏹️ End',
             'btn_clear_db': '🗑️ Reset History',
             'clear_confirm_desc': '⚠️ <b>Warning!</b> Are you sure you want to completely clear the entire VPN '
                                   'connection history? This action cannot be undone.',
             'btn_clear_confirm_yes': '✅ Yes, Clear',
             'btn_clear_confirm_no': '❌ Cancel',
             'clear_success': '✅ Connection history successfully cleared!'},
 'keyboards': {'btn_proxmox': '🖥️ Proxmox VE',
               'btn_spectre': '🛡️ Sentinel Panel',
               'btn_ansible': '🛠️ Ansible Playbooks',
               'btn_vpn_history': '📋 VPN Connection History',
               'btn_ban_center': '🛑 Ban Center',
               'btn_whitelist': '⚙️ Sentinel IPS Whitelists',
               'btn_router_clients': '🖥️ Router Clients',
               'btn_status': '📊 System Status',
               'btn_help': 'ℹ️ Help',
               'btn_back_to_menu': '🔙 Back to Main Menu',
               'btn_refresh_status': '🔄 Refresh Status',
               'status_loading': '⏳ <i>Gathering system status details...</i>',
               'reply_control_panel': '🛡️ Control Panel',
               'reply_system_status': '📊 System Status',
               'reply_help': 'ℹ️ Help',
               'main_menu_text': '<table bordered striped compact>\n'
                                 '  <tr>\n'
                                 '    <th colspan="2" align="center"><b>🛡️ Proxmox Sentinel • Control Panel</b></th>\n'
                                 '  </tr>\n'
                                 '  <tr>\n'
                                 '    <td align="left"><b>⚡ Security System</b></td>\n'
                                 '    <td align="left"><code>🟢 ACTIVE</code></td>\n'
                                 '  </tr>\n'
                                 '  <tr>\n'
                                 '    <td align="left"><b>🖥️ Proxmox Host</b></td>\n'
                                 '    <td align="left"><code>{pve_ip}</code></td>\n'
                                 '  </tr>\n'
                                 '  <tr>\n'
                                 '    <td align="left"><b>🌐 Remote VPS</b></td>\n'
                                 '    <td align="left"><code>{vps_ip}</code></td>\n'
                                 '  </tr>\n'
                                 '</table>\n'
                                 '\n'
                                 '<i>Select a section for monitoring and administration:</i>',
               'help_text': '<table bordered striped compact>\n'
                            '  <tr>\n'
                            '    <th colspan="2" align="center"><b>ℹ️ Proxmox Sentinel • Commands Help</b></th>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <th colspan="2" align="left"><b>🎛️ Core Controls</b></th>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/start</code></td>\n'
                            '    <td align="left">Interactive Control Panel</td>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/status</code></td>\n'
                            '    <td align="left">Audit & status of all hypervisor systems</td>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/id</code></td>\n'
                            '    <td align="left">Your Telegram ID and Chat ID</td>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <th colspan="2" align="left"><b>🛡️ Security & Sentinel IPS</b></th>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/threats</code></td>\n'
                            '    <td align="left">Security incident log and attacks</td>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/bans</code></td>\n'
                            '    <td align="left">Active temporary IP bans management</td>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/whitelist</code></td>\n'
                            '    <td align="left">Manage whitelists (IP, ports, processes)</td>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <th colspan="2" align="left"><b>🌐 Network & Monitoring</b></th>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/router</code></td>\n'
                            '    <td align="left">Connected router clients & activity</td>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/panel</code></td>\n'
                            '    <td align="left">Manage Sentinel Panel nodes</td>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/top</code></td>\n'
                            '    <td align="left">Active VPN sessions & traffic stats</td>\n'
                            '  </tr>\n'
                            '  <tr>\n'
                            '    <td align="left"><code>/backup</code></td>\n'
                            '    <td align="left">Create SQLite database backup</td>\n'
                            '  </tr>\n'
                            '</table>\n'
                            '\n'
                            '<details>\n'
                            '  <summary>⚡ <b>Quick Actions & Direct Syntax</b></summary>\n'
                            '  • <code>/whitelist_add &lt;IP[:Port]&gt; [node]</code> — quickly whitelist IP '
                            'address<br/>\n'
                            '  • <code>/whitelist_process &lt;process&gt; [node]</code> — quickly whitelist '
                            'process<br/>\n'
                            '  • <code>/unban_login_ip &lt;IP&gt;</code> — unban login IP address<br/>\n'
                            '  • <code>/audit</code> or <code>/logs</code> — system security audit logs\n'
                            '</details>\n'
                            '\n'
                            '<blockquote>🛡️ <b>Autonomous Protection:</b> The bot monitors SSH authentications (SSH '
                            'Auth Monitor) and network anomalies (Active IPS Engine) in real-time. Security alerts are '
                            'dispatched directly to this chat.</blockquote>',
               'welcome_message': '👋 <b>Welcome to the Proxmox Sentinel monitoring system!</b>\n'
                                  '<i>A persistent quick access panel for main commands is activated below.</i>',
               'id_message': '👤 <b>Your Telegram ID:</b> <code>{user_id}</code>\n'
                             '💬 <b>This Chat ID:</b> <code>{chat_id}</code>'}}
