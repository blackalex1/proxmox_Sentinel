from aiogram import Router, F, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import re

from .router import (
    ban_router_ip,
    unban_router_ip,
    get_router_clients,
    ban_router_port,
    unban_router_port
)
from core.db import execute_read_all, execute_read_one
from core.messages.i18n import _
from core.messages import (
    get_router_clients_list_text,
    get_router_client_details_card,
    get_router_ban_all_menu_text,
    get_router_ban_port_menu_text,
    get_router_ban_port_duration_text,
    get_router_custom_port_prompt_text,
    get_router_active_bans_text
)
from core.sender import edit_rich_message, send_rich_message

router = Router()

class RouterPortControlState(StatesGroup):
    waiting_for_custom_port = State()

# --- Вспомогательные функции рендеринга интерфейса ---

async def render_clients_list():
    clients = await get_router_clients()
    text = get_router_clients_list_text(bool(clients))
    
    kb_buttons = []
    if clients:
        for c in clients:
            status_emoji = "🟢" if c.get('active') else "⚪"
            hostname = c.get('hostname', 'Unknown')
            ip = c.get('ip')
            kb_buttons.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {hostname} ({ip})",
                    callback_data=f"r_cl:{ip}"
                )
            ])
            
    kb_buttons.append([
        InlineKeyboardButton(text=_("keyboards", "btn_refresh", "🔄 Обновить список"), callback_data="r_list")
    ])
    kb_buttons.append([
        InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu", "Главное меню"), callback_data="main_menu")
    ])
    
    return text, InlineKeyboardMarkup(inline_keyboard=kb_buttons)


async def render_client_details(ip: str):
    clients = await get_router_clients()
    client = next((c for c in clients if c['ip'] == ip), None)
    
    hostname = client['hostname'] if client else 'Unknown'
    mac = client['mac'] if client else 'Unknown'
    active = client['active'] if client else False
    
    # Проверяем наличие полной блокировки
    full_ban = await execute_read_one("SELECT * FROM temp_bans WHERE server_ip = 'router' AND dst_ip = ?", (ip,))
    # Проверяем наличие блокировок портов
    port_bans = await execute_read_all("SELECT * FROM temp_port_bans WHERE server_ip = 'router' AND client_ip = ?", (ip,))
    
    bans_count = (1 if full_ban else 0) + len(port_bans)
    text = get_router_client_details_card(hostname, ip, mac, active, full_ban, port_bans)
    
    kb_buttons = []
    
    if not full_ban:
        kb_buttons.append([
            InlineKeyboardButton(text=_("router", "btn_ban_all_full", "🛑 Заблокировать полностью"), callback_data=f"r_ban_all_menu:{ip}")
        ])
    else:
        kb_buttons.append([
            InlineKeyboardButton(text=_("router", "btn_unban_all_full", "🟢 Разблокировать полностью"), callback_data=f"r_unban_all:{ip}")
        ])
        
    kb_buttons.append([
        InlineKeyboardButton(text=_("router", "btn_ban_port_menu", "🔒 Заблокировать порт/сервис"), callback_data=f"r_ban_port_menu:{ip}")
    ])
    
    if bans_count > 0:
        kb_buttons.append([
            InlineKeyboardButton(text=_("router", "btn_manage_bans", "🔎 Управление блокировками ({count})", count=bans_count), callback_data=f"r_bans:{ip}")
        ])
        
    kb_buttons.append([
        InlineKeyboardButton(text=_("router", "btn_back_to_clients", "🔙 Назад к списку клиентов"), callback_data="r_list")
    ])
    
    return text, InlineKeyboardMarkup(inline_keyboard=kb_buttons)


# --- Стандартные команды и хэндлеры ---

@router.message(Command("router"))
async def cmd_router_clients(message: types.Message, state: FSMContext):
    """Выводит интерактивный список клиентов роутера."""
    await state.clear()
    text, kb = await render_clients_list()
    await send_rich_message(chat_id=message.chat.id, text=text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "r_list")
async def cb_router_list(callback: CallbackQuery, state: FSMContext):
    """Обновляет или открывает список клиентов."""
    await state.clear()
    text, kb = await render_clients_list()
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_cl:"))
async def cb_router_client_details(callback: CallbackQuery, state: FSMContext):
    """Открывает детальное меню управления клиентом."""
    await state.clear()
    ip = callback.data.split(":")[1]
    text, kb = await render_client_details(ip)
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# --- Управление полными блокировками (выбор времени) ---

