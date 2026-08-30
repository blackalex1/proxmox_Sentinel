import asyncio
import os
import logging
from aiogram import F
from aiogram.types import CallbackQuery
from core.config import settings, base_dir
from modules.ansible.keyboards import get_ansible_main_keyboard
from .playbooks import router

ANSIBLE_PLAYBOOKS_DIR = settings.ansible_playbooks_dir or os.path.join(base_dir, 'ansible')

async def setup_ansible_user_on_host(pub_key_content: str) -> bool:
    """Настраивает пользователя ansible на самом хосте Proxmox."""
    try:
        # 1. Проверяем, существует ли пользователь ansible
        check_user = await asyncio.create_subprocess_exec(
            "id", "ansible",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await check_user.wait()
        
        if check_user.returncode != 0:
            # Пользователь не существует, создаем его
            create_cmd = ["useradd", "-m", "-s", "/bin/bash", "ansible"]
            proc = await asyncio.create_subprocess_exec(*create_cmd)
            await proc.wait()
            logging.info("created_user_ansible_on_proxmox_host")
            
        # 2. Добавляем в sudoers для беспарольного доступа
        sudoers_line = "ansible ALL=(ALL) NOPASSWD: ALL"
        sudoers_cmd = ["bash", "-c", 
                       f"echo '{sudoers_line}' > /etc/sudoers.d/ansible && chmod 440 /etc/sudoers.d/ansible"]
        proc = await asyncio.create_subprocess_exec(*sudoers_cmd)
        await proc.wait()
        
        # 3. Настраиваем SSH authorized_keys
        setup_ssh_cmd = ["bash", "-c", 
                          f"mkdir -p /home/ansible/.ssh && "
                          f"echo '{pub_key_content.strip()}' >> /home/ansible/.ssh/authorized_keys && "
                          f"sort -u /home/ansible/.ssh/authorized_keys -o /home/ansible/.ssh/authorized_keys && "
                          f"chown -R ansible:ansible /home/ansible/.ssh && "
                          f"chmod 700 /home/ansible/.ssh && "
                          f"chmod 600 /home/ansible/.ssh/authorized_keys"]
        proc = await asyncio.create_subprocess_exec(*setup_ssh_cmd)
        await proc.wait()
        
        logging.info("successfully_configured_user_ansible_on_proxmox_host")
        return True
    except Exception as e:
        logging.error("error_configuring_user_ansible_on_proxmox_host", e)
        return False

from core.messages import (
    get_ansible_setup_host_start_text,
    get_ansible_setup_success_text,
    get_ansible_setup_failed_text,
)

@router.callback_query(F.data == "ansible_setup_host")
async def process_ansible_setup_host_handler(callback: CallbackQuery):
    await callback.message.edit_text(get_ansible_setup_host_start_text(), parse_mode="HTML")
    
    pub_key_path = os.path.join(ANSIBLE_PLAYBOOKS_DIR, 'id_ed25519_ansible.pub')
    if not os.path.exists(pub_key_path):
        err_msg = get_ansible_setup_failed_text("Proxmox VE Host", "Public key not found")
        await callback.message.edit_text(err_msg, parse_mode="HTML", reply_markup=get_ansible_main_keyboard())
        return
        
    try:
        with open(pub_key_path, 'r', encoding='utf-8') as f:
            pub_key_content = f.read().strip()
    except Exception as e:
        err_msg = get_ansible_setup_failed_text("Proxmox VE Host", str(e))
        await callback.message.edit_text(err_msg, parse_mode="HTML", reply_markup=get_ansible_main_keyboard())
        return

    # Запускаем локальную настройку
    ok = await setup_ansible_user_on_host(pub_key_content)
    
    if ok:
        succ_msg = get_ansible_setup_success_text("Proxmox VE Host")
        await callback.message.edit_text(
            succ_msg,
            parse_mode="HTML",
            reply_markup=get_ansible_main_keyboard()
        )
    else:
        err_msg = get_ansible_setup_failed_text("Proxmox VE Host", "Check bot logs")
        await callback.message.edit_text(
            err_msg,
            parse_mode="HTML",
            reply_markup=get_ansible_main_keyboard()
        )

