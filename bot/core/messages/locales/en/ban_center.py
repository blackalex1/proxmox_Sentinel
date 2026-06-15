translation = {
    "ban_center_title": "🛑 Aegis IPS Ban Center",
    "ban_center_empty": "<tr><td colspan=\"4\" style=\"padding: 8px; color: #a6adc8; text-align: center;\"><i>No active blocks in the system.<br/>All network activity is monitored by the Active IPS Engine.</i></td></tr>",
    "active_bans_header": "👤 Active Temporary IP Blocks",
    "banned_keys_header": "🔑 Banned SSH Keys",
    
    # Active IP table headers
    "col_ip": "IP Address",
    "col_node": "Node",
    "col_reason": "Reason",
    "col_expires": "Expires",
    
    # Banned keys table headers
    "col_user": "User",
    "col_banned_at": "Banned At",
    
    "reason_manual": "Manual",

    # Remaining time formatting
    "remaining_hours": "{hours}h {minutes}m",
    "remaining_minutes": "{minutes}m {seconds}s",
    "remaining_unknown": "Unknown",

    # Buttons
    "btn_unban_ip": "🔓 Unblock {ip}",
    "btn_unban_key": "🔓 Restore key (...{fp})",

    # Alerts and error messages
    "load_err": "❌ Error loading Ban Center.",
    "open_err": "❌ Error opening Ban Center.",
    "invalid_callback_err": "❌ Error: Invalid callback format.",
    "unban_in_progress": "⏳ Removing block...",
    "vps_not_found_err": "VPS with IP {ip} was not found in settings",
    "unban_success_alert": "🟢 Block on IP {ip} successfully removed!",
    "unban_failed_alert": "❌ Error removing block: {desc}",
    "key_not_found_err": "❌ Error: Key not found in DB or already restored.",
    "restore_key_in_progress": "⏳ Restoring key...",
    "invalid_lxc_id_err": "Invalid LXC ID.",
    "restore_key_success_alert": "🟢 SSH key successfully restored!",
    "restore_key_failed_alert": "❌ Error restoring key: {desc}",

    # CLI / Slash commands
    "unban_login_ip_help": "🟢 <b>Unban Login IP:</b>\nUse command: <code>/unban_login_ip &lt;ip&gt;</code>",
    "unban_login_ip_in_progress": "⏳ Unbanning IP <code>{ip}</code> on all panels...",
    "unban_login_ip_success_item": "  • {name}: 🟢 Unbanned",
    "unban_login_ip_failed_item": "  • {name}: 🔴 Error ({error})",
    "unban_login_ip_success": "✅ <b>IP <code>{ip}</code> unban results:</b>\n{details}",
    "unban_login_ip_failed": "❌ <b>Failed to unban IP <code>{ip}</code>:</b>\n{details}"
}
