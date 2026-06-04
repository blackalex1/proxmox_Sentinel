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
        if target == "local":
            import asyncio
            proc = await asyncio.create_subprocess_exec(
                "kill", "-9", str(pid),
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
                "pct", "exec", str(vmid), "--", "kill", "-9", str(pid),
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
                run_success, stdout, stderr_str = await run_remote_ssh_cmd(server, ["kill", "-9", str(pid)])
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
