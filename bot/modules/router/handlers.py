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

router = Router()

class RouterPortControlState(StatesGroup):
    waiting_for_custom_port = State()

# --- Вспомогательные функции рендеринга интерфейса ---

async def render_clients_list():
    clients = await get_router_clients()
    
    text = "🖥 <b>Клиенты вашего роутера:</b>\n"
    text += "Выберите устройство из списка ниже для управления блокировками.\n\n"
    
    kb_buttons = []
    if not clients:
        text += "⚠️ Устройства не найдены или мониторинг роутера отключен в конфигурации."
    else:
        for c in clients:
            status_emoji = "🟢" if c.get('active') else "⚪"
            hostname = c.get('hostname', 'Неизвестно')
            ip = c.get('ip')
            kb_buttons.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {hostname} ({ip})",
                    callback_data=f"r_cl:{ip}"
                )
            ])
            
    kb_buttons.append([
        InlineKeyboardButton(text="🔄 Обновить список", callback_data="r_list")
    ])
    kb_buttons.append([
        InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu", "Главное меню"), callback_data="main_menu")
    ])
    
    return text, InlineKeyboardMarkup(inline_keyboard=kb_buttons)


async def render_client_details(ip: str):
    clients = await get_router_clients()
    client = next((c for c in clients if c['ip'] == ip), None)
    
    hostname = client['hostname'] if client else 'Неизвестно'
    mac = client['mac'] if client else 'Неизвестно'
    active = client['active'] if client else False
    
    # Проверяем наличие полной блокировки
    full_ban = await execute_read_one("SELECT * FROM temp_bans WHERE server_ip = 'router' AND dst_ip = ?", (ip,))
    # Проверяем наличие блокировок портов
    port_bans = await execute_read_all("SELECT * FROM temp_port_bans WHERE server_ip = 'router' AND client_ip = ?", (ip,))
    
    bans_count = (1 if full_ban else 0) + len(port_bans)
    
    status_emoji = "🟢 Активен" if active else "⚪ Офлайн"
    ban_status = "🛑 Заблокирован полностью" if full_ban else ("🔒 Есть блокировки портов" if port_bans else "🟢 Доступ разрешен")
    
    text = (
        f"🖥 <b>Управление клиентом роутера</b>\n"
        f"-----------------------------\n"
        f"<b>Имя устройства:</b> <code>{hostname}</code>\n"
        f"<b>IP-адрес:</b> <code>{ip}</code>\n"
        f"<b>MAC-адрес:</b> <code>{mac}</code>\n"
        f"<b>Статус сети:</b> {status_emoji}\n"
        f"<b>Статус блокировки:</b> {ban_status}\n\n"
        f"🔒 Всего активных правил блокировки: <b>{bans_count}</b>"
    )
    
    kb_buttons = []
    
    if not full_ban:
        kb_buttons.append([
            InlineKeyboardButton(text="🛑 Заблокировать полностью", callback_data=f"r_ban_all_menu:{ip}")
        ])
    else:
        kb_buttons.append([
            InlineKeyboardButton(text="🟢 Разблокировать полностью", callback_data=f"r_unban_all:{ip}")
        ])
        
    kb_buttons.append([
        InlineKeyboardButton(text="🔒 Заблокировать порт/сервис", callback_data=f"r_ban_port_menu:{ip}")
    ])
    
    if bans_count > 0:
        kb_buttons.append([
            InlineKeyboardButton(text=f"🔎 Управление блокировками ({bans_count})", callback_data=f"r_bans:{ip}")
        ])
        
    kb_buttons.append([
        InlineKeyboardButton(text="🔙 Назад к списку клиентов", callback_data="r_list")
    ])
    
    return text, InlineKeyboardMarkup(inline_keyboard=kb_buttons)


# --- Стандартные команды и хэндлеры ---

@router.message(Command("router"))
async def cmd_router_clients(message: types.Message, state: FSMContext):
    """Выводит интерактивный список клиентов роутера."""
    await state.clear()
    text, kb = await render_clients_list()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "r_list")
async def cb_router_list(callback: CallbackQuery, state: FSMContext):
    """Обновляет или открывает список клиентов."""
    await state.clear()
    text, kb = await render_clients_list()
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_cl:"))
async def cb_router_client_details(callback: CallbackQuery, state: FSMContext):
    """Открывает детальное меню управления клиентом."""
    await state.clear()
    ip = callback.data.split(":")[1]
    text, kb = await render_client_details(ip)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# --- Управление полными блокировками (выбор времени) ---

