import logging
import re
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.db import get_node_whitelists, save_node_whitelists
from core.spectre_client import spectre_manager

router = Router(name="core_whitelist_router")


async def sync_whitelists_to_panels():
    """
    Синхронизирует белые списки с базами данных всех Spectre Panels.
    Отправляет для каждой панели объединение её правил и глобальных правил.
    """
    try:
        whitelists = await get_node_whitelists()
        global_ips = whitelists.get("global", {}).get("ip_ports", [])
        
        for p_key, panel in spectre_manager.panels.items():
            node_ips = whitelists.get(p_key, {}).get("ip_ports", [])
            merged_ips = list(set(global_ips + node_ips))
            
            logging.info(f"[Whitelist Sync] Синхронизация {len(merged_ips)} IP с панелью {panel.name}...")
            success, res = await panel.request("POST", "/api/security/whitelist/sync", json={"ips": merged_ips})
            if success and res.get("success"):
                logging.info(f"[Whitelist Sync] Панель {panel.name} успешно синхронизирована.")
            else:
                logging.warning(f"[Whitelist Sync] Ошибка синхронизации с {panel.name}: {res.get('msg') or res.get('error')}")
    except Exception as e:
        logging.error(f"[Whitelist Sync] Ошибка во время синхронизации: {e}")

class WhitelistState(StatesGroup):
    waiting_for_ip_port = State()
    waiting_for_process = State()

def get_node_label(node: str) -> str:
    if node == 'global':
        return "🌍 Глобально (Везде)"
    elif node == 'router':
        return "🔌 Роутер"
    elif node == 'local':
        return "🖥️ Proxmox Host"
    elif node.startswith("lxc_"):
        vmid = node.split("_")[1]
        panel = spectre_manager.get_panel_by_vmid(int(vmid))
        return f"📦 LXC {vmid} ({panel.name if panel else 'VPN'})"
    elif node.startswith("vps_"):
        ip = node.split("_")[1]
        return f"🌐 VPS {ip}"
    return node

async def get_node_selection_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🌍 Глобально (Везде)", callback_data="wl_view:global")],
        [InlineKeyboardButton(text="🔌 Роутер", callback_data="wl_view:router")],
        [InlineKeyboardButton(text="🖥️ Proxmox Host", callback_data="wl_view:local")]
    ]
    
    # Получаем все правила из БД, чтобы отобразить даже выключенные/офлайн ноды
    whitelists = await get_node_whitelists()
    nodes_with_rules = set()
    for k, v in whitelists.items():
        if v.get("ip_ports") or v.get("processes"):
            nodes_with_rules.add(k)
            
    active_nodes = set()
    
    # Добавляем обнаруженные активные панели
    for p_key, p in spectre_manager.panels.items():
        if p.source_type == 'lxc':
            node_key = f"lxc_{p.identifier}"
            active_nodes.add(node_key)
            buttons.append([InlineKeyboardButton(text=f"📦 LXC {p.identifier} ({p.name})", callback_data=f"wl_view:{node_key}")])
        elif p.source_type == 'vps':
            node_key = f"vps_{p.identifier}"
            active_nodes.add(node_key)
            buttons.append([InlineKeyboardButton(text=f"🌐 VPS {p.identifier}", callback_data=f"wl_view:{node_key}")])
            
    # Добавляем неактивные ноды, у которых есть правила в БД
    for node in sorted(nodes_with_rules):
        if node in ('global', 'router', 'local'):
            continue
        if node in active_nodes:
            continue
            
        # Узел не в сети/неактивен, но имеет сохраненные правила в БД
        label = get_node_label(node)
        buttons.append([InlineKeyboardButton(text=f"{label} (офлайн)", callback_data=f"wl_view:{node}")])
            
    # Добавляем кнопку просмотра всех правил
    buttons.append([InlineKeyboardButton(text="📋 Показать все правила", callback_data="wl_view_all")])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("whitelist"))
async def cmd_whitelist(message: types.Message, state: FSMContext):
    await state.clear()
    kb = await get_node_selection_keyboard()
    await message.answer("⚙️ <b>Управление белыми списками Aegis IPS</b>\n\nВыберите узел (ноду) для просмотра и настройки правил безопасности:", parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "whitelist_main")
