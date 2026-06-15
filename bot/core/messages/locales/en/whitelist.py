translation = {
    "whitelist_view_title": "📁 Whitelist: {node_label}",
    "whitelist_empty": "<tr><td colspan=\"2\" style=\"padding: 8px; color: #a6adc8; text-align: center;\"><i>No rules in the whitelist for this node. All connections are filtered by standard IPS rules.</i></td></tr>",
    "whitelist_type_header": "Rule Type",
    "whitelist_value_header": "Value",
    "whitelist_rule_ip_port": "🌐 IP / Port",
    "whitelist_rule_process": "⚙️ Process",
    
    "whitelist_view_all_title": "📋 All Aegis IPS Whitelist Rules",
    "whitelist_view_all_empty": "<tr><td colspan=\"2\" style=\"padding: 8px; color: #bf616a; text-align: center;\">❌ No rules configured for any node.</td></tr>",

    # Whitelist nodes labels
    "global_node": "🌍 Globally (Everywhere)",
    "router_node": "🔌 Router",
    "pve_node": "🖥️ Proxmox Host",
    "lxc_node": "📦 LXC {vmid} ({name})",
    "vps_node": "🌐 VPS {ip}",
    "offline_label": "{label} (offline)",

    # Button texts
    "btn_show_all": "📋 Show All Rules",
    "btn_back_to_nodes": "🔙 Back to Nodes Selection",
    "btn_add_ip_port": "➕ Add IP/Port",
    "btn_add_proc": "➕ Add Process",
    "btn_delete_rule": "🗑️ Delete Rule",
    "btn_back_to_nodes_list": "🔙 Back to Nodes List",
    "btn_cancel": "❌ Cancel",
    "btn_del_ip": "🗑️ IP: {item}",
    "btn_del_proc": "🗑️ Proc: {item}",
    "btn_back_to_view": "🔙 Back to View",

    # Messages / Inputs
    "manage_title": "⚙️ <b>Aegis IPS Whitelists Management</b>\n\nSelect a node to view and configure security rules:",
    "add_ip_port_title": "➕ <b>Add IP/Port to Whitelist</b>\nNode: {node_label}\n\nSend a message containing the IP address or IP:Port combination (for example: <code>1.2.3.4</code>, <code>1.2.3.4:22</code>, or <code>1.2.3.4:*</code> for any port):",
    "invalid_input": "Invalid input. Please try again or press Cancel.",
    "invalid_ip_port_format": "❌ Invalid IP/Port format. Examples: <code>192.168.1.100</code>, <code>192.168.1.100:22</code>, or <code>192.168.1.100:*</code>.",
    "rule_added_success": "🟢 <b>Rule successfully added!</b>\n\n📁 <b>Whitelist for node: {node_label}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n",
    "allowed_ip_ports": "<b>Allowed IPs / IP:Ports:</b>\n",
    "allowed_processes": "<b>Allowed Processes:</b>\n",
    "add_proc_title": "➕ <b>Add Process to Whitelist</b>\nNode: {node_label}\n\nSend a message containing the process name (for example: <code>caddy</code>, <code>nginx</code>, or <code>sshd</code>):",
    "invalid_proc_name": "❌ Invalid process name (only alphanumeric characters are allowed). Please try again.",
    "proc_added_success": "🟢 <b>Process successfully added!</b>\n\n📁 <b>Whitelist for node: {node_label}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n",
    "empty_whitelist_err": "❌ Whitelist of this node is empty. Nothing to delete.",
    "del_rule_title": "🗑️ <b>Deleting Whitelist Rules</b>\nNode: {node_label}\n\nSelect the rule you want to delete:",
    "del_success_alert": "🟢 Successfully deleted: {item}",

    # CLI / Slash commands
    "cli_add_help": "❌ Usage: <code>/whitelist_add &lt;IP or IP:Port&gt; [node]</code>\nExample: <code>/whitelist_add 1.2.3.4:22 router</code>",
    "cli_invalid_ip_port": "❌ Invalid IP/Port format.",
    "cli_added_ip_port": "🟢 Added <code>{val}</code> to the whitelist of node <b>{label}</b>.",
    "cli_rule_exists": "ℹ️ Rule <code>{val}</code> already exists for node <b>{label}</b>.",
    "cli_proc_help": "❌ Usage: <code>/whitelist_process &lt;process name&gt; [node]</code>\nExample: <code>/whitelist_process openvpn global</code>",
    "cli_invalid_proc": "❌ Invalid process name.",
    "cli_added_proc": "🟢 Added process <code>{val}</code> to the whitelist of node <b>{label}</b>.",
    "cli_proc_exists": "ℹ️ Process <code>{val}</code> already exists in the whitelist of node <b>{label}</b>.",

    # Quick Whitelist callbacks
    "qwl_invalid_callback": "❌ Invalid callback data format.",
    "qwl_added_success": "🟢 Successfully added to whitelist {label}: {val}",
    "qwl_added_msg": "\n\n✅ <b>Added to whitelist ({label}):</b> <code>{val}</code>",
    "qwl_already_whitelisted": "ℹ️ Already exists in the whitelist of {label}.",
    "qwl_save_error": "❌ An error occurred during saving."
}