@router.callback_query(F.data.startswith("r_ban_all_menu:"))
async def cb_router_ban_all_menu(callback: CallbackQuery):
    ip = callback.data.split(":")[1]
    text = f"⌛️ <b>Выберите длительность полной блокировки для устройства {ip}:</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 час", callback_data=f"r_ban_all:{ip}:3600")],
        [InlineKeyboardButton(text="1 день", callback_data=f"r_ban_all:{ip}:86400")],
        [InlineKeyboardButton(text="1 неделя", callback_data=f"r_ban_all:{ip}:604800")],
        [InlineKeyboardButton(text="Навсегда", callback_data=f"r_ban_all:{ip}:315360000")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"r_cl:{ip}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_ban_all:"))
async def cb_router_ban_all_action(callback: CallbackQuery):
    parts = callback.data.split(":")
    ip = parts[1]
    seconds = int(parts[2])
    
    await callback.answer("Выполняю блокировку по SSH...", show_alert=False)
    success, desc = await ban_router_ip(ip, delay=seconds, reason="Вручную из TG")
    if success:
        await callback.answer(f"Устройство {ip} полностью заблокировано!", show_alert=True)
    else:
        await callback.answer(f"Ошибка блокировки: {desc}", show_alert=True)
        
    text, kb = await render_client_details(ip)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# --- Управление точечными блокировками портов ---

@router.callback_query(F.data.startswith("r_ban_port_menu:"))
async def cb_router_ban_port_menu(callback: CallbackQuery):
    ip = callback.data.split(":")[1]
    text = f"🔒 <b>Выберите порт или сервис для блокировки устройства {ip}:</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Web-браузер (80, 443)", callback_data=f"r_ban_port_dur:{ip}:80_443:tcp"),
        ],
        [
            InlineKeyboardButton(text="💻 SSH консоль (22)", callback_data=f"r_ban_port_dur:{ip}:22:tcp"),
        ],
        [
            InlineKeyboardButton(text="👥 DNS запросы (53)", callback_data=f"r_ban_port_dur:{ip}:53:udp"),
        ],
        [
            InlineKeyboardButton(text="✏️ Ввести порт вручную...", callback_data=f"r_custom_port:{ip}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data=f"r_cl:{ip}")
        ]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_ban_port_dur:"))
async def cb_router_ban_port_duration_menu(callback: CallbackQuery):
    parts = callback.data.split(":")
    ip = parts[1]
    port = parts[2]
    proto = parts[3]
    
    port_label = port.replace("_", ", ")
    text = f"⌛️ <b>Выберите длительность блокировки портов {port_label}/{proto} для устройства {ip}:</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 час", callback_data=f"r_ban_port:{ip}:{port}:{proto}:3600")],
        [InlineKeyboardButton(text="1 день", callback_data=f"r_ban_port:{ip}:{port}:{proto}:86400")],
        [InlineKeyboardButton(text="1 неделя", callback_data=f"r_ban_port:{ip}:{port}:{proto}:604800")],
        [InlineKeyboardButton(text="Навсегда", callback_data=f"r_ban_port:{ip}:{port}:{proto}:315360000")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"r_ban_port_menu:{ip}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_ban_port:"))
async def cb_router_ban_port_action(callback: CallbackQuery):
    parts = callback.data.split(":")
    ip = parts[1]
    port_raw = parts[2]
    proto = parts[3]
    seconds = int(parts[4])
    
    await callback.answer("Добавляю правила блокировки порта по SSH...", show_alert=False)
    
    ports = port_raw.split("_")
    success_all = True
    errors = []
    
    for p in ports:
        success, desc = await ban_router_port(ip, int(p), proto=proto, delay=seconds, reason="Вручную из TG")
        if not success:
            success_all = False
            errors.append(desc)
            
    if success_all:
        port_label = port_raw.replace("_", ", ")
        await callback.answer(f"Порт {port_label}/{proto} успешно заблокирован!", show_alert=True)
    else:
        err_msg = ", ".join(errors)
        await callback.answer(f"Ошибка при блокировке: {err_msg}", show_alert=True)
        
    text, kb = await render_client_details(ip)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# --- Ввод пользовательского порта вручную (FSM) ---

