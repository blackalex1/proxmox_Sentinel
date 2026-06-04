import logging
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from .keyboards import get_main_menu_keyboard, get_main_menu_text, get_help_text, get_persistent_reply_keyboard

router = Router(name="core_base_router")

@router.message(Command("start"))
@router.message(F.text == "🛡️ Панель управления")
async def cmd_start(message: types.Message):
    # При старте или клике отправляем приветствие с персистентной клавиатурой
    await message.answer(
        "👋 <b>Добро пожаловать в систему мониторинга PVE Aegis!</b>\n"
        "<i>Ниже активирована постоянная панель быстрого доступа к главным командам.</i>",
        parse_mode="HTML",
        reply_markup=get_persistent_reply_keyboard()
    )
    # И сразу отправляем интерактивное меню
    await message.answer(
        get_main_menu_text(),
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(F.text == "📊 Статус систем")
async def btn_status(message: types.Message):
    from .status import cmd_status
    await cmd_status(message)

@router.message(F.text == "ℹ️ Справка")
async def btn_help(message: types.Message):
    await cmd_help(message)

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            get_main_menu_text(),
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при возврате в главное меню: {e}")
    finally:
        try:
            await callback.answer()
        except Exception:
            pass

@router.message(Command("id"))
async def cmd_id(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    await message.answer(
        f"👤 <b>Ваш Telegram ID:</b> <code>{user_id}</code>\n"
        f"💬 <b>ID этого чата:</b> <code>{chat_id}</code>",
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = get_help_text()
    await message.answer(text, parse_mode="HTML")

@router.callback_query(F.data == "help_info")
async def callback_help_info(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    try:
        await callback.message.edit_text(get_help_text(), parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logging.error(f"Ошибка при показе справки: {e}")
    finally:
        try:
            await callback.answer()
        except Exception:
            pass

@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass

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
        logging.error(f"Ошибка парсинга callback.data '{callback.data}': {e}")
        await callback.answer("Ошибка при обработке запроса.", show_alert=True)
        return

    logging.info(f"Запрос на сброс SSH-сессии: target={target}, pid={pid}")

    success = False
    error_msg = ""
    is_dead = False

    try:
        cmd = get_kill_tree_cmd(pid)
        if target == "local":
            import asyncio
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
            import asyncio
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
            from core.config import settings
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
        logging.error(f"Критическая ошибка при сбросе SSH-сессии: {e}")
        error_msg = str(e)

    if success:
        if is_dead:
            await callback.answer("Сессия уже закрыта или не найдена.", show_alert=True)
            status_text = "🔒 Сессия уже была закрыта или не найдена"
        else:
            await callback.answer("SSH-сессия успешно сброшена!", show_alert=True)
            status_text = "❌ SSH-сессия сброшена пользователем через Telegram"
        
        # Обновляем текст сообщения, убираем клавиатуру
        orig_text = callback.message.html_text or callback.message.text or ""
        new_text = f"{orig_text}\n\n🛑 <b>{status_text}</b>"
        
        try:
            await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)
        except Exception as e:
            logging.error(f"Ошибка при обновлении сообщения SSH алерты: {e}")
    else:
        logging.warning(f"Не удалось сбросить SSH-сессию {pid} на {target}: {error_msg}")
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
        logging.error(f"Ошибка парсинга callback.data '{callback.data}': {e}")
        await callback.answer("Ошибка при обработке запроса.", show_alert=True)
        return

    logging.info(f"Запрос на блокировку SSH-ключа: target={target}, pid={pid}")

    # Получаем fingerprint и username из кэша в БД
    from core.db import get_state
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
            import asyncio
            proc = await asyncio.create_subprocess_exec("sh", "-c", cmd)
            await proc.wait()
        elif target.startswith("lxc_"):
            import asyncio
            vmid = int(target.split("_")[1])
            proc = await asyncio.create_subprocess_exec("pct", "exec", str(vmid), "--", "sh", "-c", cmd)
            await proc.wait()
        else:
            from core.config import settings
            server = next((s for s in settings.remote_servers if s['ip'] == target), None)
            if server:
                from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
                await run_remote_ssh_cmd(server, [cmd])
    except Exception as e:
        logging.error(f"Ошибка при сбросе сессии перед баном ключа: {e}")

    success_ban = False
    error_msg = ""
    stdout_str = ""

    try:
        cmd_ban = get_ban_key_tree_cmd(fingerprint)
        if target == "local":
            import asyncio
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
            import asyncio
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
            from core.config import settings
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
        logging.error(f"Ошибка при блокировке SSH-ключа: {e}")
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
                from core.db import get_state, set_state
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
                    logging.info(f"Забаненный ключ {fingerprint} для {entry_username} на {target} сохранен в БД. ID: {key_id}, путь: {path}")
                    
                await set_state("banned_ssh_keys", banned_keys)
            except Exception as e:
                logging.error(f"Ошибка сохранения забаненного ключа в БД: {e}")

        await callback.answer("SSH-ключ успешно заблокирован и удален!", show_alert=True)
        # Показываем только последние 12 символов отпечатка для наглядности
        short_fp = fingerprint[-12:] if len(fingerprint) > 12 else fingerprint
        status_text = f"🚫 SSH-ключ (...{short_fp}) удален из authorized_keys и сессия сброшена"
        
        orig_text = callback.message.html_text or callback.message.text or ""
        new_text = f"{orig_text}\n\n🛑 <b>{status_text}</b>"
        
        try:
            await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)
        except Exception as e:
            logging.error(f"Ошибка при обновлении сообщения после блокировки ключа: {e}")
    else:
        logging.warning(f"Не удалось заблокировать SSH-ключ {fingerprint} на {target}: {error_msg}")
        await callback.answer(f"Не удалось заблокировать ключ: {error_msg}", show_alert=True)
