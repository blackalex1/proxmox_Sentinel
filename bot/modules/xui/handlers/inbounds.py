import html
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from modules.xui.api import xui
from modules.xui.keyboards import get_xui_main_keyboard, get_xui_inbounds_keyboard, get_xui_ib_details_keyboard

router = Router(name="xui_inbounds_router")

@router.callback_query(F.data == "xui_main")
async def process_xui_main(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        try:
            await callback.message.edit_text("🌍 <b>Панель управления 3X-UI:</b>", parse_mode="HTML", reply_markup=get_xui_main_keyboard())
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

@router.callback_query(F.data == "xui_status")
async def process_xui_status(callback: CallbackQuery):
    try:
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
                
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_xui_main_keyboard())
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("Статус обновлен")
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка получения статуса: {err_msg}", show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data == "xui_onlines")
async def process_xui_onlines(callback: CallbackQuery):
    try:
        onlines = await xui.get_online_clients()
        
        # Объединяем с локальным real-time кэшем активных подключений для 100% точности
        local_onlines = []
        try:
            from modules.proxmox.monitor.xui_connections import active_clients
            local_onlines = list(active_clients.keys())
        except Exception:
            pass
            
        if onlines is None:
            if local_onlines:
                onlines = local_onlines
            else:
                await callback.answer("Ошибка подключения к API панели", show_alert=True)
                return
        else:
            onlines = list(set(onlines) | set(local_onlines))
            
        text = "🟢 <b>Активные подключения клиентов:</b>\n\n"
        if not onlines:
            text += "<i>На данный момент нет активных подключений.</i>"
        else:
            text += f"Всего активных сессий: <b>{len(onlines)}</b>\n\n"
            for email in list(onlines)[:80]:
                email_esc = html.escape(str(email)[:50])
                text += f"👤 <code>{email_esc}</code>\n"
            if len(onlines) > 80:
                text += f"\n<i>... и еще {len(onlines) - 80} активных сессий ...</i>"
                
        if len(text) > 4000:
            text = text[:3900] + "\n\n<i>... [Список обрезан из-за лимитов Telegram] ...</i>"

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="xui_onlines")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="xui_main")]
        ])
        
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("Активные сессии обновлены")
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка: {err_msg}", show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data == "xui_inbounds")
async def process_xui_inbounds(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        inbounds = await xui.get_inbounds()
        if not inbounds:
            await callback.answer("Подключения не найдены", show_alert=True)
            return
        try:
            await callback.message.edit_text("🖧 <b>Выберите подключение (Inbound):</b>", parse_mode="HTML", reply_markup=get_xui_inbounds_keyboard(inbounds))
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка получения подключений: {err_msg}", show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("xui_ib_"))
async def process_xui_ib_select(callback: CallbackQuery, state: FSMContext):
    try:
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
        
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_xui_ib_details_keyboard(target_ib.get('id')))
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
