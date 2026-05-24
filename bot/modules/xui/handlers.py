from aiogram import Router, types, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from modules.xui.api import xui
from modules.xui.keyboards import (
    get_xui_main_keyboard, get_xui_inbounds_keyboard,
    get_xui_ib_details_keyboard, get_xui_manage_clients_keyboard,
    get_xui_client_opts_keyboard
)
from modules.xui.states import AddClientState, EditClientState
import uuid
import time

router = Router(name="xui_router")

@router.callback_query(F.data == "xui_main")
async def process_xui_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🌍 <b>Панель управления 3X-UI:</b>", parse_mode="HTML", reply_markup=get_xui_main_keyboard())

@router.callback_query(F.data == "xui_status")
async def process_xui_status(callback: CallbackQuery):
    status = await xui.get_status()
    if not status:
        await callback.answer("Ошибка получения статуса", show_alert=True)
        return
        
    cpu = status.get('cpu', 0)
    mem_obj = status.get('mem', {})
    mem_cur = mem_obj.get('current', 0) / (1024**3)
    mem_total = mem_obj.get('total', 1) / (1024**3)
    uptime = status.get('uptime', 0)
    
    hours, remainder = divmod(uptime, 3600)
    minutes, _ = divmod(remainder, 60)
    
    net_obj = status.get('netIO', {})
    up = net_obj.get('up', 0) / (1024**3)
    down = net_obj.get('down', 0) / (1024**3)

    text = (f"📊 <b>Статус 3X-UI сервера (Xray):</b>\n"
            f"Версия Xray: {status.get('xray', {}).get('version', 'unknown')}\n"
            f"CPU: {cpu:.1f}%\n"
            f"RAM: {mem_cur:.1f} / {mem_total:.1f} GB\n"
            f"Uptime: {hours}ч {minutes}м\n"
            f"Трафик: ⬆️ {up:.2f} GB | ⬇️ {down:.2f} GB")
            
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_xui_main_keyboard())

