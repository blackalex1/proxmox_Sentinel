# bot/core/messages/nodes.py
"""Шаблоны сообщений для мониторинга доступности серверов и узлов Proxmox VE на GFM Markdown."""

def get_vps_offline_alert(ip):
    return (
        f"# ⚠️ VPS Offline\n"
        f"---\n\n"
        f"### ⚠️ [Remote Monitor] Удаленный VPS-сервер отключен!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 IP-адрес** | `{ip}` |\n"
        f"| **🔌 Статус** | 🔴 Недоступен (SSH порт закрыт) |\n"
    )

def get_vps_online_alert(ip):
    return (
        f"# ✅ VPS Online\n"
        f"---\n\n"
        f"### ✅ [Remote Monitor] Связь с VPS восстановлена!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 IP-адрес** | `{ip}` |\n"
        f"| **🔌 Статус** | 🟢 Доступен (Связь восстановлена) |\n"
    )

def get_node_offline_alert(node_name, status):
    return (
        f"# ⚠️ Node Offline\n"
        f"---\n\n"
        f"### ⚠️ [Cluster Monitor] Сервер недоступен!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🖥 Сервер** | **{node_name}** |\n"
        f"| **🔌 Статус** | 🔴 {status} |\n"
    )

def get_node_online_alert(node_name):
    return (
        f"# ✅ Node Online\n"
        f"---\n\n"
        f"### ✅ [Cluster Monitor] Сервер снова в сети!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🖥 Сервер** | **{node_name}** |\n"
        f"| **🔌 Статус** | 🟢 Доступен |\n"
    )
