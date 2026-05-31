import asyncio
import os
import logging
from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from core.config import settings, base_dir
ANSIBLE_PLAYBOOKS_DIR = settings.ansible_playbooks_dir or os.path.join(base_dir, 'ansible')
from modules.ansible.keyboards import get_ansible_setup_keyboard
from modules.ansible.keys import check_and_generate_ansible_keys
from .playbooks import router

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

async def check_host_ansible_status(pub_key_content: str) -> bool:
    """Checks if user 'ansible' is configured on the Proxmox Host."""
    if not pub_key_content:
        return False
    try:
        parts = pub_key_content.strip().split()
        key_body = parts[1] if len(parts) >= 2 else pub_key_content.strip()
        
        check_cmd = [
            "bash", "-c",
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
        logging.error(f"Error checking ansible status on Proxmox Host: {e}")
        return False

@router.callback_query(F.data == "ansible_setup_env")
async def process_ansible_setup_env(callback: CallbackQuery):
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
    host_is_ok = [False]
    
    async def check_lxc(l_host):
        is_ok = await check_lxc_ansible_status(l_host['vmid'], pub_key_content)
        lxc_results.append((l_host, is_ok))
        
    async def check_vps(v_host):
        is_ok = await check_vps_ansible_status(v_host, pub_key_content)
        vps_results.append((v_host, is_ok))
        
    async def check_host():
        is_ok = await check_host_ansible_status(pub_key_content)
        host_is_ok[0] = is_ok
        
    tasks.append(check_host())
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
    
    # Добавляем Proxmox Host
    pve_ip = "127.0.0.1"
    if settings.proxmox_host:
        pve_ip = settings.proxmox_host.split(':')[0]
    host_emoji = "🟢" if host_is_ok[0] else "🔴"
    status_text += f"<b>Хост Proxmox VE:</b>\n{host_emoji} proxmox ({pve_ip})\n\n"
    
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
        f"• На самом <b>Хосте Proxmox VE</b>.\n"
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
