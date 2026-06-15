import asyncio
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from modules.proxmox.api import proxmox
from modules.proxmox.keyboards import get_vm_control_keyboard
from core.messages.i18n import _

router = Router(name="proxmox_vms_router")

@router.callback_query(F.data.startswith("vm_"))
async def process_vm_select(callback: CallbackQuery):
    try:
        # callback.data starts with "vm_"
        data = callback.data[len("vm_"):]
        parts = data.rsplit("_", 2)
        node_name = parts[0]
        vmid = parts[1]
        vm_type = parts[2]
        
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
            uptime_str = _("proxmox", "uptime_format", hours=hours, minutes=minutes, seconds=seconds)
            
            pve_version = status_data.get('pveversion', 'Unknown')
            status_online = _("proxmox", "status_online_host")
            
            text = (f"{_('proxmox', 'status_host_title', node_name=node_name)}"
                    f"{_('proxmox', 'status_label')}: {status_online}\n"
                    f"{_('proxmox', 'version_label')}: <code>{pve_version}</code>\n"
                    f"{_('proxmox', 'cpu_cores_label')}: {cpu_count}\n"
                    f"{_('proxmox', 'cpu_load_label')}: {cpu:.1f}%\n"
                    f"{_('proxmox', 'ram_usage_label')}: {mem:.1f} / {maxmem:.1f} GB\n"
                    f"{_('proxmox', 'uptime_label')}: {uptime_str}")
            
            try:
                await callback.message.edit_text(
                    text, 
                    parse_mode="HTML", 
                    reply_markup=get_vm_control_keyboard(node_name, vmid, vm_type, is_running=True)
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    await callback.answer(_("proxmox", "host_data_actual"))
                else:
                    raise
            return

        status_data = proxmox.get_vm_status(node_name, vmid, is_lxc=(vm_type=='lxc'))
        
        is_running = status_data.get('status') == 'running'
        status_text = _("proxmox", "status_online_vm") if is_running else _("proxmox", "status_offline_vm")
        
        cpu = status_data.get('cpu', 0) * 100
        mem = status_data.get('mem', 0) / (1024**3)
        maxmem = status_data.get('maxmem', 1) / (1024**3)
        uptime = status_data.get('uptime', 0)
        
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if is_running:
            uptime_str = _("proxmox", "uptime_format", hours=hours, minutes=minutes, seconds=seconds)
        else:
            uptime_str = _("proxmox", "uptime_format", hours=0, minutes=0, seconds=0)
        
        text = (f"{_('proxmox', 'status_vm_title', vmid=vmid, name=status_data.get('name', 'Unknown'))}"
                f"{_('proxmox', 'status_label')}: {status_text}\n"
                f"{_('proxmox', 'type_label')}: {vm_type.upper()}\n"
                f"CPU: {cpu:.1f}%\n"
                f"RAM: {mem:.1f} / {maxmem:.1f} GB\n"
                f"{_('proxmox', 'uptime_label')}: {uptime_str}")
        
        try:
            await callback.message.edit_text(
                text, 
                parse_mode="HTML", 
                reply_markup=get_vm_control_keyboard(node_name, vmid, vm_type, is_running)
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer(_("proxmox", "vm_data_actual"))
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(_("proxmox", "error_vm_load", err_msg=err_msg), show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("cmd_"))
async def process_vm_control(callback: CallbackQuery):
    try:
        # callback.data looks like "cmd_{action}_{node_name}_{vmid}_{vm_type}"
        data = callback.data[len("cmd_"):]
        parts = data.split("_", 1)
        action = parts[0]
        remaining = parts[1]
        
        rem_parts = remaining.rsplit("_", 2)
        node_name = rem_parts[0]
        vmid = rem_parts[1]
        vm_type = rem_parts[2]
        
        is_lxc = (vm_type == 'lxc')
        
        await callback.answer(_("proxmox", "exec_cmd", action=action), show_alert=False)
        
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
            await callback.answer(_("proxmox", "error_cmd", err_msg=err_msg), show_alert=True)
        except Exception:
            pass
