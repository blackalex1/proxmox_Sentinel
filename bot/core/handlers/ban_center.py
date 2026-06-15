import logging
import datetime
from aiogram import Router, F, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from core.db import execute_read_all, execute_write
from core.config import settings
from modules.router.router import unban_router_ip
from modules.proxmox.monitor.traffic.firewall import unban_local_ip
from modules.proxmox.monitor.remote.traffic.firewall import unban_remote_ip
from core.messages.i18n import _

router = Router(name="core_ban_center_router")

def get_target_label(server_ip: str) -> str:
    if server_ip == 'router':
        return _("whitelist", "router_node")
    elif server_ip == 'local':
        return _("whitelist", "pve_node")
    else:
        return _("whitelist", "vps_node", ip=server_ip)

async def render_ban_center(message_or_query) -> tuple[str, InlineKeyboardMarkup]:
    """Генерирует HTML-текст и клавиатуру для Центра блокировок."""
    # Получаем все временные блокировки из БД
    bans = await execute_read_all("SELECT * FROM temp_bans")
    
    # Фильтруем устаревшие баны и форматируют активные
    active_bans = []
    now = datetime.datetime.now()
    
    for row in bans:
        try:
            expire_dt = datetime.datetime.fromisoformat(row['expire_time'])
            if now >= expire_dt:
                # Баны, срок действия которых уже истек, удаляем из БД
                await execute_write(
                    "DELETE FROM temp_bans WHERE server_ip = ? AND dst_ip = ?",
                    (row['server_ip'], row['dst_ip'])
                )
                continue
            
            diff = expire_dt - now
            seconds = int(diff.total_seconds())
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            
            if hours > 0:
                remaining = _("ban_center", "remaining_hours", hours=hours, minutes=minutes)
            else:
                remaining = _("ban_center", "remaining_minutes", minutes=minutes, seconds=secs)
                
            reason = _("ban_center", "reason_manual")
            try:
                if 'reason' in row.keys():
                    reason = row['reason'] or _("ban_center", "reason_manual")
            except Exception:
                pass
                
            active_bans.append({
                'server_ip': row['server_ip'],
                'dst_ip': row['dst_ip'],
                'remaining': remaining,
                'label': get_target_label(row['server_ip']),
                'reason': reason
            })
        except Exception as e:
            logging.error("ban_center_error_processing_ban_record", e)
            active_bans.append({
                'server_ip': row['server_ip'],
                'dst_ip': row['dst_ip'],
                'remaining': _("ban_center", "remaining_unknown"),
                'label': get_target_label(row['server_ip']),
                'reason': _("ban_center", "reason_manual")
            })

    # Получаем заблокированные ключи из БД
    from core.db import get_state
    banned_keys = await get_state("banned_ssh_keys", [])

    from core.messages import get_ban_center_table
    text = get_ban_center_table(active_bans, banned_keys)
    
    kb_buttons = []
    
    if active_bans:
        for ban in active_bans:
            # Кнопка разблокировки для каждого IP
            kb_buttons.append([
                InlineKeyboardButton(
                    text=_("ban_center", "btn_unban_ip", ip=ban['dst_ip']),
                    callback_data=f"ban_center_unban:{ban['server_ip']}:{ban['dst_ip']}"
                )
            ])
            
    if banned_keys:
        for key in banned_keys:
            short_fp = key['fingerprint'][-12:] if len(key['fingerprint']) > 12 else key['fingerprint']
            # Кнопка разблокировки ключа
            kb_buttons.append([
                InlineKeyboardButton(
                    text=_("ban_center", "btn_unban_key", fp=short_fp),
                    callback_data=f"ban_center_unbankey:{key['id']}"
                )
            ])
            
    # Добавляем кнопку возврата в главное меню
    kb_buttons.append([
        InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu"), callback_data="main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    return text, reply_markup

@router.message(Command("bans"))
async def cmd_bans(message: types.Message):
    """Команда /bans для открытия Центра блокировок."""
    try:
        from modules.proxmox.monitor.utils import send_rich_message
        text, reply_markup = await render_ban_center(message)
        await send_rich_message(chat_id=message.chat.id, text=text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logging.error("ban_center_error_in_bans_handler", e)
        await message.answer(_("ban_center", "load_err"))

@router.callback_query(F.data == "ban_center_main")
async def process_ban_center_main(callback: CallbackQuery):
    """Переход в Центр блокировок по кнопке из главного меню."""
    try:
        from modules.proxmox.monitor.utils import edit_rich_message
        text, reply_markup = await render_ban_center(callback)
        await edit_rich_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.error("ban_center_error_navigating_to_ban_center", e)
        await callback.answer(_("ban_center", "open_err"), show_alert=True)

@router.callback_query(F.data.startswith("ban_center_unban:"))
async def process_ban_center_unban(callback: CallbackQuery):
    """Снятие блокировки IP вручную из Центра блокировок."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 3:
            await callback.answer(_("ban_center", "invalid_callback_err"), show_alert=True)
            return
            
        server_ip = parts[1]
        dst_ip = parts[2]
        
        success = False
        desc = ""
        
        await callback.answer(_("ban_center", "unban_in_progress"), show_alert=False)
        
        if server_ip == 'router':
            success, desc = await unban_router_ip(dst_ip)
        elif server_ip == 'local':
            success, desc = await unban_local_ip(dst_ip)
        else:
            # Поиск VPS сервера в конфигурации
            server = next((s for s in settings.remote_servers if s['ip'] == server_ip), None)
            if server:
                success, desc = await unban_remote_ip(server, dst_ip)
            else:
                success = False
                desc = _("ban_center", "vps_not_found_err", ip=server_ip)
                
        if success:
            await callback.answer(_("ban_center", "unban_success_alert", ip=dst_ip), show_alert=True)
        else:
            await callback.answer(_("ban_center", "unban_failed_alert", desc=desc), show_alert=True)
            
        # Обновляем сообщение Центра блокировок
        text, reply_markup = await render_ban_center(callback)
        try:
            from modules.proxmox.monitor.utils import edit_rich_message
            await edit_rich_message(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception:
            pass # Если текст не поменялся
            
    except Exception as e:
        logging.error("ban_center_exception_during_manual_unban", e)
        await callback.answer(_("ban_center", "unban_failed_alert", desc=str(e)), show_alert=True)

def get_unban_key_cmd(keys_path: str, key_body: str) -> str:
    import shlex
    path_q = shlex.quote(keys_path)
    body_q = shlex.quote(key_body.strip() + "\n")
    return (
        f"path={path_q}; "
        f"dir=\"${{path%/*}}\"; "
        f"pdir=\"${{dir%/*}}\"; "
        f"mkdir -p \"$dir\" && "
        f"printf %s {body_q} >> \"$path\" && "
        f"owner=$(stat -c '%U:%G' \"$pdir\" 2>/dev/null || echo 'root:root') && "
        f"chown \"$owner\" \"$path\" \"$dir\" 2>/dev/null && "
        f"chmod 700 \"$dir\" 2>/dev/null && "
        f"chmod 600 \"$path\" 2>/dev/null"
    )

@router.callback_query(F.data.startswith("ban_center_unbankey:"))
async def process_ban_center_unbankey(callback: CallbackQuery):
    """Восстановление (разблокировка) SSH-ключа из Центра блокировок."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer(_("ban_center", "invalid_callback_err"), show_alert=True)
            return
            
        key_id = parts[1]
        
        from core.db import get_state, set_state
        banned_keys = await get_state("banned_ssh_keys", [])
        
        # Находим запись ключа
        key = next((k for k in banned_keys if k['id'] == key_id), None)
        if not key:
            await callback.answer(_("ban_center", "key_not_found_err"), show_alert=True)
            return
            
        await callback.answer(_("ban_center", "restore_key_in_progress"), show_alert=False)
        
        success = False
        desc = ""
        
        target = key['target']
        username = key['username']
        keys_path = key['keys_path']
        key_body = key['key_body']
        
        cmd_unban = get_unban_key_cmd(keys_path, key_body)
        
        if target == "local":
            import asyncio
            proc = await asyncio.create_subprocess_exec(
                "sh", "-c", cmd_unban,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            success = proc.returncode == 0
            if not success:
                desc = stderr.decode().strip() or f"exit code {proc.returncode}"
                
        elif target.startswith("lxc_"):
            import asyncio
            try:
                vmid = int(target.split("_")[1])
            except Exception:
                await callback.answer(_("ban_center", "invalid_lxc_id_err"), show_alert=True)
                return
            # Восстанавливаем прямо в пространстве имен контейнера через pct exec
            proc = await asyncio.create_subprocess_exec(
                "pct", "exec", str(vmid), "--", "sh", "-c", cmd_unban,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            success = proc.returncode == 0
            if not success:
                desc = stderr.decode().strip() or f"exit code {proc.returncode}"
        else:
            # Remote VPS
            from core.config import settings
            server = next((s for s in settings.remote_servers if s['ip'] == target), None)
            if not server:
                success = False
                desc = _("ban_center", "vps_not_found_err", ip=target)
            else:
                from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
                success, stdout, stderr = await run_remote_ssh_cmd(
                    server,
                    [cmd_unban]
                )
                if not success:
                    desc = stderr or stdout
                    
        if success:
            # Удаляем запись из БД
            new_banned_keys = [k for k in banned_keys if k['id'] != key_id]
            await set_state("banned_ssh_keys", new_banned_keys)
            await callback.answer(_("ban_center", "restore_key_success_alert"), show_alert=True)
        else:
            await callback.answer(_("ban_center", "restore_key_failed_alert", desc=desc), show_alert=True)
            
        # Обновляем сообщение Центра блокировок
        text, reply_markup = await render_ban_center(callback)
        try:
            from modules.proxmox.monitor.utils import edit_rich_message
            await edit_rich_message(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception:
            pass
            
    except Exception as e:
        logging.error("ban_center_exception_during_manual_key_unban", e)
        await callback.answer(_("ban_center", "restore_key_failed_alert", desc=str(e)), show_alert=True)


@router.message(Command("unban_login_ip"))
async def cmd_unban_login_ip(message: types.Message):
    """
    Разблокирует IP-адрес, заблокированный через 2FA-оповещения, на всех панелях.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            _("ban_center", "unban_login_ip_help"),
            parse_mode="HTML"
        )
        return
        
    ip_to_unban = args[1].strip()
    status_msg = await message.reply(_("ban_center", "unban_login_ip_in_progress", ip=ip_to_unban))
    
    from core.spectre_client import spectre_manager
    
    results = []
    any_success = False
    
    for panel in spectre_manager.panels.values():
        try:
            success, res = await panel.request("POST", "api/security/unban-ip", data={"ip": ip_to_unban})
            if success and res.get("success"):
                any_success = True
                results.append(_("ban_center", "unban_login_ip_success_item", name=panel.name))
            else:
                msg = res.get("msg") or "Unknown error"
                results.append(_("ban_center", "unban_login_ip_failed_item", name=panel.name, error=msg))
        except Exception as e:
            results.append(_("ban_center", "unban_login_ip_failed_item", name=panel.name, error=str(e)))
            
    details_str = "\n".join(results)
    if any_success:
        await status_msg.edit_text(
            _("ban_center", "unban_login_ip_success", ip=ip_to_unban, details=details_str),
            parse_mode="HTML"
        )
    else:
        await status_msg.edit_text(
            _("ban_center", "unban_login_ip_failed", ip=ip_to_unban, details=details_str),
            parse_mode="HTML"
        )
