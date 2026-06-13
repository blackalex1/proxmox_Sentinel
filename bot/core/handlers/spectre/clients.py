import logging
import datetime
import html
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile, InputMediaPhoto

from core.spectre_client import spectre_manager

router = Router(name="spectre_clients_router")

def generate_qr_code_png(data: str) -> bytes:
    import io
    import qrcode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

@router.message(Command("my"))
async def cmd_my_spectre(message: types.Message):
    """
    Ищет информацию о подписке клиента по всем панелям.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "🔑 <b>Поиск подписки клиента:</b>\n"
            "Используйте команду: <code>/my &lt;email или UUID&gt;</code>",
            parse_mode="HTML"
        )
        return
        
    search_key = args[1].strip()
    status_msg = await message.reply("🔍 Поиск клиента по всем базам данных панелей...")
    
    try:
        found_clients = await spectre_manager.search_client_all(search_key)
        
        if not found_clients:
            await status_msg.edit_text("❌ <b>Клиент с таким email или UUID не найден ни на одной панели.</b>")
            return
            
        await status_msg.delete()
        
        for item in found_clients:
            ib = item["inbound"]
            c = item["client"]
            links = item["links"]
            panel_name = item["panel_name"]
            
            up_gb = c["up"] / (1024**3)
            down_gb = c["down"] / (1024**3)
            total_gb = c["total"] / (1024**3) if c["total"] > 0 else "Без лимита"
            total_gb_str = f"{total_gb:.2f} ГБ" if isinstance(total_gb, float) else total_gb
            
            if c["enable"] == 1:
                status_str = "🟢 Активен"
            else:
                reason = c.get('block_reason') or "Превышены лимиты"
                status_str = f"🔴 Заблокирован ({reason})"
                
            exp_str = "Никогда"
            if c["expiry_time"] > 0:
                dt = datetime.datetime.fromtimestamp(c["expiry_time"] / 1000)
                exp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                
            msg = (
                f"🔑 <b>Подписка: {html.escape(c['email'])}</b>\n"
                f"📡 Панель/Сервер: <b>{panel_name}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 Подключение: <b>{ib['remark']} (:{ib['port']})</b>\n"
                f"📡 Протокол: <b>{ib['protocol'].upper()}</b>\n"
                f"🚦 Скачано (DL): <b>{down_gb:.3f} ГБ</b>\n"
                f"📤 Загружено (UL): <b>{up_gb:.3f} ГБ</b>\n"
                f"💾 Лимит трафика: <b>{total_gb_str}</b>\n"
                f"⏱ Истекает: <b>{exp_str}</b>\n"
                f"⚡ Статус: <b>{status_str}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔗 <b>Ссылки для подключения:</b>\n"
            )
            
            for link in links:
                msg += f"<code>{html.escape(link)}</code>\n\n"
                
            msg += "<i>Нажмите на ссылку, чтобы скопировать её.</i>"
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 История подключений и IP", callback_data=f"vpn_hist:{c['email']}:0")]
            ])
            await message.answer(msg, parse_mode="HTML", reply_markup=kb)
            
            # Генерируем и отправляем QR-коды медиагруппой
            media_group = []
            for idx, link in enumerate(links):
                try:
                    qr_bytes = generate_qr_code_png(link)
                    photo_file = BufferedInputFile(qr_bytes, filename=f"qr_{idx}.png")
                    proto_name = link.split("://")[0].upper() if "://" in link else "VPN"
                    caption = f"QR-код {proto_name} ({idx+1})"
                    media_group.append(InputMediaPhoto(media=photo_file, caption=caption))
                except Exception as qr_err:
                    logging.error(f"Error generating QR code in Sentinel bot: {qr_err}")
            
            if media_group:
                try:
                    await message.answer_media_group(media=media_group)
                except Exception as send_err:
                    logging.error(f"Error sending QR media group in Sentinel bot: {send_err}")
            
    except Exception as e:
        logging.error(f"Error executing search all in bot: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка при поиске: {e}")

@router.callback_query(F.data.startswith("unban_tunnel:"))
async def cb_unban_tunnel(callback: CallbackQuery):
    tunnel_email = callback.data.split(":", 1)[1]
    
    original_text = callback.message.html_text if callback.message else ""
    # Удаляем часть с кнопкой ручной разблокировки
    if "👇 Вы можете разблокировать туннель вручную в один клик:" in original_text:
        original_text = original_text.split("👇 Вы можете разблокировать туннель вручную в один клик:")[0].strip()
        
    await callback.message.edit_text(
        f"{original_text}\n\n⏳ <b>Выполняется разблокировка туннеля...</b>",
        parse_mode="HTML"
    )
    
    try:
        unblock_res = await spectre_manager.enable_client_everywhere(tunnel_email)
        
        unblock_details = []
        all_success = True
        for panel_name, success, msg in unblock_res:
            status_str = "🟢 Успешно" if success else "🔴 Ошибка"
            if not success:
                all_success = False
            unblock_details.append(f"  • {panel_name}: {status_str} ({msg})")
        unblock_details_str = "\n".join(unblock_details)
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        if all_success:
            await callback.message.edit_text(
                f"{original_text}\n\n✅ <b>Туннель успешно разблокирован вручную!</b>\n"
                f"📋 <b>Детали разблокировки:</b>\n{unblock_details_str}\n"
                f"🕒 Время: <code>{timestamp}</code>",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"{original_text}\n\n⚠️ <b>Туннель разблокирован с ошибками:</b>\n"
                f"📋 <b>Детали разблокировки:</b>\n{unblock_details_str}\n"
                f"🕒 Время: <code>{timestamp}</code>",
                parse_mode="HTML",
                reply_markup=callback.message.reply_markup
            )
    except Exception as e:
        logging.error(f"Error unbanning tunnel manually: {e}")
        await callback.message.edit_text(
            f"{original_text}\n\n❌ <b>Ошибка при разблокировке:</b> <code>{e}</code>",
            parse_mode="HTML",
            reply_markup=callback.message.reply_markup
        )
        
    await callback.answer()

@router.message(Command("ban"))
async def cmd_ban_client(message: types.Message):
    """
    Блокирует VPN-клиента на всех панелях.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "🛑 <b>Блокировка клиента:</b>\n"
            "Используйте команду: <code>/ban &lt;email&gt;</code>",
            parse_mode="HTML"
        )
        return
        
    email = args[1].strip()
    status_msg = await message.reply(f"⏳ Блокировка клиента <code>{email}</code> на всех панелях...")
    
    try:
        results = await spectre_manager.disable_client_everywhere(email)
        
        detail_lines = []
        any_success = False
        for panel_name, success, msg in results:
            status_str = "🟢 Заблокирован" if success else "🔴 Ошибка"
            if success:
                any_success = True
            detail_lines.append(f"  • {panel_name}: {status_str} ({msg})")
            
        details_str = "\n".join(detail_lines)
        if any_success:
            await status_msg.edit_text(
                f"✅ <b>Результаты блокировки клиента <code>{email}</code>:</b>\n{details_str}",
                parse_mode="HTML"
            )
        else:
            await status_msg.edit_text(
                f"❌ <b>Не удалось заблокировать клиента <code>{email}</code>:</b>\n{details_str}",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Error executing manual ban in Sentinel bot: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка при блокировке: {e}")

@router.message(Command("unban"))
async def cmd_unban_client(message: types.Message):
    """
    Разблокирует VPN-клиента на всех панелях.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "🟢 <b>Разблокировка клиента:</b>\n"
            "Используйте команду: <code>/unban &lt;email&gt;</code>",
            parse_mode="HTML"
        )
        return
        
    email = args[1].strip()
    status_msg = await message.reply(f"⏳ Разблокировка клиента <code>{email}</code> на всех панелях...")
    
    try:
        results = await spectre_manager.enable_client_everywhere(email)
        
        detail_lines = []
        any_success = False
        for panel_name, success, msg in results:
            status_str = "🟢 Разблокирован" if success else "🔴 Ошибка"
            if success:
                any_success = True
            detail_lines.append(f"  • {panel_name}: {status_str} ({msg})")
            
        details_str = "\n".join(detail_lines)
        if any_success:
            await status_msg.edit_text(
                f"✅ <b>Результаты разблокировки клиента <code>{email}</code>:</b>\n{details_str}",
                parse_mode="HTML"
            )
        else:
            await status_msg.edit_text(
                f"❌ <b>Не удалось разблокировать клиента <code>{email}</code>:</b>\n{details_str}",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Error executing manual unban in Sentinel bot: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка при разблокировке: {e}")

@router.callback_query(F.data.startswith("tg_2fa_approve:"))
async def cb_tg_2fa_approve(callback: CallbackQuery):
    token = callback.data.split(":", 1)[1]
    
    # Ищем панель, которая примет этот токен
    success_found = False
    error_msg = None
    for p_key, panel in spectre_manager.panels.items():
        success, res = await panel.request("POST", "/api/auth/tg-2fa/action", json={"token": token, "action": "approve"})
        if success and res.get("success"):
            success_found = True
            break
        elif success:
            error_msg = res.get("msg")
            
    if success_found:
        await callback.message.edit_text("✅ <b>Вход успешно разрешен.</b>", parse_mode="HTML")
    else:
        await callback.answer(f"❌ Ошибка: {error_msg or 'Не удалось подтвердить ни на одной панели'}", show_alert=True)

@router.callback_query(F.data.startswith("tg_2fa_block:"))
async def cb_tg_2fa_block(callback: CallbackQuery):
    parts = callback.data.split(":")
    token = parts[1]
    
    if len(parts) > 2 and parts[2] == "confirm":
        success_found = False
        error_msg = None
        for p_key, panel in spectre_manager.panels.items():
            success, res = await panel.request("POST", "/api/auth/tg-2fa/action", json={"token": token, "action": "block"})
            if success and res.get("success"):
                success_found = True
                break
            elif success:
                error_msg = res.get("msg")
                
        if success_found:
            await callback.message.edit_text("🛑 <b>IP-адрес заблокирован.</b>", parse_mode="HTML")
        else:
            await callback.answer(f"❌ Ошибка: {error_msg or 'Не удалось заблокировать ни на одной панели'}", show_alert=True)
        return
        
    # Запрос подтверждения
    original_text = callback.message.html_text if callback.message else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔥 Да, заблокировать IP", callback_data=f"tg_2fa_block:{token}:confirm"),
            InlineKeyboardButton(text="🔙 Отмена", callback_data=f"tg_2fa_cancel_block:{token}")
        ]
    ])
    
    await callback.message.edit_text(
        f"{original_text}\n\n⚠️ <b>Вы уверены? Блокировка вашего IP лишит вас доступа к серверу!</b>",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tg_2fa_cancel_block:"))
async def cb_tg_2fa_cancel_block(callback: CallbackQuery):
    token = callback.data.split(":", 1)[1]
    
    original_text = callback.message.html_text if callback.message else ""
    warning_marker = "\n\n⚠️ Вы уверены?"
    if warning_marker in original_text:
        original_text = original_text.split(warning_marker)[0]
    elif "⚠️" in original_text:
        original_text = original_text.split("⚠️")[0].strip()
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, разрешить", callback_data=f"tg_2fa_approve:{token}"),
            InlineKeyboardButton(text="❌ Заблокировать IP", callback_data=f"tg_2fa_block:{token}")
        ]
    ])
    
    await callback.message.edit_text(
        original_text,
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer("Блокировка IP отменена")