async def cb_whitelist_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = await get_node_selection_keyboard()
    try:
        await callback.message.edit_text("⚙️ <b>Управление белыми списками Aegis IPS</b>\n\nВыберите узел (ноду) для просмотра и настройки правил безопасности:", parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data == "wl_view_all")
async def cb_whitelist_view_all(callback: CallbackQuery):
    from core.messages import get_whitelist_view_all_table
    from modules.proxmox.monitor.utils import edit_rich_message
    
    whitelists = await get_node_whitelists()
    msg_text = get_whitelist_view_all_table(whitelists, get_node_label)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К выбору узла", callback_data="whitelist_main")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    
    await edit_rich_message(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=msg_text,
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("wl_view:"))
async def cb_whitelist_view(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    node = callback.data.split(":", 1)[1]
    
    whitelists = await get_node_whitelists()
    wl = whitelists.get(node, {"ip_ports": [], "processes": []})
    
    ip_ports = wl.get("ip_ports", [])
    processes = wl.get("processes", [])
    
    from core.messages import get_whitelist_view_table
    from modules.proxmox.monitor.utils import edit_rich_message
    
    text = get_whitelist_view_table(get_node_label(node), ip_ports, processes)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить IP/Порт", callback_data=f"wl_add_ip_port:{node}"),
            InlineKeyboardButton(text="➕ Добавить Процесс", callback_data=f"wl_add_proc:{node}")
        ],
        [InlineKeyboardButton(text="🗑️ Удалить правило", callback_data=f"wl_del_select:{node}")],
        [InlineKeyboardButton(text="🔙 Назад к списку узлов", callback_data="whitelist_main")]
    ])
    
    try:
        await edit_rich_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("wl_add_ip_port:"))
async def cb_whitelist_add_ip_port(callback: CallbackQuery, state: FSMContext):
    node = callback.data.split(":", 1)[1]
    await state.update_data(node=node)
    await state.set_state(WhitelistState.waiting_for_ip_port)
    
    await callback.message.edit_text(
        f"➕ <b>Добавление IP/Порта в белый список</b>\nУзел: {get_node_label(node)}\n\n"
        f"Отправьте сообщением IP-адрес или связку IP:Порт (например: <code>1.2.3.4</code> или <code>1.2.3.4:22</code>, или <code>1.2.3.4:*</code> для любого порта):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"wl_view:{node}")]
        ])
    )
    await callback.answer()

@router.message(WhitelistState.waiting_for_ip_port)
async def process_ip_port_input(message: types.Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    node = data.get("node")
    
    if not val:
        await message.reply("Неверный ввод. Попробуйте еще раз или нажмите Отмена.")
        return
        
    # Базовая валидация IP / IP:Port
    # Разрешаем IPv4, IPv4:Port, IPv4:*
    match = re.match(r'^^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::(?:\d+|\*))?$$', val)
    if not match:
        await message.reply("❌ Неверный формат IP/Порта. Примеры: <code>192.168.1.100</code> или <code>192.168.1.100:22</code> или <code>192.168.1.100:*</code>.", parse_mode="HTML")
        return
        
    whitelists = await get_node_whitelists()
    if node not in whitelists:
        whitelists[node] = {"ip_ports": [], "processes": []}
        
    if val not in whitelists[node]["ip_ports"]:
        whitelists[node]["ip_ports"].append(val)
        await save_node_whitelists(whitelists)
        await sync_whitelists_to_panels()
        
    await state.clear()
    
    # Возвращаемся к просмотру ноды
    wl = whitelists[node]
    text = f"🟢 <b>Правило успешно добавлено!</b>\n\n📁 <b>Белый список для узла: {get_node_label(node)}</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    if wl["ip_ports"]:
        text += "<b>Разрешенные IP / IP:Порты:</b>\n"
        for item in wl["ip_ports"]:
            text += f"  • <code>{item}</code>\n"
        text += "\n"
    if wl["processes"]:
        text += "<b>Разрешенные процессы:</b>\n"
        for item in wl["processes"]:
            text += f"  • <code>{item}</code>\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить IP/Порт", callback_data=f"wl_add_ip_port:{node}"),
            InlineKeyboardButton(text="➕ Добавить Процесс", callback_data=f"wl_add_proc:{node}")
        ],
        [InlineKeyboardButton(text="🗑️ Удалить правило", callback_data=f"wl_del_select:{node}")],
        [InlineKeyboardButton(text="🔙 Назад к списку узлов", callback_data="whitelist_main")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("wl_add_proc:"))
