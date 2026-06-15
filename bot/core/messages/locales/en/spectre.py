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
    "timeline_show_more": "*... show more ...*"
}
