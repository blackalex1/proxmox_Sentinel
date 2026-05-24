import asyncio
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from modules.proxmox.api import proxmox
from modules.proxmox.keyboards import get_vm_control_keyboard

router = Router(name="proxmox_vms_router")

@router.callback_query(F.data.startswith("vm_"))
async def process_vm_select(callback: CallbackQuery):
    try:
        _, node_name, vmid, vm_type = callback.data.split("_")
        
        if vm_type == 'host' or str(vmid) == '0':
            status_data = proxmox.get_node_status(node_name)
            
            cpu_data = status_data.get('cpuinfo', {})
            cpu_count = cpu_data.get('cpus', 1)
            cpu = status_data.get('cpu', 0) * 100
            
            memory_data = status_data.get('memory', {})
            mem = memory_data.get('used', 0) / (1024**3)
            maxmem = memory_data.get('total', 1) / (1024**3)
            
            uptime = status_data.get('uptime', 0)
            hours, remainder = divmod(uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours}ч {minutes}м {seconds}с"
            
            pve_version = status_data.get('pveversion', 'Unknown')
            
            text = (f"💻 <b>Хост Proxmox VE ({node_name})</b>\n\n"
                    f"Статус: 🟢 Включен\n"
                    f"Версия PVE: <code>{pve_version}</code>\n"
                    f"Ядер CPU: {cpu_count}\n"
                    f"Нагрузка CPU: {cpu:.1f}%\n"
                    f"Потребление RAM: {mem:.1f} / {maxmem:.1f} GB\n"
                    f"Uptime: {uptime_str}")
            
            try:
                await callback.message.edit_text(
                    text, 
                    parse_mode="HTML", 
                    reply_markup=get_vm_control_keyboard(node_name, vmid, vm_type, is_running=True)
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    await callback.answer("Данные хоста актуальны")
                else:
                    raise
            return

        status_data = proxmox.get_vm_status(node_name, vmid, is_lxc=(vm_type=='lxc'))
        
        is_running = status_data.get('status') == 'running'
        status_text = "🟢 Включена" if is_running else "🔴 Выключена"
        
        cpu = status_data.get('cpu', 0) * 100
        mem = status_data.get('mem', 0) / (1024**3)
        maxmem = status_data.get('maxmem', 1) / (1024**3)
        uptime = status_data.get('uptime', 0)
        
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}ч {minutes}м {seconds}с" if is_running else "0ч 0м 0с"
        
        text = (f"🖥 <b>ВМ {vmid} ({status_data.get('name', 'Unknown')})</b>\n\n"
                f"Статус: {status_text}\n"
                f"Тип: {vm_type.upper()}\n"
                f"CPU: {cpu:.1f}%\n"
                f"RAM: {mem:.1f} / {maxmem:.1f} GB\n"
                f"Uptime: {uptime_str}")
        
        try:
            await callback.message.edit_text(
                text, 
                parse_mode="HTML", 
                reply_markup=get_vm_control_keyboard(node_name, vmid, vm_type, is_running)
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("Данные ВМ актуальны")
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка загрузки ВМ: {err_msg}", show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("cmd_"))
async def process_vm_control(callback: CallbackQuery):
    try:
        action, node_name, vmid, vm_type = callback.data.split("_")[1:5]
        is_lxc = (vm_type == 'lxc')
        
        await callback.answer(f"⏳ Выполняю команду {action}...", show_alert=False)
        
        if action == "start": proxmox.start_vm(node_name, vmid, is_lxc)
        elif action == "stop": proxmox.stop_vm(node_name, vmid, is_lxc)
        elif action == "shutdown": proxmox.shutdown_vm(node_name, vmid, is_lxc)
        elif action == "reboot": proxmox.reboot_vm(node_name, vmid, is_lxc)
        
        await asyncio.sleep(2) 
        
        callback.data = f"vm_{node_name}_{vmid}_{vm_type}"
        await process_vm_select(callback)
        
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"❌ Ошибка команды:\n{err_msg}", show_alert=True)
        except Exception:
            pass