@router.callback_query(F.data.startswith("r_ban_all_menu:"))
async def cb_router_ban_all_menu(callback: CallbackQuery):
    ip = callback.data.split(":")[1]
    text = get_router_ban_all_menu_text(ip)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("router", "dur_1_hour", "1 час"), callback_data=f"r_ban_all:{ip}:3600")],
        [InlineKeyboardButton(text=_("router", "dur_1_day", "1 день"), callback_data=f"r_ban_all:{ip}:86400")],
        [InlineKeyboardButton(text=_("router", "dur_1_week", "1 неделя"), callback_data=f"r_ban_all:{ip}:604800")],
        [InlineKeyboardButton(text=_("router", "dur_forever", "Навсегда"), callback_data=f"r_ban_all:{ip}:315360000")],
        [InlineKeyboardButton(text=_("keyboards", "btn_back", "🔙 Назад"), callback_data=f"r_cl:{ip}")]
    ])
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_ban_all:"))
async def cb_router_ban_all_action(callback: CallbackQuery):
    parts = callback.data.split(":")
    ip = parts[1]
    seconds = int(parts[2])
    
    await callback.answer(_("router", "action_applying_ssh", "Выполняю блокировку по SSH..."), show_alert=False)
    success, desc = await ban_router_ip(ip, delay=seconds, reason="Вручную из TG")
    if success:
        await callback.answer(_("router", "ip_blocked_successfully", ip=ip), show_alert=True)
    else:
        await callback.answer(_("router", "ip_block_failed", desc=desc), show_alert=True)
        
    text, kb = await render_client_details(ip)
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")


# --- Управление точечными блокировками портов ---

@router.callback_query(F.data.startswith("r_ban_port_menu:"))
async def cb_router_ban_port_menu(callback: CallbackQuery):
    ip = callback.data.split(":")[1]
    text = get_router_ban_port_menu_text(ip)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=_("router", "btn_web_service", "🌐 Web-браузер (80, 443)"), callback_data=f"r_ban_port_dur:{ip}:80_443:tcp"),
        ],
        [
            InlineKeyboardButton(text=_("router", "btn_ssh_service", "💻 SSH консоль (22)"), callback_data=f"r_ban_port_dur:{ip}:22:tcp"),
        ],
        [
            InlineKeyboardButton(text=_("router", "btn_dns_service", "👥 DNS запросы (53)"), callback_data=f"r_ban_port_dur:{ip}:53:udp"),
        ],
        [
            InlineKeyboardButton(text=_("router", "btn_custom_port", "✏️ Ввести порт вручную..."), callback_data=f"r_custom_port:{ip}")
        ],
        [
            InlineKeyboardButton(text=_("keyboards", "btn_back", "🔙 Назад"), callback_data=f"r_cl:{ip}")
        ]
    ])
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_ban_port_dur:"))
async def cb_router_ban_port_duration_menu(callback: CallbackQuery):
    parts = callback.data.split(":")
    ip = parts[1]
    port = parts[2]
    proto = parts[3]
    
    port_label = port.replace("_", ", ")
    text = get_router_ban_port_duration_text(ip, port_label, proto)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("router", "dur_1_hour", "1 час"), callback_data=f"r_ban_port:{ip}:{port}:{proto}:3600")],
        [InlineKeyboardButton(text=_("router", "dur_1_day", "1 день"), callback_data=f"r_ban_port:{ip}:{port}:{proto}:86400")],
        [InlineKeyboardButton(text=_("router", "dur_1_week", "1 неделя"), callback_data=f"r_ban_port:{ip}:{port}:{proto}:604800")],
        [InlineKeyboardButton(text=_("router", "dur_forever", "Навсегда"), callback_data=f"r_ban_port:{ip}:{port}:{proto}:315360000")],
        [InlineKeyboardButton(text=_("keyboards", "btn_back", "🔙 Назад"), callback_data=f"r_ban_port_menu:{ip}")]
    ])
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_ban_port:"))
async def cb_router_ban_port_action(callback: CallbackQuery):
    parts = callback.data.split(":")
    ip = parts[1]
    port_raw = parts[2]
    proto = parts[3]
    seconds = int(parts[4])
    
    await callback.answer(_("router", "action_banning_port_ssh", "Добавляю правила блокировки порта по SSH..."), show_alert=False)
    
    ports = port_raw.split("_")
    success_all = True
    errors = []
    
    for p in ports:
        success, desc = await ban_router_port(ip, int(p), proto=proto, delay=seconds, reason="Вручную из TG")
        if not success:
            success_all = False
            errors.append(desc)
            
    port_label = port_raw.replace("_", ", ")
    if success_all:
        await callback.answer(_("router", "port_blocked_success", port=port_label, proto=proto), show_alert=True)
    else:
        err_msg = ", ".join(errors)
        await callback.answer(_("router", "ip_block_failed", desc=err_msg), show_alert=True)
        
    text, kb = await render_client_details(ip)
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")


