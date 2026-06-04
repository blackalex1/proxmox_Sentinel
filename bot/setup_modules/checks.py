import os
import shutil
import asyncio

from setup_modules.utils import print_header, print_success, print_warning, print_error, print_info

async def check_systemd_service():
    """Check if the proxmox-lxc-bot systemd service is active."""
    print_header("Проверка службы Systemd")
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "is-active", "proxmox-lxc-bot.service",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, _ = await proc.communicate()
        status = stdout_bytes.decode('utf-8').strip()
        
        if status == "active":
            print_success("Служба proxmox-lxc-bot.service АКТИВНА.")
            return True
        else:
            print_warning(f"Служба proxmox-lxc-bot.service не запущена (Статус: {status}).")
            print_warning("Запустите службу перед началом теста: sudo systemctl start proxmox-lxc-bot.service")
            return False
    except Exception as e:
        print_error(f"Не удалось проверить статус службы через systemctl: {e}")
        return False

async def check_sysctl():
    """Verify net.bridge.bridge-nf-call-iptables sysctl configuration."""
    print_header("Проверка конфигурации моста ядра (Sysctl)")
    try:
        proc = await asyncio.create_subprocess_exec(
            "sysctl", "-n", "net.bridge.bridge-nf-call-iptables",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, _ = await proc.communicate()
        val = stdout_bytes.decode('utf-8').strip()
        
        if val == "1":
            print_success("net.bridge.bridge-nf-call-iptables установлен в 1 (трафик моста идет через iptables).")
            return True
        else:
            print_error(f"net.bridge.bridge-nf-call-iptables равен {val} (должен быть 1).")
            print_info("Попробуйте выполнить: sudo sysctl -w net.bridge.bridge-nf-call-iptables=1")
            return False
    except Exception as e:
        print_error(f"Не удалось прочитать параметры sysctl: {e}")
        return False

async def get_running_containers():
    """List running LXC containers on the host."""
    print_header("Поиск запущенных LXC-контейнеров")
    if not shutil.which("pct"):
        print_warning("Утилита pct не найдена. Возможно, этот скрипт запущен не на хосте Proxmox VE.")
        return []
        
    try:
        proc = await asyncio.create_subprocess_exec(
            "pct", "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, _ = await proc.communicate()
        lines = stdout_bytes.decode('utf-8').splitlines()
        
        running_vmids = []
        # Пропускаем заголовок pct list
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                vmid = parts[0]
                status = parts[1]
                name = parts[2]
                if status == "running":
                    running_vmids.append((int(vmid), name))
                    print_info(f"Обнаружен запущенный контейнер VMID {vmid} ({name})")
                    
        if not running_vmids:
            print_warning("Нет запущенных LXC-контейнеров на этом хосте.")
        return running_vmids
    except Exception as e:
        print_error(f"Ошибка при получении списка контейнеров: {e}")
        return []

async def get_running_vms():
    """List running QEMU VMs to log status details."""
    print_header("Поиск запущенных Виртуальных Машин (QEMU)")
    if not shutil.which("qm"):
        return []
    try:
        proc = await asyncio.create_subprocess_exec(
            "qm", "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, _ = await proc.communicate()
        lines = stdout_bytes.decode('utf-8').splitlines()
        
        running_vms = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                vmid = parts[0]
                status = parts[2]
                name = parts[1]
                if status == "running":
                    running_vms.append((int(vmid), name))
                    print_info(f"Обнаружена запущенная виртуальная машина QEMU VMID {vmid} ({name})")
        return running_vms
    except Exception as e:
        print_error(f"Ошибка при получении списка виртуальных машин: {e}")
        return []

async def check_lxc_firewall_enabled(vmid):
    """Check if at least one network interface has firewall=1 enabled in the LXC configuration."""
    conf_path = f"/etc/pve/lxc/{vmid}.conf"
    if not os.path.exists(conf_path):
        return False
    try:
        with open(conf_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("net") and ":" in line:
                    if "firewall=1" in line:
                        return True
    except Exception:
        pass
    return False
