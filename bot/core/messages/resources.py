# bot/core/messages/resources.py
"""Шаблоны сообщений для мониторинга ресурсов (VPS & LXC) на GFM Markdown с поддержкой i18n."""

from core.config import settings
from core.messages.i18n import _

def get_vps_cpu_alert(ip, cpu):
    return _(
        "resources", "vps_cpu_alert",
        ip=ip, cpu=cpu, threshold=settings.monitor_lxc_cpu
    )

def get_vps_ram_alert(ip, ram_pct):
    return _(
        "resources", "vps_ram_alert",
        ip=ip, ram_pct=ram_pct, threshold=settings.monitor_lxc_ram
    )

def get_vps_disk_alert(ip, disk_pct):
    return _(
        "resources", "vps_disk_alert",
        ip=ip, disk_pct=disk_pct, threshold=settings.monitor_lxc_disk
    )

def get_lxc_state_alert(emoji, vmid, name, node_name, status_text):
    return _(
        "resources", "lxc_state_alert",
        emoji=emoji, vmid=vmid, name=name,
        node_name=node_name, status_text=status_text
    )

def get_lxc_cpu_alert(vmid, name, cpu):
    return _(
        "resources", "lxc_cpu_alert",
        vmid=vmid, name=name, cpu=cpu, threshold=settings.monitor_lxc_cpu
    )

def get_lxc_ram_alert(vmid, name, mem_pct, mem, maxmem):
    return _(
        "resources", "lxc_ram_alert",
        vmid=vmid, name=name, mem_pct=mem_pct,
        mem=mem / (1024**3), maxmem=maxmem / (1024**3),
        threshold=settings.monitor_lxc_ram
    )

def get_lxc_disk_alert(vmid, name, disk_pct, disk, maxdisk):
    return _(
        "resources", "lxc_disk_alert",
        vmid=vmid, name=name, disk_pct=disk_pct,
        disk=disk / (1024**3), maxdisk=maxdisk / (1024**3),
        threshold=settings.monitor_lxc_disk
    )
