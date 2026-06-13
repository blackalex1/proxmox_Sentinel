# bot/core/messages/resources.py
"""Шаблоны сообщений для мониторинга ресурсов (VPS & LXC)."""

from core.config import settings

def get_vps_cpu_alert(ip, cpu):
    return (
        f"<h1>⚠️ CPU High Load</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ [VPS Monitor] Высокая нагрузка CPU (более 5 минут)!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🌐 VPS IP</b></td>\n"
        f"    <td><code>{ip}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔴 CPU load</b></td>\n"
        f"    <td><b>{cpu:.1f}%</b> (Порог: {settings.monitor_lxc_cpu}%)</td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_vps_ram_alert(ip, ram_pct):
    return (
        f"<h1>⚠️ RAM High Usage</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ [VPS Monitor] Высокое потребление RAM (более 5 минут)!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🌐 VPS IP</b></td>\n"
        f"    <td><code>{ip}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔴 ОЗУ load</b></td>\n"
        f"    <td><b>{ram_pct:.1f}%</b> (Порог: {settings.monitor_lxc_ram}%)</td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_vps_disk_alert(ip, disk_pct):
    return (
        f"<h1>⚠️ Disk Full Alert</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ [VPS Monitor] Переполнение Диска VPS!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🌐 VPS IP</b></td>\n"
        f"    <td><code>{ip}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔴 Диск usage</b></td>\n"
        f"    <td><b>{disk_pct:.1f}%</b> (Порог: {settings.monitor_lxc_disk}%)</td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_lxc_state_alert(emoji, vmid, name, node_name, status_text):
    return (
        f"<h1>{emoji} VM Status Alert</h1>\n"
        f"<hr/>\n\n"
        f"<h3>{emoji} Изменение статуса LXC контейнера!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>📦 ID</b></td>\n"
        f"    <td><code>{vmid}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🏷 Имя</b></td>\n"
        f"    <td><code>{name}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>⚡️ Сервер</b></td>\n"
        f"    <td><code>{node_name}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>ℹ️ Статус</b></td>\n"
        f"    <td><b>{status_text}</b></td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_lxc_cpu_alert(vmid, name, cpu):
    return (
        f"<h1>⚠️ CPU Load Alert</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ [LXC Monitor] Высокая нагрузка CPU (более 5 минут)!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>📦 LXC Container</b></td>\n"
        f"    <td>{vmid} (<code>{name}</code>)</td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔴 CPU load</b></td>\n"
        f"    <td><b>{cpu:.1f}%</b> (Порог: {settings.monitor_lxc_cpu}%)</td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_lxc_ram_alert(vmid, name, mem_pct, mem, maxmem):
    return (
        f"<h1>⚠️ RAM Load Alert</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ [LXC Monitor] Высокое потребление RAM (более 5 минут)!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>📦 LXC Container</b></td>\n"
        f"    <td>{vmid} (<code>{name}</code>)</td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔴 ОЗУ usage</b></td>\n"
        f"    <td><b>{mem_pct:.1f}%</b> ({mem / (1024**3):.1f} / {maxmem / (1024**3):.1f} GB) (Порог: {settings.monitor_lxc_ram}%)</td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_lxc_disk_alert(vmid, name, disk_pct, disk, maxdisk):
    return (
        f"<h1>⚠️ Disk Full Alert</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ [LXC Monitor] Переполнение Диска LXC!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>📦 LXC Container</b></td>\n"
        f"    <td>{vmid} (<code>{name}</code>)</td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔴 Диск usage</b></td>\n"
        f"    <td><b>{disk_pct:.1f}%</b> ({disk / (1024**3):.1f} / {maxdisk / (1024**3):.1f} GB) (Порог: {settings.monitor_lxc_disk}%)</td>\n"
        f"  </tr>\n"
        f"</table>"
    )
