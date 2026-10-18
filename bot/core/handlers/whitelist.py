import logging
import re
from typing import Optional
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.db import get_node_whitelists, save_node_whitelists
from core.spectre_client import spectre_manager
from core.messages.i18n import _

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
            
            logging.info("whitelist_sync_sinkhronizatsiya_ip_s_panelyu", len(merged_ips), panel.name)
            success, res = await panel.request("POST", "/api/security/whitelist/sync", json={"ips": merged_ips})
            if success and res.get("success"):
                logging.info("whitelist_sync_panel_successfully_synchronized", panel.name)
            else:
                logging.warning("whitelist_sync_synchronization_error", panel.name, res.get('msg') or res.get('error'))
    except Exception as e:
        logging.error("whitelist_sync_error_during_synchronization", e)

class WhitelistState(StatesGroup):
    waiting_for_ip_port = State()
    waiting_for_process = State()

def get_node_label(node: str) -> str:
    if node == 'global':
        return _("whitelist", "global_node")
    elif node == 'router':
        return _("whitelist", "router_node")
    elif node == 'local':
        return _("whitelist", "pve_node")
    elif node.startswith("lxc_"):
        vmid = node.split("_")[1]
        panel = spectre_manager.get_panel_by_vmid(int(vmid))
        return _("whitelist", "lxc_node", vmid=vmid, name=panel.name if panel else 'VPN')
    elif node.startswith("vps_"):
        ip = node.split("_")[1]
        return _("whitelist", "vps_node", ip=ip)
    return node

async def get_node_selection_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=_("whitelist", "global_node"), callback_data="wl_view:global")],
        [InlineKeyboardButton(text=_("whitelist", "router_node"), callback_data="wl_view:router")],
        [InlineKeyboardButton(text=_("whitelist", "pve_node"), callback_data="wl_view:local")]
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
            buttons.append([InlineKeyboardButton(text=_("whitelist", "lxc_node", vmid=p.identifier, name=p.name), callback_data=f"wl_view:{node_key}")])
        elif p.source_type == 'vps':
            node_key = f"vps_{p.identifier}"
            active_nodes.add(node_key)
            buttons.append([InlineKeyboardButton(text=_("whitelist", "vps_node", ip=p.identifier), callback_data=f"wl_view:{node_key}")])
            
    # Добавляем неактивные ноды, у которых есть правила в БД
    for node in sorted(nodes_with_rules):
        if node in ('global', 'router', 'local'):
            continue
        if node in active_nodes:
            continue
            
        # Узел не в сети/неактивен, но имеет сохраненные правила в БД
        label = get_node_label(node)
        buttons.append([InlineKeyboardButton(text=_("whitelist", "offline_label", label=label), callback_data=f"wl_view:{node}")])
            
    # Добавляем кнопку просмотра всех правил
    buttons.append([InlineKeyboardButton(text="🌐 Доверенные контейнеры (VPN/P2P)", callback_data="wl_trusted_vmids")])
    buttons.append([InlineKeyboardButton(text=_("whitelist", "btn_show_all"), callback_data="wl_view_all")])
    buttons.append([InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu"), callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("whitelist"))
async def cmd_whitelist(message: types.Message, state: FSMContext):
    await state.clear()
    kb = await get_node_selection_keyboard()
    await message.answer(_("whitelist", "manage_title"), parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "whitelist_main")
async def cb_whitelist_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = await get_node_selection_keyboard()
    try:
        await callback.message.edit_text(_("whitelist", "manage_title"), parse_mode="HTML", reply_markup=kb)
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
        [InlineKeyboardButton(text=_("whitelist", "btn_back_to_nodes"), callback_data="whitelist_main")],
        [InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu"), callback_data="main_menu")]
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
            InlineKeyboardButton(text=_("whitelist", "btn_add_ip_port"), callback_data=f"wl_add_ip_port:{node}"),
            InlineKeyboardButton(text=_("whitelist", "btn_add_proc"), callback_data=f"wl_add_proc:{node}")
        ],
        [InlineKeyboardButton(text=_("whitelist", "btn_delete_rule"), callback_data=f"wl_del_select:{node}")],
        [InlineKeyboardButton(text=_("whitelist", "btn_back_to_nodes_list"), callback_data="whitelist_main")]
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
        _("whitelist", "add_ip_port_title", node_label=get_node_label(node)),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("whitelist", "btn_cancel"), callback_data=f"wl_view:{node}")]
        ])
    )
    await callback.answer()

