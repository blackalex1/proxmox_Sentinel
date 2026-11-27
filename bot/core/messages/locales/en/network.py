# Locale bundle: network (en)

translations = {'proxy': {'proxy_switch_alert': '# ⚠️ Proxy Switch Alert\n'
                                 '---\n'
                                 '\n'
                                 '### ⚠️ [Proxy Monitor] Primary proxy is not responding!\n'
                                 '\n'
                                 '🔄 Bot has automatically switched to backup connection channel.\n'
                                 '\n'
                                 '| Parameter | Value |\n'
                                 '| :--- | :--- |\n'
                                 '| **❌ Primary Proxy** | `{primary_proxy}` |\n'
                                 '| **🔄 Backup Channel** | `{new_proxy}` |\n'
                                 '| **🛡 Failover Tier** | {tier_info} |\n',
           'proxy_restored_alert': '# ✅ Proxy Restored\n'
                                   '---\n'
                                   '\n'
                                   '### ✅ [Proxy Monitor] Primary proxy is back online!\n'
                                   '\n'
                                   '🔄 Successfully reverted to primary connection.\n'
                                   '\n'
                                   '| Parameter | Value |\n'
                                   '| :--- | :--- |\n'
                                   '| **🔌 Connection** | `{primary_proxy}` |\n'
                                   '| **ℹ️ Status** | 🟢 Online (Primary Proxy) |\n'},
 'router': {'router_recovery_alert': '# 🚨 Security Recovery\n'
                                     '---\n'
                                     '\n'
                                     '### 🚨 CRITICAL THREAT: Access restored for trusted node!\n'
                                     '\n'
                                     "The bot detected that a trusted IP address (Proxmox VE host or administrator's "
                                     'phone) was blocked on the router! The block was **automatically lifted** by the '
                                     'bot.\n'
                                     '\n'
                                     '🌐 **Trusted IP:** `{ip}`\n'
                                     '\n'
                                     '<details>\n'
                                     '  <summary>📋 <b>Show found and removed rules</b></summary>\n'
                                     '  <pre><code>{rules_str}</code></pre>\n'
                                     '</details>',
            'router_unknown_block_alert': '# ⚠️ Router Reconciliation\n'
                                          '---\n'
                                          '\n'
                                          '### ⚠️ Unknown block detected on the router!\n'
                                          '\n'
                                          "The bot detected blocking rules for IPs that are not in the bot's temporary "
                                          'bans database. For security and synchronization purposes, the block was '
                                          'automatically lifted.\n'
                                          '\n'
                                          '🌐 **IP Address:** `{ip}`\n'
                                          '\n'
                                          '<details>\n'
                                          '  <summary>📋 <b>Show found and removed rules</b></summary>\n'
                                          '  <pre><code>{rules_str}</code></pre>\n'
                                          '</details>',
            'router_autoblock_alert': '# 🛑 Router Auto-Block\n'
                                      '---\n'
                                      '\n'
                                      '### 🛑 [Router Security] Device automatically blocked!\n'
                                      '\n'
                                      '| Parameter | Value |\n'
                                      '| :--- | :--- |\n'
                                      '| **🎯 Reason** | Violation limit reached ({threshold}+ attempts in 10 min) |\n'
                                      '| **👤 Blocked IP** | `{src_ip}` |\n'
                                      '| **🧭 Last Target** | `{dst_host}:{dst_port}` (`{proto}`) |\n'
                                      '\n'
                                      '*Sentinel Security Guard • Time: {timestamp}*',
            'router_port_alert': '# 🚨 Router {type_str} Alert\n'
                                 '---\n'
                                 '\n'
                                 '### 🚨 [Router Security: {type_str}] Access to sensitive port!\n'
                                 '\n'
                                 '| Parameter | Value |\n'
                                 '| :--- | :--- |\n'
                                 '| **🔌 Protocol** | `{proto}` |\n'
                                 '| **👤 Source** | `{src_ip}:{src_port}` |\n'
                                 '| **🎯 Target** | `{dst_host}:{dst_port}` |\n'
                                 '\n'
                                 '*Sentinel Security Guard • Time: {timestamp}*',
            'btn_unblock_ip_router': '🟢 Unblock IP on router',
            'btn_block_ip_router': '🛑 Block IP on router',
            'btn_allow_port_alert': '🟢 Allow {port}',
            'btn_allow_all_alert': '🌐 Allow All Ports',
            'btn_ban_all_full': '🛑 Block Completely',
            'btn_unban_all_full': '🟢 Unblock Completely',
            'btn_ban_port_menu': '🔒 Block Port/Service',
            'btn_allow_port_menu': '🟢 Allow Port/Service',
            'btn_allow_all_ports': '🌐 Allow All Ports (Trusted)',
            'btn_manage_bans': '🔎 Manage Restrictions ({count})',
            'btn_manage_rules': '🔎 Manage Rules ({count})',
            'btn_back_to_clients': '🔙 Back to Clients List',
            'btn_web_service': '🌐 Web Browser (80, 443)',
            'btn_ssh_service': '💻 SSH Console (22)',
            'btn_dns_service': '👥 DNS Queries (53)',
            'btn_db_service': '🗄 Databases (3306, 5432)',
            'btn_proxmox_rdp_service': '🖥 Proxmox / RDP (8006, 3389)',
            'btn_custom_port': '✏️ Enter Port Manually...',
            'btn_unban_port_action': '❌ Remove block {port}/{proto}',
            'btn_disallow_port_action': '❌ Revoke {port}/{proto}',
            'btn_unban_all_action': '🟢 Remove full block',
            'dur_1_hour': '1 hour',
            'dur_1_day': '1 day',
            'dur_1_week': '1 week',
            'dur_forever': 'Forever',
            'prompt_ban_all_duration': '⌛️ <b>Select full block duration for device {ip}:</b>',
            'prompt_ban_port_service': '🔒 <b>Select port or service to block on device {ip}:</b>',
            'prompt_ban_port_duration': '⌛️ <b>Select block duration for ports {port}/{proto} on device {ip}:</b>',
            'prompt_custom_port_input': '✏️ <b>Port restriction for device {ip}</b>\n'
                                        '\n'
                                        'Enter port number or port/protocol (e.g. <code>80</code>, '
                                        '<code>53/udp</code>, <code>8080/tcp</code>):',
            'prompt_allow_port_service': '🟢 <b>Allow Ports for Device {ip}</b>\n'
                                         '\n'
                                         'Select a service or port to permanently whitelist (traffic will not be '
                                         'blocked or trigger alerts):',
            'prompt_custom_allow_port_input': '🟢 <b>Allow Port for Device {ip}</b>\n'
                                              '\n'
                                              'Enter port number (1-65535) or port/proto (e.g. <code>8080</code>, '
                                              '<code>8080/tcp</code>, <code>53/udp</code> or <code>0</code> for all '
                                              'ports):',
            'active_bans_header': '🔎 <b>Active rules for device {ip}:</b>\n\n',
            'active_ban_ip_item': ' • <b>Full IP Block</b> (Expires: {expire})\n',
            'active_ban_port_item': ' • <b>Port {port}/{proto}</b> (Expires: {expire})\n',
            'active_bans_empty': 'No active rules for this device.',
            'err_session_lost': '❌ Error: session lost. Please restart with /router',
            'err_invalid_proto': '❌ Invalid protocol. Specify tcp or udp (e.g. 80/tcp or 53/udp)',
            'err_invalid_port': '❌ Port must be a number between 1 and 65535 (or 0 for all ports).',
            'action_applying_ssh': 'Applying block via SSH...',
            'action_unbanning_ssh': 'Removing block via SSH...',
            'action_unbanning_port_ssh': 'Removing port {port}/{proto} block via SSH...',
            'action_banning_port_ssh': 'Adding port block rules via SSH...',
            'action_allowing_port_ssh': 'Adding port allow rules via SSH...',
            'action_disallowing_port_ssh': 'Removing port allow rules via SSH...',
            'port_blocked_success': 'Port {port}/{proto} successfully blocked!',
            'port_unblocked_success': 'Port {port}/{proto} block removed!',
            'port_allowed_success': '🟢 Port {port}/{proto} allowed for {ip}!',
            'port_disallowed_success': 'Permission for port {port}/{proto} revoked!',
            'ip_blocked_successfully': '🛑 IP {ip} successfully blocked on router!',
            'ip_block_failed': '❌ Block error: {desc}',
            'ip_block_error': 'Error during block: {e}',
            'ip_unblocked_successfully': '🟢 Block from IP {ip} successfully removed!',
            'ip_unblock_failed': '❌ Unblock error: {desc}',
            'ip_unblock_error': 'Error during unblock: {e}',
            'device_blocked_text': '\n\n🛑 <b>DEVICE {ip} BLOCKED ON ROUTER!</b>',
            'invalid_data_format': 'Error: invalid data format.',
            'clients_list_empty': '⚠️ No devices found or router monitoring is disabled in configuration.',
            'clients_list_header': '🖥 <b>Router connected devices:</b>\n'
                                   'Select a device below to manage network restrictions and allowed ports.\n',
            'client_details_title': '🖥 Router Client Management',
            'col_device_name': 'Device Name',
            'col_ip': 'IP Address',
            'col_mac': 'MAC Address',
            'col_net_status': 'Network Status',
            'col_ban_status': 'Restriction Status',
            'col_allowed_ports': 'Allowed Ports',
            'allowed_ports_all': '🌐 All Ports (Trusted)',
            'allowed_ports_none': 'Default',
            'status_active': '🟢 Active',
            'status_offline': '⚪ Offline',
            'ban_status_full': '🛑 Fully Blocked',
            'ban_status_ports': '🔒 Port Restrictions Active',
            'ban_status_none': '🟢 Access Allowed',
            'client_active_rules_footer': '🔒 Active rules count: <b>{count}</b>'},
 'whitelist': {'whitelist_view_title': '📁 Whitelist: {node_label}',
               'whitelist_empty': '<tr><td colspan="2" style="padding: 8px; color: #a6adc8; text-align: center;"><i>No '
                                  'rules in the whitelist for this node. All connections are filtered by standard IPS '
                                  'rules.</i></td></tr>',
               'whitelist_type_header': 'Rule Type',
               'whitelist_value_header': 'Value',
               'whitelist_rule_ip_port': '🌐 IP / Port',
               'whitelist_rule_process': '⚙️ Process',
               'whitelist_view_all_title': '📋 All Sentinel IPS Whitelist Rules',
               'whitelist_view_all_empty': '<tr><td colspan="2" style="padding: 8px; color: #bf616a; text-align: '
                                           'center;">❌ No rules configured for any node.</td></tr>',
               'global_node': '🌍 Globally (Everywhere)',
               'router_node': '🔌 Router',
               'pve_node': '🖥️ Proxmox Host',
               'lxc_node': '📦 LXC {vmid} ({name})',
               'vps_node': '🌐 VPS {ip}',
               'offline_label': '{label} (offline)',
               'btn_show_all': '📋 Show All Rules',
               'btn_back_to_nodes': '🔙 Back to Nodes Selection',
               'btn_add_ip_port': '➕ Add IP/Port',
               'btn_add_proc': '➕ Add Process',
               'btn_delete_rule': '🗑️ Delete Rule',
               'btn_back_to_nodes_list': '🔙 Back to Nodes List',
               'btn_cancel': '❌ Cancel',
               'btn_del_ip': '🗑️ IP: {item}',
               'btn_del_proc': '🗑️ Proc: {item}',
               'btn_back_to_view': '🔙 Back to View',
               'manage_title': '⚙️ <b>Sentinel IPS Whitelists Management</b>\n'
                               '\n'
                               'Select a node to view and configure security rules:',
               'add_ip_port_title': '➕ <b>Add IP/Port to Whitelist</b>\n'
                                    'Node: {node_label}\n'
                                    '\n'
                                    'Send a message containing the IP address or IP:Port combination (for example: '
                                    '<code>1.2.3.4</code>, <code>1.2.3.4:22</code>, or <code>1.2.3.4:*</code> for any '
                                    'port):',
               'invalid_input': 'Invalid input. Please try again or press Cancel.',
               'invalid_ip_port_format': '❌ Invalid IP/Port format. Examples: <code>192.168.1.100</code>, '
                                         '<code>192.168.1.100:22</code>, or <code>192.168.1.100:*</code>.',
               'rule_added_success': '🟢 <b>Rule successfully added!</b>\n'
                                     '\n'
                                     '📁 <b>Whitelist for node: {node_label}</b>\n'
                                     '━━━━━━━━━━━━━━━━━━━━━━━━\n',
               'allowed_ip_ports': '<b>Allowed IPs / IP:Ports:</b>\n',
               'allowed_processes': '<b>Allowed Processes:</b>\n',
               'add_proc_title': '➕ <b>Add Process to Whitelist</b>\n'
                                 'Node: {node_label}\n'
                                 '\n'
                                 'Send a message containing the process name (for example: <code>caddy</code>, '
                                 '<code>nginx</code>, or <code>sshd</code>):',
               'invalid_proc_name': '❌ Invalid process name (only alphanumeric characters are allowed). Please try '
                                    'again.',
               'proc_added_success': '🟢 <b>Process successfully added!</b>\n'
                                     '\n'
                                     '📁 <b>Whitelist for node: {node_label}</b>\n'
                                     '━━━━━━━━━━━━━━━━━━━━━━━━\n',
               'empty_whitelist_err': '❌ Whitelist of this node is empty. Nothing to delete.',
               'del_rule_title': '🗑️ <b>Deleting Whitelist Rules</b>\n'
                                 'Node: {node_label}\n'
                                 '\n'
                                 'Select the rule you want to delete:',
               'del_success_alert': '🟢 Successfully deleted: {item}',
               'cli_add_help': '❌ Usage: <code>/whitelist_add &lt;IP or IP:Port&gt; [node]</code>\n'
                               'Example: <code>/whitelist_add 1.2.3.4:22 router</code>',
               'cli_invalid_ip_port': '❌ Invalid IP/Port format.',
               'cli_added_ip_port': '🟢 Added <code>{val}</code> to the whitelist of node <b>{label}</b>.',
               'cli_rule_exists': 'ℹ️ Rule <code>{val}</code> already exists for node <b>{label}</b>.',
               'cli_proc_help': '❌ Usage: <code>/whitelist_process &lt;process name&gt; [node]</code>\n'
                                'Example: <code>/whitelist_process openvpn global</code>',
               'cli_invalid_proc': '❌ Invalid process name.',
               'cli_added_proc': '🟢 Added process <code>{val}</code> to the whitelist of node <b>{label}</b>.',
               'cli_proc_exists': 'ℹ️ Process <code>{val}</code> already exists in the whitelist of node '
                                  '<b>{label}</b>.',
               'qwl_invalid_callback': '❌ Invalid callback data format.',
               'qwl_added_success': '🟢 Successfully added to whitelist {label}: {val}',
               'qwl_added_msg': '\n\n✅ <b>Added to whitelist ({label}):</b> <code>{val}</code>',
               'qwl_already_whitelisted': 'ℹ️ Already exists in the whitelist of {label}.',
               'qwl_save_error': '❌ An error occurred during saving.'}}