@router.callback_query(F.data.startswith("r_custom_port:"))
async def cb_router_custom_port_prompt(callback: CallbackQuery, state: FSMContext):
    ip = callback.data.split(":")[1]
    await state.update_data(ip=ip)
    await state.set_state(RouterPortControlState.waiting_for_custom_port)
    
    text = (
        f"✏️ <b>Блокировка порта для устройства {ip}</b>\n\n"
        f"Введите номер порта или порт/протокол (например: <code>80</code>, <code>53/udp</code>, <code>8080/tcp</code>):"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"r_ban_port_menu:{ip}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.message(RouterPortControlState.waiting_for_custom_port)
async def process_custom_port_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ip = data.get("ip")
    if not ip:
        await message.answer("❌ Ошибка: сессия утеряна. Начните заново с команды /router")
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
        await message.reply("❌ Неверный протокол. Укажите tcp или udp (например, 80/tcp или 53/udp)")
        return
        
    if not port_str.isdigit():
        await message.reply("❌ Порт должен быть числом от 1 до 65535.")
        return
        
    port = int(port_str)
    if not (1 <= port <= 65535):
        await message.reply("❌ Порт должен быть в диапазоне от 1 до 65535.")
        return
        
    await state.clear()
    
    text = (
        f"⌛️ <b>Выберите длительность блокировки порта {port}/{proto} для устройства {ip}:</b>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 час", callback_data=f"r_ban_port:{ip}:{port}:{proto}:3600")],
        [InlineKeyboardButton(text="1 день", callback_data=f"r_ban_port:{ip}:{port}:{proto}:86400")],
        [InlineKeyboardButton(text="1 неделя", callback_data=f"r_ban_port:{ip}:{port}:{proto}:604800")],
        [InlineKeyboardButton(text="Навсегда", callback_data=f"r_ban_port:{ip}:{port}:{proto}:315360000")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"r_cl:{ip}")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# --- Управление активными блокировками устройства ---

@router.callback_query(F.data.startswith("r_bans:"))
async def cb_router_active_bans_list(callback: CallbackQuery):
    ip = callback.data.split(":")[1]
    
    full_ban = await execute_read_one("SELECT * FROM temp_bans WHERE server_ip = 'router' AND dst_ip = ?", (ip,))
    port_bans = await execute_read_all("SELECT * FROM temp_port_bans WHERE server_ip = 'router' AND client_ip = ?", (ip,))
    
    text = f"🔎 <b>Активные блокировки для устройства {ip}:</b>\n\n"
    
    kb_buttons = []
    if full_ban:
        expire = full_ban.get('expire_time')
        expire_label = expire.split(".")[0].replace("T", " ") if expire else "never"
        text += f" • <b>Полная блокировка IP</b> (Истекает: {expire_label})\n"
        kb_buttons.append([
            InlineKeyboardButton(text="🟢 Снять полную блокировку", callback_data=f"r_unban_all:{ip}")
        ])
        
    for pb in port_bans:
        p = pb['port']
        proto = pb['protocol']
        expire = pb['expire_time']
        expire_label = expire.split(".")[0].replace("T", " ") if expire and expire != "never" else "Навсегда"
        text += f" • <b>Порт {p}/{proto}</b> (Истекает: {expire_label})\n"
        kb_buttons.append([
            InlineKeyboardButton(text=f"❌ Снять блок {p}/{proto}", callback_data=f"r_unban_port:{ip}:{p}:{proto}")
        ])
        
    if not full_ban and not port_bans:
        text += "Нет активных блокировок для этого устройства."
        
    kb_buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"r_cl:{ip}")
    ])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("r_unban_all:"))
async def cb_router_unban_all_action(callback: CallbackQuery):
    ip = callback.data.split(":")[1]
    
    await callback.answer("Снимаю блокировку по SSH...", show_alert=False)
    success, desc = await unban_router_ip(ip)
    if success:
        await callback.answer(f"Полная блокировка с IP {ip} успешно снята!", show_alert=True)
    else:
        await callback.answer(f"Ошибка при разблокировке: {desc}", show_alert=True)
        
    text, kb = await render_client_details(ip)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("r_unban_port:"))
async def cb_router_unban_port_action(callback: CallbackQuery):
    parts = callback.data.split(":")
    ip = parts[1]
    port = int(parts[2])
    proto = parts[3]
    
    await callback.answer(f"Снимаю блокировку порта {port}/{proto} по SSH...", show_alert=False)
    success, desc = await unban_router_port(ip, port, proto)
    if success:
        await callback.answer(f"Блокировка порта {port}/{proto} снята!", show_alert=True)
    else:
        await callback.answer(f"Ошибка при снятии блокировки: {desc}", show_alert=True)
        
    full_ban = await execute_read_one("SELECT * FROM temp_bans WHERE server_ip = 'router' AND dst_ip = ?", (ip,))
    port_bans = await execute_read_all("SELECT * FROM temp_port_bans WHERE server_ip = 'router' AND client_ip = ?", (ip,))
    
    if full_ban or port_bans:
        await cb_router_active_bans_list(callback)
    else:
        text, kb = await render_client_details(ip)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


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
                        await callback.message.edit_text(new_text, reply_markup=kb, parse_mode="HTML")
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
                new_text = new_text.replace(f"\n\n🛑 <b>DEVICE {ip} BLOCKED ON ROUTER!</b>", "")
                try:
                    await callback.message.edit_text(new_text, reply_markup=kb, parse_mode="HTML")
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
