translation = {
    "new_ip_alert": (
        "# 🚨 New IP Connection\n"
        "---\n\n"
        "### 🚨 [{protocol} Security] Connection detected from a new IP!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **📦 Panel** | `{panel_name}` |\n"
        "| **👤 User** | `{username}` |\n"
        "| **🌐 New IP** | `{client_ip}` ⚠️ [WARNING] |\n"
        "{geo_row}\n"
        "<details>\n"
        "  <summary>📋 <b>Previous connections</b></summary>\n"
        "  <pre><code>{history_text}</code></pre>\n"
        "</details>"
    ),
    "session_activity_card": (
        "# 📊 Session Activity\n"
        "---\n\n"
        "### 📊 [{protocol}] Session activity on {panel_name}\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **👤 User** | `{username}` |\n"
        "| **📥 Downloaded** | `{download}` |\n"
        "| **📤 Uploaded** | `{upload}` |\n\n"
        "<details>\n"
        "  <summary>📋 <b>Event timeline</b></summary>\n"
        "  <pre><code>{timeline}</code></pre>\n"
        "</details>"
    ),
    "client_disconnected_alert": (
        "# 🔴 Client Disconnected\n"
        "---\n\n"
        "### 🔴 [{protocol}] Client disconnected from {panel_name}\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **👤 User** | `{username}` |\n"
        "| **🌐 IP Address** | `{client_ip}` |\n"
        "{geo_row}"
    ),
    "ips_autoblock_alert_audit": (
        "# 🛑 Account Auto-Blocked\n"
        "---\n\n"
        "### 🛑 [IPS: Auto-Block on {panel_name}]\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **👤 User** | `{email}` |\n"
        "| **📝 Reason** | **{details}** |\n"
    ),
    "login_success_alert": (
        "# 🔑 Web GUI Access\n"
        "---\n\n"
        "### 🟢 Login successful on {panel_name}\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **👤 Login** | `{username}` |\n"
        "| **🌐 IP Address** | `{ip}` |\n"
        "{geo_row}"
        "| **ℹ️ Details** | **{details}** |\n"
    ),
    "spectre_2fa_alert": (
        "# 🔑 Spectre 2FA Prompt\n"
        "---\n\n"
        "### 🔑 [Spectre 2FA: Login Attempt]\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🖥 Panel** | **{panel_name}** |\n"
        "| **👤 User** | `{username}` |\n"
        "| **🌐 IP Address** | `{client_ip}` |\n"
        "{geo_row}"
    ),
    "panel_status_message": (
        "# 📊 Server Status: {panel_name}\n"
        "---\n\n"
        "### 📊 Current Server Status\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🖥️ CPU** | `[{cpu_bar}] {cpu:.1f}%` |\n"
        "| **💾 RAM** | `[{mem_bar}] {mem_curr:.2f} / {mem_tot:.2f} GB` |\n"
        "| **⏱️ Uptime** | `{uptime_str}` |\n"
        "| **🖧 Inbounds** | `{total_inbounds}` |\n"
        "| **👥 Clients** | `{total_clients}` |\n"
        "| **🟢 Active** | `{active_clients}` |\n"
        "| **🔵 Online** | `{online_clients}` |\n"
        "| **🔴 Blocked** | `{blocked_clients}` |\n"
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
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🖥️ Panel** | `{panel_name}` |\n"
        "| **🚦 Downloaded (DL)** | `{down_gb:.3f} GB` |\n"
        "| **📤 Uploaded (UL)** | `{up_gb:.3f} GB` |\n"
        "| **💾 Traffic Limit** | `{total_gb_str}` |\n"
        "| **⏱️ Expires** | `{exp_str}` |\n"
        "| **⚡ Status** | **{status_str}** |\n"
    ),
    "btn_conn_history": "📊 Connection History & IP",

    # Action results
    "act_banned_success": "Successfully blocked",
    "act_unbanned_success": "Successfully unblocked",
    "act_panel_error": "Panel-side error",
    "act_success_alert": "✅ {success_msg}!",
    "act_failed_alert": "❌ Error: {desc}"
}