@router.message(WhitelistState.waiting_for_ip_port)
async def process_ip_port_input(message: types.Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    node = data.get("node")
    
    if not val:
        await message.reply(_("whitelist", "invalid_input"))
        return
        
    # Базовая валидация IP / IP:Port
    # Разрешаем IPv4, IPv4:Port, IPv4:*
    match = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::(?:\d+|\*))?$', val)
    if not match:
        await message.reply(_("whitelist", "invalid_ip_port_format"), parse_mode="HTML")
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
    text = _("whitelist", "rule_added_success", node_label=get_node_label(node))
    if wl["ip_ports"]:
        text += _("whitelist", "allowed_ip_ports")
        for item in wl["ip_ports"]:
            text += f"  • <code>{item}</code>\n"
        text += "\n"
    if wl["processes"]:
        text += _("whitelist", "allowed_processes")
        for item in wl["processes"]:
            text += f"  • <code>{item}</code>\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=_("whitelist", "btn_add_ip_port"), callback_data=f"wl_add_ip_port:{node}"),
            InlineKeyboardButton(text=_("whitelist", "btn_add_proc"), callback_data=f"wl_add_proc:{node}")
        ],
        [InlineKeyboardButton(text=_("whitelist", "btn_delete_rule"), callback_data=f"wl_del_select:{node}")],
        [InlineKeyboardButton(text=_("whitelist", "btn_back_to_nodes_list"), callback_data="whitelist_main")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("wl_add_proc:"))
async def cb_whitelist_add_proc(callback: CallbackQuery, state: FSMContext):
    node = callback.data.split(":", 1)[1]
    await state.update_data(node=node)
    await state.set_state(WhitelistState.waiting_for_process)
    
    await callback.message.edit_text(
        _("whitelist", "add_proc_title", node_label=get_node_label(node)),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("whitelist", "btn_cancel"), callback_data=f"wl_view:{node}")]
        ])
    )
    await callback.answer()