# --- Ввод пользовательского порта вручную (FSM) ---

@router.callback_query(F.data.startswith("r_custom_port:"))
async def cb_router_custom_port_prompt(callback: CallbackQuery, state: FSMContext):
    ip = callback.data.split(":")[1]
    await state.update_data(ip=ip)
    await state.set_state(RouterPortControlState.waiting_for_custom_port)
    
    text = get_router_custom_port_prompt_text(ip)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("keyboards", "btn_cancel", "❌ Отмена"), callback_data=f"r_ban_port_menu:{ip}")]
    ])
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.message(RouterPortControlState.waiting_for_custom_port)
async def process_custom_port_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ip = data.get("ip")
    if not ip:
        await send_rich_message(chat_id=message.chat.id, text=_("router", "err_session_lost"))
        await state.clear()
        return
        
    text_input = message.text.strip().lower()
    proto = 'tcp'
    port_str = text_input
    
    if '/' in text_input:
        parts = text_input.split('/')
        port_str = parts[0].strip()
        proto = parts[1].strip()
        
    if proto not in ('tcp', 'udp'):
        await send_rich_message(chat_id=message.chat.id, text=_("router", "err_invalid_proto"))
        return
        
    if not port_str.isdigit():
        await send_rich_message(chat_id=message.chat.id, text=_("router", "err_invalid_port"))
        return
        
    port = int(port_str)
    if not (1 <= port <= 65535):
        await send_rich_message(chat_id=message.chat.id, text=_("router", "err_invalid_port"))
        return
        
    await state.clear()
    
    text = get_router_ban_port_duration_text(ip, str(port), proto)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("router", "dur_1_hour", "1 час"), callback_data=f"r_ban_port:{ip}:{port}:{proto}:3600")],
        [InlineKeyboardButton(text=_("router", "dur_1_day", "1 день"), callback_data=f"r_ban_port:{ip}:{port}:{proto}:86400")],
        [InlineKeyboardButton(text=_("router", "dur_1_week", "1 неделя"), callback_data=f"r_ban_port:{ip}:{port}:{proto}:604800")],
        [InlineKeyboardButton(text=_("router", "dur_forever", "Навсегда"), callback_data=f"r_ban_port:{ip}:{port}:{proto}:315360000")],
        [InlineKeyboardButton(text=_("keyboards", "btn_cancel", "🔙 Отмена"), callback_data=f"r_cl:{ip}")]
    ])
    
    await send_rich_message(chat_id=message.chat.id, text=text, reply_markup=kb, parse_mode="HTML")


# --- Управление активными блокировками устройства ---

@router.callback_query(F.data.startswith("r_bans:"))
async def cb_router_active_bans_list(callback: CallbackQuery):
    ip = callback.data.split(":")[1]
    
    full_ban = await execute_read_one("SELECT * FROM temp_bans WHERE server_ip = 'router' AND dst_ip = ?", (ip,))
    port_bans = await execute_read_all("SELECT * FROM temp_port_bans WHERE server_ip = 'router' AND client_ip = ?", (ip,))
    
    text = get_router_active_bans_text(ip, full_ban, port_bans)
    
    kb_buttons = []
    if full_ban:
        kb_buttons.append([
            InlineKeyboardButton(text=_("router", "btn_unban_all_action", "🟢 Снять полную блокировку"), callback_data=f"r_unban_all:{ip}")
        ])
        
    for pb in port_bans:
        p = pb['port']
        proto = pb['protocol']
        kb_buttons.append([
            InlineKeyboardButton(text=_("router", "btn_unban_port_action", f"❌ Снять блок {p}/{proto}", port=p, proto=proto), callback_data=f"r_unban_port:{ip}:{p}:{proto}")
        ])
        
    kb_buttons.append([
        InlineKeyboardButton(text=_("keyboards", "btn_back", "🔙 Назад"), callback_data=f"r_cl:{ip}")
    ])
    
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_unban_all:"))
async def cb_router_unban_all_action(callback: CallbackQuery):
    ip = callback.data.split(":")[1]
    
    await callback.answer(_("router", "action_unbanning_ssh", "Снимаю блокировку по SSH..."), show_alert=False)
    success, desc = await unban_router_ip(ip)
    if success:
        await callback.answer(_("router", "ip_unblocked_successfully", ip=ip), show_alert=True)
    else:
        await callback.answer(_("router", "ip_unblock_failed", desc=desc), show_alert=True)
        
    text, kb = await render_client_details(ip)
    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("r_unban_port:"))
