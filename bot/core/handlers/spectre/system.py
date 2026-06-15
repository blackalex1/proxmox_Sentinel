import logging
import datetime
import html
import asyncio
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile

from core.spectre_client import spectre_manager
from core.messages.i18n import _

router = Router(name="spectre_system_router")

@router.message(Command("backup"))
async def cmd_backup(message: types.Message):
    """
    Создает бэкап базы данных.
    """
    panels = spectre_manager.panels
    if not panels:
        await message.reply(_("spectre", "no_panels_err"))
        return
        
    if len(panels) == 1:
        panel_key = list(panels.keys())[0]
        await run_backup_for_panel(message, panel_key)
    else:
        buttons = []
        for p_key, p in panels.items():
            buttons.append([InlineKeyboardButton(text=p.name, callback_data=f"spectre_backup:{p_key}")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply(_("spectre", "select_panel_backup"), reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("spectre_backup:"))
async def cb_backup(callback: CallbackQuery):
    panel_key = callback.data.split(":", 1)[1]
    await callback.message.delete()
    await run_backup_for_panel(callback.message, panel_key)
    await callback.answer()

async def run_backup_for_panel(message: types.Message, panel_key: str):
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await message.answer(_("spectre", "panel_not_found"))
        return
        
    status_msg = await message.answer(_("spectre", "backup_in_progress", name=panel.name))
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
                caption=_("spectre", "backup_success", name=panel.name)
            )
        except Exception as e:
            await status_msg.edit_text(_("spectre", "backup_send_err", error=e))
    else:
        error_info = res.get("msg") or res.get("error") or _("spectre", "unknown_error")
        await status_msg.edit_text(_("spectre", "backup_failed", name=panel.name, error=error_info))

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
        await message.reply(_("spectre", "select_panel_status"), reply_markup=kb, parse_mode="HTML")

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
        await message.answer(_("spectre", "panel_not_found"))
        return
        
    status_msg = await message.answer(_("spectre", "status_fetching", name=panel.name))
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
        error_info = res.get("msg") or res.get("error") or _("spectre", "unknown_error")
        await status_msg.edit_text(_("spectre", "status_failed", name=panel.name, error=error_info))

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
        await message.reply(_("spectre", "no_panels_err"))
        return
        
    status_msg = await message.reply(_("spectre", "traffic_stats_fetching"))
    
    async def fetch_top(panel):
        success, res = await panel.request("GET", "/api/security/top-traffic", params={"period": period})
        return panel, success, res
        
    tasks = [fetch_top(p) for p in panels.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    from core.messages import get_top_traffic_table
    from modules.proxmox.monitor.utils import edit_rich_message
    
    msg = get_top_traffic_table(results, period)
    
    await edit_rich_message(
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        text=msg,
        parse_mode="HTML"
    )

@router.message(Command("audit", "logs"))
async def cmd_audit(message: types.Message):
    """
    Выводит последние 10 действий администраторов из лога аудита.
    """
    panels = spectre_manager.panels
    if not panels:
        await message.reply(_("spectre", "no_panels_err"))
        return
        
    if len(panels) == 1:
        panel_key = list(panels.keys())[0]
        await run_audit_for_panel(message, panel_key)
    else:
        buttons = []
        for p_key, p in panels.items():
            buttons.append([InlineKeyboardButton(text=p.name, callback_data=f"spectre_audit:{p_key}")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply(_("spectre", "select_panel_audit"), reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("spectre_audit:"))
async def cb_audit(callback: CallbackQuery):
    panel_key = callback.data.split(":", 1)[1]
    await callback.message.delete()
    await run_audit_for_panel(callback.message, panel_key)
    await callback.answer()

async def run_audit_for_panel(message: types.Message, panel_key: str):
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await message.answer(_("spectre", "panel_not_found"))
        return
        
    status_msg = await message.answer(_("spectre", "audit_logs_fetching", name=panel.name))
    success, res = await panel.get_audit_logs(limit=10)
    
    if success and res.get("success"):
        logs = res.get("logs", [])
        if not logs:
            await status_msg.edit_text(_("spectre", "audit_logs_empty", name=panel.name))
            return
            
        msg = _("spectre", "audit_logs_title", name=panel.name)
        
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
        error_info = res.get("msg") or res.get("error") or _("spectre", "unknown_error")
        await status_msg.edit_text(_("spectre", "audit_logs_failed", name=panel.name, error=error_info))
