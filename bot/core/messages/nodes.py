# bot/core/messages/nodes.py
"""Шаблоны сообщений для мониторинга доступности серверов и узлов Proxmox VE."""

def get_vps_offline_alert(ip):
    return (
        f"<h1>⚠️ VPS Offline</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ [Remote Monitor] Удаленный VPS-сервер отключен!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🌐 IP-адрес</b></td>\n"
        f"    <td><code>{ip}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔌 Статус</b></td>\n"
        f"    <td>🔴 Недоступен (SSH порт закрыт)</td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_vps_online_alert(ip):
    return (
        f"<h1>✅ VPS Online</h1>\n"
        f"<hr/>\n\n"
        f"<h3>✅ [Remote Monitor] Связь с VPS восстановлена!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🌐 IP-адрес</b></td>\n"
        f"    <td><code>{ip}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔌 Статус</b></td>\n"
        f"    <td>🟢 Доступен (Связь восстановлена)</td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_node_offline_alert(node_name, status):
    return (
        f"<h1>⚠️ Node Offline</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ [Cluster Monitor] Сервер недоступен!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🖥 Сервер</b></td>\n"
        f"    <td><b>{node_name}</b></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔌 Статус</b></td>\n"
        f"    <td>🔴 {status}</td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_node_online_alert(node_name):
    return (
        f"<h1>✅ Node Online</h1>\n"
        f"<hr/>\n\n"
        f"<h3>✅ [Cluster Monitor] Сервер снова в сети!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🖥 Сервер</b></td>\n"
        f"    <td><b>{node_name}</b></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔌 Статус</b></td>\n"
        f"    <td>🟢 Доступен</td>\n"
        f"  </tr>\n"
        f"</table>"
    )
