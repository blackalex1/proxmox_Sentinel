import asyncio
import os
import html
import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from core.config import settings, base_dir
from modules.ansible.keyboards import get_ansible_main_keyboard

ANSIBLE_PLAYBOOKS_DIR = settings.ansible_playbooks_dir or os.path.join(base_dir, 'ansible')

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