async def cb_whitelist_add_proc(callback: CallbackQuery, state: FSMContext):
    node = callback.data.split(":", 1)[1]
    await state.update_data(node=node)
    await state.set_state(WhitelistState.waiting_for_process)
    
    await callback.message.edit_text(
        f"➕ <b>Добавление процесса в белый список</b>\nУзел: {get_node_label(node)}\n\n"
        f"Отправьте сообщением имя процесса (например: <code>caddy</code>, <code>nginx</code> или <code>sshd</code>):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"wl_view:{node}")]
        ])
    )
    await callback.answer()

@router.message(WhitelistState.waiting_for_process)
async def process_process_input(message: types.Message, state: FSMContext):
    val = message.text.strip().lower()
    data = await state.get_data()
    node = data.get("node")
    
    if not val or not val.isalnum():
        await message.reply("❌ Неверное имя процесса (разрешены только латинские буквы и цифры). Попробуйте еще раз.")
        return
        
    whitelists = await get_node_whitelists()
    if node not in whitelists:
        whitelists[node] = {"ip_ports": [], "processes": []}
        
    if val not in whitelists[node]["processes"]:
        whitelists[node]["processes"].append(val)
        await save_node_whitelists(whitelists)
        await sync_whitelists_to_panels()
        
    await state.clear()
    
    wl = whitelists[node]
    text = f"🟢 <b>Процесс успешно добавлен!</b>\n\n📁 <b>Белый список для узла: {get_node_label(node)}</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    if wl["ip_ports"]:
        text += "<b>Разрешенные IP / IP:Порты:</b>\n"
        for item in wl["ip_ports"]:
            text += f"  • <code>{item}</code>\n"
        text += "\n"
    if wl["processes"]:
        text += "<b>Разрешенные процессы:</b>\n"
        for item in wl["processes"]:
            text += f"  • <code>{item}</code>\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить IP/Порт", callback_data=f"wl_add_ip_port:{node}"),
            InlineKeyboardButton(text="➕ Добавить Процесс", callback_data=f"wl_add_proc:{node}")
        ],
        [InlineKeyboardButton(text="🗑️ Удалить правило", callback_data=f"wl_del_select:{node}")],
        [InlineKeyboardButton(text="🔙 Назад к списку узлов", callback_data="whitelist_main")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("wl_del_select:"))
