import logging
import asyncio
import uuid
import re
import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.config import settings

router = Router(name="core_ssh_alerts_router")

def get_kill_tree_cmd(pid: int) -> str:
    return (
        f"if [ ! -d '/proc/{pid}' ]; then echo 'No such process' >&2; exit 1; fi; "
        f"pids='{pid}'; "
        f"if command -v pgrep >/dev/null 2>&1; then "
        f"to_check='{pid}'; "
        f"while [ -n \"$to_check\" ]; do "
        f"next_check=''; "
        f"for p in $to_check; do "
        f"children=$(pgrep -P \"$p\" 2>/dev/null | tr '\\n' ' '); "
        f"if [ -n \"$children\" ]; then "
        f"pids=\"$pids $children\"; "
        f"next_check=\"$next_check $children\"; "
        f"fi; "
        f"done; "
        f"to_check=\"$next_check\"; "
        f"done; "
        f"else "
        f"to_check='{pid}'; "
        f"while [ -n \"$to_check\" ]; do "
        f"next_check=''; "
        f"for p in /proc/[0-9]*; do "
        f"curr_pid=${{p##*/}}; "
        f"[ -f \"$p/status\" ] || continue; "
        f"ppid=''; "
        f"while read -r label value; do "
        f"if [ \"$label\" = \"PPid:\" ]; then ppid=\"$value\"; break; fi; "
        f"done < \"$p/status\"; "
        f"if [ -n \"$ppid\" ]; then "
        f"case \" $to_check \" in "
        f"*\" $ppid \"*) "
        f"case \" $pids \" in "
        f"*\" $curr_pid \"*) ;; "
        f"*) "
        f"pids=\"$pids $curr_pid\"; "
        f"next_check=\"$next_check $curr_pid\"; "
        f";; "
        f"esac; "
        f";; "
        f"esac; "
        f"fi; "
        f"done; "
        f"to_check=\"$next_check\"; "
        f"done; "
        f"fi; "
        f"for p in $pids; do kill -9 \"$p\" 2>/dev/null; done"
    )

def get_ban_key_tree_cmd(fp: str) -> str:
    return (
        f"temp_out=$(mktemp 2>/dev/null || echo '/tmp/tkey_$$'); "
        f"removed_any=0; "
        f"for path in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do "
        f"[ -f \"$path\" ] || continue; "
        f"removed_from_file=0; "
        f"> \"$temp_out\"; "
        f"while IFS= read -r line || [ -n \"$line\" ]; do "
        f"case \"$line\" in "
        f"\\#*|\"\") "
        f"echo \"$line\" >> \"$temp_out\"; "
        f"continue; "
        f";; "
        f"esac; "
        f"keygen_out=$(echo \"$line\" | ssh-keygen -l -f - 2>/dev/null); "
        f"if [ $? -eq 0 ] && echo \"$keygen_out\" | grep -F -q \"{fp}\"; then "
        f"removed_from_file=1; "
        f"removed_any=1; "
        f"echo \"DELETED_KEY:$path:$line\"; "
        f"continue; "
        f";; "
        f"fi; "
        f"echo \"$line\" >> \"$temp_out\"; "
        f"done < \"$path\"; "
        f"if [ $removed_from_file -eq 1 ]; then "
        f"cat \"$temp_out\" > \"$path\"; "
        f"fi; "
        f"done; "
        f"rm -f \"$temp_out\"; "
        f"if [ $removed_any -eq 1 ]; then "
        f"echo \"SUCCESS\"; "
        f"else "
        f"echo \"NOT_FOUND\"; "
        f"fi"
    )