@router.callback_query(F.data == "xui_onlines")
async def process_xui_onlines(callback: CallbackQuery):
    onlines = await xui.get_online_clients()
    if onlines is None:
        await callback.answer("Ошибка подключения к API панели", show_alert=True)
        return
        
    text = "🟢 <b>Активные подключения клиентов:</b>\n\n"
    if not onlines:
        text += "<i>На данный момент нет активных подключений.</i>"
    else:
        text += f"Всего активных сессий: <b>{len(onlines)}</b>\n\n"
        for email in onlines:
            text += f"👤 <code>{email}</code>\n"
            
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="xui_onlines")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="xui_main")]
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "xui_inbounds")
async def process_xui_inbounds(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    inbounds = await xui.get_inbounds()
    if not inbounds:
        await callback.answer("Подключения не найдены", show_alert=True)
        return
    await callback.message.edit_text("🖧 <b>Выберите подключение (Inbound):</b>", parse_mode="HTML", reply_markup=get_xui_inbounds_keyboard(inbounds))

@router.callback_query(F.data.startswith("xui_ib_"))
async def process_xui_ib_select(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    ib_id = callback.data.split("_")[2].replace('txt', '')
    inbounds = await xui.get_inbounds()
    target_ib = next((i for i in inbounds if str(i.get('id')) == ib_id), None)
    
    if not target_ib:
        await callback.answer("Inbound не найден", show_alert=True)
        return
        
    up = target_ib.get('up', 0) / (1024**3)
    down = target_ib.get('down', 0) / (1024**3)
    
    clients = target_ib.get('clientStats', [])
    
    text = f"🖧 <b>Inbound: {target_ib.get('remark')} (Порт: {target_ib.get('port')})</b>\n"
    text += f"Общий трафик: ⬆️ {up:.2f} GB | ⬇️ {down:.2f} GB\n"
    text += f"Всего клиентов: {len(clients)}\n\n"
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_xui_ib_details_keyboard(target_ib.get('id')))

@router.callback_query(F.data.startswith("xui_manage_clients_"))
async def xui_manage_clients(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = parts[3]
    page = int(parts[4])
    
    inbounds = await xui.get_inbounds()
    target_ib = next((i for i in inbounds if str(i.get('id')) == inbound_id), None)
    if not target_ib:
        await callback.answer("Inbound не найден", show_alert=True)
        return
        
    # clientStats only has up/down/email, settings has full client info
    import json
    settings = json.loads(target_ib.get('settings', '{}'))
    clients = settings.get('clients', [])
    
    onlines = await xui.get_online_clients()
    
    text = f"👥 Управление клиентами (Стр. {page+1}):"
    await callback.message.edit_text(text, reply_markup=get_xui_manage_clients_keyboard(int(inbound_id), clients, page, onlines=onlines))

@router.callback_query(F.data.startswith("xui_c_opts_"))
async def xui_client_opts(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = parts[3]
    client_id = parts[4]
    
    inbounds = await xui.get_inbounds()
    target_ib = next((i for i in inbounds if str(i.get('id')) == inbound_id), None)
    if not target_ib:
        return
        
    import json
    settings = json.loads(target_ib.get('settings', '{}'))
    clients = settings.get('clients', [])
    target_c = next((c for c in clients if c.get('id') == client_id or c.get('password') == client_id), None)
    
    if not target_c:
        await callback.answer("Клиент не найден", show_alert=True)
        return
        
    email = target_c.get('email', 'Unknown')
    text = f"✏️ <b>Клиент {email}</b>\n\nВыберите действие:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_xui_client_opts_keyboard(int(inbound_id), client_id))

@router.callback_query(F.data.startswith("xui_del_client_"))
async def xui_delete_client(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = parts[3]
    client_id = parts[4]
    
    res = await xui.delete_client(inbound_id, client_id)
    if res:
        await callback.answer("✅ Клиент успешно удален", show_alert=True)
        await process_xui_ib_select(callback, FSMContext(storage=None, key=callback.from_user.id)) # fallback redirect
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)

@router.callback_query(F.data.startswith("xui_get_key_"))
async def xui_get_client_key(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = parts[3]
    client_id = parts[4]
    
    inbounds = await xui.get_inbounds()
    target_ib = next((i for i in inbounds if str(i.get('id')) == inbound_id), None)
    if not target_ib:
        await callback.answer("Inbound не найден", show_alert=True)
        return
        
    import json
    settings = json.loads(target_ib.get('settings', '{}'))
    clients = settings.get('clients', [])
    target_c = next((c for c in clients if c.get('id') == client_id or c.get('password') == client_id), None)
    
    if not target_c:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    email = target_c.get('email', 'Unknown')
    links = await xui.get_client_links_api(int(inbound_id), email)
    if not links:
        links = xui.get_client_links(target_ib, target_c)
        
    if not links:
        await callback.answer("Не удалось сгенерировать ссылку", show_alert=True)
        return
        
    text = f"🔑 <b>Ключи для клиента {email}:</b>\n\n"
    for link in links:
        text += f"<code>{link}</code>\n\n"
    
    text += "<i>Нажмите на ключ, чтобы скопировать.</i>"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# === ADD CLIENT FSM ===

@router.callback_query(F.data.startswith("xui_add_client_"))
async def xui_add_client_start(callback: CallbackQuery, state: FSMContext):
    inbound_id = callback.data.split("_")[3]
    await state.update_data(inbound_id=inbound_id)
    await state.set_state(AddClientState.email)
    await callback.message.answer("✉️ Введите email нового клиента:")

@router.message(AddClientState.email)
async def xui_add_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    await state.set_state(AddClientState.total_gb)
    await message.answer("💾 Введите лимит трафика в ГБ (0 для безлимита):")

@router.message(AddClientState.total_gb)
async def xui_add_gb(message: Message, state: FSMContext):
    try:
        gb = float(message.text.strip())
        await state.update_data(total_gb=int(gb * (1024**3)))
    except ValueError:
        await message.answer("Пожалуйста, введите число (например, 0 или 50.5):")
        return
        
    await state.set_state(AddClientState.expiry_days)
    await message.answer("⏱ Введите срок действия в днях (0 для навсегда):")

@router.message(AddClientState.expiry_days)
async def xui_add_days(message: Message, state: FSMContext):
    try:
        days = float(message.text.strip())
        if days == 0:
            expiry_time = 0
        else:
            expiry_time = int(time.time() * 1000) + int(days * 86400000)
        await state.update_data(expiry_time=expiry_time)
    except ValueError:
        await message.answer("Пожалуйста, введите число дней:")
        return
        
    data = await state.get_data()
    inbound_id = data['inbound_id']
    email = data['email']
    total_gb = data['total_gb']
    expiry = data['expiry_time']
    client_uuid = str(uuid.uuid4())
    
    res = await xui.add_client(inbound_id, client_uuid, email, total_gb=total_gb, expiry_time=expiry)
    if res:
        await message.answer(f"✅ Клиент <b>{email}</b> успешно добавлен!\nUUID/Password: {client_uuid}", parse_mode="HTML")
    else:
        await message.answer("❌ Ошибка при добавлении клиента. Возможно Inbound не поддерживает UUID или API изменилось.")
    await state.clear()

# === EDIT CLIENT FSM ===

@router.callback_query(F.data.startswith("xui_edit_client_"))
async def xui_edit_client_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    inbound_id = parts[3]
    client_id = parts[4]
    
    inbounds = await xui.get_inbounds()
    target_ib = next((i for i in inbounds if str(i.get('id')) == inbound_id), None)
    email = "Unknown"
    if target_ib:
        import json
        clients = json.loads(target_ib.get('settings', '{}')).get('clients', [])
        target_c = next((c for c in clients if c.get('id') == client_id or c.get('password') == client_id), None)
        if target_c:
            email = target_c.get('email', 'Unknown')

    await state.update_data(inbound_id=inbound_id, client_id=client_id, email=email)
    await state.set_state(EditClientState.total_gb)
    await callback.message.answer(f"Изменение клиента <b>{email}</b>.\n💾 Введите новый лимит трафика в ГБ (0 для безлимита):", parse_mode="HTML")

@router.message(EditClientState.total_gb)
async def xui_edit_gb(message: Message, state: FSMContext):
    try:
        gb = float(message.text.strip())
        await state.update_data(total_gb=int(gb * (1024**3)))
    except ValueError:
        await message.answer("Пожалуйста, введите число:")
        return
        
    await state.set_state(EditClientState.expiry_days)
    await message.answer("⏱ Введите новый срок действия в днях от текущего момента (0 для навсегда):")

@router.message(EditClientState.expiry_days)
async def xui_edit_days(message: Message, state: FSMContext):
    try:
        days = float(message.text.strip())
        if days == 0:
            expiry_time = 0
        else:
            expiry_time = int(time.time() * 1000) + int(days * 86400000)
        await state.update_data(expiry_time=expiry_time)
    except ValueError:
        await message.answer("Пожалуйста, введите число дней:")
        return
        
    data = await state.get_data()
    inbound_id = data['inbound_id']
    client_id = data['client_id']
    email = data['email']
    total_gb = data['total_gb']
    expiry = data['expiry_time']
    
    res = await xui.update_client(inbound_id, client_id, email, total_gb=total_gb, expiry_time=expiry)
    if res:
        await message.answer(f"✅ Лимиты клиента <b>{email}</b> успешно обновлены!", parse_mode="HTML")
    else:
        await message.answer("❌ Ошибка при обновлении клиента.")
    await state.clear()
