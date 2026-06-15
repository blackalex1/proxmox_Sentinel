import asyncio
import logging
from core.config import settings
from .ssh_workers import monitor_router_conntrack, monitor_router_syslog

async def monitor_router_connections():
    """Фоновый воркер для мониторинга трафика роутера через SSH conntrack/iptables."""
    mode = getattr(settings, 'router_monitor_mode', 'conntrack').lower()
    
    if not settings.router_monitor_enable:
        return
        
    if mode == 'conntrack':
        await monitor_router_conntrack()
        return
        
    if mode == 'iptables':
        await monitor_router_syslog()
        return

    logging.error("router_monitor_unknown_traffic_monitoring_mode", mode)



