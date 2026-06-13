# bot/core/messages/proxy.py
"""Шаблоны сообщений для мониторинга прокси на GFM Markdown."""

def get_proxy_switch_alert(primary_proxy, new_proxy):
    return (
        f"# ⚠️ Proxy Switch Alert\n"
        f"---\n\n"
        f"### ⚠️ [Proxy Monitor] Основной прокси не отвечает!\n\n"
        f"🔄 Бот автоматически переключился на резервное SOCKS5 подключение.\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **❌ Основной прокси** | `{primary_proxy}` |\n"
        f"| **🔄 Резервный прокси** | `{new_proxy}` |\n"
    )

def get_proxy_restored_alert(primary_proxy):
    return (
        f"# ✅ Proxy Restored\n"
        f"---\n\n"
        f"### ✅ [Proxy Monitor] Основной прокси снова доступен!\n\n"
        f"🔄 Успешно вернулись на основное подключение.\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🔌 Подключение** | `{primary_proxy}` |\n"
        f"| **ℹ️ Статус** | 🟢 В сети (Основной прокси) |\n"
    )
