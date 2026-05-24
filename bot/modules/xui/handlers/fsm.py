import uuid
import time
from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from modules.xui.api import xui
from modules.xui.states import AddClientState, EditClientState

router = Router(name="xui_fsm_router")

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