@router.message(WhitelistState.waiting_for_process)
async def process_process_input(message: types.Message, state: FSMContext):
    val = message.text.strip().lower()
    data = await state.get_data()
    node = data.get("node")
    
    if not val or not val.isalnum():
        await message.reply(_("whitelist", "invalid_proc_name"))
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
    text = _("whitelist", "proc_added_success", node_label=get_node_label(node))
    if wl["ip_ports"]:
        text += _("whitelist", "allowed_ip_ports")
        for item in wl["ip_ports"]:
            text += f"  • <code>{item}</code>\n"
        text += "\n"
    if wl["processes"]:
        text += _("whitelist", "allowed_processes")
        for item in wl["processes"]:
            text += f"  • <code>{item}</code>\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=_("whitelist", "btn_add_ip_port"), callback_data=f"wl_add_ip_port:{node}"),
            InlineKeyboardButton(text=_("whitelist", "btn_add_proc"), callback_data=f"wl_add_proc:{node}")
        ],
        [InlineKeyboardButton(text=_("whitelist", "btn_delete_rule"), callback_data=f"wl_del_select:{node}")],
        [InlineKeyboardButton(text=_("whitelist", "btn_back_to_nodes_list"), callback_data="whitelist_main")]
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
        await callback.answer(_("whitelist", "empty_whitelist_err"), show_alert=True)
        return
        
    buttons = []
    
    for item in ip_ports:
        buttons.append([InlineKeyboardButton(text=_("whitelist", "btn_del_ip", item=item), callback_data=f"wl_del_item:{node}:ip_ports:{item}")])
    for item in processes:
        buttons.append([InlineKeyboardButton(text=_("whitelist", "btn_del_proc", item=item), callback_data=f"wl_del_item:{node}:processes:{item}")])
        
    buttons.append([InlineKeyboardButton(text=_("whitelist", "btn_back_to_view"), callback_data=f"wl_view:{node}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(_("whitelist", "del_rule_title", node_label=get_node_label(node)), parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("wl_del_item:"))
async def cb_whitelist_del_item(callback: CallbackQuery):
    raw = callback.data.removeprefix("wl_del_item:")
    if ":ip_ports:" in raw:
        node, item = raw.split(":ip_ports:", 1)
        item_type = "ip_ports"
    elif ":processes:" in raw:
        node, item = raw.split(":processes:", 1)
        item_type = "processes"
    else:
        parts = raw.split(":", 2)
        if len(parts) >= 3:
            node, item_type, item = parts[0], parts[1], parts[2]
        else:
            return
    
    whitelists = await get_node_whitelists()
    if node in whitelists and item_type in whitelists[node]:
        if item in whitelists[node][item_type]:
            whitelists[node][item_type].remove(item)
            await save_node_whitelists(whitelists)
            await sync_whitelists_to_panels()
            await callback.answer(_("whitelist", "del_success_alert", item=item), show_alert=True)
            
    # Обновляем меню выбора удаления
    await cb_whitelist_del_select(callback)


# --- SLASH COMMANDS HANDLERS ---

@router.message(Command("whitelist_add"))
async def cmd_whitelist_add_cli(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply(_("whitelist", "cli_add_help"), parse_mode="HTML")
        return
        
    val = args[1].strip()
    node = args[2].strip() if len(args) > 2 else "global"
    
    match = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::(?:\d+|\*))?$', val)
    if not match:
        await message.reply(_("whitelist", "cli_invalid_ip_port"))
        return
        
    whitelists = await get_node_whitelists()
    if node not in whitelists:
        whitelists[node] = {"ip_ports": [], "processes": []}
        
    if val not in whitelists[node]["ip_ports"]:
        whitelists[node]["ip_ports"].append(val)
        await save_node_whitelists(whitelists)
        await sync_whitelists_to_panels()
        await message.reply(_("whitelist", "cli_added_ip_port", val=val, label=get_node_label(node)), parse_mode="HTML")
    else:
        await message.reply(_("whitelist", "cli_rule_exists", val=val, label=get_node_label(node)), parse_mode="HTML")

@router.message(Command("whitelist_process"))
async def cmd_whitelist_process_cli(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply(_("whitelist", "cli_proc_help"), parse_mode="HTML")
        return
        
    val = args[1].strip().lower()
    node = args[2].strip() if len(args) > 2 else "global"
    
    if not val or not val.isalnum():
        await message.reply(_("whitelist", "cli_invalid_proc"))
        return
        
    whitelists = await get_node_whitelists()
    if node not in whitelists:
        whitelists[node] = {"ip_ports": [], "processes": []}
        
    if val not in whitelists[node]["processes"]:
        whitelists[node]["processes"].append(val)
        await save_node_whitelists(whitelists)
        await sync_whitelists_to_panels()
        await message.reply(_("whitelist", "cli_added_proc", val=val, label=get_node_label(node)), parse_mode="HTML")
    else:
        await message.reply(_("whitelist", "cli_proc_exists", val=val, label=get_node_label(node)), parse_mode="HTML")


@router.callback_query(F.data.startswith("qwl:"))
async def cb_quick_whitelist(callback: CallbackQuery):
    try:
        raw = callback.data.removeprefix("qwl:")
        if ":ip:" in raw:
            node, val = raw.split(":ip:", 1)
            wl_type = "ip"
        elif ":ipport:" in raw:
            node, val = raw.split(":ipport:", 1)
            wl_type = "ipport"
        else:
            parts = raw.split(":", 2)
            if len(parts) >= 3:
                node, wl_type, val = parts[0], parts[1], parts[2]
            else:
                await callback.answer(_("whitelist", "qwl_invalid_callback"), show_alert=True)
                return
        
        # Если тип ipport, val содержит ip:port. Если тип ip, val содержит ip.
        whitelists = await get_node_whitelists()
        if node not in whitelists:
            whitelists[node] = {"ip_ports": [], "processes": []}
            
        if val not in whitelists[node]["ip_ports"]:
            whitelists[node]["ip_ports"].append(val)
            await save_node_whitelists(whitelists)
            await sync_whitelists_to_panels()
            
            await callback.answer(_("whitelist", "qwl_added_success", label=get_node_label(node), val=val), show_alert=True)
            
            orig_text = callback.message.html_text or callback.message.text or ""
            new_text = f"{orig_text}" + _("whitelist", "qwl_added_msg", label=get_node_label(node), val=val)
            try:
                await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)
            except Exception:
                pass
        else:
            await callback.answer(_("whitelist", "qwl_already_whitelisted", label=get_node_label(node)), show_alert=True)
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
    except Exception as e:
        logging.error("error_during_quick_white-listing", e)
        await callback.answer(_("whitelist", "qwl_save_error"), show_alert=True)


@router.callback_query(F.data == "wl_trusted_vmids")
async def cb_whitelist_trusted_vmids(callback: CallbackQuery, state: Optional[FSMContext] = None):
    if state:
        await state.clear()
    from modules.proxmox.monitor.traffic.parser import get_trusted_vpn_vmids_sync
    trusted = get_trusted_vpn_vmids_sync()
    
    text = (
        "🌐 <b>Доверенные LXC контейнеры (VPN / P2P транзит)</b>\n"
        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        "Контейнерам из этого списка <b>разрешены любые исходящие порты</b> (для P2P, стриминга, BitTorrent, Shadowsocks/SS-KD и клиентов).\n"
        "При этом любые попытки доступа на <b>sensitive порты</b> (SSH 22, БД, Proxmox 8006) продолжают строго отслеживаться и пресекаться.\n\n"
    )
    if trusted:
        text += "<b>Активные доверенные контейнеры:</b>\n"
        for v in trusted:
            panel = spectre_manager.get_panel_by_vmid(v)
            name = f" ({panel.name})" if panel else ""
            text += f"• <b>LXC {v}</b>{name} — <i>VPN/P2P режим активен</i>\n"
    else:
        text += "<i>В списке пока нет доверенных контейнеров.</i>\n"

    kb_buttons = []
    # Кнопки для удаления каждого доверенного контейнера
    for v in trusted:
        kb_buttons.append([
            InlineKeyboardButton(text=f"🗑 Убрать LXC {v} из доверенных", callback_data=f"untrust_lxc:{v}")
        ])
    
    kb_buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="whitelist_main")
    ])
    
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    try:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("trust_lxc:"))
async def cb_trust_lxc(callback: CallbackQuery):
    try:
        vmid_str = callback.data.split(":", 1)[1]
        vmid = int(vmid_str)
        from core.db import add_trusted_vpn_vmid
        await add_trusted_vpn_vmid(vmid)
        from modules.proxmox.monitor.traffic.parser import update_trusted_vpn_vmids_cache
        await update_trusted_vpn_vmids_cache()
        try:
            from modules.proxmox.monitor.firewall import setup_vpn_container_rules
            setup_vpn_container_rules()
        except Exception:
            pass

        await callback.answer(
            f"✅ LXC {vmid} добавлен в доверенные узлы (VPN/P2P)!\nВсе порты разрешены, кроме sensitive.",
            show_alert=True
        )
        orig_text = callback.message.html_text or callback.message.text or ""
        new_text = f"{orig_text}\n\n🌐 <b>LXC {vmid} переведен в доверенный режим (VPN/P2P)</b>"
        try:
            await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
    except Exception as e:
        logging.error("error_trusting_lxc", e)
        await callback.answer("Ошибка при добавлении контейнера в доверенные", show_alert=True)


