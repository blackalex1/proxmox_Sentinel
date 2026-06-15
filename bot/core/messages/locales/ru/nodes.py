translation = {
    "vps_offline_alert": (
        "# ⚠️ VPS Offline\n"
        "---\n\n"
        "### ⚠️ [Remote Monitor] Удаленный VPS-сервер отключен!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 IP-адрес** | `{ip}` |\n"
        "| **🔌 Статус** | 🔴 Недоступен (SSH порт закрыт) |\n"
    ),
    "vps_online_alert": (
        "# ✅ VPS Online\n"
        "---\n\n"
        "### ✅ [Remote Monitor] Связь с VPS восстановлена!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 IP-адрес** | `{ip}` |\n"
        "| **🔌 Статус** | 🟢 Доступен (Связь восстановлена) |\n"
    ),
    "node_offline_alert": (
        "# ⚠️ Node Offline\n"
        "---\n\n"
        "### ⚠️ [Cluster Monitor] Сервер недоступен!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🖥 Сервер** | **{node_name}** |\n"
        "| **🔌 Статус** | 🔴 {status} |\n"
    ),
    "node_online_alert": (
        "# ✅ Node Online\n"
        "---\n\n"
        "### ✅ [Cluster Monitor] Сервер снова в сети!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🖥 Сервер** | **{node_name}** |\n"
        "| **🔌 Статус** | 🟢 Доступен |\n"
    ),
    
    # HTML status table fields
    "status_audit_title": "📊 Аудит статуса систем PVE Aegis",
    "hypervisor_header": "🖥 Hypervisor (Proxmox VE)",
    "pve_not_configured": "⚪ <b>Proxmox VE:</b> Не настроен",
    "pve_error": "🔴 <b>Proxmox VE:</b> Ошибка: <code>{error}</code>",
    "pve_nodes_not_found": "🔴 <b>Proxmox VE:</b> Ноды не найдены",
    "pve_online_detail": "🟢 online (CPU: {cpu:.1f}% | RAM: {mem:.1f}/{maxmem:.1f} GB)",
    "pve_offline_detail": "🔴 offline",
    "security_services_header": "🛡 Фоновые службы безопасности",
    "service_active": "🟢 Активен",
    "service_stopped": "🔴 Остановлен",
    "ips_enabled": "🟢 Защита включена",
    "ips_disabled": "🔴 Защита выключена",
    "remote_vps_disabled_env": "⚪ Выключен в .env"
}
