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

router = Router(name="ansible_router")

class AnsibleState(StatesGroup):
    waiting_for_host = State()


@router.callback_query(F.data == "ansible_main")
async def process_ansible_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    # Импортируем и вызываем автоматическое наполнение hosts.ini
    from modules.ansible.keyboards import generate_ansible_hosts_ini
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


# ==========================================
# Управление окружением и пользователями Ansible
# ==========================================

async def setup_ansible_user_in_lxc(vmid: int, pub_key_content: str) -> bool:
    """Настраивает пользователя ansible в LXC контейнере с помощью pct exec."""
    try:
        # 1. Проверяем, существует ли пользователь ansible
        check_user = await asyncio.create_subprocess_exec(
            "pct", "exec", str(vmid), "--", "id", "ansible",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await check_user.wait()
        
        if check_user.returncode != 0:
            # Пользователь не существует, создаем его
            create_cmd = ["pct", "exec", str(vmid), "--", "useradd", "-m", "-s", "/bin/bash", "ansible"]
            proc = await asyncio.create_subprocess_exec(*create_cmd)
            await proc.wait()
            logging.info(f"Создан пользователь ansible в LXC {vmid}")
            
        # 2. Добавляем в sudoers для беспарольного доступа
        # В некоторых дистрибутивах нужно установить sudo, если его нет
        install_sudo = await asyncio.create_subprocess_exec(
            "pct", "exec", str(vmid), "--", "apt-get", "-y", "install", "sudo",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await install_sudo.wait()
        
        # Добавляем беспарольный sudo
        sudoers_line = "ansible ALL=(ALL) NOPASSWD: ALL"
        sudoers_cmd = ["pct", "exec", str(vmid), "--", "bash", "-c", 
                       f"echo '{sudoers_line}' > /etc/sudoers.d/ansible && chmod 440 /etc/sudoers.d/ansible"]
        proc = await asyncio.create_subprocess_exec(*sudoers_cmd)
        await proc.wait()
        
        # 3. Настраиваем SSH authorized_keys
        setup_ssh_cmd = ["pct", "exec", str(vmid), "--", "bash", "-c", 
                         f"mkdir -p /home/ansible/.ssh && "
                         f"echo '{pub_key_content.strip()}' > /home/ansible/.ssh/authorized_keys && "
                         f"chown -R ansible:ansible /home/ansible/.ssh && "
                         f"chmod 700 /home/ansible/.ssh && "
                         f"chmod 600 /home/ansible/.ssh/authorized_keys"]
        proc = await asyncio.create_subprocess_exec(*setup_ssh_cmd)
        await proc.wait()
        
        logging.info(f"Успешно настроен пользователь ansible в LXC {vmid}")
        return True
    except Exception as e:
        logging.error(f"Ошибка настройки пользователя ansible в LXC {vmid}: {e}")
        return False


async def setup_ansible_user_on_remote_vps(server: dict, pub_key_content: str) -> bool:
    """Настраивает пользователя ansible на удаленном VPS по SSH (под root)."""
    from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
    try:
        # 1. Проверяем, существует ли пользователь ansible
        success, stdout, stderr = await run_remote_ssh_cmd(server, ["id ansible"])
        user_exists = success and "uid=" in stdout
        
        if not user_exists:
            # Создаем пользователя
            create_success, _, create_err = await run_remote_ssh_cmd(server, ["useradd -m -s /bin/bash ansible"])
            if not create_success:
                logging.error(f"Не удалось создать пользователя ansible на VPS {server['ip']}: {create_err}")
                return False
                
        # 2. Настраиваем sudoers
        # Устанавливаем sudo на VPS на случай, если его нет
        await run_remote_ssh_cmd(server, ["apt-get -y install sudo || yum -y install sudo"])
        
        sudoers_line = "ansible ALL=(ALL) NOPASSWD: ALL"
        sudo_cmd = f"echo '{sudoers_line}' > /etc/sudoers.d/ansible && chmod 440 /etc/sudoers.d/ansible"
        sudo_success, _, sudo_err = await run_remote_ssh_cmd(server, [sudo_cmd])
        if not sudo_success:
            logging.error(f"Не удалось настроить sudoers на VPS {server['ip']}: {sudo_err}")
            return False
            
        # 3. Настраиваем SSH авторизацию
        ssh_cmd = (f"mkdir -p /home/ansible/.ssh && "
                   f"echo '{pub_key_content.strip()}' > /home/ansible/.ssh/authorized_keys && "
                   f"chown -R ansible:ansible /home/ansible/.ssh && "
                   f"chmod 700 /home/ansible/.ssh && "
                   f"chmod 600 /home/ansible/.ssh/authorized_keys")
        ssh_success, _, ssh_err = await run_remote_ssh_cmd(server, [ssh_cmd])
        if not ssh_success:
            logging.error(f"Не удалось настроить SSH authorized_keys на VPS {server['ip']}: {ssh_err}")
            return False
            
        logging.info(f"Успешно настроен пользователь ansible на удаленном VPS {server['ip']}")
        return True
    except Exception as e:
        logging.error(f"Ошибка настройки пользователя ansible на VPS {server['ip']}: {e}")
        return False


async def check_lxc_ansible_status(vmid: int, pub_key_content: str) -> bool:
    """Checks if user 'ansible' is configured in LXC container."""
    if not pub_key_content:
        return False
    try:
        parts = pub_key_content.strip().split()
        key_body = parts[1] if len(parts) >= 2 else pub_key_content.strip()
        
        check_cmd = [
            "pct", "exec", str(vmid), "--", "bash", "-c",
            f"id ansible && test -f /home/ansible/.ssh/authorized_keys && grep -q '{key_body}' /home/ansible/.ssh/authorized_keys"
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *check_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        return proc.returncode == 0
    except Exception as e:
        logging.error(f"Error checking ansible status in LXC {vmid}: {e}")
        return False


async def check_vps_ansible_status(server: dict, pub_key_content: str) -> bool:
    """Checks if user 'ansible' is configured on remote VPS."""
    if not pub_key_content:
        return False
    from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
    try:
        parts = pub_key_content.strip().split()
        key_body = parts[1] if len(parts) >= 2 else pub_key_content.strip()
        
        check_cmd = f"id ansible && test -f /home/ansible/.ssh/authorized_keys && grep -q '{key_body}' /home/ansible/.ssh/authorized_keys"
        success, _, _ = await run_remote_ssh_cmd(server, [check_cmd])
        return success
    except Exception as e:
        logging.error(f"Error checking ansible status on VPS {server.get('ip')}: {e}")
        return False


@router.callback_query(F.data == "ansible_setup_env")
async def process_ansible_setup_env(callback: CallbackQuery):
    from modules.ansible.keyboards import get_ansible_setup_keyboard, check_and_generate_ansible_keys
    
    # 1. Отвечаем на callback и показываем индикатор загрузки
    await callback.answer("Проверяю статус хостов...")
    
    status_msg = callback.message
    try:
        await callback.message.edit_text(
            "🔍 <b>Настройка окружения Ansible</b>\n\n"
            "⌛ <i>Опрашиваю состояние LXC контейнеров и удаленных серверов, пожалуйста, подождите...</i>",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "there is no text in the message to edit" in str(e):
            await callback.message.delete()
            status_msg = await callback.message.answer(
                "🔍 <b>Настройка окружения Ansible</b>\n\n"
                "⌛ <i>Опрашиваю состояние LXC контейнеров и удаленных серверов, пожалуйста, подождите...</i>",
                parse_mode="HTML"
            )
        else:
            raise e
    
    # Генерируем/проверяем ключи
    check_and_generate_ansible_keys(ANSIBLE_PLAYBOOKS_DIR)
    
    pub_key_path = os.path.join(ANSIBLE_PLAYBOOKS_DIR, 'id_ed25519_ansible.pub')
    pub_key_content = ""
    if os.path.exists(pub_key_path):
        try:
            with open(pub_key_path, 'r', encoding='utf-8') as f:
                pub_key_content = f.read().strip()
        except Exception as e:
            logging.error(f"Error reading public key: {e}")
            
    # Получаем список активных LXC
    from modules.proxmox.api import proxmox
    lxc_hosts = []
    if proxmox.proxmox:
        try:
            resources = proxmox.proxmox.cluster.resources.get(type='vm')
            for res in resources:
                if res.get('type') == 'lxc' and res.get('status') == 'running':
                    lxc_hosts.append({
                        'vmid': res.get('vmid'),
                        'name': res.get('name'),
                        'node': res.get('node')
                    })
        except Exception as e:
            logging.error(f"Error fetching PVE resources for status check: {e}")
            
    # Получаем список VPS
    vps_hosts = settings.remote_servers or []
    
    # Опрашиваем хосты в параллели
    lxc_results = []
    vps_results = []
    tasks = []
    
    async def check_lxc(l_host):
        is_ok = await check_lxc_ansible_status(l_host['vmid'], pub_key_content)
        lxc_results.append((l_host, is_ok))
        
    async def check_vps(v_host):
        is_ok = await check_vps_ansible_status(v_host, pub_key_content)
        vps_results.append((v_host, is_ok))
        
    for lxc in lxc_hosts:
        tasks.append(check_lxc(lxc))
    for vps in vps_hosts:
        tasks.append(check_vps(vps))
        
    if tasks:
        await asyncio.gather(*tasks)
        
    # Сортируем
    lxc_results.sort(key=lambda x: x[0]['vmid'])
    vps_results.sort(key=lambda x: x[0].get('ip', ''))
    
    # Формируем статус-текст
    status_text = ""
    if lxc_results:
        status_text += "<b>Контейнеры LXC:</b>\n"
        for l_host, is_ok in lxc_results:
            emoji = "🟢" if is_ok else "🔴"
            status_text += f"{emoji} LXC {l_host['vmid']} ({l_host['name']})\n"
        status_text += "\n"
    else:
        status_text += "<b>Контейнеры LXC:</b>\n<i>Нет активных контейнеров</i>\n\n"
        
    if vps_results:
        status_text += "<b>Удаленные VPS серверы:</b>\n"
        for v_host, is_ok in vps_results:
            emoji = "🟢" if is_ok else "🔴"
            label = v_host.get('label') or 'VPS'
            status_text += f"{emoji} {label} ({v_host.get('ip')})\n"
        status_text += "\n"
    else:
        status_text += "<b>Удаленные VPS серверы:</b>\n<i>Нет настроенных VPS серверов</i>\n\n"
        
    await status_msg.edit_text(
        f"🔑 <b>Настройка окружения Ansible</b>\n\n"
        f"Я могу автоматически создать пользователя <code>ansible</code> с беспарольным доступом <code>sudo</code> "
        f"и установить сгенерированный публичный SSH-ключ:\n"
        f"• Во все <b>активные LXC контейнеры</b> на хосте Proxmox.\n"
        f"• На все <b>удаленные VPS сервера</b>, добавленные в конфигурацию.\n\n"
        f"📋 <b>Текущий статус готовности хостов:</b>\n"
        f"{status_text}"
        f"<i>🟢 — настроен для работы с Ansible\n"
        f"🔴 — не настроен (или недоступен)</i>\n\n"
        f"Выберите область настройки:",
        parse_mode="HTML",
        reply_markup=get_ansible_setup_keyboard()
    )


@router.callback_query(F.data == "ansible_setup_lxc")
async def process_ansible_setup_lxc_handler(callback: CallbackQuery):
    await callback.message.edit_text("⏳ Начинаю настройку во всех активных LXC контейнерах. Это может занять несколько секунд...")
    
    pub_key_path = os.path.join(ANSIBLE_PLAYBOOKS_DIR, 'id_ed25519_ansible.pub')
    if not os.path.exists(pub_key_path):
        await callback.message.edit_text(
            "❌ Ошибка: Публичный ключ не найден. Пожалуйста, перезапустите бота, чтобы он сгенерировал ключи.",
            reply_markup=get_ansible_main_keyboard()
        )
        return
        
    try:
        with open(pub_key_path, 'r', encoding='utf-8') as f:
            pub_key_content = f.read().strip()
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка чтения публичного ключа: {e}", reply_markup=get_ansible_main_keyboard())
        return

    from modules.proxmox.api import proxmox
    success_ids = []
    failed_ids = []
    
    if not proxmox.proxmox:
        await callback.message.edit_text("❌ Ошибка: Подключение к Proxmox VE не настроено.", reply_markup=get_ansible_main_keyboard())
        return

    try:
        resources = proxmox.proxmox.cluster.resources.get(type='vm')
        tasks = []
        
        async def run_setup_for_lxc(res):
            if res.get('type') == 'lxc' and res.get('status') == 'running':
                vmid = res.get('vmid')
                # Вызываем наш хелпер настройки
                ok = await setup_ansible_user_in_lxc(vmid, pub_key_content)
                if ok:
                    success_ids.append(vmid)
                else:
                    failed_ids.append(vmid)

        for res in resources:
            if res.get('type') == 'lxc' and res.get('status') == 'running':
                tasks.append(run_setup_for_lxc(res))
                
        if tasks:
            await asyncio.gather(*tasks)
            
        success_str = ", ".join(map(str, sorted(success_ids))) if success_ids else "нет"
        failed_str = ", ".join(map(str, sorted(failed_ids))) if failed_ids else "нет"
        
        await callback.message.edit_text(
            f"✅ <b>Настройка LXC завершена!</b>\n\n"
            f"🟢 <b>Успешно настроены:</b> <code>{success_str}</code>\n"
            f"🔴 <b>Ошибки настройки:</b> <code>{failed_str}</code>\n\n"
            f"<i>Пользователь ansible получил беспарольный доступ sudo и публичный SSH-ключ.</i>",
            parse_mode="HTML",
            reply_markup=get_ansible_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ansible LXC setup error: {e}")
        await callback.message.edit_text(f"❌ Системная ошибка при настройке LXC: {e}", reply_markup=get_ansible_main_keyboard())


@router.callback_query(F.data == "ansible_setup_vps")
async def process_ansible_setup_vps_handler(callback: CallbackQuery):
    await callback.message.edit_text("⏳ Начинаю настройку на всех удаленных VPS серверах. Пожалуйста, подождите...")
    
    pub_key_path = os.path.join(ANSIBLE_PLAYBOOKS_DIR, 'id_ed25519_ansible.pub')
    if not os.path.exists(pub_key_path):
        await callback.message.edit_text(
            "❌ Ошибка: Публичный ключ не найден. Пожалуйста, перезапустите бота, чтобы он сгенерировал ключи.",
            reply_markup=get_ansible_main_keyboard()
        )
        return
        
    try:
        with open(pub_key_path, 'r', encoding='utf-8') as f:
            pub_key_content = f.read().strip()
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка чтения публичного ключа: {e}", reply_markup=get_ansible_main_keyboard())
        return

    from core.config import settings
    if not settings.remote_servers:
        await callback.message.edit_text("❌ Ошибка: В файле .env не настроены удаленные сервера VPS.", reply_markup=get_ansible_main_keyboard())
        return

    success_ips = []
    failed_ips = []
    tasks = []
    
    async def run_setup_for_vps(server):
        ok = await setup_ansible_user_on_remote_vps(server, pub_key_content)
        if ok:
            success_ips.append(server['ip'])
        else:
            failed_ips.append(server['ip'])
            
    for server in settings.remote_servers:
        tasks.append(run_setup_for_vps(server))
        
    if tasks:
        await asyncio.gather(*tasks)
        
    success_str = ", ".join(success_ips) if success_ips else "нет"
    failed_str = ", ".join(failed_ips) if failed_ips else "нет"
    
    await callback.message.edit_text(
        f"✅ <b>Настройка VPS завершена!</b>\n\n"
        f"🟢 <b>Успешно настроены:</b> <code>{success_str}</code>\n"
        f"🔴 <b>Ошибки настройки:</b> <code>{failed_str}</code>\n\n"
        f"<i>Пользователь ansible получил беспарольный доступ sudo и авторизован по SSH-ключу.</i>",
        parse_mode="HTML",
        reply_markup=get_ansible_main_keyboard()
    )