@router.callback_query(F.data.startswith("termssh:"))
async def process_terminate_ssh(callback: CallbackQuery):
    if not callback.message or not hasattr(callback.message, "edit_text"):
        try:
            await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        except Exception:
            pass
        return

    # Разбираем target и sshd_pid
    # callback.data в формате: termssh:<target>:<pid>
    try:
        data_parts = callback.data.rsplit(":", 1)
        if len(data_parts) != 2:
            await callback.answer("Неверный формат callback-данных.", show_alert=True)
            return
        
        term_part, pid_str = data_parts
        _, target = term_part.split(":", 1)
        pid = int(pid_str)
    except Exception as e:
        logging.error("error_parsing_callback_data", callback.data, e)
        await callback.answer("Ошибка при обработке запроса.", show_alert=True)
        return

    logging.info("ssh_session_drop_request_target_pid", target, pid)

    success = False
    error_msg = ""
    is_dead = False

    try:
        cmd = get_kill_tree_cmd(pid)
        if target == "local":
            proc = await asyncio.create_subprocess_exec(
                "sh", "-c", cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            stderr_str = stderr.decode('utf-8', errors='ignore')
            if proc.returncode == 0:
                success = True
            elif "no such process" in stderr_str.lower() or "esrch" in stderr_str.lower():
                success = True
                is_dead = True
            else:
                error_msg = stderr_str.strip() or f"exit code {proc.returncode}"

        elif target.startswith("lxc_"):
            try:
                vmid = int(target.split("_")[1])
            except Exception:
                await callback.answer("Неверный ID LXC.", show_alert=True)
                return
            proc = await asyncio.create_subprocess_exec(
                "pct", "exec", str(vmid), "--", "sh", "-c", cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            stderr_str = stderr.decode('utf-8', errors='ignore')
            if proc.returncode == 0:
                success = True
            elif "no such process" in stderr_str.lower() or "esrch" in stderr_str.lower():
                success = True
                is_dead = True
            else:
                error_msg = stderr_str.strip() or f"exit code {proc.returncode}"

        else:
            # Удаленный VPS (target - это IP-адрес)
            server = next((s for s in settings.remote_servers if s['ip'] == target), None)
            if not server:
                error_msg = f"Сервер {target} не найден в настройках."
            else:
                from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
                run_success, stdout, stderr_str = await run_remote_ssh_cmd(server, [cmd])
                if run_success:
                    success = True
                elif "no such process" in stderr_str.lower() or "esrch" in stderr_str.lower():
                    success = True
                    is_dead = True
                else:
                    error_msg = stderr_str.strip() or "Ошибка выполнения команды по SSH"

    except Exception as e:
        logging.error("critical_error_dropping_ssh_session", e)
        error_msg = str(e)

    if success:
        if is_dead:
            logging.info("ssh_drop_ssh_session_on_was_already", pid, target)
            await callback.answer("Сессия уже закрыта или не найдена.", show_alert=True)
            status_text = "🔒 Сессия уже была закрыта или не найдена"
        else:
            logging.info("ssh_drop_session_successfully_terminated_dropped", pid, target)
            await callback.answer("SSH-сессия успешно сброшена!", show_alert=True)
            status_text = "❌ SSH-сессия сброшена пользователем через Telegram"
        
        # Обновляем текст сообщения, убираем клавиатуру
        orig_text = callback.message.html_text or callback.message.text or ""
        new_text = f"{orig_text}\n\n🛑 <b>{status_text}</b>"
        
        try:
            await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)
        except Exception as e:
            logging.error("error_updating_ssh_alert_message", e)
    else:
        logging.warning("failed_to_drop_ssh_session_on", pid, target, error_msg)
        await callback.answer(f"Не удалось сбросить сессию: {error_msg}", show_alert=True)


@router.callback_query(F.data.startswith("bankey:"))
async def process_ban_ssh_key(callback: CallbackQuery):
    if not callback.message or not hasattr(callback.message, "edit_text"):
        try:
            await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        except Exception:
            pass
        return

    # Разбираем target и sshd_pid
    # callback.data в формате: bankey:<target>:<pid>
    try:
        data_parts = callback.data.rsplit(":", 1)
        if len(data_parts) != 2:
            await callback.answer("Неверный формат callback-данных.", show_alert=True)
            return
        
        term_part, pid_str = data_parts
        _, target = term_part.split(":", 1)
        pid = int(pid_str)
    except Exception as e:
        logging.error("error_parsing_callback_data", callback.data, e)
        await callback.answer("Ошибка при обработке запроса.", show_alert=True)
        return

    logging.info("ssh_key_block_request_target_pid", target, pid)

    # Получаем fingerprint и username из кэша в БД
    from core.db import get_state, set_state
    cache = await get_state("ssh_key_cache", {})
    cache_entry = cache.get(f"{target}:{pid}")
    if not cache_entry:
        await callback.answer("Не удалось найти отпечаток ключа (кэш устарел).", show_alert=True)
        return

    fingerprint, username = cache_entry

    # Сначала принудительно сбрасываем саму сессию
    try:
        cmd = get_kill_tree_cmd(pid)
        if target == "local":
            proc = await asyncio.create_subprocess_exec("sh", "-c", cmd)
            await proc.wait()
            logging.info("ssh_drop_ssh_session_on_terminated_before", pid, target, proc.returncode)
        elif target.startswith("lxc_"):
            vmid = int(target.split("_")[1])
            proc = await asyncio.create_subprocess_exec("pct", "exec", str(vmid), "--", "sh", "-c", cmd)
            await proc.wait()
            logging.info("ssh_drop_ssh_session_in_lxc_terminated", pid, vmid, proc.returncode)
        else:
            server = next((s for s in settings.remote_servers if s['ip'] == target), None)
            if server:
                from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
                run_success, stdout, stderr = await run_remote_ssh_cmd(server, [cmd])
                logging.info("ssh_drop_ssh_session_on_vps_terminated", pid, target, run_success)
    except Exception as e:
        logging.error("error_dropping_session_before_key_ban", e)

    success_ban = False
    error_msg = ""
    stdout_str = ""

    try:
        cmd_ban = get_ban_key_tree_cmd(fingerprint)
        if target == "local":
            proc = await asyncio.create_subprocess_exec(
                "sh", "-c", cmd_ban,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()
            if proc.returncode == 0 and "SUCCESS" in stdout_str:
                success_ban = True
            elif "NOT_FOUND" in stdout_str:
                error_msg = "Ключ не найден в authorized_keys."
            else:
                error_msg = stderr_str or stdout_str or f"exit code {proc.returncode}"

        elif target.startswith("lxc_"):
            try:
                vmid = int(target.split("_")[1])
            except Exception:
                await callback.answer("Неверный ID LXC.", show_alert=True)
                return
            # Запускаем в пространстве имен контейнера через pct exec
            proc = await asyncio.create_subprocess_exec(
                "pct", "exec", str(vmid), "--", "sh", "-c", cmd_ban,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()
            if proc.returncode == 0 and "SUCCESS" in stdout_str:
                success_ban = True
            elif "NOT_FOUND" in stdout_str:
                error_msg = "Ключ не найден в authorized_keys."
            else:
                error_msg = stderr_str or stdout_str or f"exit code {proc.returncode}"

        else:
            # Remote VPS
            server = next((s for s in settings.remote_servers if s['ip'] == target), None)
            if not server:
                error_msg = f"Сервер {target} не найден в настройках."
            else:
                from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
                run_success, stdout_str, stderr_str = await run_remote_ssh_cmd(
                    server,
                    [cmd_ban]
                )
                if run_success and "SUCCESS" in stdout_str:
                    success_ban = True
                elif "NOT_FOUND" in stdout_str:
                    error_msg = "Ключ не найден в authorized_keys."
                else:
                    error_msg = stderr_str or stdout_str or "Ошибка выполнения скрипта блокировки"
    except Exception as e:
        logging.error("error_blocking_ssh_key", e)
        error_msg = str(e)

    if success_ban:
        # Извлекаем пути и тела удаленных ключей из stdout_str
        deleted_entries = []
        for line in stdout_str.splitlines():
            if line.startswith("DELETED_KEY:"):
                parts = line.split(":", 2)
                if len(parts) == 3:
                    _, path, k_body = parts
                    deleted_entries.append((path.strip(), k_body.strip()))
        
        # Сохраняем заблокированные ключи в БД для Центра блокировок
        if deleted_entries:
            try:
                import uuid
                import re
                import datetime
                banned_keys = await get_state("banned_ssh_keys", [])
                
                for path, k_body in deleted_entries:
                    key_id = str(uuid.uuid4())[:8]
                    
                    # Извлекаем имя пользователя из пути для красивого отображения в панели
                    match = re.search(r'/home/([^/]+)/', path)
                    entry_username = "root"
                    if match:
                        entry_username = match.group(1)
                    elif "/root/" in path:
                        entry_username = "root"
                    else:
                        entry_username = username or "root"
                    
                    banned_keys.append({
                        "id": key_id,
                        "target": target,
                        "username": entry_username,
                        "fingerprint": fingerprint,
                        "key_body": k_body,
                        "keys_path": path,
                        "banned_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    logging.info("banned_key_for_on_saved_in_db", fingerprint, entry_username, target, key_id, path)
                    
                await set_state("banned_ssh_keys", banned_keys)
            except Exception as e:
                logging.error("error_saving_banned_key_in_db", e)

        await callback.answer("SSH-ключ успешно заблокирован и удален!", show_alert=True)
        # Показываем только последние 12 символов отпечатка для наглядности
        short_fp = fingerprint[-12:] if len(fingerprint) > 12 else fingerprint
        status_text = f"🚫 SSH-ключ (...{short_fp}) удален из authorized_keys и сессия сброшена"
        
        orig_text = callback.message.html_text or callback.message.text or ""
        new_text = f"{orig_text}\n\n🛑 <b>{status_text}</b>"
        
        try:
            await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)
        except Exception as e:
            logging.error("error_updating_message_after_key_blocking", e)
    else:
        logging.warning("failed_to_block_ssh_key_on", fingerprint, target, error_msg)
        await callback.answer(f"Не удалось заблокировать ключ: {error_msg}", show_alert=True)
