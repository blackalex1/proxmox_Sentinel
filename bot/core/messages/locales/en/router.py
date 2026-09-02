translation = {
    "router_recovery_alert": (
        "# 🚨 Security Recovery\n"
        "---\n\n"
        "### 🚨 CRITICAL THREAT: Access restored for trusted node!\n\n"
        "The bot detected that a trusted IP address (Proxmox VE host or administrator's phone) was blocked on the router! The block was **automatically lifted** by the bot.\n\n"
        "🌐 **Trusted IP:** `{ip}`\n\n"
        "<details>\n"
        "  <summary>📋 <b>Show found and removed rules</b></summary>\n"
        "  <pre><code>{rules_str}</code></pre>\n"
        "</details>"
    ),
    "router_unknown_block_alert": (
        "# ⚠️ Router Reconciliation\n"
        "---\n\n"
        "### ⚠️ Unknown block detected on the router!\n\n"
        "The bot detected blocking rules for IPs that are not in the bot's temporary bans database. For security and synchronization purposes, the block was automatically lifted.\n\n"
        "🌐 **IP Address:** `{ip}`\n\n"
        "<details>\n"
        "  <summary>📋 <b>Show found and removed rules</b></summary>\n"
        "  <pre><code>{rules_str}</code></pre>\n"
        "</details>"
    ),
    "router_autoblock_alert": (
        "# 🛑 Router Auto-Block\n"
        "---\n\n"
        "### 🛑 [Router Security] Device automatically blocked!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🎯 Reason** | Violation limit reached ({threshold}+ attempts in 10 min) |\n"
        "| **👤 Blocked IP** | `{src_ip}` |\n"
        "| **🧭 Last Target** | `{dst_host}:{dst_port}` (`{proto}`) |\n\n"
        "*Sentinel Security Guard • Time: {timestamp}*"
    ),
    "router_port_alert": (
        "# 🚨 Router {type_str} Alert\n"
        "---\n\n"
        "### 🚨 [Router Security: {type_str}] Access to sensitive port!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🔌 Protocol** | `{proto}` |\n"
        "| **👤 Source** | `{src_ip}:{src_port}` |\n"
        "| **🎯 Target** | `{dst_host}:{dst_port}` |\n\n"
        "*Sentinel Security Guard • Time: {timestamp}*"
    ),
    "btn_unblock_ip_router": "🟢 Unblock IP on router",
    "btn_block_ip_router": "🛑 Block IP on router",
    "btn_ban_all_full": "🛑 Block Completely",
    "btn_unban_all_full": "🟢 Unblock Completely",
    "btn_ban_port_menu": "🔒 Block Port/Service",
    "btn_manage_bans": "🔎 Manage Restrictions ({count})",
    "btn_back_to_clients": "🔙 Back to Clients List",
    "btn_web_service": "🌐 Web Browser (80, 443)",
    "btn_ssh_service": "💻 SSH Console (22)",
    "btn_dns_service": "👥 DNS Queries (53)",
    "btn_custom_port": "✏️ Enter Port Manually...",
    "btn_unban_port_action": "❌ Remove block {port}/{proto}",
    "btn_unban_all_action": "🟢 Remove full block",
    
    "dur_1_hour": "1 hour",
    "dur_1_day": "1 day",
    "dur_1_week": "1 week",
    "dur_forever": "Forever",
    
    "prompt_ban_all_duration": "⌛️ <b>Select full block duration for device {ip}:</b>",
    "prompt_ban_port_service": "🔒 <b>Select port or service to block on device {ip}:</b>",
    "prompt_ban_port_duration": "⌛️ <b>Select block duration for ports {port}/{proto} on device {ip}:</b>",
    "prompt_custom_port_input": (
        "✏️ <b>Port restriction for device {ip}</b>\n\n"
        "Enter port number or port/protocol (e.g. <code>80</code>, <code>53/udp</code>, <code>8080/tcp</code>):"
    ),
    "active_bans_header": "🔎 <b>Active restrictions for device {ip}:</b>\n\n",
    "active_ban_ip_item": " • <b>Full IP Block</b> (Expires: {expire})\n",
    "active_ban_port_item": " • <b>Port {port}/{proto}</b> (Expires: {expire})\n",
    "active_bans_empty": "No active restrictions for this device.",
    
    "err_session_lost": "❌ Error: session lost. Please restart with /router",
    "err_invalid_proto": "❌ Invalid protocol. Specify tcp or udp (e.g. 80/tcp or 53/udp)",
    "err_invalid_port": "❌ Port must be a number between 1 and 65535.",
    "action_applying_ssh": "Applying block via SSH...",
    "action_unbanning_ssh": "Removing block via SSH...",
    "action_unbanning_port_ssh": "Removing port {port}/{proto} block via SSH...",
    "action_banning_port_ssh": "Adding port block rules via SSH...",
    "port_blocked_success": "Port {port}/{proto} successfully blocked!",
    "port_unblocked_success": "Port {port}/{proto} block removed!",
    
    "ip_blocked_successfully": "🛑 IP {ip} successfully blocked on router!",
    "ip_block_failed": "❌ Block error: {desc}",
    "ip_block_error": "Error during block: {e}",
    "ip_unblocked_successfully": "🟢 Block from IP {ip} successfully removed!",
    "ip_unblock_failed": "❌ Unblock error: {desc}",
    "ip_unblock_error": "Error during unblock: {e}",
    "device_blocked_text": "\n\n🛑 <b>DEVICE {ip} BLOCKED ON ROUTER!</b>",
    "invalid_data_format": "Error: invalid data format.",
    
    # UI and Client Details
    "clients_list_empty": "⚠️ No devices found or router monitoring is disabled in configuration.",
    "clients_list_header": "🖥 <b>Router connected devices:</b>\nSelect a device below to manage network restrictions.\n",
    "client_details_title": "🖥 Router Client Management",
    "col_device_name": "Device Name",
    "col_ip": "IP Address",
    "col_mac": "MAC Address",
    "col_net_status": "Network Status",
    "col_ban_status": "Restriction Status",
    "status_active": "🟢 Active",
    "status_offline": "⚪ Offline",
    "ban_status_full": "🛑 Fully Blocked",
    "ban_status_ports": "🔒 Port Restrictions Active",
    "ban_status_none": "🟢 Access Allowed",
    "client_active_rules_footer": "🔒 Active restriction rules count: <b>{count}</b>",
}