async def cb_whitelist_del_select(callback: CallbackQuery):
    node = callback.data.split(":", 1)[1]
    
    whitelists = await get_node_whitelists()
    wl = whitelists.get(node, {"ip_ports": [], "processes": []})
    
    ip_ports = wl.get("ip_ports", [])
    processes = wl.get("processes", [])
    
    if not ip_ports and not processes:
        await callback.answer("❌ Белый список этого узла пуст. Нечего удалять.", show_alert=True)
        return
        
    buttons = []
    
    for item in ip_ports:
        buttons.append([InlineKeyboardButton(text=f"🗑️ IP: {item}", callback_data=f"wl_del_item:{node}:ip_ports:{item}")])
    for item in processes:
        buttons.append([InlineKeyboardButton(text=f"🗑️ Proc: {item}", callback_data=f"wl_del_item:{node}:processes:{item}")])
        
    buttons.append([InlineKeyboardButton(text="🔙 Назад к просмотру", callback_data=f"wl_view:{node}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(f"🗑️ <b>Удаление правил белого списка</b>\nУзел: {get_node_label(node)}\n\nВыберите правило, которое хотите удалить:", parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("wl_del_item:"))
async def cb_whitelist_del_item(callback: CallbackQuery):
    parts = callback.data.split(":", 3)
    node = parts[1]
    item_type = parts[2] # "ip_ports" или "processes"
    item = parts[3]
    
    whitelists = await get_node_whitelists()
    if node in whitelists and item_type in whitelists[node]:
        if item in whitelists[node][item_type]:
            whitelists[node][item_type].remove(item)
            await save_node_whitelists(whitelists)
            await sync_whitelists_to_panels()
            await callback.answer(f"🟢 Успешно удалено: {item}", show_alert=True)
            
    # Обновляем меню выбора удаления
    await cb_whitelist_del_select(callback)


# --- SLASH COMMANDS HANDLERS ---

@router.message(Command("whitelist_add"))
async def cmd_whitelist_add_cli(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply("❌ Использование: <code>/whitelist_add &lt;IP или IP:Port&gt; [node]</code>\nПример: <code>/whitelist_add 1.2.3.4:22 router</code>", parse_mode="HTML")
        return
        
    val = args[1].strip()
    node = args[2].strip() if len(args) > 2 else "global"
    
    match = re.match(r'^^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::(?:\d+|\*))?$$', val)
    if not match:
        await message.reply("❌ Неверный формат IP/Порта.")
        return
        
    whitelists = await get_node_whitelists()
    if node not in whitelists:
        whitelists[node] = {"ip_ports": [], "processes": []}
        
    if val not in whitelists[node]["ip_ports"]:
        whitelists[node]["ip_ports"].append(val)
        await save_node_whitelists(whitelists)
        await sync_whitelists_to_panels()
        await message.reply(f"🟢 Добавлено <code>{val}</code> в белый список узла <b>{get_node_label(node)}</b>.", parse_mode="HTML")
    else:
        await message.reply(f"ℹ️ Правило <code>{val}</code> уже существует для узла <b>{get_node_label(node)}</b>.", parse_mode="HTML")

@router.message(Command("whitelist_process"))
async def cmd_whitelist_process_cli(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply("❌ Использование: <code>/whitelist_process &lt;имя процесса&gt; [node]</code>\nПример: <code>/whitelist_process openvpn global</code>", parse_mode="HTML")
        return
        
    val = args[1].strip().lower()
    node = args[2].strip() if len(args) > 2 else "global"
    
    if not val or not val.isalnum():
        await message.reply("❌ Неверное имя процесса.")
        return
        
    whitelists = await get_node_whitelists()
    if node not in whitelists:
        whitelists[node] = {"ip_ports": [], "processes": []}
        
    if val not in whitelists[node]["processes"]:
        whitelists[node]["processes"].append(val)
        await save_node_whitelists(whitelists)
        await sync_whitelists_to_panels()
        await message.reply(f"🟢 Добавлен процесс <code>{val}</code> в белый список узла <b>{get_node_label(node)}</b>.", parse_mode="HTML")
    else:
        await message.reply(f"ℹ️ Процесс <code>{val}</code> уже находится в белом списке узла <b>{get_node_label(node)}</b>.", parse_mode="HTML")


@router.callback_query(F.data.startswith("qwl:"))
async def cb_quick_whitelist(callback: CallbackQuery):
    try:
        parts = callback.data.split(":", 3)
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат callback-данных.", show_alert=True)
            return
            
        node = parts[1]
        wl_type = parts[2]
        val = parts[3]
        
        # Если тип ipport, val содержит ip:port. Если тип ip, val содержит ip.
        whitelists = await get_node_whitelists()
        if node not in whitelists:
            whitelists[node] = {"ip_ports": [], "processes": []}
            
        if val not in whitelists[node]["ip_ports"]:
            whitelists[node]["ip_ports"].append(val)
            await save_node_whitelists(whitelists)
            await sync_whitelists_to_panels()
            
            await callback.answer(f"🟢 Успешно добавлено в белый список {get_node_label(node)}: {val}", show_alert=True)
            
            orig_text = callback.message.html_text or callback.message.text or ""
            new_text = f"{orig_text}\n\n✅ <b>Добавлено в белый список ({get_node_label(node)}):</b> <code>{val}</code>"
            try:
                await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)
            except Exception:
                pass
        else:
            await callback.answer(f"ℹ️ Уже находится в белом списке {get_node_label(node)}.", show_alert=True)
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
    except Exception as e:
        logging.error(f"Ошибка при быстром добавлении в белый список: {e}")
        await callback.answer("❌ Произошла ошибка при сохранении.", show_alert=True)
