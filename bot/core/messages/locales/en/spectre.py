translation = {
    "new_ip_alert": (
        "# 🚨 New IP Connection\n"
        "---\n\n"
        "### 🚨 [{protocol} Security] Connection detected from a new IP!\n\n"
        '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
        '  <tr style="background-color: #1e1e2e; color: #ffffff;">\n'
        '    <th style="padding: 8px; text-align: left;"><b>Parameter</b></th>\n'
        '    <th style="padding: 8px; text-align: left;"><b>Value</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>📦 Panel</b></td>\n'
        '    <td style="padding: 8px;"><code>{panel_name}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>👤 User</b></td>\n'
        '    <td style="padding: 8px;"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🌐 New IP</b></td>\n'
        '    <td style="padding: 8px;"><code>{client_ip}</code> ⚠️ [WARNING]</td>\n'
        '  </tr>\n'
        '{geo_row}'
        '</table>\n\n'
        "<details>\n"
        "  <summary>📋 <b>Previous connections</b></summary>\n"
        "  <pre><code>{history_text}</code></pre>\n"
        "</details>"
    ),
    "session_activity_card": (
        "# 📊 Session Activity\n"
        "---\n\n"
        "### 📊 [{protocol}] Session activity on {panel_name}\n\n"
        '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
        '  <tr style="background-color: #1e1e2e; color: #ffffff;">\n'
        '    <th style="padding: 8px; text-align: left;"><b>Parameter</b></th>\n'
        '    <th style="padding: 8px; text-align: left;"><b>Value</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>👤 User</b></td>\n'
        '    <td style="padding: 8px;"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>📥 Downloaded</b></td>\n'
        '    <td style="padding: 8px;"><code>{download}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>📤 Uploaded</b></td>\n'
        '    <td style="padding: 8px;"><code>{upload}</code></td>\n'
        '  </tr>\n'
        '</table>\n\n'
        "<details>\n"
        "  <summary>📋 <b>Event timeline</b></summary>\n"
        "  <pre><code>{timeline}</code></pre>\n"
        "</details>"
    ),
    "client_disconnected_alert": (
        "# 🔴 Client Disconnected\n"
        "---\n\n"
        "### 🔴 [{protocol}] Client disconnected from {panel_name}\n\n"
        '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
        '  <tr style="background-color: #1e1e2e; color: #ffffff;">\n'
        '    <th style="padding: 8px; text-align: left;"><b>Parameter</b></th>\n'
        '    <th style="padding: 8px; text-align: left;"><b>Value</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>👤 User</b></td>\n'
        '    <td style="padding: 8px;"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🌐 IP Address</b></td>\n'
        '    <td style="padding: 8px;"><code>{client_ip}</code></td>\n'
        '  </tr>\n'
        '{geo_row}'
        '</table>'
    ),
    "ips_autoblock_alert_audit": (
        "# 🛑 Account Auto-Blocked\n"
        "---\n\n"
        "### 🛑 [IPS: Auto-Block on {panel_name}]\n\n"
        '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
        '  <tr style="background-color: #1e1e2e; color: #ffffff;">\n'
        '    <th style="padding: 8px; text-align: left;"><b>Parameter</b></th>\n'
        '    <th style="padding: 8px; text-align: left;"><b>Value</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>👤 User</b></td>\n'
        '    <td style="padding: 8px;"><code>{email}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>📝 Reason</b></td>\n'
        '    <td style="padding: 8px;"><b>{details}</b></td>\n'
        '  </tr>\n'
        '</table>'
    ),
    "login_success_alert": (
        "# 🔑 Web GUI Access\n"
        "---\n\n"
        "### 🟢 Login successful on {panel_name}\n\n"
        '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
        '  <tr style="background-color: #1e1e2e; color: #ffffff;">\n'
        '    <th style="padding: 8px; text-align: left;"><b>Parameter</b></th>\n'
        '    <th style="padding: 8px; text-align: left;"><b>Value</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>👤 Login</b></td>\n'
        '    <td style="padding: 8px;"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🌐 IP Address</b></td>\n'
        '    <td style="padding: 8px;"><code>{ip}</code></td>\n'
        '  </tr>\n'
        '{geo_row}'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>ℹ️ Details</b></td>\n'
        '    <td style="padding: 8px;"><b>{details}</b></td>\n'
        '  </tr>\n'
        '</table>'
    ),
    "spectre_2fa_alert": (
        "# 🔑 Spectre 2FA Prompt\n"
        "---\n\n"
        "### 🔑 [Spectre 2FA: Login Attempt]\n\n"
        '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
        '  <tr style="background-color: #1e1e2e; color: #ffffff;">\n'
        '    <th style="padding: 8px; text-align: left;"><b>Parameter</b></th>\n'
        '    <th style="padding: 8px; text-align: left;"><b>Value</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🖥 Panel</b></td>\n'
        '    <td style="padding: 8px;"><b>{panel_name}</b></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>👤 User</b></td>\n'
        '    <td style="padding: 8px;"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🌐 IP Address</b></td>\n'
        '    <td style="padding: 8px;"><code>{client_ip}</code></td>\n'
        '  </tr>\n'
        '{geo_row}'
        '</table>'
    ),
    "panel_status_message": (
        "# 📊 Server Status: {panel_name}\n"
        "---\n\n"
        "### 📊 Current Server Status\n\n"
        '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
        '  <tr style="background-color: #1e1e2e; color: #ffffff;">\n'
        '    <th style="padding: 8px; text-align: left;"><b>Parameter</b></th>\n'
        '    <th style="padding: 8px; text-align: left;"><b>Value</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🖥️ CPU</b></td>\n'
        '    <td style="padding: 8px;"><code>[{cpu_bar}] {cpu:.1f}%</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>💾 RAM</b></td>\n'
        '    <td style="padding: 8px;"><code>[{mem_bar}] {mem_curr:.2f} / {mem_tot:.2f} GB</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>⏱️ Uptime</b></td>\n'
        '    <td style="padding: 8px;"><code>{uptime_str}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🖧 Inbounds</b></td>\n'
        '    <td style="padding: 8px;"><code>{total_inbounds}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>👥 Clients</b></td>\n'
        '    <td style="padding: 8px;"><code>{total_clients}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🟢 Active</b></td>\n'
        '    <td style="padding: 8px;"><code>{active_clients}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🔵 Online</b></td>\n'
        '    <td style="padding: 8px;"><code>{online_clients}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🔴 Blocked</b></td>\n'
        '    <td style="padding: 8px;"><code>{blocked_clients}</code></td>\n'
        '  </tr>\n'
        '</table>\n'
    ),
    
    # Traffic table
    "top_traffic_title": "🏆 Top Traffic Consumers ({period_label})",
    "top_traffic_today": "Today",
    "top_traffic_month": "Month",
    "top_traffic_error": "❌ {panel_name}: {error_info}",
    "top_traffic_panel_header": "📌 Panel: {panel_name}",
    "top_traffic_rank": "#",
    "top_traffic_user": "User",
    "top_traffic_traffic": "Traffic",
    "top_traffic_no_activity": "No user activity",
    "top_traffic_no_data": "No user activity data on panels.",
    "top_traffic_footer": "\n<i>To switch use: <code>/top today</code> or <code>/top month</code></i>",
    
    # Misc strings
    "history_unknown": "unknown",
    "history_empty": "no previous connections",
    "uptime_format": "{days}d {hours}h {minutes}m",
    "timeline_show_more": "*... show more ...*",

    # Panel handler menu strings
    "panel_not_found_err": "❌ <b>Spectre Panels not found.</b>\nMake sure the panels are running and reachable.",
    "open_panel_btn": "📱 Open {name}",
    "clients_list_btn": "👥 Clients List",
    "status_btn": "⚙️ Status",
    "add_slave_btn": "➕ Add Slave",
    "add_master_btn": "➕ Add Master",
    "add_master_node_btn": "➕ Add Master Node",
    "spectre_panel_title": "🚀 <b>Spectre Panel Control</b>\n\nServer: <code>{name}</code>",
    "select_panel_title": "🚀 <b>Select Spectre Panel to manage:</b>",
    "panel_not_found": "❌ Panel not found.",
    "open_webapp_btn": "📱 Open WebApp",
    "audit_logs_btn": "📋 Audit Logs",
    "backup_btn": "📥 Backup",
    "vps_logs_btn": "🔒 VPS Login Logs",
    "back_to_list_btn": "🔙 Back to List",
    "manage_panel_title": "🚀 <b>Manage panel {name}</b>\n\nSelect action:",
    "generating_join_code": "⏳ <b>Generating join code for slave node on {name}...</b>",
    "add_slave_title": (
        "➕ <b>Add Slave Node for {name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 Join Code:\n<code>{join_code}</code>\n"
        "⏱ Expires: <b>{expiry_str}</b>\n\n"
        "💻 <b>Command to run on the slave server:</b>\n\n"
        "🐳 <b>Option A (in Docker container):</b>\n"
        "<code>docker compose exec -T spectre-panel python register_node.py --master \"{master_url}\" --join-code \"{join_code}\"</code>\n\n"
        "🐍 <b>Option B (locally on host via Virtualenv):</b>\n"
        "<code>.venv/bin/python register_node.py --master \"{master_url}\" --join-code \"{join_code}\"</code>\n\n"
        "<i>Run the appropriate command in the slave panel directory to register the public key.</i>"
    ),
    "back_btn": "🔙 Back",
    "generating_error": "❌ <b>Error generating join code for {name}:</b>\n<code>{error_info}</code>",
    "add_master_title": (
        "➕ <b>Add New Master Panel to Controller</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "To connect another Master panel to your Telegram bot:\n\n"
        "1️⃣ Open the controller's <code>.env</code> configuration file.\n"
        "2️⃣ Add or edit the <code>SPECTRE_PANELS</code> variable. This is a JSON list of panels:\n\n"
        "<code>SPECTRE_PANELS='[\n"
        "  {{\"name\": \"My Panel\", \"url\": \"https://ip:port\", \"token\": \"api_token_here\", \"secret_path\": \"secret\"}}\n"
        "]'</code>\n\n"
        "3️⃣ Restart the bot. It will automatically detect it and add it to the menu."
    ),

    # Setup slave node command
    "setup_slave_help": (
        "💻 <b>Setup server as a slave node:</b>\n"
        "Use format: <code>/setup_slave &lt;master_url&gt; &lt;join_code&gt;</code>\n\n"
        "<i>Example:</i>\n<code>/setup_slave https://master.com/secret JOIN-E5A73D1C</code>"
    ),
    "setup_slave_init": "⏳ <b>Initializing connection to Master server...</b>",
    "setup_slave_rejected": "❌ <b>Registration rejected by Master (code {status}):</b>\n<code>{error_info}</code>",
    "setup_slave_success": (
        "✅ <b>Server successfully configured as a slave node!</b>\n\n"
        "Node ID: <code>{node_id}</code>\n"
        "Config saved to: <code>{config_path}</code>\n"
        "🔗 Connection with Master established successfully."
    ),
    "setup_slave_error": "❌ <b>An error occurred while setting up the slave node:</b>\n<code>{error_info}</code>",

    # Admin actions and sessions
    "data_format_err": "Data format error",
    "panel_not_found_or_disabled": "Panel not found or disabled",
    "sessions_fetch_err": "Failed to retrieve sessions from panel",
    "sessions_terminated": "\n\n❌ <b>Sessions of user {username} from IP {ip} successfully terminated ({terminated} sess.).</b>",
    "sessions_terminated_alert": "Sessions successfully terminated",
    "no_active_sessions_err": "Active sessions not found on the panel",
    "error_alert": "Error: {error}",
    "reset_pwd_manual_unsupported": "Cannot reset password for panel configured manually (.env)",
    "reset_pwd_success": "\n\n🔑 <b>Password for user {username} successfully changed!</b>\nNew password: <tg-spoiler><code>{new_pwd}</code></tg-spoiler>",
    "reset_pwd_success_alert": "Password successfully changed",
    "reset_pwd_failed": "Failed to reset password: {error_info}",

    # Clients list and pagination
    "loading_clients": "⏳ Loading client list for <b>{name}</b>...",
    "load_clients_err": "❌ <b>Failed to load clients from panel {name}</b>",
    "clients_list_empty": "👥 <b>Client list on panel {name} is empty.</b>",
    "nav_back": "◀️ Back",
    "nav_start": "⏹️ Start",
    "nav_forward": "Forward ▶️",
    "nav_end": "⏹️ End",
    "back_to_menu_btn": "🔙 Back to Panel Menu",
    "clients_list_title": "👥 <b>Clients on panel {name}</b> (Total: {total_clients}):",

    # Client view/card
    "client_not_found_err": "❌ <b>Client {email} not found on panel.</b>",
    "no_limit": "No limit",
    "status_online": "🟢 Online",
    "status_offline": "⚪ Offline",
    "btn_ban_client": "🛑 Block",
    "btn_unban_client": "🟢 Unblock",
    "expiry_never": "Never",
    "blocked_by_admin": "Blocked by admin",
    "status_blocked": "🔴 Blocked ({reason})",
    "client_profile_card": (
        "# 👤 Client Profile: {email}\n"
        "---\n\n"
        "### 👤 VPN Client Profile\n\n"
        '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
        '  <tr style="background-color: #1e1e2e; color: #ffffff;">\n'
        '    <th style="padding: 8px; text-align: left;"><b>Parameter</b></th>\n'
        '    <th style="padding: 8px; text-align: left;"><b>Value</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🖥️ Panel</b></td>\n'
        '    <td style="padding: 8px;"><code>{panel_name}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>🚦 Downloaded (DL)</b></td>\n'
        '    <td style="padding: 8px;"><code>{down_gb:.3f} GB</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>📤 Uploaded (UL)</b></td>\n'
        '    <td style="padding: 8px;"><code>{up_gb:.3f} GB</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>💾 Traffic Limit</b></td>\n'
        '    <td style="padding: 8px;"><code>{total_gb_str}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>⏱️ Expires</b></td>\n'
        '    <td style="padding: 8px;"><code>{exp_str}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td style="padding: 8px;"><b>⚡ Status</b></td>\n'
        '    <td style="padding: 8px;"><b>{status_str}</b></td>\n'
        '  </tr>\n'
        '</table>\n'
    ),
    "btn_conn_history": "📊 Connection History & IP",

    # Action results
    "act_banned_success": "Successfully blocked",
    "act_unbanned_success": "Successfully unblocked",
    "act_panel_error": "Panel-side error",
    "act_success_alert": "✅ {success_msg}!",
    "act_failed_alert": "❌ Error: {desc}",

    # System and Backup handler keys
    "no_panels_err": "❌ <b>Spectre Panels not found.</b>",
    "select_panel_backup": "📥 <b>Select a panel to create backup:</b>",
    "backup_in_progress": "⏳ Creating database backup for <b>{name}</b>...",
    "backup_success": "✅ <b>Backup successfully created!</b>\nServer: <code>{name}</code>",
    "backup_send_err": "❌ Error sending backup file: {error}",
    "backup_failed": "❌ <b>Failed to create backup for {name}:</b>\n<code>{error}</code>",
    "unknown_error": "Unknown error",
    "select_panel_status": "📊 <b>Select a panel to check system status:</b>",
    "status_fetching": "⏳ Fetching system status from <b>{name}</b>...",
    "status_failed": "❌ <b>Failed to get status from {name}:</b>\n<code>{error}</code>",
    "traffic_stats_fetching": "📊 Fetching traffic statistics from all panels...",
    "select_panel_audit": "📋 <b>Select a panel to view audit logs:</b>",
    "audit_logs_fetching": "⏳ Fetching audit logs from <b>{name}</b>...",
    "audit_logs_empty": "📁 <b>{name}</b>: Audit log is empty.",
    "audit_logs_title": "📋 <b>Recent actions on panel: {name}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n",
    "audit_logs_failed": "❌ <b>Failed to get audit logs from {name}:</b>\n<code>{error}</code>",

    # Client search and actions keys
    "my_subscription_title": "🔑 <b>Client Subscription Lookup:</b>\nUse command: <code>/my &lt;email or UUID&gt;</code>",
    "lookup_in_progress": "🔍 Searching for client across all panels database...",
    "client_not_found_everywhere": "❌ <b>Client with this email or UUID was not found on any panel.</b>",
    "no_traffic_limit": "No limit",
    "limit_gb": "{limit:.2f} GB",
    "status_active": "🟢 Active",
    "reason_limit_exceeded": "Limits exceeded",
    "status_blocked_with_reason": "🔴 Blocked ({reason})",
    "expires_never": "Never",
    "client_card_sub_title": (
        "🔑 <b>Subscription: {email}</b>\n"
        "📡 Panel/Server: <b>{panel_name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 Inbound: <b>{remark} (:{port})</b>\n"
        "📡 Protocol: <b>{protocol}</b>\n"
        "🚦 Downloaded (DL): <b>{download_gb:.3f} GB</b>\n"
        "📤 Uploaded (UL): <b>{upload_gb:.3f} GB</b>\n"
        "💾 Traffic Limit: <b>{total_gb_str}</b>\n"
        "⏱ Expires: <b>{expiry_str}</b>\n"
        "⚡ Status: <b>{status_str}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 <b>Connection links:</b>\n"
    ),
    "copy_link_hint": "\n<i>Click on link to copy it.</i>",
    "btn_conn_history_and_ip": "📊 Connection History & IPs",
    "qr_code_caption": "QR Code {protocol} ({index})",
    "lookup_error": "❌ Search error occurred: {error}",
    "unbanning_tunnel_hint": "👇 You can unblock tunnel manually in one click:",
    "unbanning_tunnel_progress": "⏳ Unblocking tunnel...",
    "manual_unban_success_details": (
        "{original_text}\n\n✅ <b>Tunnel successfully unblocked manually!</b>\n"
        "📋 <b>Unblock Details:</b>\n{details}\n"
        "🕒 Time: <code>{timestamp}</code>"
    ),
    "manual_unban_failed_details": (
        "{original_text}\n\n⚠️ <b>Tunnel unblocked with errors:</b>\n"
        "📋 <b>Unblock Details:</b>\n{details}\n"
        "🕒 Time: <code>{timestamp}</code>"
    ),
    "manual_unban_error": "{original_text}\n\n❌ <b>Unblocking error:</b> <code>{error}</code>",
    "ban_help": "🛑 <b>Block Client:</b>\nUse command: <code>/ban &lt;email&gt;</code>",
    "ban_progress": "⏳ Blocking client <code>{email}</code> on all panels...",
    "ban_status_success": "🟢 Blocked",
    "ban_status_error": "🔴 Error",
    "ban_success_results": "✅ <b>Results of blocking client <code>{email}</code>:</b>\n{details}",
    "ban_failed_results": "❌ <b>Failed to block client <code>{email}</code>:</b>\n{details}",
    "ban_error": "❌ Error occurred while blocking: {error}",
    "unban_help": "🟢 <b>Unblock Client:</b>\nUse command: <code>/unban &lt;email&gt;</code>",
    "unban_progress": "⏳ Unblocking client <code>{email}</code> on all panels...",
    "unban_status_success": "🟢 Unblocked",
    "unban_status_error": "🔴 Error",
    "unban_success_results": "✅ <b>Results of unblocking client <code>{email}</code>:</b>\n{details}",
    "unban_failed_results": "❌ <b>Failed to unblock client <code>{email}</code>:</b>\n{details}",
    "unban_error": "❌ Error occurred while unblocking: {error}",
    "tg_2fa_approved": "✅ <b>Access successfully allowed.</b>",
    "tg_2fa_blocked": "🛑 <b>IP address blocked.</b>",
    "tg_2fa_error": "❌ Error: {error}",
    "tg_2fa_unblock_failed": "Failed to block on any panel",
    "tg_2fa_approve_failed": "Failed to approve on any panel",
    "tg_2fa_block_confirm_btn": "🔥 Yes, block IP",
    "tg_2fa_block_cancel_btn": "🔙 Cancel",
    "tg_2fa_block_confirm_text": "{original_text}\n\n⚠️ <b>Are you sure? Blocking your IP will restrict your access to the server!</b>",
    "tg_2fa_approve_btn": "✅ Yes, allow",
    "tg_2fa_block_btn": "❌ Block IP",
    "tg_2fa_block_cancelled_alert": "IP blocking cancelled",

    # Timeline and Duration strings
    "timeline_connect": "🟢 <code>[{timestamp}]</code> Connected from <code>{ip}</code>",
    "timeline_disconnect": "🔴 <code>[{timestamp}]</code> Disconnected <code>{ip}</code> — {duration}",
    "duration_sec": "{val} sec",
    "duration_min_sec": "{min} min {sec} sec",
    "duration_hour_min": "{hour} h {min} min"
}
