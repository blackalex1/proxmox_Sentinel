import asyncio
import os
import glob
import html
import logging
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.config import ANSIBLE_PLAYBOOKS_DIR
from modules.ansible.keyboards import get_ansible_main_keyboard, get_ansible_dynamic_host_keyboard

router = Router(name="ansible_router")

class AnsibleState(StatesGroup):
    waiting_for_host = State()


@router.callback_query(F.data == "ansible_main")
async def process_ansible_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not ANSIBLE_PLAYBOOKS_DIR or not os.path.exists(ANSIBLE_PLAYBOOKS_DIR):
        await callback.message.edit_text(
            f"🛠 <b>Управление Ansible:</b>\n"
            f"❌ Папка <code>{ANSIBLE_PLAYBOOKS_DIR}</code> не найдена.\n"
            f"Создайте эту папку (Playbooks) во время запуска или проверьте настройки <code>ANSIBLE_PLAYBOOKS_DIR</code> в .env",
            parse_mode="HTML",
            reply_markup=get_ansible_main_keyboard()
        )
        return
        
    await callback.message.edit_text(
        "🛠 <b>Управление Ansible:</b>\nВыберите плейбук для запуска:",
        parse_mode="HTML",
        reply_markup=get_ansible_main_keyboard()
    )


@router.callback_query(F.data.startswith("ansible_run_"))
async def ask_for_host(callback: CallbackQuery, state: FSMContext):
    clean_name = callback.data.split("ansible_run_")[1]
    
    files = glob.glob(os.path.join(ANSIBLE_PLAYBOOKS_DIR, "*.yml")) + glob.glob(os.path.join(ANSIBLE_PLAYBOOKS_DIR, "*.yaml"))
    playbook_path = next((f for f in files if os.path.basename(f)[:50] == clean_name), None)
            
    if not playbook_path or not os.path.exists(playbook_path):
        await callback.answer("Файл плейбука не найден!", show_alert=True)
        return

    real_filename = os.path.basename(playbook_path)
    
    # Сохраняем путь в FSM
    await state.update_data(playbook_path=playbook_path, real_filename=real_filename)
    await state.set_state(AnsibleState.waiting_for_host)
    
    await callback.message.edit_text(
        f"🛠 Плейбук: <b>{real_filename}</b>\n\n"
        f"На каких хостах (или группах) вы хотите его запустить?\n"
        f"<i>✏️ Выберите цель из списка (прочитано из вашего hosts.ini)</i>\n"
        f"<i>или напишите свой вариант вручную прямо в чат:</i>",
        parse_mode="HTML",
        reply_markup=get_ansible_dynamic_host_keyboard()
    )


async def execute_ansible_playbook(message_or_callback, state: FSMContext, limit_host: str = None):
    data = await state.get_data()
    playbook_path = data.get('playbook_path')
    real_filename = data.get('real_filename')
    await state.clear()
    
    if not playbook_path:
        return
        
    # Поиск файла инвентаризации
    inventory_files = ['hosts.ini', 'inventory', 'hosts']
    inventory_path = None
    for f in inventory_files:
        p = os.path.join(ANSIBLE_PLAYBOOKS_DIR, f)
        if os.path.exists(p):
            inventory_path = p
            break
            
    cmd = ["ansible-playbook", playbook_path]
    if inventory_path:
        cmd.extend(["-i", inventory_path])
        
    if limit_host:
        cmd.extend(["--limit", limit_host])

    target_text = f"на хосте: <b>{html.escape(limit_host)}</b>" if limit_host else "на <b>всех хостах</b>"
    
    if isinstance(message_or_callback, types.Message):
        status_msg = await message_or_callback.answer(f"⏳ Запускаю <b>{real_filename}</b> {target_text}...\nОжидайте результата.", parse_mode="HTML")
    else:
        status_msg = message_or_callback.message
        await message_or_callback.message.edit_text(f"⏳ Запускаю <b>{real_filename}</b> {target_text}...\nОжидайте результата.", parse_mode="HTML")
        await message_or_callback.answer(f"Запускаю...")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=ANSIBLE_PLAYBOOKS_DIR
        )
        
        stdout, stderr = await process.communicate()
        
        output = stdout.decode('utf-8', errors='ignore')
        err_output = stderr.decode('utf-8', errors='ignore')
        
        full_log = output
        if err_output:
            full_log += "\n\n=== ERRRORS ===\n" + err_output
            
        status = "✅ Успешно" if process.returncode == 0 else f"❌ Ошибка (Код: {process.returncode})"
        
        full_log_escaped = html.escape(full_log)
        
        if len(full_log_escaped) > 3500:
            temp_log_path = f"ansible_log_{real_filename}.txt"
            with open(temp_log_path, "w", encoding="utf-8") as f:
                f.write(full_log)
                
            from aiogram.types import FSInputFile
            logfile = FSInputFile(temp_log_path)
            await status_msg.delete()
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.answer_document(
                    document=logfile, 
                    caption=f"📝 Полный лог <b>{real_filename}</b> {target_text}.\nСтатус: {status}", 
                    parse_mode="HTML",
                    reply_markup=get_ansible_main_keyboard()
                )
            else:
                await status_msg.answer_document(
                    document=logfile, 
                    caption=f"📝 Полный лог <b>{real_filename}</b> {target_text}.\nСтатус: {status}", 
                    parse_mode="HTML",
                    reply_markup=get_ansible_main_keyboard()
                )
            os.remove(temp_log_path)
        else:
            await status_msg.edit_text(
                f"📝 Отчет по <b>{real_filename}</b> {target_text}\nСтатус: {status}\n<pre><code class='language-bash'>{full_log_escaped}</code></pre>",
                parse_mode="HTML",
                reply_markup=get_ansible_main_keyboard()
            )

    except Exception as e:
        logging.error(f"Ansible run error: {e}")
        await status_msg.edit_text(
            f"❌ Системная ошибка при инициализации Ansible:\nУбедитесь, что 'ansible-playbook' установлен.\n<code>{e}</code>", 
            parse_mode="HTML", 
            reply_markup=get_ansible_main_keyboard()
        )


@router.callback_query(AnsibleState.waiting_for_host, F.data == "ansible_do_all")
async def process_ansible_all(callback: CallbackQuery, state: FSMContext):
    await execute_ansible_playbook(callback, state, limit_host=None)


@router.callback_query(AnsibleState.waiting_for_host, F.data.startswith("ansible_do_t_"))
async def process_ansible_specific_host(callback: CallbackQuery, state: FSMContext):
    limit_host = callback.data.split("ansible_do_t_")[1]
    await execute_ansible_playbook(callback, state, limit_host=limit_host)


@router.message(AnsibleState.waiting_for_host)
async def process_ansible_host_input(message: types.Message, state: FSMContext):
    limit_host = message.text.strip()
    await execute_ansible_playbook(message, state, limit_host=limit_host)
