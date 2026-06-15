# bot/core/messages/router.py
"""Шаблоны сообщений для мониторинга роутера на GFM Markdown с поддержкой i18n."""

from core.config import settings
from core.messages.i18n import _

def get_router_recovery_alert(ip, rules_str):
    return _(
        "router", "router_recovery_alert",
        ip=ip, rules_str=rules_str
    )

def get_router_unknown_block_alert(ip, rules_str):
    return _(
        "router", "router_unknown_block_alert",
        ip=ip, rules_str=rules_str
    )

def get_router_autoblock_alert(src_ip, dst_host, dst_port, proto, timestamp):
    return _(
        "router", "router_autoblock_alert",
        src_ip=src_ip, dst_host=dst_host, dst_port=dst_port,
        proto=proto, timestamp=timestamp, threshold=settings.router_max_violations
    )

def get_router_port_alert(type_str, proto, src_ip, src_port, dst_host, dst_port, timestamp):
    return _(
        "router", "router_port_alert",
        type_str=type_str, proto=proto, src_ip=src_ip,
        src_port=src_port, dst_host=dst_host, dst_port=dst_port,
        timestamp=timestamp
    )
