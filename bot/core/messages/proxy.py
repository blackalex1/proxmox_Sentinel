# bot/core/messages/proxy.py
"""Шаблоны сообщений для мониторинга прокси."""

def get_proxy_switch_alert(primary_proxy, new_proxy):
    return (
        f"<h1>⚠️ Proxy Switch Alert</h1>\n"
        f"<hr/>\n\n"
        f"<h3>⚠️ [Proxy Monitor] Основной прокси не отвечает!</h3>\n\n"
        f"🔄 Бот автоматически переключился на резервное SOCKS5 подключение.\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>❌ Основной прокси</b></td>\n"
        f"    <td><code>{primary_proxy}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔄 Резервный прокси</b></td>\n"
        f"    <td><code>{new_proxy}</code></td>\n"
        f"  </tr>\n"
        f"</table>"
    )

def get_proxy_restored_alert(primary_proxy):
    return (
        f"<h1>✅ Proxy Restored</h1>\n"
        f"<hr/>\n\n"
        f"<h3>✅ [Proxy Monitor] Основной прокси снова доступен!</h3>\n\n"
        f"🔄 Успешно вернулись на основное подключение.\n\n"
        f"<table bordered striped>\n"
        f"  <tr>\n"
        f"    <th align=\"left\">Параметр</th>\n"
        f"    <th align=\"left\">Значение</th>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>🔌 Подключение</b></td>\n"
        f"    <td><code>{primary_proxy}</code></td>\n"
        f"  </tr>\n"
        f"  <tr>\n"
        f"    <td><b>ℹ️ Статус</b></td>\n"
        f"    <td>🟢 В сети (Основной прокси)</td>\n"
        f"  </tr>\n"
        f"</table>"
    )
