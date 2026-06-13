# bot/core/messages/resources.py
"""Шаблоны сообщений для мониторинга ресурсов (VPS & LXC) на GFM Markdown."""

from core.config import settings

def get_vps_cpu_alert(ip, cpu):
    return (
        f"# ⚠️ CPU High Load\n"
        f"---\n\n"
        f"### ⚠️ [VPS Monitor] Высокая нагрузка CPU (более 5 минут)!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 VPS IP** | `{ip}` |\n"
        f"| **🔴 CPU load** | **{cpu:.1f}%** (Порог: {settings.monitor_lxc_cpu}%) |\n"
    )

def get_vps_ram_alert(ip, ram_pct):
    return (
        f"# ⚠️ RAM High Usage\n"
        f"---\n\n"
        f"### ⚠️ [VPS Monitor] Высокое потребление RAM (более 5 минут)!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 VPS IP** | `{ip}` |\n"
        f"| **🔴 ОЗУ load** | **{ram_pct:.1f}%** (Порог: {settings.monitor_lxc_ram}%) |\n"
    )

def get_vps_disk_alert(ip, disk_pct):
    return (
        f"# ⚠️ Disk Full Alert\n"
        f"---\n\n"
        f"### ⚠️ [VPS Monitor] Переполнение Диска VPS!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 VPS IP** | `{ip}` |\n"
        f"| **🔴 Диск usage** | **{disk_pct:.1f}%** (Порог: {settings.monitor_lxc_disk}%) |\n"
    )

def get_lxc_state_alert(emoji, vmid, name, node_name, status_text):
    return (
        f"# {emoji} VM Status Alert\n"
        f"---\n\n"
        f"### {emoji} Изменение статуса LXC контейнера!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 ID** | `{vmid}` |\n"
        f"| **🏷 Имя** | `{name}` |\n"
        f"| **⚡️ Сервер** | `{node_name}` |\n"
        f"| **ℹ️ Статус** | **{status_text}** |\n"
    )

def get_lxc_cpu_alert(vmid, name, cpu):
    return (
        f"# ⚠️ CPU Load Alert\n"
        f"---\n\n"
        f"### ⚠️ [LXC Monitor] Высокая нагрузка CPU (более 5 минут)!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 LXC Container** | {vmid} (`{name}`) |\n"
        f"| **🔴 CPU load** | **{cpu:.1f}%** (Порог: {settings.monitor_lxc_cpu}%) |\n"
    )

def get_lxc_ram_alert(vmid, name, mem_pct, mem, maxmem):
    return (
        f"# ⚠️ RAM Load Alert\n"
        f"---\n\n"
        f"### ⚠️ [LXC Monitor] Высокое потребление RAM (более 5 минут)!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 LXC Container** | {vmid} (`{name}`) |\n"
        f"| **🔴 ОЗУ usage** | **{mem_pct:.1f}%** ({mem / (1024**3):.1f} / {maxmem / (1024**3):.1f} GB) (Порог: {settings.monitor_lxc_ram}%) |\n"
    )

def get_lxc_disk_alert(vmid, name, disk_pct, disk, maxdisk):
    return (
        f"# ⚠️ Disk Full Alert\n"
        f"---\n\n"
        f"### ⚠️ [LXC Monitor] Переполнение Диска LXC!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 LXC Container** | {vmid} (`{name}`) |\n"
        f"| **🔴 Диск usage** | **{disk_pct:.1f}%** ({disk / (1024**3):.1f} / {maxdisk / (1024**3):.1f} GB) (Порог: {settings.monitor_lxc_disk}%) |\n"
    )
