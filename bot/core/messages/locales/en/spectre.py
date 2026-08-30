translation = {
    "new_ip_alert": (
        "🚨 <b>New IP Connection</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <b>[{protocol}] Connection detected from a new IP!</b>\n\n"
        "📦 <b>Panel:</b> <code>{panel_name}</code>\n"
        "👤 <b>User:</b> <code>{username}</code>\n"
        "🌐 <b>New IP:</b> <code>{client_ip}</code> ⚠️\n"
        "{geo_row}\n"
        "📋 <b>Previous connections:</b>\n"
        "<pre><code>{history_text}</code></pre>"
    ),
    "btn_approve_ip": "✅ Approve IP",
    "ip_approved_success_toast": "✅ IP {ip} successfully approved!",
    "ip_approve_failed": "❌ Failed to approve IP.",
    "select_audit_category": "📋 <b>Select log category for panel {name}:</b>",
    "audit_cat_all": "📂 All logs",
    "audit_cat_logins": "🔑 Logins",
    "audit_cat_clients": "👤 Client management",
    "audit_cat_inbounds": "🔌 Inbounds / Protocols",
    "audit_cat_security": "🛡️ Security / Bans",
    "audit_cat_settings": "⚙️ System settings",
    "btn_back_to_categories": "🔙 To categories",
    "session_activity_card": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>📊 [{protocol}] {panel_name}</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>👤 User</b></td>\n'
        '    <td align="left"><code>{username}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📥 Downloaded</b></td>\n'
        '    <td align="left"><b>{download}</b></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>📤 Uploaded</b></td>\n'
        '    <td align="left"><b>{upload}</b></td>\n'
        '  </tr>\n'
        '</table>\n\n'
        '<details>\n'
        '  <summary>📋 <b>Event timeline</b></summary>\n'
        '  <pre><code>{timeline}</code></pre>\n'
        '</details>'
    ),

    "client_disconnected_alert": (
        "🔴 <b>Client Disconnected</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔴 <b>[{protocol}] Client disconnected:</b> <code>{panel_name}</code>\n\n"
        "👤 <b>User:</b> <code>{username}</code>\n"
        "🌐 <b>IP Address:</b> <code>{client_ip}</code>\n"
        "{geo_row}"
    ),
    "ips_autoblock_alert_audit": (
        "🛑 <b>Account Auto-Blocked</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🛑 <b>[IPS] Auto-Block:</b> <code>{panel_name}</code>\n\n"
        "👤 <b>User:</b> <code>{email}</code>\n"
        "📝 <b>Reason:</b> <b>{details}</b>"
    ),
    "login_success_alert": (
        "🔑 <b>Web GUI Access</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 <b>Login successful:</b> <code>{panel_name}</code>\n\n"
        "👤 <b>Login:</b> <code>{username}</code>\n"
        "🌐 <b>IP Address:</b> <code>{ip}</code>\n"
        "{geo_row}"
        "ℹ️ <b>Details:</b> <code>{details}</code>"
    ),
    "spectre_2fa_alert": (
        "🔑 <b>Sentinel 2FA Prompt</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>Login Attempt:</b> <code>{panel_name}</code>\n\n"
        "👤 <b>User:</b> <code>{username}</code>\n"
        "🌐 <b>IP Address:</b> <code>{client_ip}</code>\n"
        "{geo_row}"
    ),
    "panel_status_message": (
        "📊 <b>Server Status: {panel_name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🖥️ <b>CPU:</b> <code>[{cpu_bar}] {cpu:.1f}%</code>\n"
        "💾 <b>RAM:</b> <code>[{mem_bar}] {mem_curr:.2f} / {mem_tot:.2f} GB</code>\n"
        "⏱️ <b>Uptime:</b> <code>{uptime_str}</code>\n"
        "🖧 <b>Inbounds:</b> <code>{total_inbounds}</code>\n"
        "👥 <b>Clients:</b> <code>{total_clients}</code> (🟢 {active_clients} / 🔵 {online_clients} / 🔴 {blocked_clients})\n"
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
    "panel_not_found_err": "❌ <b>Sentinel Panels not found.</b>\nMake sure the panels are running and reachable.",
    "open_panel_btn": "📱 Open {name}",
    "clients_list_btn": "👥 Clients List",
    "status_btn": "⚙️ Status",
    "add_slave_btn": "➕ Add Slave",
    "add_master_btn": "➕ Add Master",
    "add_master_node_btn": "➕ Add Master Node",
    "spectre_panel_title": "🛡️ <b>Sentinel Panel Control</b>\n\nServer: <code>{name}</code>",
    "select_panel_title": "🛡️ <b>Select Sentinel Panel to manage:</b>",
    "panel_not_found": "❌ Panel not found.",
    "open_webapp_btn": "📱 Open WebApp",
    "audit_logs_btn": "📋 Audit Logs",
    "backup_btn": "📥 Backup",
    "vps_logs_btn": "🔒 VPS Login Logs",
    "back_to_list_btn": "🔙 Back to List",
    "manage_panel_title": "🛡️ <b>Manage panel {name}</b>\n\nSelect action:",
    "generating_join_code": "⏳ <b>Generating join code for slave node on {name}...</b>",
    "add_slave_title": (
        "➕ <b>Add Slave Node for {name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 Join Code:\n<code>{join_code}</code>\n"
        "⏱ Expires: <b>{expiry_str}</b>\n\n"
        "💻 <b>Command to run on the slave server:</b>\n\n"
        "🐳 <b>Option A (in Docker container):</b>\n"
        "<code>docker compose exec -T sentinel-panel python register_node.py --master \"{master_url}\" --join-code \"{join_code}\"</code>\n\n"
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
        "2️⃣ Add or edit the <code>SENTINEL_PANELS</code> variable. This is a JSON list of panels:\n\n"
        "<code>SENTINEL_PANELS='[\n"
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
        "👤 <b>Client Profile: {email}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🖥️ <b>Panel:</b> <code>{panel_name}</code>\n"
        "🚦 <b>Downloaded (DL):</b> <code>{down_gb:.3f} GB</code>\n"
        "📤 <b>Uploaded (UL):</b> <code>{up_gb:.3f} GB</code>\n"
        "💾 <b>Limit:</b> <code>{total_gb_str}</code>\n"
        "⏱️ <b>Expires:</b> <code>{exp_str}</code>\n"
        "⚡ <b>Status:</b> {status_str}\n"
    ),
    "btn_conn_history": "📊 Connection History & IP",

    # Action results
    "act_banned_success": "Successfully blocked",
    "act_unbanned_success": "Successfully unblocked",
    "act_panel_error": "Panel-side error",
    "act_success_alert": "✅ {success_msg}!",
    "act_failed_alert": "❌ Error: {desc}",

    # System and Backup handler keys
    "no_panels_err": "❌ <b>Sentinel Panels not found.</b>",
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
    "unbanning_tunnel_progress": "⏳ <i>Unblocking tunnel across all connected nodes...</i>",
    "manual_unban_success_details": (
        "{original_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 <b>Tunnel successfully unblocked manually!</b>\n\n"
        "📋 <b>Details by node and panel:</b>\n"
        "{details}\n\n"
        "🕒 <i>Execution time:</i> <code>{timestamp}</code> • <i>Status:</i> 🟢 <b>Active</b>"
    ),
    "manual_unban_failed_details": (
        "{original_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <b>Tunnel unblocked with warnings:</b>\n\n"
        "📋 <b>Details by node and panel:</b>\n"
        "{details}\n\n"
        "🕒 <i>Execution time:</i> <code>{timestamp}</code>"
    ),
    "manual_unban_error": (
        "{original_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ <b>Error unblocking tunnel:</b>\n"
        "<code>{error}</code>"
    ),
    "ban_help": "🛑 <b>Block Client:</b>\nUse command: <code>/ban &lt;email&gt;</code>",
    "ban_progress": "⏳ <i>Blocking client <code>{email}</code> on all target panels...</i>",
    "ban_status_success": "🟢 Blocked",
    "ban_status_error": "🔴 Error",
    "ban_success_results": (
        "🛑 <b>Client <code>{email}</code> successfully blocked!</b>\n\n"
        "📋 <b>Details by panel:</b>\n"
        "{details}"
    ),
    "ban_failed_results": (
        "❌ <b>Failed to block client <code>{email}</code>:</b>\n\n"
        "📋 <b>Details by panel:</b>\n"
        "{details}"
    ),
    "ban_error": "❌ <b>Error occurred while blocking:</b> <code>{error}</code>",
    "unban_help": "🟢 <b>Unblock Client:</b>\nUse command: <code>/unban &lt;email&gt;</code>",
    "unban_progress": "⏳ <i>Unblocking client <code>{email}</code> on all available panels...</i>",
    "unban_status_success": "🟢 Unblocked",
    "unban_status_error": "🔴 Error",
    "unban_success_results": (
        "🟢 <b>Client <code>{email}</code> successfully unblocked!</b>\n\n"
        "📋 <b>Details by panel:</b>\n"
        "{details}"
    ),
    "unban_failed_results": (
        "❌ <b>Failed to unblock client <code>{email}</code>:</b>\n\n"
        "📋 <b>Details by panel:</b>\n"
        "{details}"
    ),
    "unban_error": "❌ <b>Error occurred while unblocking:</b> <code>{error}</code>",
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
    "timeline_connect": "🟢 [{timestamp}] Connected from {ip}",
    "timeline_disconnect": "🔴 [{timestamp}] Disconnected {ip} — {duration}",
    "duration_sec": "{val} sec",
    "duration_min_sec": "{min} min {sec} sec",
    "duration_hour_min": "{hour} h {min} min"
}

