import logging
import datetime
import html
import asyncio
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile

from core.spectre_client import spectre_manager

router = Router(name="spectre_system_router")

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

from core.messages.spectre import get_panel_status_message

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
        mem_pct = (mem_curr / mem_tot) * 100.0 if mem_tot else 0.0
        uptime = stats.get("uptime", 0)
        
        msg = get_panel_status_message(
            panel_name=panel.name,
            cpu=cpu,
            mem_curr=mem_curr,
            mem_tot=mem_tot,
            mem_pct=mem_pct,
            uptime=uptime,
            total_inbounds=counts.get('total_inbounds', 0),
            total_clients=counts.get('total_clients', 0),
            active_clients=counts.get('active_clients', 0),
            online_clients=counts.get('online_clients', 0),
            blocked_clients=counts.get('blocked_clients', 0)
        )
        await status_msg.delete()
        from modules.proxmox.monitor.utils import send_rich_message
        await send_rich_message(
            chat_id=message.chat.id,
            text=msg,
            parse_mode="markdown"
        )
    else:
        error_info = res.get("msg") or res.get("error") or "Неизвестная ошибка"
        await status_msg.edit_text(f"❌ <b>Ошибка получения статуса {panel.name}:</b>\n<code>{error_info}</code>")

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
