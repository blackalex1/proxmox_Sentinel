import asyncio
import os
import logging
from aiogram import F
from aiogram.types import CallbackQuery
from core.config import settings, base_dir
from modules.ansible.keyboards import get_ansible_main_keyboard
from .playbooks import router

ANSIBLE_PLAYBOOKS_DIR = settings.ansible_playbooks_dir or os.path.join(base_dir, 'ansible')

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
