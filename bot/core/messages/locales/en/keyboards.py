translation = {
    # Inline buttons
    "btn_proxmox": "🖥️ Proxmox VE",
    "btn_spectre": "🛡️ Sentinel Panel",
    "btn_ansible": "🛠️ Ansible Playbooks",
    "btn_vpn_history": "📋 VPN Connection History",
    "btn_ban_center": "🛑 Ban Center",
    "btn_whitelist": "⚙️ Sentinel IPS Whitelists",
    "btn_router_clients": "🖥️ Router Clients",
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
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>🛡️ Proxmox Sentinel • Control Panel</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>⚡ Security System</b></td>\n'
        '    <td align="left"><code>🟢 ACTIVE</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🖥️ Proxmox Host</b></td>\n'
        '    <td align="left"><code>{pve_ip}</code></td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><b>🌐 Remote VPS</b></td>\n'
        '    <td align="left"><code>{vps_ip}</code></td>\n'
        '  </tr>\n'
        '</table>\n\n'
        '<i>Select a section for monitoring and administration:</i>'
    ),
    "help_text": (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>ℹ️ Proxmox Sentinel • Commands Help</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <th colspan="2" align="left"><b>🎛️ Core Controls</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/start</code></td>\n'
        '    <td align="left">Interactive Control Panel</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/status</code></td>\n'
        '    <td align="left">Audit & status of all hypervisor systems</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/id</code></td>\n'
        '    <td align="left">Your Telegram ID and Chat ID</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <th colspan="2" align="left"><b>🛡️ Security & Sentinel IPS</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/threats</code></td>\n'
        '    <td align="left">Security incident log and attacks</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/bans</code></td>\n'
        '    <td align="left">Active temporary IP bans management</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/whitelist</code></td>\n'
        '    <td align="left">Manage whitelists (IP, ports, processes)</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <th colspan="2" align="left"><b>🌐 Network & Monitoring</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/router</code></td>\n'
        '    <td align="left">Connected router clients & activity</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/panel</code></td>\n'
        '    <td align="left">Manage Sentinel Panel nodes</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/top</code></td>\n'
        '    <td align="left">Active VPN sessions & traffic stats</td>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>/backup</code></td>\n'
        '    <td align="left">Create SQLite database backup</td>\n'
        '  </tr>\n'
        '</table>\n\n'
        '<details>\n'
        '  <summary>⚡ <b>Quick Actions & Direct Syntax</b></summary>\n'
        '  • <code>/whitelist_add &lt;IP[:Port]&gt; [node]</code> — quickly whitelist IP address<br/>\n'
        '  • <code>/whitelist_process &lt;process&gt; [node]</code> — quickly whitelist process<br/>\n'
        '  • <code>/unban_login_ip &lt;IP&gt;</code> — unban login IP address<br/>\n'
        '  • <code>/audit</code> or <code>/logs</code> — system security audit logs\n'
        '</details>\n\n'
        '<blockquote>🛡️ <b>Autonomous Protection:</b> The bot monitors SSH authentications (SSH Auth Monitor) and network anomalies (Active IPS Engine) in real-time. Security alerts are dispatched directly to this chat.</blockquote>'
    ),

    
    # Base command responses
    "welcome_message": (
        "👋 <b>Welcome to the Proxmox Sentinel monitoring system!</b>\n"
        "<i>A persistent quick access panel for main commands is activated below.</i>"
    ),
    "id_message": (
        "👤 <b>Your Telegram ID:</b> <code>{user_id}</code>\n"
        "💬 <b>This Chat ID:</b> <code>{chat_id}</code>"
    )
}

