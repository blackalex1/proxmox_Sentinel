translation = {
    "router_recovery_alert": (
        "# 🚨 Security Recovery\n"
        "---\n\n"
        "### 🚨 КРИТИЧЕСКАЯ УГРОЗА: Восстановлен доступ для доверенного узла!\n\n"
        "Бот обнаружил, что доверенный IP-адрес (хост Proxmox VE или телефон администратора) был заблокирован на роутере! Блокировка была **автоматически снята** ботом.\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 Доверенный IP** | `{ip}` |\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n"
        "  <pre><code>{rules_str}</code></pre>\n"
        "</details>"
    ),
    "router_unknown_block_alert": (
        "# ⚠️ Router Reconciliation\n"
        "---\n\n"
        "### ⚠️ Обнаружена неизвестная блокировка на роутере!\n\n"
        "Бот обнаружил правила блокировки для IP, которых нет в базе данных временных банов бота. В целях безопасности и синхронизации блокировка была автоматически снята.\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 IP-адрес** | `{ip}` |\n\n"
        "<details>\n"
        "  <summary>📋 <b>Показать найденные и удаленные правила</b></summary>\n"
        "  <pre><code>{rules_str}</code></pre>\n"
        "</details>"
    ),
    "router_autoblock_alert": (
        "# 🛑 Router Auto-Block\n"
        "---\n\n"
        "### 🛑 [Router Security] Устройство заблокировано автоматически!\n\n"
        "🎯 Причина: Превышен лимит сетевых нарушений ({threshold}+ попыток доступа к чувствительным портам за 10 минут).\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **👤 Заблокированный IP** | `{src_ip}` |\n"
        "| **🧭 Последняя цель** | `{dst_host}:{dst_port}` ({proto}) |\n\n"
        "*Aegis Security Guard • Время: {timestamp}*"
    ),
    "router_port_alert": (
        "# 🚨 Router {type_str} Alert\n"
        "---\n\n"
        "### 🚨 [Router Security: {type_str}] Обнаружен доступ к чувствительному порту!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🔌 Протокол** | `{proto}` |\n"
        "| **👤 Источник** | `{src_ip}:{src_port}` |\n"
        "| **🎯 Назначение** | `{dst_host}:{dst_port}` |\n\n"
        "*Aegis Security Guard • Время: {timestamp}*"
    ),
    "btn_unblock_ip_router": "🟢 Разблокировать IP на роутере",
    "btn_block_ip_router": "🛑 Заблокировать IP на роутере",
    "ip_blocked_successfully": "🛑 IP {ip} успешно заблокирован на роутере!",
    "ip_block_failed": "❌ Ошибка блокировки: {desc}",
    "ip_block_error": "Ошибка при блокировке: {e}",
    "ip_unblocked_successfully": "🟢 Блокировка с IP {ip} снята!",
    "ip_unblock_failed": "❌ Ошибка снятия блокировки: {desc}",
    "ip_unblock_error": "Ошибка при разблокировке: {e}",
    "device_blocked_text": "\n\n🛑 <b>УСТРОЙСТВО {ip} ЗАБЛОКИРОВАНО НА РОУТЕРЕ!</b>",
    "invalid_data_format": "Ошибка: неверный формат данных.",
}
