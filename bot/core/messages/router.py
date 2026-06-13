# bot/core/messages/router.py
"""Шаблоны сообщений для мониторинга роутера."""

from core.config import settings

def get_router_recovery_alert(ip, rules_str):
    return (
        f"<h1>🚨 Security Recovery</h1>\n"
        f"<hr/>\n\n"
        f"<h3>🚨 КРИТИЧЕСКАЯ УГРОЗА: Восстановлен доступ для доверенного узла!</h3>\n\n"
        f"Бот обнаружил, что доверенный IP-адрес (хост Proxmox VE или телефон администратора) был заблокирован на роутере! Блокировка была <b>автоматически снята</b> ботом.\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🌐 Доверенный IP</b></td>\n"
        f"    <td><code>{ip}</code></td>\n"
        f"  </tr>\n"
        f"</table>\n\n"
        f"<details>\n"
        f"  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n"
        f"  <pre><code>{rules_str}</code></pre>\n"
        f"</details>"
    )

def get_router_unknown_block_alert(ip, rules_str):
    return (
        f"<h1>⚠️ Router Reconciliation</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ Обнаружена неизвестная блокировка на роутере!</h3>\n\n"
        f"Бот обнаружил правила блокировки для IP, которых нет в базе данных временных банов бота. В целях безопасности и синхронизации блокировка была автоматически снята.\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🌐 IP-адрес</b></td>\n"
        f"    <td><code>{ip}</code></td>\n"
        f"  </tr>\n"
        f"</table>\n\n"
        f"<details>\n"
        f"  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n"
        f"  <pre><code>{rules_str}</code></pre>\n"
        f"</details>"
    )

def get_router_autoblock_alert(src_ip, dst_host, dst_port, proto, timestamp):
    return (
        f"<h1>🛑 Router Auto-Block</h1>\n"
        f"<hr/>\n\n"
        f"<h3>🛑 [Router Security] Устройство заблокировано автоматически!</h3>\n\n"
        f"🎯 Причина: Превышен лимит сетевых нарушений ({settings.router_max_violations}+ попыток доступа к чувствительным портам за 10 минут).\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>👤 Заблокированный IP</b></td>\n"
        f"    <td><code>{src_ip}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🧭 Последняя цель</b></td>\n"
        f"    <td><code>{dst_host}:{dst_port}</code> ({proto})</td>\n"
        f"  </tr>\n"
        f"</table>\n\n"
        f"<i>Aegis Security Guard • Время: {timestamp}</i>"
    )

def get_router_port_alert(type_str, proto, src_ip, src_port, dst_host, dst_port, timestamp):
    return (
        f"<h1>🚨 Router {type_str} Alert</h1>\n"
        f"<hr/>\n\n"
        f"<h3>🚨 [Router Security: {type_str}] Обнаружен доступ к чувствительному порту!</h3>\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔌 Протокол</b></td>\n"
        f"    <td><code>{proto}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>👤 Источник</b></td>\n"
        f"    <td><code>{src_ip}:{src_port}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🎯 Назначение</b></td>\n"
        f"    <td><code>{dst_host}:{dst_port}</code></td>\n"
        f"  </tr>\n"
        f"</table>\n\n"
        f"<i>Aegis Security Guard • Время: {timestamp}</i>"
    )
