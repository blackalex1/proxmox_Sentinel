translation = {
    # Inline buttons
    "btn_proxmox": "🖥️ Proxmox VE",
    "btn_spectre": "🚀 Spectre VPN Panel",
    "btn_ansible": "🛠️ Ansible Playbooks",
    "btn_vpn_history": "📋 VPN Connection History",
    "btn_ban_center": "🛑 Ban Center",
    "btn_whitelist": "⚙️ Aegis IPS Whitelists",
    "btn_status": "📊 System Status",
    "btn_help": "ℹ️ Help",
    "btn_back_to_menu": "🔙 Back to Main Menu",
    "btn_refresh_status": "🔄 Refresh Status",
    "status_loading": "⏳ <i>Gathering system status details...</i>",
    
    # Reply buttons
    "reply_control_panel": "🛡️ Control Panel",
    "reply_system_status": "📊 System Status",
    "reply_help": "ℹ️ Help",
    
    # Menu and help texts
    "main_menu_text": (
        "🛡️ <b>PVE Aegis IPS • Control Panel</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <b>Protection System:</b> <code>🟢 ACTIVE</code>\n"
        "🖥️ <b>Proxmox Host:</b> <code>{pve_ip}</code>\n"
        "🌐 <b>Remote VPS:</b> <code>{vps_ip}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Select a section for monitoring and administration:"
    ),
    "help_text": (
        "ℹ️ <b>PVE Aegis Commands Help:</b>\n\n"
        "• /start — Show interactive control panel (Main Menu)\n"
        "• /status — Fast audit and status of all systems (Proxmox, background services)\n"
        "• /bans — Control center for active temporary IP blocks\n"
        "• /whitelist — Manage Aegis IPS whitelists (IP, ports, processes)\n"
        "• /whitelist_add &lt;IP or IP:Port&gt; [node] — Quickly add IP to whitelist\n"
        "• /whitelist_process &lt;process&gt; [node] — Quickly add process to whitelist\n"
        "• /help — Show this help message\n"
        "• /id — Show your Telegram ID / Chat ID\n\n"
        "🛡️ <i>The bot automatically monitors authorization attempts (SSH Auth Monitor) and unauthorized network activity (Active IPS Engine) in real-time. All alerts are sent directly to this chat.</i>"
    ),
    
    # Base command responses
    "welcome_message": (
        "👋 <b>Welcome to the PVE Aegis monitoring system!</b>\n"
        "<i>A persistent quick access panel for main commands is activated below.</i>"
    ),
    "id_message": (
        "👤 <b>Your Telegram ID:</b> <code>{user_id}</code>\n"
        "💬 <b>This Chat ID:</b> <code>{chat_id}</code>"
    )
}
