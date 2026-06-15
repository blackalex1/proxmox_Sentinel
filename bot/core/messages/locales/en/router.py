translation = {
    "router_recovery_alert": (
        "# 🚨 Security Recovery\n"
        "---\n\n"
        "### 🚨 CRITICAL THREAT: Access restored for trusted node!\n\n"
        "The bot detected that a trusted IP address (Proxmox VE host or administrator's phone) was blocked on the router! The block was **automatically lifted** by the bot.\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 Trusted IP** | `{ip}` |\n\n"
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
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 IP Address** | `{ip}` |\n\n"
        "<details>\n"
        "  <summary>📋 <b>Show found and removed rules</b></summary>\n"
        "  <pre><code>{rules_str}</code></pre>\n"
        "</details>"
    ),
    "router_autoblock_alert": (
        "# 🛑 Router Auto-Block\n"
        "---\n\n"
        "### 🛑 [Router Security] Device blocked automatically!\n\n"
        "🎯 Reason: Network violations limit exceeded ({threshold}+ attempts to access sensitive ports in 10 minutes).\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **👤 Blocked IP** | `{src_ip}` |\n"
        "| **🧭 Last Target** | `{dst_host}:{dst_port}` ({proto}) |\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    ),
    "router_port_alert": (
        "# 🚨 Router {type_str} Alert\n"
        "---\n\n"
        "### 🚨 [Router Security: {type_str}] Access to sensitive port detected!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🔌 Protocol** | `{proto}` |\n"
        "| **👤 Source** | `{src_ip}:{src_port}` |\n"
        "| **🎯 Target** | `{dst_host}:{dst_port}` |\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    )
}
