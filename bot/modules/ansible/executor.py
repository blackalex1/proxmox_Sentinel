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
        
    playbook_path = os.path.abspath(playbook_path)
        
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

    # Определяем целевые IP-адреса для динамического обхода алертов во время выполнения
    from modules.ansible.parser import get_ansible_inventory_ips
    try:
        inventory_ips = get_ansible_inventory_ips(ANSIBLE_PLAYBOOKS_DIR)
    except Exception:
        inventory_ips = set()
        
    running_targets = set()
    if limit_host:
        import re
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', limit_host):
            running_targets.add(limit_host)
        else:
            from modules.ansible.inventory import get_existing_ip_mappings
            try:
                ip_to_name, _ = get_existing_ip_mappings(ANSIBLE_PLAYBOOKS_DIR)
                for ip, name in ip_to_name.items():
                    if name == limit_host:
                        running_targets.add(ip)
            except Exception:
                pass
    else:
        running_targets = inventory_ips

    from modules.proxmox.monitor.state import active_ansible_targets
    active_ansible_targets.update(running_targets)
    
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
        
        # Поиск хостов, требующих перезагрузки
        reboot_hosts = []
        if real_filename == 'update_servers.yml' and process.returncode == 0:
            import re
            for line in output.splitlines():
                m = re.search(r'Reboot required on\s+([a-zA-Z0-9_\-\.]+)', line)
                if m:
                    h_name = m.group(1).strip()
                    if h_name not in reboot_hosts:
                        reboot_hosts.append(h_name)

        # Формирование клавиатуры
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = get_ansible_main_keyboard()
        if reboot_hosts:
            reboot_buttons = []
            for h in reboot_hosts:
                reboot_buttons.append([InlineKeyboardButton(text=f"🔄 Перезагрузить {h}", callback_data=f"ansible_reboot_host:{h}")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=reboot_buttons + keyboard.inline_keyboard)

        if len(full_log_escaped) > 3500:
            temp_log_path = f"ansible_log_{real_filename}.txt"
            with open(temp_log_path, "w", encoding="utf-8") as f:
                f.write(full_log)
                
            from aiogram.types import FSInputFile
            logfile = FSInputFile(temp_log_path)
            await status_msg.delete()
            
            caption = f"📝 Полный лог <b>{real_filename}</b> {target_text}.\nСтатус: {status}"
            if reboot_hosts:
                caption += f"\n\n⚠️ <b>Требуется перезагрузка для:</b>\n" + "\n".join([f"• {h}" for h in reboot_hosts])
            
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.answer_document(
                    document=logfile, 
                    caption=caption, 
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await status_msg.answer_document(
                    document=logfile, 
                    caption=caption, 
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            os.remove(temp_log_path)
        else:
            text = f"📝 Отчет по <b>{real_filename}</b> {target_text}\nСтатус: {status}\n<pre><code class='language-bash'>{full_log_escaped}</code></pre>"
            if reboot_hosts:
                text += f"\n\n⚠️ <b>Требуется перезагрузка для:</b>\n" + "\n".join([f"• {h}" for h in reboot_hosts])
                
            await status_msg.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

    except Exception as e:
        logging.error(f"Ansible run error: {e}")
        await status_msg.edit_text(
            f"❌ Системная ошибка при инициализации Ansible:\nУбедитесь, что 'ansible-playbook' установлен.\n<code>{e}</code>", 
            parse_mode="HTML", 
            reply_markup=get_ansible_main_keyboard()
        )
    finally:
        from modules.proxmox.monitor.state import active_ansible_targets
        for ip in running_targets:
            active_ansible_targets.discard(ip)

async def reboot_host_via_ansible(message_or_callback, host_name: str):
    playbook_path = os.path.abspath(os.path.join(ANSIBLE_PLAYBOOKS_DIR, 'reboot_server.yml'))
    
    inventory_files = ['hosts.ini', 'inventory', 'hosts']
    inventory_path = None
    for f in inventory_files:
        p = os.path.join(ANSIBLE_PLAYBOOKS_DIR, f)
        if os.path.exists(p):
            inventory_path = p
            break
            
    cmd = ["ansible-playbook", playbook_path, "--limit", host_name]
    if inventory_path:
        cmd.extend(["-i", inventory_path])
        
    if isinstance(message_or_callback, types.CallbackQuery):
        status_msg = message_or_callback.message
        await message_or_callback.message.edit_text(f"⏳ Перезагружаю хост <b>{html.escape(host_name)}</b> через Ansible...", parse_mode="HTML")
        try:
            await message_or_callback.answer()
        except Exception:
            pass
    else:
        status_msg = await message_or_callback.answer(f"⏳ Перезагружаю хост <b>{html.escape(host_name)}</b> через Ansible...", parse_mode="HTML")

    # Определяем целевой IP для временного обхода алертов
    running_targets = set()
    if host_name:
        import re
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host_name):
            running_targets.add(host_name)
        else:
            from modules.ansible.inventory import get_existing_ip_mappings
            try:
                ip_to_name, _ = get_existing_ip_mappings(ANSIBLE_PLAYBOOKS_DIR)
                for ip, name in ip_to_name.items():
                    if name == host_name:
                        running_targets.add(ip)
            except Exception:
                pass

    from modules.proxmox.monitor.state import active_ansible_targets
    active_ansible_targets.update(running_targets)

    try:
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
            
            if process.returncode == 0:
                await status_msg.edit_text(
                    f"✅ Хост <b>{html.escape(host_name)}</b> успешно перезагружен!",
                    parse_mode="HTML",
                    reply_markup=get_ansible_main_keyboard()
                )
            else:
                full_log = output + "\n\n=== ERRRORS ===\n" + err_output
                logging.error(f"Failed to reboot {host_name}: {full_log}")
                await status_msg.edit_text(
                    f"❌ Ошибка перезагрузки хоста <b>{html.escape(host_name)}</b>:\n<pre><code class='language-bash'>{html.escape(err_output or output)[:1000]}</code></pre>",
                    parse_mode="HTML",
                    reply_markup=get_ansible_main_keyboard()
                )
        finally:
            from modules.proxmox.monitor.state import active_ansible_targets
            for ip in running_targets:
                active_ansible_targets.discard(ip)
    except Exception as e:
        logging.error(f"Error rebooting host {host_name}: {e}")
        await status_msg.edit_text(
            f"❌ Системная ошибка при перезагрузке хоста {host_name}:\n<code>{e}</code>",
            parse_mode="HTML",
            reply_markup=get_ansible_main_keyboard()
        )
