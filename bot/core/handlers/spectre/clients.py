import logging
import datetime
import html
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile, InputMediaPhoto

from core.spectre_client import spectre_manager
from core.messages.i18n import _

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
            _("spectre", "my_subscription_title"),
            parse_mode="HTML"
        )
        return
        
    search_key = args[1].strip()
    status_msg = await message.reply(_("spectre", "lookup_in_progress"))
    
    try:
        found_clients = await spectre_manager.search_client_all(search_key)
        
        if not found_clients:
            await status_msg.edit_text(_("spectre", "client_not_found_everywhere"))
            return
            
        await status_msg.delete()
        
        for item in found_clients:
            ib = item["inbound"]
            c = item["client"]
            links = item["links"]
            panel_name = item["panel_name"]
            
            up_gb = c["up"] / (1024**3)
            down_gb = c["down"] / (1024**3)
            total_gb = c["total"] / (1024**3) if c["total"] > 0 else _("spectre", "no_traffic_limit")
            total_gb_str = _("spectre", "limit_gb", limit=total_gb) if isinstance(total_gb, float) else total_gb
            
            if c["enable"] == 1:
                status_str = _("spectre", "status_active")
            else:
                reason = c.get('block_reason') or _("spectre", "reason_limit_exceeded")
                status_str = _("spectre", "status_blocked_with_reason", reason=reason)
                
            exp_str = _("spectre", "expires_never")
            if c["expiry_time"] > 0:
                dt = datetime.datetime.fromtimestamp(c["expiry_time"] / 1000)
                exp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                
            msg = _(
                "spectre",
                "client_card_sub_title",
                email=html.escape(c['email']),
                panel_name=panel_name,
                remark=ib['remark'],
                port=ib['port'],
                protocol=ib['protocol'].upper(),
                download_gb=down_gb,
                upload_gb=up_gb,
                total_gb_str=total_gb_str,
                expiry_str=exp_str,
                status_str=status_str
            )
            
            for link in links:
                msg += f"<code>{html.escape(link)}</code>\n\n"
                
            msg += _("spectre", "copy_link_hint")
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("spectre", "btn_conn_history_and_ip"), callback_data=f"vpn_hist:{c['email']}:0")]
            ])
            await message.answer(msg, parse_mode="HTML", reply_markup=kb)
            
            # Генерируем и отправляем QR-коды медиагруппой
            media_group = []
            for idx, link in enumerate(links):
                try:
                    qr_bytes = generate_qr_code_png(link)
                    photo_file = BufferedInputFile(qr_bytes, filename=f"qr_{idx}.png")
                    proto_name = link.split("://")[0].upper() if "://" in link else "VPN"
                    caption = _("spectre", "qr_code_caption", protocol=proto_name, index=idx+1)
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
        await status_msg.edit_text(_("spectre", "lookup_error", error=e))

