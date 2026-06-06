import logging
import datetime
import html
import asyncio
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo, BufferedInputFile, InputMediaPhoto

from core.spectre_client import spectre_manager

router = Router(name="core_spectre_router")

@router.message(Command("panel"))
async def cmd_panel(message: types.Message):
    """
    Открывает WebApp Spectre Panel. Если панелей несколько, предлагает выбор.
    """
    panels = spectre_manager.panels
    if not panels:
        await message.reply("❌ <b>Панели Spectre Panel не обнаружены.</b>\nУбедитесь, что панели запущены и доступны.")
        return
        
    if len(panels) == 1:
        panel = list(panels.values())[0]
        # http://<ip>:<port>/<secret_path>/
        webapp_url = f"{panel.url}/{panel.secret_path}/"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📱 Открыть {panel.name}", web_app=WebAppInfo(url=webapp_url))]
        ])
        await message.reply(
            f"🚀 <b>Панель управления Spectre Panel</b>\n\nСервер: <code>{panel.name}</code>",
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        # Рисуем список кнопок для выбора панели
        buttons = []
        for p_key, p in panels.items():
            webapp_url = f"{p.url}/{p.secret_path}/"
            buttons.append([InlineKeyboardButton(text=f"📱 {p.name}", web_app=WebAppInfo(url=webapp_url))])
            
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply(
            "🚀 <b>Выберите Spectre Panel для управления:</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )

@router.message(Command("backup"))
async def cmd_backup(message: types.Message):
    """
    Создает бэкап базы данных.
    """
    panels = spectre_manager.panels
    if not panels:
        await message.reply("❌ <b>Панели Spectre Panel не обнаружены.</b>")
        return
        
    if len(panels) == 1:
        panel_key = list(panels.keys())[0]
        await run_backup_for_panel(message, panel_key)
    else:
        buttons = []
        for p_key, p in panels.items():
            buttons.append([InlineKeyboardButton(text=p.name, callback_data=f"spectre_backup:{p_key}")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("📥 <b>Выберите панель для создания бэкапа:</b>", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("spectre_backup:"))
async def cb_backup(callback: CallbackQuery):
    panel_key = callback.data.split(":", 1)[1]
    await callback.message.delete()
    await run_backup_for_panel(callback.message, panel_key)
    await callback.answer()

async def run_backup_for_panel(message: types.Message, panel_key: str):
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await message.answer("❌ Панель не найдена.")
        return
        
    status_msg = await message.answer(f"⏳ Создание резервной копии для <b>{panel.name}</b>...")
    success, res = await panel.request("GET", "/api/security/backup")
    
    if success and res.get("success") and "dump" in res:
        try:
            dump_data = res["dump"]
            file_bytes = dump_data.encode("utf-8")
            timestamp = int(datetime.datetime.now().timestamp())
            document = BufferedInputFile(file_bytes, filename=f"spectre_backup_{panel.identifier}_{timestamp}.json")
            
            await status_msg.delete()
            await message.answer_document(
                document,
                caption=f"✅ <b>Резервная копия успешно создана!</b>\nСервер: <code>{panel.name}</code>"
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ Ошибка отправки бэкапа: {e}")
    else:
        error_info = res.get("msg") or res.get("error") or "Неизвестная ошибка"
        await status_msg.edit_text(f"❌ <b>Не удалось создать бэкап для {panel.name}:</b>\n<code>{error_info}</code>")

@router.message(Command("status"))
async def cmd_status_spectre(message: types.Message):
    """
    Выводит системный статус панели.
    """
    panels = spectre_manager.panels
    if not panels:
        # Если панелей нет, это не сбой, т.к. команда переопределяет статус ботов Aegis.
        # Но мы обработаем это: оригинальный Aegis /status обрабатывается в bot/core/handlers/status.py
        # Мы регистрируем этот хэндлер с фильтром, чтобы он срабатывал только если есть аргумент или панели
        return
        
    if len(panels) == 1:
        panel_key = list(panels.keys())[0]
        await run_status_for_panel(message, panel_key)
    else:
        buttons = []
        for p_key, p in panels.items():
            buttons.append([InlineKeyboardButton(text=p.name, callback_data=f"spectre_status:{p_key}")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("📊 <b>Выберите панель для проверки статуса:</b>", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("spectre_status:"))
async def cb_status(callback: CallbackQuery):
    panel_key = callback.data.split(":", 1)[1]
    await callback.message.delete()
    await run_status_for_panel(callback.message, panel_key)
    await callback.answer()

async def run_status_for_panel(message: types.Message, panel_key: str):
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await message.answer("❌ Панель не найдена.")
        return
        
    status_msg = await message.answer(f"⏳ Получение статуса от <b>{panel.name}</b>...")
    success, res = await panel.request("GET", "/api/security/system-status")
    
    if success and res.get("success"):
        stats = res.get("stats", {})
        counts = res.get("counts", {})
        
        cpu = stats.get("cpu", 0.0)
        mem = stats.get("mem", {})
        mem_curr = mem.get("current", 0) / (1024**3)
        mem_tot = mem.get("total", 0) / (1024**3)
        uptime = stats.get("uptime", 0)
        
        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60
        uptime_str = f"{days}д {hours}ч {minutes}м"
        
        msg = (
            f"📊 <b>Статус сервера: {panel.name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🖥️ Загрузка CPU: <b>{cpu}%</b>\n"
            f"💾 Оперативная память: <b>{mem_curr:.2f} ГБ / {mem_tot:.2f} ГБ</b>\n"
            f"⏱ Время работы (Uptime): <b>{uptime_str}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🖧 Всего подключений (Inbounds): <b>{counts.get('total_inbounds', 0)}</b>\n"
            f"👥 Всего клиентов: <b>{counts.get('total_clients', 0)}</b>\n"
            f"🟢 Активных пользователей: <b>{counts.get('active_clients', 0)}</b>\n"
            f"🔴 Заблокированных: <b>{counts.get('blocked_clients', 0)}</b>"
        )
        await status_msg.delete()
        await message.answer(msg, parse_mode="HTML")
    else:
        error_info = res.get("msg") or res.get("error") or "Неизвестная ошибка"
        await status_msg.edit_text(f"❌ <b>Ошибка получения статуса {panel.name}:</b>\n<code>{error_info}</code>")

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
            await message.answer(msg, parse_mode="HTML")
            
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
        from core.spectre_client import spectre_manager
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


@router.message(Command("top"))
async def cmd_top_spectre(message: types.Message):
    """
    Выводит суммарные топы трафика по всем панелям, сгруппированные по нодам.
    """
    args = message.text.split(maxsplit=1)
    period = "today"
    if len(args) > 1 and args[1].strip().lower() in ["month", "месяц"]:
        period = "month"
        
    panels = spectre_manager.panels
    if not panels:
        await message.reply("❌ <b>Панели Spectre Panel не обнаружены.</b>")
        return
        
    status_msg = await message.reply("📊 Получение статистики по трафику со всех панелей...")
    
    async def fetch_top(panel):
        success, res = await panel.request("GET", "/api/security/top-traffic", params={"period": period})
        return panel, success, res
        
    tasks = [fetch_top(p) for p in panels.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    title = "🏆 <b>Топ потребителей трафика (Сегодня)</b>" if period == "today" else "🏆 <b>Топ потребителей трафика (За месяц)</b>"
    msg = f"{title}\n"
    
    has_any_data = False
    for r in results:
        if isinstance(r, Exception):
            logging.error(f"Error fetching top traffic: {r}")
            continue
            
        panel, success, res = r
        if not success or not res.get("success"):
            error_info = res.get("msg") or res.get("error") or "Неизвестная ошибка"
            msg += f"\n❌ <b>{panel.name}</b>: <code>{error_info}</code>\n"
            continue
            
        users = res.get("users", [])
        if users:
            has_any_data = True
            msg += f"\n📌 <b>Панель {panel.name}:</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for idx, user in enumerate(users[:10], 1):
                gb = user["total"] / (1024**3)
                msg += f"{idx}. 👤 <code>{html.escape(user['email'])}</code>: <b>{gb:.3f} GB</b>\n"
        else:
            msg += f"\n📌 <b>Панель {panel.name}:</b> Нет активности\n"
            
    if not has_any_data and len(panels) > 0:
        msg += "\nНет данных об активности пользователей на панелях."
        
    msg += "\n\n<i>Для переключения используйте: <code>/top today</code> или <code>/top month</code></i>"
    
    await status_msg.delete()
    await message.reply(msg, parse_mode="HTML")


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
    parts = callback.data.split(":", 2)
    token = parts[1]
    ip = parts[2] if len(parts) > 2 else "unknown"
    
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
        await callback.message.edit_text(f"🛑 <b>IP {ip} заблокирован.</b>", parse_mode="HTML")
    else:
        await callback.answer(f"❌ Ошибка: {error_msg or 'Не удалось заблокировать ни на одной панели'}", show_alert=True)



