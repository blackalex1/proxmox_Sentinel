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

