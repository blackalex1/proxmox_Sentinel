import asyncio
import logging
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from modules.proxmox.api import proxmox
from modules.proxmox.keyboards import get_node_keyboard, get_vms_keyboard, get_vm_control_keyboard

router = Router(name="proxmox_router")

class ProxmoxCloneState(StatesGroup):
    waiting_for_new_id = State()
    waiting_for_new_name = State()

@router.callback_query(F.data == "proxmox_main")
async def process_proxmox_main(callback: CallbackQuery):
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = get_node_keyboard().inline_keyboard
        kb.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
        
        await callback.message.edit_text(
            "👨‍💻 <b>Панель управления Proxmox:</b>\nВыберите сервер из списка ниже:", 
            parse_mode="HTML", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка подключения: {e}", show_alert=True)

@router.callback_query(F.data == "back_to_nodes")
async def process_back_to_nodes(callback: CallbackQuery):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = get_node_keyboard().inline_keyboard
    kb.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    await callback.message.edit_text(
        "👨‍💻 <b>Панель управления Proxmox:</b>\nВыберите сервер из списка ниже:", 
        parse_mode="HTML", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("node_"))
async def process_node_select(callback: CallbackQuery):
    try:
        node_name = callback.data.split("_")[1]
        await callback.message.edit_text(
            f"<b>Виртуальные машины на сервере {node_name}:</b>", 
            parse_mode="HTML", 
            reply_markup=get_vms_keyboard(node_name)
        )
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

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
            
            await callback.message.edit_text(
                text, 
                parse_mode="HTML", 
                reply_markup=get_vm_control_keyboard(node_name, vmid, vm_type, is_running=True)
            )
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
        
        await callback.message.edit_text(
            text, 
            parse_mode="HTML", 
            reply_markup=get_vm_control_keyboard(node_name, vmid, vm_type, is_running)
        )
    except Exception as e:
        await callback.answer(f"Ошибка загрузки ВМ: {e}", show_alert=True)

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
        await callback.answer(f"❌ Ошибка команды:\n{e}", show_alert=True)

@router.callback_query(F.data.startswith("cmd_clone_"))
async def start_proxmox_clone(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    node_name = parts[2]
    vmid = parts[3]
    vm_type = parts[4]
    
    await state.update_data(
        node_name=node_name,
        src_vmid=vmid,
        vm_type=vm_type,
        is_lxc=(vm_type == 'lxc')
    )
    
    await state.set_state(ProxmoxCloneState.waiting_for_new_id)
    await callback.message.answer(
        f"📝 <b>Клонирование {vm_type.upper()} {vmid} ({node_name})</b>\n\n"
        f"Введите <b>ID</b> для новой машины (например, 105):",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ProxmoxCloneState.waiting_for_new_id)
async def process_clone_id(message: types.Message, state: FSMContext):
    new_id = message.text.strip()
    if not new_id.isdigit():
        await message.answer("❌ ID должен быть числом! Попробуйте еще раз:")
        return
        
    await state.update_data(new_id=new_id)
    await state.set_state(ProxmoxCloneState.waiting_for_new_name)
    await message.answer("Введите <b>имя</b> для новой машины (например, my-new-server):", parse_mode="HTML")

@router.message(ProxmoxCloneState.waiting_for_new_name)
async def process_clone_name(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    await state.clear()
    
    node_name = data['node_name']
    src_vmid = data['src_vmid']
    new_id = data['new_id']
    is_lxc = data['is_lxc']
    
    status_msg = await message.answer("⏳ Начинаю клонирование...")
    try:
        proxmox.clone_vm(node_name, src_vmid, new_id, new_name, is_lxc)
        await status_msg.edit_text(f"✅ Клонирование успешно запущено!\nНовая машина ID: {new_id}, Имя: {new_name}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка клонирования: {e}")

@router.callback_query(F.data.startswith("lxc_auth_"))
async def process_lxc_auth_logs(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        node_name = parts[2]
        vmid = int(parts[3])
        
        from modules.proxmox.monitor import lxc_auth_history, lxc_name_cache
        name = lxc_name_cache.get(vmid, "Хост Proxmox VE" if vmid == 0 else "Unknown")
        history = lxc_auth_history.get(vmid, [])
        
        if vmid == 0:
            text = f"🔒 <b>Логи авторизации Хоста {node_name}:</b>\n\n"
        else:
            text = f"🔒 <b>Логи авторизации LXC {vmid} ({name}):</b>\n\n"
        
        if not history:
            text += "<i>История пуста или бот был недавно перезапущен. Логи появятся при новых попытках входа.</i>"
        else:
            # Берем последние 12 записей, чтобы сообщение умещалось на экране
            for item in list(history)[-12:]:
                t_emoji = "🟢" if item['type'] == 'SUCCESS' else "🔴" if item['type'] == 'FAILED' else "🛠"
                text += f"{t_emoji} <code>{item['time']}</code> | <b>{item['user']}</b>\n"
                text += f"   └─ {item['msg']} (IP: <code>{item['ip']}</code>)\n\n"
                
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        back_type = 'host' if vmid == 0 else 'lxc'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить лог", callback_data=f"lxc_auth_{node_name}_{vmid}")],
            [InlineKeyboardButton(text="🔙 Назад к ВМ", callback_data=f"vm_{node_name}_{vmid}_{back_type}")]
        ])
        
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        await callback.answer(f"Ошибка получения логов: {e}", show_alert=True)

@router.callback_query(F.data.startswith("lxc_ports_"))
async def process_lxc_port_traffic(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        node_name = parts[2]
        vmid = int(parts[3])
        
        from modules.proxmox.monitor import lxc_traffic_history, lxc_name_cache
        name = lxc_name_cache.get(vmid, "Хост Proxmox VE" if vmid == 0 else "Unknown")
        history = lxc_traffic_history.get(vmid, [])
        
        if vmid == 0:
            text = f"🌐 <b>Сетевая активность Хоста {node_name}:</b>\n"
        else:
            text = f"🌐 <b>Сетевая активность LXC {vmid} ({name}):</b>\n"
        text += "<i>(Последние соединения и уровень их безопасности)</i>\n\n"
        
        if not history:
            text += "<i>Соединений не зафиксировано. Сетевая активность появится при прохождении нового трафика.</i>"
        else:
            # Берем последние 12 записей
            for item in list(history)[-12:]:
                emoji = item.get('risk_emoji', '🟢')
                label = item.get('label', 'Входящее соединение' if item['direction'] == 'IN' else 'Исходящее соединение')
                
                dir_str = "📥 IN" if item['direction'] == 'IN' else "📤 OUT"
                text += f"{emoji} <code>{item['time']}</code> | <b>{dir_str}</b> | <code>{item['proto']}</code>\n"
                text += f"   └─ <b>{label}</b>\n"
                if item['direction'] == 'IN':
                    text += f"      <code>{item['src']}:{item['spt']}</code> ➡️ <b>:{item['dpt']}</b>\n\n"
                else:
                    text += f"      <b>:{item['spt']}</b> ➡️ <code>{item['dst']}:{item['dpt']}</code>\n\n"
                    
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        back_type = 'host' if vmid == 0 else 'lxc'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить активность", callback_data=f"lxc_ports_{node_name}_{vmid}")],
            [InlineKeyboardButton(text="🔙 Назад к ВМ", callback_data=f"vm_{node_name}_{vmid}_{back_type}")]
        ])
        
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        await callback.answer(f"Ошибка получения сетевой активности: {e}", show_alert=True)


@router.callback_query(F.data.startswith("unblock_hysteria:"))
async def process_unblock_hysteria(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        username = parts[1]
        server_ip = parts[2] if len(parts) > 2 else None
        
        await callback.answer(f"⏳ Разблокирую {username}...", show_alert=False)
        
        from core.config import REMOTE_SERVERS
        server = None
        if server_ip:
            for s in REMOTE_SERVERS:
                if s['ip'] == server_ip:
                    server = s
                    break
        if not server and REMOTE_SERVERS:
            server = REMOTE_SERVERS[0]
            
        if not server:
            await callback.answer("❌ Сервер для разблокировки не найден.", show_alert=True)
            return
            
        from modules.proxmox.monitor.remote import unblock_remote_hysteria_user
        success = await unblock_remote_hysteria_user(server, username)
        
        if success:
            await callback.message.edit_text(
                f"✅ <b>Управление доступом Hysteria ({server['ip']}):</b>\n\n"
                f"👤 Пользователь <code>{username}</code> был успешно <b>разблокирован</b> администратором!",
                parse_mode="HTML",
                reply_markup=None
            )
        else:
            await callback.answer(f"❌ Не удалось разблокировать {username} на VPS {server['ip']}. Проверьте логи.", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)