@router.callback_query(F.data.startswith("untrust_lxc:"))
async def cb_untrust_lxc(callback: CallbackQuery):
    try:
        vmid_str = callback.data.split(":", 1)[1]
        vmid = int(vmid_str)
        from core.db import remove_trusted_vpn_vmid
        await remove_trusted_vpn_vmid(vmid)
        from modules.proxmox.monitor.traffic.parser import update_trusted_vpn_vmids_cache
        await update_trusted_vpn_vmids_cache()
        try:
            from modules.proxmox.monitor.firewall import cleanup_vpn_container_rules
            cleanup_vpn_container_rules(vmid)
        except Exception:
            pass

        await callback.answer(
            f"⚠️ LXC {vmid} удален из доверенных узлов. Включен строгий режим мониторинга.",
            show_alert=True
        )
        # Если мы были в меню доверенных, обновляем список
        if callback.message and "Доверенные LXC контейнеры" in (callback.message.text or ""):
            await cb_whitelist_trusted_vmids(callback, None)
        else:
            orig_text = callback.message.html_text or callback.message.text or ""
            new_text = f"{orig_text}\n\n⚠️ <b>LXC {vmid} удален из доверенных (строгий режим)</b>"
            try:
                await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)
            except Exception:
                pass
    except Exception as e:
        logging.error("error_untrusting_lxc", e)
        await callback.answer("Ошибка при удалении контейнера из доверенных", show_alert=True)


@router.callback_query(F.data.startswith("qblock:ip:"))
async def cb_quick_block_ip(callback: CallbackQuery):
    try:
        ip = callback.data.removeprefix("qblock:ip:")
        from modules.proxmox.monitor.traffic.firewall import block_local_ip
        await block_local_ip(ip, delay=3600, reason="Быстрая блокировка из алерта")
        await callback.answer(f"🚫 IP {ip} заблокирован на 1 час (iptables DROP)", show_alert=True)

        orig_text = callback.message.html_text or callback.message.text or ""
        new_text = f"{orig_text}\n\n🚫 <b>IP {ip} заблокирован на 1 час (iptables DROP)</b>"
        try:
            await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
    except Exception as e:
        logging.error("error_quick_blocking_ip", e)
        await callback.answer("Ошибка при блокировке IP", show_alert=True)


@router.callback_query(F.data.startswith("copy:ip:"))
async def cb_copy_ip(callback: CallbackQuery):
    try:
        ip = callback.data.removeprefix("copy:ip:")
        await callback.answer(f"{ip}", show_alert=True)
    except Exception:
        await callback.answer()
