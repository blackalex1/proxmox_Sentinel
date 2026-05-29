import asyncio
import os
import glob
import html
import logging
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from core.config import settings, base_dir
ANSIBLE_PLAYBOOKS_DIR = settings.ansible_playbooks_dir or os.path.join(base_dir, 'ansible')
from modules.ansible.keyboards import get_ansible_main_keyboard, get_ansible_dynamic_host_keyboard
from modules.ansible.inventory import generate_ansible_hosts_ini
from modules.ansible.executor import execute_ansible_playbook

router = Router(name="ansible_router")

class AnsibleState(StatesGroup):
    waiting_for_host = State()

@router.callback_query(F.data == "ansible_main")
async def process_ansible_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    # Импортируем и вызываем автоматическое наполнение hosts.ini
    generate_ansible_hosts_ini(ANSIBLE_PLAYBOOKS_DIR)
    
    if not ANSIBLE_PLAYBOOKS_DIR or not os.path.exists(ANSIBLE_PLAYBOOKS_DIR):
        try:
            await callback.message.edit_text(
                f"🛠 <b>Управление Ansible:</b>\n"
                f"❌ Папка <code>{ANSIBLE_PLAYBOOKS_DIR}</code> не найдена.\n"
                f"Создайте эту папку (Playbooks) во время запуска или проверьте настройки <code>ANSIBLE_PLAYBOOKS_DIR</code> в .env",
                parse_mode="HTML",
                reply_markup=get_ansible_main_keyboard()
            )
        except TelegramBadRequest as e:
            if "there is no text in the message to edit" in str(e):
                await callback.message.delete()
                await callback.message.answer(
                    f"🛠 <b>Управление Ansible:</b>\n"
                    f"❌ Папка <code>{ANSIBLE_PLAYBOOKS_DIR}</code> не найдена.\n"
                    f"Создайте эту папку (Playbooks) во время запуска или проверьте настройки <code>ANSIBLE_PLAYBOOKS_DIR</code> в .env",
                    parse_mode="HTML",
                    reply_markup=get_ansible_main_keyboard()
                )
            elif "message is not modified" not in str(e):
                raise e
        await callback.answer()
        return
        
    try:
        await callback.message.edit_text(
            "🛠 <b>Управление Ansible:</b>\nВыберите плейбук для запуска:",
            parse_mode="HTML",
            reply_markup=get_ansible_main_keyboard()
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            if "there is no text in the message to edit" in str(e):
                await callback.message.delete()
                await callback.message.answer(
                    "🛠 <b>Управление Ansible:</b>\nВыберите плейбук для запуска:",
                    parse_mode="HTML",
                    reply_markup=get_ansible_main_keyboard()
                )
            else:
                raise e
    await callback.answer()

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
    
    try:
        await callback.message.edit_text(
            f"🛠 Плейбук: <b>{real_filename}</b>\n\n"
            f"На каких хостах (или группах) вы хотите его запустить?\n"
            f"<i>✏️ Выберите цель из списка (прочитано из вашего hosts.ini)</i>\n"
            f"<i>или напишите свой вариант вручную прямо в чат:</i>",
            parse_mode="HTML",
            reply_markup=get_ansible_dynamic_host_keyboard()
        )
    except TelegramBadRequest as e:
        if "there is no text in the message to edit" in str(e):
            await callback.message.delete()
            await callback.message.answer(
                f"🛠 Плейбук: <b>{real_filename}</b>\n\n"
                f"На каких хостах (или группах) вы хотите его запустить?\n"
                f"<i>✏️ Выберите цель из списка (прочитано из вашего hosts.ini)</i>\n"
                f"<i>или напишите свой вариант вручную прямо в чат:</i>",
                parse_mode="HTML",
                reply_markup=get_ansible_dynamic_host_keyboard()
            )
        else:
            raise e



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
