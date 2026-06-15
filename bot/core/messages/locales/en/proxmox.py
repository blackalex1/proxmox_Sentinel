translation = {
    "title": "👨‍💻 <b>Proxmox Control Panel:</b>\nSelect a server from the list below:",
    "error_connect": "❌ Connection error: {err_msg}",
    "error": "Error: {err_msg}",
    "vms_title": "<b>Virtual Machines on server {node_name}:</b>",
    
    # Keyboard button labels
    "host_label": "💻 [Host] Proxmox VE",
    "back_to_nodes": "🔙 Back to Servers",
    "host_logs_btn": "🔒 Host Login Logs",
    "host_traffic_btn": "🌐 Host Traffic",
    "wl_ips_btn": "⚙️ IPS Whitelist",
    "refresh_status_btn": "🔄 Refresh Status",
    "back_to_vms_btn": "🔙 Back to VM List",
    "shutdown_btn": "🔌 Graceful Shutdown",
    "stop_btn": "🛑 Stop VM",
    "reboot_btn": "🔄 Reboot VM",
    "start_btn": "▶️ Start VM",
    "auth_logs_btn": "🔒 Login Logs",
    "ports_traffic_btn": "🌐 Port Traffic",
    "clone_btn": "👯 Clone VM",
    "refresh_log_btn": "🔄 Refresh Log",
    "back_to_vm_btn": "🔙 Back to VM",
    "refresh_traffic_btn": "🔄 Refresh Activity",
    "back_to_panel_btn": "🔙 Back to Panel",
    
    # VM / Node status cards
    "status_host_title": "💻 <b>Proxmox VE Host ({node_name})</b>\n\n",
    "status_vm_title": "🖥 <b>VM {vmid} ({name})</b>\n\n",
    "status_label": "Status",
    "status_online_vm": "🟢 Running",
    "status_online_host": "🟢 Online",
    "status_offline_vm": "🔴 Stopped",
    "version_label": "PVE Version",
    "cpu_cores_label": "CPU Cores",
    "cpu_load_label": "CPU Load",
    "ram_usage_label": "RAM Usage",
    "uptime_label": "Uptime",
    "type_label": "Type",
    
    # Alert notifications
    "host_data_actual": "Host data is up to date",
    "vm_data_actual": "VM data is up to date",
    "error_vm_load": "Error loading VM: {err_msg}",
    "exec_cmd": "⏳ Executing command {action}...",
    "error_cmd": "❌ Command error:\n{err_msg}",
    "uptime_format": "{hours}h {minutes}m {seconds}s",

    # Clone module
    "clone_title": "📝 <b>Cloning {vm_type} {vmid} ({node_name})</b>\n\nEnter <b>ID</b> for the new machine (e.g., 105):",
    "clone_id_nan": "❌ ID must be a number! Please try again:",
    "clone_name_prompt": "Enter a <b>name</b> for the new machine (e.g., my-new-server):",
    "clone_starting": "⏳ Starting cloning...",
    "clone_success": "✅ Cloning successfully started!\nNew VM ID: {new_id}, Name: {new_name}",
    "clone_error": "❌ Cloning error: {error}",

    # Logs module
    "host_label_default": "Proxmox VE Host",
    "auth_logs_host_title": "🔒 <b>Authorization logs for Host {node_name}:</b>\n\n",
    "auth_logs_lxc_title": "🔒 <b>Authorization logs for LXC {vmid} ({name}):</b>\n\n",
    "auth_logs_vps_title": "🔒 <b>Authorization logs for VPS ({server_ip}):</b>\n\n",
    "logs_empty": "<i>History is empty or the bot was recently restarted. Logs will appear upon new login attempts.</i>",
    "logs_truncated": "\n\n<i>... [Part of logs truncated due to Telegram size limits] ...</i>",
    "log_actual": "Log is up to date",
    "log_error": "Error retrieving logs: {err_msg}",
    "log_vps_error": "Error retrieving VPS logs: {err_msg}",

    # Traffic logs module
    "traffic_host_title": "🌐 <b>Network activity for Host {node_name}:</b>\n",
    "traffic_lxc_title": "🌐 <b>Network activity for LXC {vmid} ({name}):</b>\n",
    "traffic_subtitle": "<i>(Recent connections and their threat level)</i>\n\n",
    "traffic_empty": "<i>No connections recorded. Network activity will appear when new traffic passes.</i>",
    "traffic_direction_in_label": "Inbound connection",
    "traffic_direction_out_label": "Outbound connection",
    "traffic_truncated": "\n\n<i>... [Part of activity truncated due to Telegram size limits] ...</i>",
    "traffic_actual": "Activity is up to date",
    "traffic_error": "Error retrieving network activity: {err_msg}"
}
