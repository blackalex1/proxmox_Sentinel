import datetime
import logging
from core.config import settings
from modules.proxmox.monitor.utils import send_alert_to_admins
from modules.proxmox.monitor.state import lxc_alert_throttle
from modules.mihomo.router import ban_router_ip
from .parser import find_mihomo_connection_id, parse_router_conntrack_line, parse_router_iptables_line
from .helpers import check_is_bot_or_admin

recent_mihomo_violations = {}

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
        if settings.router_ssh_enable and settings.mihomo_auto_ban:
            if src_ip not in recent_mihomo_violations:
                recent_mihomo_violations[src_ip] = []
            recent_mihomo_violations[src_ip].append(curr_time)
            
            recent_mihomo_violations[src_ip] = [t for t in recent_mihomo_violations[src_ip] if curr_time - t <= 600]
            
            if len(recent_mihomo_violations[src_ip]) >= settings.mihomo_max_violations:
                recent_mihomo_violations[src_ip] = []
                
                success, desc = await ban_router_ip(src_ip)
                if success:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🟢 Разблокировать IP на роутере", callback_data=f"mihomo_unblock:{src_ip}")]
                    ])
                    
                    msg = (f"🛑 <b>[Router Security: Auto-Block] Устройство заблокировано автоматически!</b>\n\n"
                           f"👤 <b>Заблокированный IP:</b> <code>{src_ip}</code>\n"
                           f"🎯 <b>Причина:</b> Превышен лимит сетевых нарушений ({settings.mihomo_max_violations}+ попыток доступа к чувствительным портам за 10 минут).\n"
                           f"🧭 <b>Последняя цель:</b> <code>{dst_host}:{dst_port}</code> ({proto})\n"
                           f"🕒 <b>Время блокировки:</b> <code>{timestamp}</code>")
                            
                    await send_alert_to_admins(msg, reply_markup=kb)
                    logging.warning(f"[Router IPS] Устройство {src_ip} автоматически забанено на роутере!")
                    return
            
        # 3. Троттлинг предупреждений
        throttle_key = (f"router_{src_ip}", 'threat', 'sensitive_port', dst_host, dst_port)
        last_alert = lxc_alert_throttle.get(throttle_key, 0)
        if curr_time - last_alert < 15:
            return
        lxc_alert_throttle[throttle_key] = curr_time
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        
        conn_id = None
        if settings.mihomo_monitor_enable:
            conn_id = await find_mihomo_connection_id(src_ip, src_port, dst_port)
            if conn_id:
                buttons.append([InlineKeyboardButton(text="⚡️ Разорвать соединение", callback_data=f"mihomo_kill:{conn_id}")])
                
        if settings.router_ssh_enable:
            buttons.append([InlineKeyboardButton(text="🛑 Заблокировать IP на роутере", callback_data=f"mihomo_block:{src_ip}")])
            
        kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        msg = (f"🚨 <b>[Router Security: IPTables] Обнаружен доступ к чувствительному порту!</b>\n\n"
               f"🌐 Протокол: <code>{proto}</code>\n"
               f"👤 Устройство (Источник): <code>{src_ip}:{src_port}</code>\n"
               f"🎯 Назначение: <code>{dst_host}:{dst_port}</code>\n"
               f"🕒 Время: <code>{timestamp}</code>")
                
        await send_alert_to_admins(msg, reply_markup=kb)
        logging.warning(f"[Router IPS] Устройство {src_ip} обратилось к чувствительному порту {dst_host}:{dst_port}")
        
    except Exception as e:
        logging.error(f"Ошибка при обработке лога iptables роутера: {e}")

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
        if settings.router_ssh_enable and settings.mihomo_auto_ban:
            if src_ip not in recent_mihomo_violations:
                recent_mihomo_violations[src_ip] = []
            recent_mihomo_violations[src_ip].append(curr_time)
            
            recent_mihomo_violations[src_ip] = [t for t in recent_mihomo_violations[src_ip] if curr_time - t <= 600]
            
            if len(recent_mihomo_violations[src_ip]) >= settings.mihomo_max_violations:
                recent_mihomo_violations[src_ip] = []
                
                success, desc = await ban_router_ip(src_ip)
                if success:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🟢 Разблокировать IP на роутере", callback_data=f"mihomo_unblock:{src_ip}")]
                    ])
                    
                    msg = (f"🛑 <b>[Router Security: Auto-Block] Устройство заблокировано автоматически!</b>\n\n"
                           f"👤 <b>Заблокированный IP:</b> <code>{src_ip}</code>\n"
                           f"🎯 <b>Причина:</b> Превышен лимит сетевых нарушений ({settings.mihomo_max_violations}+ попыток доступа к чувствительным портам за 10 минут).\n"
                           f"🧭 <b>Последняя цель:</b> <code>{dst_host}:{dst_port}</code> ({proto})\n"
                           f"🕒 <b>Время блокировки:</b> <code>{timestamp}</code>")
                            
                    await send_alert_to_admins(msg, reply_markup=kb)
                    logging.warning(f"[Router IPS] Устройство {src_ip} автоматически забанено на роутере!")
                    return
            
        # 3. Троттлинг предупреждений
        throttle_key = (f"router_{src_ip}", 'threat', 'sensitive_port', dst_host, dst_port)
        last_alert = lxc_alert_throttle.get(throttle_key, 0)
        if curr_time - last_alert < 15:
            return
        lxc_alert_throttle[throttle_key] = curr_time
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        
        conn_id = None
        if settings.mihomo_monitor_enable:
            conn_id = await find_mihomo_connection_id(src_ip, src_port, dst_port)
            if conn_id:
                buttons.append([InlineKeyboardButton(text="⚡️ Разорвать соединение", callback_data=f"mihomo_kill:{conn_id}")])
                
        if settings.router_ssh_enable:
            buttons.append([InlineKeyboardButton(text="🛑 Заблокировать IP на роутере", callback_data=f"mihomo_block:{src_ip}")])
            
        kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        msg = (f"🚨 <b>[Router Security: Conntrack] Обнаружен доступ к чувствительному порту!</b>\n\n"
               f"🌐 Протокол: <code>{proto}</code>\n"
               f"👤 Устройство (Источник): <code>{src_ip}:{src_port}</code>\n"
               f"🎯 Назначение: <code>{dst_host}:{dst_port}</code>\n"
               f"🕒 Время: <code>{timestamp}</code>")
                
        await send_alert_to_admins(msg, reply_markup=kb)
        logging.warning(f"[Router IPS: Conntrack] Устройство {src_ip} обратилось к чувствительному порту {dst_host}:{dst_port}")
        
    except Exception as e:
        logging.error(f"Ошибка при обработке лога conntrack роутера: {e}")
