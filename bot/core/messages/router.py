# bot/core/messages/router.py
"""Шаблоны сообщений для мониторинга роутера на GFM Markdown."""

from core.config import settings

def get_router_recovery_alert(ip, rules_str):
    return (
        f"# 🚨 Security Recovery\n"
        f"---\n\n"
        f"### 🚨 КРИТИЧЕСКАЯ УГРОЗА: Восстановлен доступ для доверенного узла!\n\n"
        f"Бот обнаружил, что доверенный IP-адрес (хост Proxmox VE или телефон администратора) был заблокирован на роутере! Блокировка была **автоматически снята** ботом.\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 Доверенный IP** | `{ip}` |\n\n"
        f"<details>\n"
        f"  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n"
        f"  <pre><code>{rules_str}</code></pre>\n"
        f"</details>"
    )

def get_router_unknown_block_alert(ip, rules_str):
    return (
        f"# ⚠️ Router Reconciliation\n"
        f"---\n\n"
        f"### ⚠️ Обнаружена неизвестная блокировка на роутере!\n\n"
        f"Бот обнаружил правила блокировки для IP, которых нет в базе данных временных банов бота. В целях безопасности и синхронизации блокировка была автоматически снята.\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🌐 IP-адрес** | `{ip}` |\n\n"
        f"<details>\n"
        f"  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n"
        f"  <pre><code>{rules_str}</code></pre>\n"
        f"</details>"
    )

def get_router_autoblock_alert(src_ip, dst_host, dst_port, proto, timestamp):
    return (
        f"# 🛑 Router Auto-Block\n"
        f"---\n\n"
        f"### 🛑 [Router Security] Устройство заблокировано автоматически!\n\n"
        f"🎯 Причина: Превышен лимит сетевых нарушений ({settings.router_max_violations}+ попыток доступа к чувствительным портам за 10 минут).\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **👤 Заблокированный IP** | `{src_ip}` |\n"
        f"| **🧭 Последняя цель** | `{dst_host}:{dst_port}` ({proto}) |\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )

def get_router_port_alert(type_str, proto, src_ip, src_port, dst_host, dst_port, timestamp):
    return (
        f"# 🚨 Router {type_str} Alert\n"
        f"---\n\n"
        f"### 🚨 [Router Security: {type_str}] Обнаружен доступ к чувствительному порту!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🔌 Протокол** | `{proto}` |\n"
        f"| **👤 Источник** | `{src_ip}:{src_port}` |\n"
        f"| **🎯 Назначение** | `{dst_host}:{dst_port}` |\n\n"
        f"*Aegis Security Guard • Время: {timestamp}*"
    )
