import datetime
import logging
from core.config import settings
from modules.proxmox.monitor.utils import send_alert_to_admins
from core.messages import get_router_autoblock_alert, get_router_port_alert
from modules.proxmox.monitor.state import lxc_alert_throttle
from modules.router.router import ban_router_ip
from .parser import parse_router_conntrack_line, parse_router_iptables_line
from .helpers import check_is_bot_or_admin
from core.messages.i18n import _

recent_router_violations = {}

async def handle_router_iptables_log_line(line):
    """Обрабатывает распарсенную лог-строку iptables/nftables от роутера."""
    try:
        event = parse_router_iptables_line(line)
        if not event:
            return
            
        src_ip = event['src_ip']
        src_port = event['src_port']
        dst_host = event['dst_host']
        dst_port = event['dst_port']
        proto = event['proto']
        
        # 1. Проверяем, идет ли запрос на чувствительный порт
        is_sensitive = dst_port in settings.monitor_lxc_ports_sensitive
        if not is_sensitive:
            return
            
        # Проверяем белый список IP (с детальной проверкой процессов на хосте)
        if await check_is_bot_or_admin(src_ip, src_port, dst_host, dst_port):
            return
                
        import time as pytime
        curr_time = pytime.time()
        
        # 2. Обработка автоматического бана (Auto-Ban)
        if settings.router_monitor_enable and settings.router_auto_ban:
            if src_ip not in recent_router_violations:
                recent_router_violations[src_ip] = []
            recent_router_violations[src_ip].append(curr_time)
            
            recent_router_violations[src_ip] = [t for t in recent_router_violations[src_ip] if curr_time - t <= 600]
            
            if len(recent_router_violations[src_ip]) >= settings.router_max_violations:
                recent_router_violations[src_ip] = []
                
                success, desc = await ban_router_ip(src_ip, reason=f"Порт {dst_port} ({proto})")
                if success:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    msg = get_router_autoblock_alert(src_ip, dst_host, dst_port, proto, timestamp)
                    
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=_("router", "btn_unblock_ip_router"), callback_data=f"router_unblock:{src_ip}")]
                    ])
                    
                    await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=kb)
                    logging.warning("router_ips_device_automatically_banned_on_router", src_ip)
                    return
            
        # 3. Троттлинг предупреждений
        throttle_key = (f"router_{src_ip}", 'threat', 'sensitive_port', dst_host, dst_port)
        last_alert = lxc_alert_throttle.get(throttle_key, 0)
        if curr_time - last_alert < 15:
            return
        lxc_alert_throttle[throttle_key] = curr_time
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        
        if settings.router_monitor_enable:
            buttons.append([InlineKeyboardButton(text=_("router", "btn_block_ip_router"), callback_data=f"router_block:{src_ip}")])
            
        kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        msg = get_router_port_alert("IPTables", proto, src_ip, src_port, dst_host, dst_port, timestamp)
                
        await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=kb)
        logging.warning("router_ips_device_accessed_sensitive_port", src_ip, dst_host, dst_port)
        
    except Exception as e:
        logging.error("error_processing_router_iptables_log", e)

async def handle_router_conntrack_log_line(line):
    """Обрабатывает распарсенную строку conntrack от роутера."""
    try:
        event = parse_router_conntrack_line(line)
        if not event:
            return
            
        src_ip = event['src_ip']
        src_port = event['src_port']
        dst_host = event['dst_host']
        dst_port = event['dst_port']
        proto = event['proto']
        
        # 1. Проверяем, идет ли запрос на чувствительный порт
        is_sensitive = dst_port in settings.monitor_lxc_ports_sensitive
        if not is_sensitive:
            return
            
        # Проверяем белый список IP (с детальной проверкой процессов на хосте)
        if await check_is_bot_or_admin(src_ip, src_port, dst_host, dst_port):
            return
                
        import time as pytime
        curr_time = pytime.time()
        
        # 2. Обработка автоматического бана (Auto-Ban)
        if settings.router_monitor_enable and settings.router_auto_ban:
            if src_ip not in recent_router_violations:
                recent_router_violations[src_ip] = []
            recent_router_violations[src_ip].append(curr_time)
            
            recent_router_violations[src_ip] = [t for t in recent_router_violations[src_ip] if curr_time - t <= 600]
            
            if len(recent_router_violations[src_ip]) >= settings.router_max_violations:
                recent_router_violations[src_ip] = []
                
                success, desc = await ban_router_ip(src_ip, reason=f"Порт {dst_port} ({proto})")
                if success:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    msg = get_router_autoblock_alert(src_ip, dst_host, dst_port, proto, timestamp)
                    
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=_("router", "btn_unblock_ip_router"), callback_data=f"router_unblock:{src_ip}")]
                    ])
                    
                    await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=kb)
                    logging.warning("router_ips_device_automatically_banned_on_router", src_ip)
                    return
            
        # 3. Троттлинг предупреждений
        throttle_key = (f"router_{src_ip}", 'threat', 'sensitive_port', dst_host, dst_port)
        last_alert = lxc_alert_throttle.get(throttle_key, 0)
        if curr_time - last_alert < 15:
            return
        lxc_alert_throttle[throttle_key] = curr_time
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        
        if settings.router_monitor_enable:
            buttons.append([InlineKeyboardButton(text=_("router", "btn_block_ip_router"), callback_data=f"router_block:{src_ip}")])
            
        kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        msg = get_router_port_alert("Conntrack", proto, src_ip, src_port, dst_host, dst_port, timestamp)
                
        await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=kb)
        logging.warning("router_ips_conntrack_device_accessed_sensitive_port", src_ip, dst_host, dst_port)
        
    except Exception as e:
        logging.error("error_processing_router_conntrack_log", e)
