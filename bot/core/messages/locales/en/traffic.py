translation = {
    "ips_investigation_success_alert": (
        "# ✅ IPS Investigation Done\n"
        "---\n\n"
        "### ✅ [IPS: Investigation Complete] Violator found!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **👤 Violator (Xray)** | `{xray_client}` (Blocked) |\n"
        "| **🔓 Hysteria Tunnel** | `{tunnel_email}` (Unblocked) |\n"
        "| **🌐 Attack Route** | Ingress: `{target_panel_name}` (Xray{inbound_display})<br/>Transit: `{tunnel_email}` (Hysteria2)<br/>Egress: VPS `{server_ip}` → `{dst_ip}:{dpt}` |\n\n"
        "✨ *All other tunnel users are back online!*\n\n"
        "<details>\n"
        "  <summary>📋 <b>Show global block details of the violator</b></summary>\n"
        "  <pre><code>{block_details_str}</code></pre>\n"
        "</details>\n\n"
        "<details>\n"
        "  <summary>📋 <b>Show unblock details of the Hysteria tunnel</b></summary>\n"
        "  <pre><code>{unblock_details_str}</code></pre>\n"
        "</details>\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    ),
    "ips_investigation_failed_alert": (
        "# ⚠️ IPS Investigation Failed\n"
        "---\n\n"
        "### ⚠️ [IPS: Investigation Failed] Violator not detected!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🚨 Tunnel Status** | `{tunnel_email}` (Left in ban) |\n"
        "| **🎯 Attack Target** | `{dst_ip}:{dpt}` |\n\n"
        "<details>\n"
        "  <summary>🔍 <b>Show gathered log fragments</b></summary>\n"
        "  <pre><code>{logs_text}</code></pre>\n"
        "</details>\n\n"
        "👇 You can unblock the tunnel manually in one click:\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    ),
    "ips_sensitive_access_alert": (
        "# 🚨 Traffic Security Alert\n"
        "---\n\n"
        "### 🚨 [VPS Traffic Security] Ingress access to sensitive port!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **🔌 Protocol** | `{proto}` |\n"
        "| **👤 Source** | `{src}:{spt}` |\n"
        "| **🎯 Target** | `{dst}:{dpt}` |\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    ),
    "ips_hysteria_attack_alert": (
        "# 🚨 Traffic Attack Detected\n"
        "---\n\n"
        "### 🚨 [VPS Traffic IPS] Attack detected through Hysteria tunnel!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **🔥 Temporary Ban** | `{email}` |\n"
        "| **🔌 Protocol** | `{proto}` |\n"
        "| **👤 Source** | `{src}:{spt}` |\n"
        "| **🎯 Target** | `{dst}:{dpt}` |\n\n"
        "🔍 *Asynchronous investigation launched to find the specific violator inside the tunnel...*\n\n"
        "<details>\n"
        "  <summary>📋 <b>Show tunnel block status</b></summary>\n"
        "  <pre><code>{block_details_str}</code></pre>\n"
        "</details>\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    ),
    "ips_xray_attack_alert": (
        "# 🚨 Traffic Attack Blocked\n"
        "---\n\n"
        "### 🚨 [VPS Traffic IPS] Network attack blocked!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **👤 Violator (Xray)** | `{email}`{inbound_display} |\n"
        "| **🔌 Protocol** | `{proto}` |\n"
        "| **👤 Source** | `{src}:{spt}`{proc_info} |\n"
        "| **🎯 Target** | `{dst}:{dpt}` |\n\n"
        "<details>\n"
        "  <summary>🚨 <b>Show auto-block status of the violator account</b></summary>\n"
        "  <pre><code>{block_details_str}</code></pre>\n"
        "</details>\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    ),
    "ips_whitelisted_alert": (
        "# ℹ️ Connection Allowed\n"
        "---\n\n"
        "### ℹ️ [VPS Traffic] Connection allowed (in IPS whitelist)\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **📁 Process** | `{proc_name}` |\n"
        "| **🔌 Protocol** | `{proto}` |\n"
        "| **👤 Source** | `{src}:{spt}` |\n"
        "| **🎯 Target** | `{dst}:{dpt}` |\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    ),
    "ips_process_killed_alert": (
        "# 🚨 Traffic Attack Blocked\n"
        "---\n\n"
        "### 🚨 [VPS Traffic IPS] Network attack blocked!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **🔥 Action** | **Process automatically terminated (kill -9)** |\n"
        "| **📁 Process** | `{proc_name}` (PID: `{killed_pid}`) |\n"
        "| **🔌 Protocol** | `{proto}` |\n"
        "| **👤 Source** | `{src}:{spt}` |\n"
        "| **🎯 Target** | `{dst}:{dpt}` |\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    ),
    "ips_process_warning_alert": (
        "# ⚠️ Traffic Sensitive Alert\n"
        "---\n\n"
        "### ⚠️ [VPS Traffic Warning] Outgoing connection to sensitive port!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS Server** | `{server_ip}` |\n"
        "| **🔌 Protocol** | `{proto}` |\n"
        "| **👤 Source** | `{src}:{spt}`{proc_info} |\n"
        "| **🎯 Target** | `{dst}:{dpt}` |\n\n"
        "*Note: Process has already exited or was not found. • Time: {timestamp}*"
    ),
    "local_traffic_alert": (
        "# {clean_h1}\n"
        "---\n\n"
        "### {title}\n\n"
        "ℹ️ Description: *{desc_with_client}*\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **📦 Container** | {vmid} (`{container_name}`) |\n"
        "| **🏷 Threat** | {label} |\n"
        "| **🔌 Protocol** | `{proto}` |\n"
        "| **🧭 Direction** | {direction_text} |\n"
        "| **👤 Source** | `{src}:{spt}` |\n"
        "| **🎯 Target** | `{dst}:{dpt}` |"
        "{vpn_ip_row}"
        "{vpn_client_row}"
        "{vpn_inbound_row}\n\n"
        "{block_details_block}\n\n"
        "*Aegis Security Guard • Time: {timestamp}*"
    ),
    
    # helper elements
    "local_h1_allowed": "ℹ️ Connection Allowed",
    "local_h1_blocked": "🚨 Attack Blocked",
    "local_h1_critical": "🚨 Critical Alert",
    "local_h1_warning": "⚠️ Warning Alert",
    "local_h1_default": "⚠️ Traffic Alert",
    "local_direction_in": "INBOUND",
    "local_direction_out": "OUTBOUND",
    "local_real_ip": "\n| **👤 Real IP** | `{real_client_ip}` |",
    "local_vpn_client": "\n| **👤 VPN Client** | `{xray_client_email}` |",
    "local_vpn_inbound": "\n| **🔌 VPN Inbound** | `{inbound_tag}` |",
    "local_block_status": "\n\n<details>\n  <summary>🚨 <b>Show auto-block status of the account</b></summary>\n  <pre><code>{block_details_str}</code></pre>\n</details>",
    "proc_info_tmpl": " (Process: `{proc_name}`)"
}
