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


async def _process_router_event(event_type: str, event: dict):
    """Общий обработчик сетевых событий роутера с поведенческим анализом от Go-ядра."""
    src_ip = event['src_ip']
    src_port = event['src_port']
    dst_host = event['dst_host']
    dst_port = event['dst_port']
    proto = event['proto']

    # Ядро sentinel-core выполняет поведенческий анализ (сканирование, брутфорс, эксплойт-порты)
    is_threat = event.get('is_threat', False)
    should_autoban = event.get('should_autoban', False)
    reason = event.get('reason') or f"Порт {dst_port} ({proto})"

    if not is_threat:
        return

    # Проверяем, заблокирован ли уже этот IP полностью или точечно для этого порта на роутере
    from core.db import execute_read_one
    full_ban = await execute_read_one("SELECT 1 FROM temp_bans WHERE server_ip = 'router' AND dst_ip = ?", (src_ip,))
    if full_ban:
        return
    port_ban = await execute_read_one("SELECT 1 FROM temp_port_bans WHERE server_ip = 'router' AND client_ip = ? AND port = ? AND protocol = ?", (src_ip, dst_port, proto.lower()))
    if port_ban:
        return

    # Проверяем системные процессы самого бота на хосте (чтобы бот не блокировал свои SSH-опросы роутера/серверов)
    if await check_is_bot_or_admin(src_ip, src_port, dst_host, dst_port):
        return

    import time as pytime
    curr_time = pytime.time()

    # 1. Автоматический бан при подтвержденной угрозе от ядра
    if settings.router_monitor_enable and settings.router_auto_ban and should_autoban:
        success, desc = await ban_router_ip(src_ip, reason=reason)
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

    # 2. Троттлинг предупреждений
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
    msg = get_router_port_alert(event_type, proto, src_ip, src_port, dst_host, dst_port, timestamp)

    await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=kb)
    logging.warning(f"router_ips_{event_type.lower()}_device_accessed_sensitive_port", src_ip, dst_host, dst_port)


async def handle_router_iptables_log_line(line: str):
    """Обрабатывает распарсенную лог-строку iptables/nftables от роутера через Go-ядро."""
    try:
        event = parse_router_iptables_line(line)
        if not event:
            return
        await _process_router_event("IPTables", event)
    except Exception as e:
        logging.error("error_processing_router_iptables_log", e)


async def handle_router_conntrack_log_line(line: str):
    """Обрабатывает распарсенную строку conntrack от роутера через Go-ядро."""
    try:
        event = parse_router_conntrack_line(line)
        if not event:
            return
        await _process_router_event("Conntrack", event)
    except Exception as e:
        logging.error("error_processing_router_conntrack_log", e)

