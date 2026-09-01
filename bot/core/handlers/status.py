import logging
import html
import asyncio
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from core.config import settings
from core.messages.i18n import _
from core.sender import send_rich_message, edit_rich_message

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
    
    panels_status = None
    try:
        from core.spectre_client import spectre_manager
        if spectre_manager.panels:
            panels_status = []
            
            async def _check_panel(p):
                try:
                    success, res = await asyncio.wait_for(p.request("GET", "/api/security/system-status"), timeout=2.5)
                    if success and isinstance(res, dict) and res.get("success"):
                        stats = res.get("stats", {})
                        counts = res.get("counts", {})
                        return {
                            "name": p.name,
                            "status": "online",
                            "cpu": stats.get("cpu", 0),
                            "online": counts.get("online_clients", 0),
                            "total": counts.get("total_clients", 0),
                            "url": p.url
                        }
                    elif success and isinstance(res, dict):
                        return {
                            "name": p.name,
                            "status": "online",
                            "url": p.url
                        }
                    else:
                        err = res.get("error", "offline") if isinstance(res, dict) else "offline"
                        return {
                            "name": p.name,
                            "status": "offline",
                            "error": err
                        }
                except Exception as e:
                    return {
                        "name": p.name,
                        "status": "offline",
                        "error": str(e)
                    }

            tasks = [_check_panel(p) for p in spectre_manager.panels.values()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, dict):
                    panels_status.append(res)
    except Exception as e:
        logging.debug("failed_gathering_panels_for_status", e)
    
    return get_system_status_table(
        pve_nodes=pve_nodes,
        pve_error=pve_error,
        pve_configured=pve_configured,
        services=services,
        panels=panels_status
    )

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    response_text = await get_system_status_text()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("keyboards", "btn_refresh_status"), callback_data="status_check")],
        [InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu"), callback_data="main_menu")]
    ])
    await send_rich_message(
        chat_id=message.chat.id,
        text=response_text,
        reply_markup=kb
    )

@router.callback_query(F.data == "status_check")
async def callback_status_check(callback: CallbackQuery):
    response_text = await get_system_status_text()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("keyboards", "btn_refresh_status"), callback_data="status_check")],
        [InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu"), callback_data="main_menu")]
    ])
    
    try:
        if callback.message:
            await edit_rich_message(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=response_text,
                reply_markup=kb
            )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            logging.error("error_showing_systems_status", e)
    finally:
        try:
            await callback.answer()
        except Exception:
            pass