async def cb_router_unban_port_action(callback: CallbackQuery):
    parts = callback.data.split(":")
    ip = parts[1]
    port = int(parts[2])
    proto = parts[3]
    
    await callback.answer(_("router", "action_unbanning_port_ssh", f"Снимаю блокировку порта {port}/{proto} по SSH...", port=port, proto=proto), show_alert=False)
    success, desc = await unban_router_port(ip, port, proto)
    if success:
        await callback.answer(_("router", "port_unblocked_success", port=port, proto=proto), show_alert=True)
    else:
        await callback.answer(_("router", "ip_unblock_failed", desc=desc), show_alert=True)
        
    full_ban = await execute_read_one("SELECT * FROM temp_bans WHERE server_ip = 'router' AND dst_ip = ?", (ip,))
    port_bans = await execute_read_all("SELECT * FROM temp_port_bans WHERE server_ip = 'router' AND client_ip = ?", (ip,))
    
    if full_ban or port_bans:
        await cb_router_active_bans_list(callback)
    else:
        text, kb = await render_client_details(ip)
        await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=text, reply_markup=kb, parse_mode="HTML")


# --- Сохраняем обратную совместимость для системных алертов ---

@router.callback_query(F.data.startswith("router_block:"))
async def handle_router_block_ip(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer(_("router", "invalid_data_format"), show_alert=True)
            return
            
        ip = parts[1]
        success, desc = await ban_router_ip(ip)
        if success:
            await callback.answer(_("router", "ip_blocked_successfully", ip=ip), show_alert=True)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("router", "btn_unblock_ip_router"), callback_data=f"router_unblock:{ip}")]
            ])
            text = callback.message.text
            if text:
                if "🛑 УСТРОЙСТВО " not in text and "🛑 DEVICE " not in text:
                    new_text = text + _("router", "device_blocked_text", ip=ip)
                    try:
                        await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=new_text, reply_markup=kb, parse_mode="HTML")
                    except Exception as e:
                        logging.error("failed_to_edit_message_on_ban", e)
            else:
                try:
                    await callback.message.edit_reply_markup(reply_markup=kb)
                except Exception as e:
                    logging.error("failed_to_change_keyboard_on_ban", e)
        else:
            await callback.answer(_("router", "ip_block_failed", desc=desc), show_alert=True)
    except Exception as e:
        logging.error("error_in_router_block_callback_handler", e)
        await callback.answer(_("router", "ip_block_error", e=e), show_alert=True)


@router.callback_query(F.data.startswith("router_unblock:"))
async def handle_router_unblock_ip(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer(_("router", "invalid_data_format"), show_alert=True)
            return
            
        ip = parts[1]
        success, desc = await unban_router_ip(ip)
        if success:
            await callback.answer(_("router", "ip_unblocked_successfully", ip=ip), show_alert=True)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("router", "btn_block_ip_router"), callback_data=f"router_block:{ip}")]
            ])
            text = callback.message.text
            if text:
                new_text = text.replace(f"\n\n🛑 <b>УСТРОЙСТВО {ip} ЗАБЛОКИРОВАНО НА РОУТЕРЕ!</b>", "")
                new_id = new_text.replace(f"\n\n🛑 <b>DEVICE {ip} BLOCKED ON ROUTER!</b>", "")
                try:
                    await edit_rich_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=new_id, reply_markup=kb, parse_mode="HTML")
                except Exception as e:
                    logging.error("failed_to_edit_message_on_unban", e)
            else:
                try:
                    await callback.message.edit_reply_markup(reply_markup=kb)
                except Exception as e:
                    logging.error("failed_to_change_keyboard_on_unban", e)
        else:
            await callback.answer(_("router", "ip_unblock_failed", desc=desc), show_alert=True)
    except Exception as e:
        logging.error("error_in_router_unblock_callback_handler", e)
        await callback.answer(_("router", "ip_unblock_error", e=e), show_alert=True)
