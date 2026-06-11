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
    Открывает меню управления Spectre Panel.
    """
    panels = spectre_manager.panels
    if not panels:
        await message.reply("❌ <b>Панели Spectre Panel не обнаружены.</b>\nУбедитесь, что панели запущены и доступны.")
        return
        
    if len(panels) == 1:
        panel_key = list(panels.keys())[0]
        panel = list(panels.values())[0]
        webapp_url = f"{panel.url}/{panel.secret_path}/"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📱 Открыть {panel.name}", web_app=WebAppInfo(url=webapp_url))],
            [
                InlineKeyboardButton(text="➕ Добавить слейв", callback_data=f"spectre_add_slave:{panel_key}"),
                InlineKeyboardButton(text="➕ Добавить мастер", callback_data="spectre_add_master")
            ]
        ])
        await message.reply(
            f"🚀 <b>Панель управления Spectre Panel</b>\n\nСервер: <code>{panel.name}</code>",
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        buttons = []
        for p_key, p in panels.items():
            buttons.append([InlineKeyboardButton(text=f"📱 {p.name}", callback_data=f"spectre_menu:{p_key}")])
        buttons.append([InlineKeyboardButton(text="➕ Добавить мастер ноду", callback_data="spectre_add_master")])
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
            f"🔵 В сети (Онлайн): <b>{counts.get('online_clients', 0)}</b>\n"
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


@router.message(Command("audit", "logs"))
async def cmd_audit(message: types.Message):
    """
    Выводит последние 10 действий администраторов из лога аудита.
    """
    panels = spectre_manager.panels
    if not panels:
        await message.reply("❌ <b>Панели Spectre Panel не обнаружены.</b>")
        return
        
    if len(panels) == 1:
        panel_key = list(panels.keys())[0]
        await run_audit_for_panel(message, panel_key)
    else:
        buttons = []
        for p_key, p in panels.items():
            buttons.append([InlineKeyboardButton(text=p.name, callback_data=f"spectre_audit:{p_key}")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("📋 <b>Выберите панель для просмотра лога аудита:</b>", reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("spectre_audit:"))
async def cb_audit(callback: CallbackQuery):
    panel_key = callback.data.split(":", 1)[1]
    await callback.message.delete()
    await run_audit_for_panel(callback.message, panel_key)
    await callback.answer()


async def run_audit_for_panel(message: types.Message, panel_key: str):
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await message.answer("❌ Панель не найдена.")
        return
        
    status_msg = await message.answer(f"⏳ Получение логов аудита от <b>{panel.name}</b>...")
    success, res = await panel.get_audit_logs(limit=10)
    
    if success and res.get("success"):
        logs = res.get("logs", [])
        if not logs:
            await status_msg.edit_text(f"📁 <b>{panel.name}</b>: Лог аудита пуст.")
            return
            
        msg = f"📋 <b>Последние действия в панели: {panel.name}</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        for log in logs:
            dt = datetime.datetime.fromtimestamp(log["timestamp"])
            time_str = dt.strftime("%d.%m %H:%M:%S")
            target_str = f" ➔ <code>{html.escape(log['target'])}</code>" if log.get('target') else ""
            details_str = f" (<i>{html.escape(log['details'])}</i>)" if log.get('details') else ""
            
            msg += f"🕒 <code>{time_str}</code> | 👤 <b>{html.escape(log['username'])}</b>\n"
            msg += f"⚙️ <code>{html.escape(log['action'])}</code>{target_str}{details_str}\n"
            msg += "────────────────────────\n"
            
        await status_msg.delete()
        await message.answer(msg, parse_mode="HTML")
    else:
        error_info = res.get("msg") or res.get("error") or "Неизвестная ошибка"
        await status_msg.edit_text(f"❌ <b>Ошибка получения логов {panel.name}:</b>\n<code>{error_info}</code>")


@router.callback_query(F.data.startswith("spectre_menu:"))
async def cb_spectre_menu(callback: CallbackQuery):
    panel_key = callback.data.split(":", 1)[1]
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await callback.answer("❌ Панель не найдена.", show_alert=True)
        return
        
    webapp_url = f"{panel.url}/{panel.secret_path}/"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📱 Открыть WebApp", web_app=WebAppInfo(url=webapp_url))],
        [
            InlineKeyboardButton(text="⚙️ Статус", callback_data=f"spectre_status:{panel_key}"),
            InlineKeyboardButton(text="📋 Логи аудита", callback_data=f"spectre_audit:{panel_key}")
        ],
        [
            InlineKeyboardButton(text="📥 Бэкап", callback_data=f"spectre_backup:{panel_key}"),
            InlineKeyboardButton(text="➕ Добавить слейв", callback_data=f"spectre_add_slave:{panel_key}")
        ],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="spectre_list")]
    ])
    await callback.message.edit_text(
        f"🚀 <b>Управление панелью {panel.name}</b>\n\nВыберите действие:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "spectre_list")
async def cb_spectre_list(callback: CallbackQuery):
    panels = spectre_manager.panels
    buttons = []
    for p_key, p in panels.items():
        buttons.append([InlineKeyboardButton(text=f"📱 {p.name}", callback_data=f"spectre_menu:{p_key}")])
    buttons.append([InlineKeyboardButton(text="➕ Добавить мастер ноду", callback_data="spectre_add_master")])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        "🚀 <b>Выберите Spectre Panel для управления:</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("spectre_add_slave:"))
async def cb_add_slave(callback: CallbackQuery):
    panel_key = callback.data.split(":", 1)[1]
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await callback.answer("❌ Панель не найдена.", show_alert=True)
        return
        
    await callback.message.edit_text(
        f"⏳ <b>Генерация кода подключения для слейв-ноды на {panel.name}...</b>",
        parse_mode="HTML"
    )
    
    # Запрос join-code с Мастер-панели
    success, res = await panel.request("POST", "/api/nodes/join-code")
    if success and "code" in res:
        join_code = res["code"]
        expires_at = res["expires_at"]
        dt = datetime.datetime.fromtimestamp(expires_at)
        expiry_str = dt.strftime("%d.%m %H:%M:%S")
        
        master_url = f"{panel.url}"
        if panel.secret_path:
            master_url += f"/{panel.secret_path}"
            
        msg = (
            f"➕ <b>Добавление слейв-ноды для {panel.name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 Код подключения (Join Code):\n<code>{join_code}</code>\n"
            f"⏱ Истекает: <b>{expiry_str}</b>\n\n"
            f"💻 <b>Команда для запуска на слейв-сервере:</b>\n"
            f"<code>python register_node.py --master \"{master_url}\" --join-code \"{join_code}\"</code>\n\n"
            f"<i>Запустите эту команду в директории слейв-панели для регистрации публичного ключа.</i>"
        )
        
        back_data = f"spectre_menu:{panel_key}" if len(spectre_manager.panels) > 1 else "spectre_list"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=back_data)]
        ])
        await callback.message.edit_text(msg, reply_markup=kb, parse_mode="HTML")
    else:
        error_info = res.get("msg") or res.get("error") or "Неизвестная ошибка"
        back_data = f"spectre_menu:{panel_key}" if len(spectre_manager.panels) > 1 else "spectre_list"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=back_data)]
        ])
        await callback.message.edit_text(
            f"❌ <b>Ошибка генерации кода подключения для {panel.name}:</b>\n<code>{error_info}</code>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        
    await callback.answer()


@router.callback_query(F.data == "spectre_add_master")
async def cb_add_master(callback: CallbackQuery):
    msg = (
        f"➕ <b>Добавление новой Мастер-панели в Контроллер</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Чтобы подключить еще одну Мастер-панель к вашему Telegram-боту:\n\n"
        f"1️⃣ Откройте конфигурационный файл <code>.env</code> контроллера.\n"
        f"2️⃣ Добавьте или отредактируйте переменную <code>SPECTRE_PANELS</code>. Это JSON-список панелей:\n\n"
        f"<code>SPECTRE_PANELS='[\n"
        f"  {{\"name\": \"Моя Панель\", \"url\": \"https://ip:port\", \"token\": \"api_token_here\", \"secret_path\": \"secret\"}}\n"
        f"]'</code>\n\n"
        f"3️⃣ Перезапустите бота. Он автоматически обнаружит её и добавит в меню."
    )
    back_data = "spectre_list"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=back_data)]
    ])
    await callback.message.edit_text(msg, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.message(Command("setup_slave"))
async def cmd_setup_slave(message: types.Message):
    """
    Команда для автоматической настройки текущего сервера в качестве слейв-ноды.
    Формат: /setup_slave <master_url> <join_code>
    """
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply(
            "💻 <b>Настройка сервера как слейв-ноды:</b>\n"
            "Используйте формат: <code>/setup_slave &lt;master_url&gt; &lt;join_code&gt;</code>\n\n"
            "<i>Пример:</i>\n<code>/setup_slave https://master.com/secret JOIN-E5A73D1C</code>",
            parse_mode="HTML"
        )
        return
        
    master_url = args[1].strip()
    join_code = args[2].strip()
    
    status_msg = await message.reply("⏳ <b>Инициализация подключения к Мастер-серверу...</b>")
    
    try:
        import os
        import json
        import aiohttp
        from cryptography.hazmat.primitives.asymmetric import ed25519
        
        # 1. Генерируем ключи Ed25519
        private_key = ed25519.Ed25519PrivateKey.generate()
        priv_hex = private_key.private_bytes_raw().hex()
        pub_hex = private_key.public_key().public_bytes_raw().hex()
        
        # 2. Выполняем запрос регистрации к Мастеру
        register_url = f"{master_url.rstrip('/')}/api/nodes/register"
        payload = {
            "join_code": join_code,
            "public_key": pub_hex
        }
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(register_url, json=payload, timeout=15) as response:
                if response.status != 200:
                    text = await response.text()
                    await status_msg.edit_text(
                        f"❌ <b>Регистрация отклонена Мастером (код {response.status}):</b>\n<code>{text[:200]}</code>"
                    )
                    return
                    
                data = await response.json()
                
        # 3. Находим путь к установленной локальной панели
        candidate_paths = [
            "/opt/spectre-panel",
            "/root/Spectre-panel",
            "/home/spectre-panel",
            "/app",
            "/opt/Spectre-panel"
        ]
        
        # fallback to adjacent directory for development/Windows
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # PycharmProjects
        panel_dev_dir = os.path.join(base_dir, "panel")
        if os.path.exists(panel_dev_dir):
            candidate_paths.insert(0, panel_dev_dir)
            
        target_dir = None
        for path in candidate_paths:
            if os.path.exists(path):
                target_dir = path
                break
                
        if not target_dir:
            target_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        config_path = os.path.join(target_dir, "node_config.json")
        
        # Сохраняем конфиг ноды
        config = {
            "node_id": data["node_id"],
            "node_api_token": data["node_api_token"],
            "master_public_key": data["master_public_key"],
            "master_url": master_url,
            "private_key": priv_hex,
            "public_key": pub_hex
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            
        try:
            os.chmod(config_path, 0o600)
        except Exception:
            pass
            
        await status_msg.edit_text(
            f"✅ <b>Сервер успешно настроен как слейв-нода!</b>\n\n"
            f"ID Ноды: <code>{data['node_id']}</code>\n"
            f"Конфиг сохранен в: <code>{config_path}</code>\n"
            f"🔗 Связь с Мастером установлена успешно."
        )
    except Exception as e:
        logging.error(f"Error in setup_slave handler: {e}")
        await status_msg.edit_text(f"❌ <b>Произошла ошибка при настройке слейв-ноды:</b>\n<code>{e}</code>")





