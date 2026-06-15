import html
import logging
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from core.messages.i18n import _

router = Router(name="proxmox_logs_router")

@router.callback_query(F.data.startswith("lxc_auth_"))
async def process_lxc_auth_logs(callback: CallbackQuery):
    try:
        # callback.data looks like "lxc_auth_{node_name}_{vmid}"
        data = callback.data[len("lxc_auth_"):]
        node_name, vmid_str = data.rsplit("_", 1)
        vmid = int(vmid_str)
        
        from modules.proxmox.monitor import lxc_auth_history, lxc_name_cache
        name = lxc_name_cache.get(vmid, _("proxmox", "host_label_default") if vmid == 0 else "Unknown")
        history = lxc_auth_history.get(vmid, [])
        
        if vmid == 0:
            text = _("proxmox", "auth_logs_host_title", node_name=node_name)
        else:
            text = _("proxmox", "auth_logs_lxc_title", vmid=vmid, name=name)
        
        if not history:
            text += _("proxmox", "logs_empty")
        else:
            for item in list(history)[-10:]:
                t_emoji = "🟢" if item.get('type') == 'SUCCESS' else "🔴" if item.get('type') == 'FAILED' else "🛠"
                user_esc = html.escape(str(item.get('user', 'unknown'))[:30])
                msg_esc = html.escape(str(item.get('msg', ''))[:80])
                ip_esc = html.escape(str(item.get('ip', 'N/A'))[:45])
                text += f"{t_emoji} <code>{item.get('time', '')}</code> | <b>{user_esc}</b>\n"
                text += f"   └─ {msg_esc} (IP: <code>{ip_esc}</code>)\n\n"
                
        if len(text) > 4000:
            text = text[:3900] + _("proxmox", "logs_truncated")

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        back_type = 'host' if vmid == 0 else 'lxc'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("proxmox", "refresh_log_btn"), callback_data=f"lxc_auth_{node_name}_{vmid}")],
            [InlineKeyboardButton(text=_("proxmox", "back_to_vm_btn"), callback_data=f"vm_{node_name}_{vmid}_{back_type}")]
        ])
        
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer(_("proxmox", "log_actual"))
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(_("proxmox", "log_error", err_msg=err_msg), show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("lxc_ports_"))
async def process_lxc_port_traffic(callback: CallbackQuery):
    try:
        # callback.data looks like "lxc_ports_{node_name}_{vmid}"
        data = callback.data[len("lxc_ports_"):]
        node_name, vmid_str = data.rsplit("_", 1)
        vmid = int(vmid_str)
        
        from modules.proxmox.monitor import lxc_traffic_history, lxc_name_cache
        name = lxc_name_cache.get(vmid, _("proxmox", "host_label_default") if vmid == 0 else "Unknown")
        history = lxc_traffic_history.get(vmid, [])
        
        if vmid == 0:
            text = _("proxmox", "traffic_host_title", node_name=node_name)
        else:
            text = _("proxmox", "traffic_lxc_title", vmid=vmid, name=name)
        text += _("proxmox", "traffic_subtitle")
        
        if not history:
            text += _("proxmox", "traffic_empty")
        else:
            for item in list(history)[-10:]:
                emoji = item.get('risk_emoji', '🟢')
                label = item.get('label', _("proxmox", "traffic_direction_in_label") if item['direction'] == 'IN' else _("proxmox", "traffic_direction_out_label"))
                
                label_esc = html.escape(str(label)[:80])
                proto_esc = html.escape(str(item.get('proto', 'TCP'))[:10])
                src_esc = html.escape(str(item.get('src', ''))[:45])
                dst_esc = html.escape(str(item.get('dst', ''))[:45])
                spt_esc = html.escape(str(item.get('spt', ''))[:10])
                dpt_esc = html.escape(str(item.get('dpt', ''))[:10])
                
                dir_str = "📥 IN" if item['direction'] == 'IN' else "📤 OUT"
                text += f"{emoji} <code>{item['time']}</code> | <b>{dir_str}</b> | <code>{proto_esc}</code>\n"
                text += f"   └─ <b>{label_esc}</b>\n"
                if item['direction'] == 'IN':
                    text += f"      <code>{src_esc}:{spt_esc}</code> ➡️ <b>:{dpt_esc}</b>\n\n"
                else:
                    text += f"      <b>:{spt_esc}</b> ➡️ <code>{dst_esc}:{dpt_esc}</code>\n\n"
                    
        if len(text) > 4000:
            text = text[:3900] + _("proxmox", "traffic_truncated")

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        back_type = 'host' if vmid == 0 else 'lxc'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("proxmox", "refresh_traffic_btn"), callback_data=f"lxc_ports_{node_name}_{vmid}")],
            [InlineKeyboardButton(text=_("proxmox", "back_to_vm_btn"), callback_data=f"vm_{node_name}_{vmid}_{back_type}")]
        ])
        
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer(_("proxmox", "traffic_actual"))
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(_("proxmox", "traffic_error", err_msg=err_msg), show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("vps_auth_"))
async def process_vps_auth_logs(callback: CallbackQuery):
    try:
        server_ip = callback.data[len("vps_auth_"):]
        
        from modules.proxmox.monitor import lxc_auth_history
        history = lxc_auth_history.get(server_ip, [])
        
        text = _("proxmox", "auth_logs_vps_title", server_ip=server_ip)
        
        if not history:
            text += _("proxmox", "logs_empty")
        else:
            for item in list(history)[-10:]:
                t_emoji = "🟢" if item.get('type') == 'SUCCESS' else "🔴" if item.get('type') == 'FAILED' else "🛠"
                user_esc = html.escape(str(item.get('user', 'unknown'))[:30])
                msg_esc = html.escape(str(item.get('msg', ''))[:80])
                ip_esc = html.escape(str(item.get('ip', 'N/A'))[:45])
                text += f"{t_emoji} <code>{item.get('time', '')}</code> | <b>{user_esc}</b>\n"
                text += f"   └─ {msg_esc} (IP: <code>{ip_esc}</code>)\n\n"
                
        if len(text) > 4000:
            text = text[:3900] + _("proxmox", "logs_truncated")

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from core.spectre_client.manager import spectre_manager
        
        panel_key = None
        for p_key, p in spectre_manager.panels.items():
            if p.source_type == 'vps' and p.identifier == server_ip:
                panel_key = p_key
                break
                
        kb_buttons = [
            [InlineKeyboardButton(text=_("proxmox", "refresh_log_btn"), callback_data=f"vps_auth_{server_ip}")]
        ]
        if panel_key:
            kb_buttons.append([InlineKeyboardButton(text=_("proxmox", "back_to_panel_btn"), callback_data=f"spectre_menu:{panel_key}")])
        else:
            kb_buttons.append([InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu"), callback_data="main_menu")])
            
        kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer(_("proxmox", "log_actual"))
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(_("proxmox", "log_vps_error", err_msg=err_msg), show_alert=True)
        except Exception:
            pass
