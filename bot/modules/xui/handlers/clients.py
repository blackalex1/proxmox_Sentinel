import json
import html
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from modules.xui.api import xui
from modules.xui.keyboards import get_xui_manage_clients_keyboard, get_xui_client_opts_keyboard

router = Router(name="xui_clients_router")

@router.callback_query(F.data.startswith("xui_manage_clients_"))
async def xui_manage_clients(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        inbound_id = parts[3]
        page = int(parts[4])
        
        inbounds = await xui.get_inbounds()
        target_ib = next((i for i in inbounds if str(i.get('id')) == inbound_id), None)
        if not target_ib:
            await callback.answer("Inbound не найден", show_alert=True)
            return
            
        settings = json.loads(target_ib.get('settings', '{}'))
        clients = settings.get('clients', [])
        
        onlines = await xui.get_online_clients()
        
        text = f"👥 Управление клиентами (Стр. {page+1}):"
        try:
            await callback.message.edit_text(text, reply_markup=get_xui_manage_clients_keyboard(int(inbound_id), clients, page, onlines=onlines))
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка: {err_msg}", show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("xui_c_opts_"))
async def xui_client_opts(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        inbound_id = parts[3]
        client_id = parts[4]
        
        inbounds = await xui.get_inbounds()
        target_ib = next((i for i in inbounds if str(i.get('id')) == inbound_id), None)
        if not target_ib:
            return
            
        settings = json.loads(target_ib.get('settings', '{}'))
        clients = settings.get('clients', [])
        target_c = next((c for c in clients if c.get('id') == client_id or c.get('password') == client_id), None)
        
        if not target_c:
            await callback.answer("Клиент не найден", show_alert=True)
            return
            
        email = target_c.get('email', 'Unknown')
        email_esc = html.escape(str(email)[:50])
        text = f"✏️ <b>Клиент {email_esc}</b>\n\nВыберите действие:"
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_xui_client_opts_keyboard(int(inbound_id), client_id))
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка: {err_msg}", show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("xui_del_client_"))
async def xui_delete_client(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        inbound_id = parts[3]
        client_id = parts[4]
        
        res = await xui.delete_client(inbound_id, client_id)
        if res:
            await callback.answer("✅ Клиент успешно удален", show_alert=True)
            from modules.xui.handlers.inbounds import process_xui_ib_select
            from aiogram.fsm.context import FSMContext
            await process_xui_ib_select(callback, FSMContext(storage=None, key=callback.from_user.id))
        else:
            await callback.answer("❌ Ошибка при удалении", show_alert=True)
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка: {err_msg}", show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("xui_get_key_"))
async def xui_get_client_key(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        inbound_id = parts[3]
        client_id = parts[4]
        
        inbounds = await xui.get_inbounds()
        target_ib = next((i for i in inbounds if str(i.get('id')) == inbound_id), None)
        if not target_ib:
            await callback.answer("Inbound не найден", show_alert=True)
            return
            
        settings = json.loads(target_ib.get('settings', '{}'))
        clients = settings.get('clients', [])
        target_c = next((c for c in clients if c.get('id') == client_id or c.get('password') == client_id), None)
        
        if not target_c:
            await callback.answer("Клиент не найден", show_alert=True)
            return
        email = target_c.get('email', 'Unknown')
        email_esc = html.escape(str(email)[:50])
        links = await xui.get_client_links_api(int(inbound_id), email)
        if not links:
            links = xui.get_client_links(target_ib, target_c)
            
        if not links:
            await callback.answer("Не удалось сгенерировать ссылку", show_alert=True)
            return
            
        text = f"🔑 <b>Ключи для клиента {email_esc}:</b>\n\n"
        for link in links:
            link_esc = html.escape(str(link))
            text += f"<code>{link_esc}</code>\n\n"
        
        text += "<i>Нажмите на ключ, чтобы скопировать.</i>"
        
        if len(text) > 4000:
            text = text[:3900] + "\n\n<i>... [Ключи обрезаны из-за лимитов Telegram] ...</i>"
            
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка: {err_msg}", show_alert=True)
        except Exception:
            pass
