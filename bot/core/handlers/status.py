import logging
import html
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from core.config import settings

router = Router(name="core_status_router")

def is_task_running(task_name: str) -> bool:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    for t in asyncio.all_tasks(loop):
        if t.get_name() == task_name and not t.done():
            return True
    return False

import asyncio

async def get_system_status_text() -> str:
    from core.messages import get_system_status_table
    from modules.proxmox.api import proxmox
    
    pve_configured = False
    pve_error = None
    pve_nodes = None
    
    try:
        if proxmox.proxmox:
            pve_configured = True
            pve_nodes = proxmox.get_nodes()
    except Exception as e:
        pve_error = str(e)
        
    services = {
        "resource_monitor": is_task_running("monitor_lxc_resources"),
        "auth_watcher": is_task_running("monitor_lxc_auth"),
        "ips_engine": is_task_running("monitor_lxc_traffic"),
        "remote_monitor": is_task_running("monitor_remote_server") if settings.remote_monitor_enable else None
    }
    
    return get_system_status_table(
        pve_nodes=pve_nodes,
        pve_error=pve_error,
        pve_configured=pve_configured,
        services=services
    )

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    from modules.proxmox.monitor.utils import edit_rich_message
    
    status_msg = await message.answer("⏳ <i>Сбор информации о состоянии систем...</i>", parse_mode="HTML")
    response_text = await get_system_status_text()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="status_check")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    await edit_rich_message(
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        text=response_text,
        parse_mode="HTML",
        reply_markup=kb
    )

@router.callback_query(F.data == "status_check")
async def callback_status_check(callback: CallbackQuery):
    from modules.proxmox.monitor.utils import edit_rich_message
    
    try:
        await edit_rich_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="⏳ <i>Сбор информации о состоянии систем...</i>",
            parse_mode="HTML"
        )
    except Exception:
        pass
        
    response_text = await get_system_status_text()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="status_check")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    
    try:
        await edit_rich_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=response_text,
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            logging.error(f"Ошибка при показе статуса систем: {e}")
    finally:
        try:
            await callback.answer()
        except Exception:
            pass
