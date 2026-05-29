import asyncio
import os
import logging
from aiogram import F
from aiogram.types import CallbackQuery
from core.config import settings, base_dir
from modules.ansible.keyboards import get_ansible_main_keyboard
from .playbooks import router

ANSIBLE_PLAYBOOKS_DIR = settings.ansible_playbooks_dir or os.path.join(base_dir, 'ansible')

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
