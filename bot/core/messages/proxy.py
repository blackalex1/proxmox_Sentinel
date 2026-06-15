# bot/core/messages/proxy.py
"""Шаблоны сообщений для мониторинга прокси на GFM Markdown с поддержкой i18n."""

from core.messages.i18n import _

def get_proxy_switch_alert(primary_proxy, new_proxy):
    return _(
        "proxy", "proxy_switch_alert",
        primary_proxy=primary_proxy, new_proxy=new_proxy
    )

def get_proxy_restored_alert(primary_proxy):
    return _(
        "proxy", "proxy_restored_alert",
        primary_proxy=primary_proxy
    )
