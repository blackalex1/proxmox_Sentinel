translation = {
    "vps_offline_alert": (
        "# ⚠️ VPS Offline\n"
        "---\n\n"
        "### ⚠️ [Remote Monitor] Remote VPS server is offline!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 IP Address** | `{ip}` |\n"
        "| **🔌 Status** | 🔴 Offline (SSH port closed) |\n"
    ),
    "vps_online_alert": (
        "# ✅ VPS Online\n"
        "---\n\n"
        "### ✅ [Remote Monitor] Connection with VPS restored!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 IP Address** | `{ip}` |\n"
        "| **🔌 Status** | 🟢 Online (Connection restored) |\n"
    ),
    "node_offline_alert": (
        "# ⚠️ Node Offline\n"
        "---\n\n"
        "### ⚠️ [Cluster Monitor] Server is offline!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🖥 Server** | **{node_name}** |\n"
        "| **🔌 Status** | 🔴 {status} |\n"
    ),
    "node_online_alert": (
        "# ✅ Node Online\n"
        "---\n\n"
        "### ✅ [Cluster Monitor] Server is back online!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🖥 Server** | **{node_name}** |\n"
        "| **🔌 Status** | 🟢 Online |\n"
    ),
    
    # HTML status table fields
    "status_audit_title": "📊 PVE Aegis System Status Audit",
    "hypervisor_header": "🖥 Hypervisor (Proxmox VE)",
    "pve_not_configured": "⚪ <b>Proxmox VE:</b> Not configured",
    "pve_error": "🔴 <b>Proxmox VE:</b> Error: <code>{error}</code>",
    "pve_nodes_not_found": "🔴 <b>Proxmox VE:</b> Nodes not found",
    "pve_online_detail": "🟢 online (CPU: {cpu:.1f}% | RAM: {mem:.1f}/{maxmem:.1f} GB)",
    "pve_offline_detail": "🔴 offline",
    "security_services_header": "🛡 Background Security Services",
    "service_active": "🟢 Active",
    "service_stopped": "🔴 Stopped",
    "ips_enabled": "🟢 Protection enabled",
    "ips_disabled": "🔴 Protection disabled",
    "remote_vps_disabled_env": "⚪ Disabled in .env"
}
