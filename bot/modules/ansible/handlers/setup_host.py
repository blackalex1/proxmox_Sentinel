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
            logging.info("Создан пользователь ansible на хосте Proxmox")
            
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
        
        logging.info("Успешно настроен пользователь ansible на хосте Proxmox")
        return True
    except Exception as e:
        logging.error(f"Ошибка настройки пользователя ansible на хосте Proxmox: {e}")
        return False

@router.callback_query(F.data == "ansible_setup_host")
async def process_ansible_setup_host_handler(callback: CallbackQuery):
    await callback.message.edit_text("⏳ Начинаю настройку на хосте Proxmox VE. Это может занять несколько секунд...")
    
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

    # Запускаем локальную настройку
    ok = await setup_ansible_user_on_host(pub_key_content)
    
    if ok:
        await callback.message.edit_text(
            "✅ <b>Настройка Хоста Proxmox завершена!</b>\n\n"
            "🟢 Пользователь <code>ansible</code> успешно настроен непосредственно на гипервизоре.\n"
            "Ему предоставлен беспарольный доступ <code>sudo</code> и прописан публичный SSH-ключ бота.",
            parse_mode="HTML",
            reply_markup=get_ansible_main_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка при настройке Хоста Proxmox</b>\n\n"
            "Не удалось настроить пользователя <code>ansible</code> локально на хосте. Проверьте логи бота.",
            parse_mode="HTML",
            reply_markup=get_ansible_main_keyboard()
        )