@router.callback_query(F.data.startswith("unban_tunnel:"))
async def cb_unban_tunnel(callback: CallbackQuery):
    tunnel_email = callback.data.split(":", 1)[1]
    
    original_text = callback.message.html_text if callback.message else ""
    # Удаляем часть с кнопкой ручной разблокировки
    hint_text = _("spectre", "unbanning_tunnel_hint")
    if hint_text in original_text:
        original_text = original_text.split(hint_text)[0].strip()
    elif "👇 Вы можете разблокировать туннель вручную в один клик:" in original_text:
        original_text = original_text.split("👇 Вы можете разблокировать туннель вручную в один клик:")[0].strip()
        
    await callback.message.edit_text(
        f"{original_text}\n\n" + _("spectre", "unbanning_tunnel_progress"),
        parse_mode="HTML"
    )
    
    try:
        unblock_res = await spectre_manager.enable_client_everywhere(tunnel_email)
        
        all_success, detail_lines = spectre_manager.parse_action_results(unblock_res, action="unban")
        unblock_details_str = "\n".join(detail_lines)
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        if all_success:
            await callback.message.edit_text(
                _("spectre", "manual_unban_success_details", original_text=original_text, details=unblock_details_str, timestamp=timestamp),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                _("spectre", "manual_unban_failed_details", original_text=original_text, details=unblock_details_str, timestamp=timestamp),
                parse_mode="HTML",
                reply_markup=callback.message.reply_markup
            )
    except Exception as e:
        logging.error(f"Error unbanning tunnel manually: {e}")
        await callback.message.edit_text(
            _("spectre", "manual_unban_error", original_text=original_text, error=e),
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
            _("spectre", "ban_help"),
            parse_mode="HTML"
        )
        return
        
    email = args[1].strip()
    status_msg = await message.reply(_("spectre", "ban_progress", email=email))
    
    try:
        results = await spectre_manager.disable_client_everywhere(email)
        
        any_success, detail_lines = spectre_manager.parse_action_results(results, action="ban")
        details_str = "\n".join(detail_lines)
        if any_success:
            await status_msg.edit_text(
                _("spectre", "ban_success_results", email=email, details=details_str),
                parse_mode="HTML"
            )
        else:
            await status_msg.edit_text(
                _("spectre", "ban_failed_results", email=email, details=details_str),
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Error executing manual ban in Sentinel bot: {e}")
        await status_msg.edit_text(_("spectre", "ban_error", error=e))
 
@router.message(Command("unban"))
async def cmd_unban_client(message: types.Message):
    """
    Разблокирует VPN-клиента на всех панелях.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            _("spectre", "unban_help"),
            parse_mode="HTML"
        )
        return
        
    email = args[1].strip()
    status_msg = await message.reply(_("spectre", "unban_progress", email=email))
    
    try:
        results = await spectre_manager.enable_client_everywhere(email)
        
        any_success, detail_lines = spectre_manager.parse_action_results(results, action="unban")
        details_str = "\n".join(detail_lines)
        if any_success:
            await status_msg.edit_text(
                _("spectre", "unban_success_results", email=email, details=details_str),
                parse_mode="HTML"
            )
        else:
            await status_msg.edit_text(
                _("spectre", "unban_failed_results", email=email, details=details_str),
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Error executing manual unban in Sentinel bot: {e}")
        await status_msg.edit_text(_("spectre", "unban_error", error=e))

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
        await callback.message.edit_text(_("spectre", "tg_2fa_approved"), parse_mode="HTML")
    else:
        await callback.answer(_("spectre", "tg_2fa_error", error=error_msg or _("spectre", "tg_2fa_approve_failed")), show_alert=True)

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
            await callback.message.edit_text(_("spectre", "tg_2fa_blocked"), parse_mode="HTML")
        else:
            await callback.answer(_("spectre", "tg_2fa_error", error=error_msg or _("spectre", "tg_2fa_unblock_failed")), show_alert=True)
        return
        
    # Запрос подтверждения
    original_text = callback.message.html_text if callback.message else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=_("spectre", "tg_2fa_block_confirm_btn"), callback_data=f"tg_2fa_block:{token}:confirm"),
            InlineKeyboardButton(text=_("spectre", "tg_2fa_block_cancel_btn"), callback_data=f"tg_2fa_cancel_block:{token}")
        ]
    ])
    
    await callback.message.edit_text(
        _("spectre", "tg_2fa_block_confirm_text", original_text=original_text),
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tg_2fa_cancel_block:"))
async def cb_tg_2fa_cancel_block(callback: CallbackQuery):
    token = callback.data.split(":", 1)[1]
    
    original_text = callback.message.html_text if callback.message else ""
    warning_marker = "\n\n⚠️ Вы уверены?"
    warning_marker_en = "\n\n⚠️ Are you sure?"
    if warning_marker in original_text:
        original_text = original_text.split(warning_marker)[0]
    elif warning_marker_en in original_text:
        original_text = original_text.split(warning_marker_en)[0]
    elif "⚠️" in original_text:
        original_text = original_text.split("⚠️")[0].strip()
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=_("spectre", "tg_2fa_approve_btn"), callback_data=f"tg_2fa_approve:{token}"),
            InlineKeyboardButton(text=_("spectre", "tg_2fa_block_btn"), callback_data=f"tg_2fa_block:{token}")
        ]
    ])
    
    await callback.message.edit_text(
        original_text,
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer(_("spectre", "tg_2fa_block_cancelled_alert"))
