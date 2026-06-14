import os
import platform
import subprocess
import logging

from core.config import settings
VPN_VMID = settings.vpn_vmid

def setup_vpn_container_rules():
    """Установка logging-правил iptables внутри VPN-контейнера для контроля локальных процессов."""
    if platform.system() != 'Linux' or os.geteuid() != 0:
        return False
    if not VPN_VMID:
        logging.info("Мониторинг внутреннего трафика VPN-контейнера отключен (VPN_VMID=0).")
        return False
    try:
        # Проверяем, запущен ли контейнер
        status_check = subprocess.run(
            ["pct", "status", str(VPN_VMID)],
            capture_output=True,
            text=True
        )
        if "status: running" not in status_check.stdout:
            logging.info(f"VPN контейнер {VPN_VMID} не запущен. Пропускаем установку правил.")
            return False

        # Проверяем наличие правила во внутренней цепочке OUTPUT
        check_cmd = [
            "pct", "exec", str(VPN_VMID), "--",
            "iptables", "-C", "OUTPUT", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "LXC_VPN_LOCAL_OUT: "
        ]
        check_run = subprocess.run(check_cmd, capture_output=True)
        if check_run.returncode != 0:
            insert_cmd = [
                "pct", "exec", str(VPN_VMID), "--",
                "iptables", "-I", "OUTPUT", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "LXC_VPN_LOCAL_OUT: "
            ]
            subprocess.run(insert_cmd, check=True)
            logging.info(f"Успешно установлено iptables правило для локальных процессов внутри VPN контейнера {VPN_VMID}.")
        else:
            logging.info(f"Правило для локальных процессов уже установлено в VPN контейнере {VPN_VMID}.")
        return True
    except Exception as e:
        logging.error(f"Ошибка при установке iptables правил в VPN контейнере {VPN_VMID}: {e}")
        return False


def cleanup_vpn_container_rules():
    """Удаление logging-правил iptables из VPN-контейнера."""
    if platform.system() != 'Linux' or os.geteuid() != 0:
        return
    if not VPN_VMID:
        return
    try:
        # Проверяем статус контейнера перед удалением
        status_check = subprocess.run(
            ["pct", "status", str(VPN_VMID)],
            capture_output=True,
            text=True
        )
        if "status: running" not in status_check.stdout:
            return
        delete_cmd = [
            "pct", "exec", str(VPN_VMID), "--",
            "iptables", "-D", "OUTPUT", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "LXC_VPN_LOCAL_OUT: "
        ]
        subprocess.run(delete_cmd, capture_output=True)
        logging.info(f"Правила iptables успешно удалены из VPN контейнера {VPN_VMID}.")
    except Exception as e:
        logging.error(f"Ошибка при удалении iptables правил из VPN контейнера {VPN_VMID}: {e}")


def setup_iptables():
    """Установка logging-правил в iptables для захвата трафика LXC и Хоста."""
    if platform.system() != 'Linux':
        logging.warning("Трафик портов: Мониторинг доступен только на Linux.")
        return False
        
    try:
        # Проверяем, есть ли права root
        if os.geteuid() != 0:
            logging.error("Трафик портов: Требуются права ROOT (sudo) для установки правил iptables.")
            return False

        # Автоматическая настройка ядерных параметров фильтрации моста (sysctl)
        try:
            # 1. Попытка загрузить модуль ядра br_netfilter
            subprocess.run(["modprobe", "br_netfilter"], capture_output=True, timeout=3)
            
            # 2. Проверяем текущее значение sysctl
            sysctl_check = subprocess.run(
                ["sysctl", "-n", "net.bridge.bridge-nf-call-iptables"],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            # Если значение отсутствует, равно 0 или возвращает ошибку — принудительно включаем
            if sysctl_check.returncode != 0 or sysctl_check.stdout.strip() != "1":
                subprocess.run(
                    ["sysctl", "-w", "net.bridge.bridge-nf-call-iptables=1"],
                    capture_output=True,
                    check=True,
                    timeout=3
                )
                logging.info("Автоматически включен ядерный параметр sysctl net.bridge.bridge-nf-call-iptables=1.")
            else:
                logging.info("Ядерный параметр net.bridge.bridge-nf-call-iptables уже включен (1).")
        except Exception as sysctl_err:
            logging.warning(f"Не удалось автоматически настроить bridge-nf-call-iptables: {sysctl_err}. Убедитесь, что модуль br_netfilter загружен.")

        # Inbound правило (входящие к LXC через physdev)
        in_check = subprocess.run(
            ["iptables", "-C", "FORWARD", "-m", "physdev", "--physdev-out", "veth+", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "LXC_CONN: "],
            capture_output=True
        )
        if in_check.returncode != 0:
            subprocess.run(
                ["iptables", "-I", "FORWARD", "-m", "physdev", "--physdev-out", "veth+", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "LXC_CONN: "],
                check=True
            )
            logging.info("Установлено iptables правило для ВХОДЯЩЕГО трафика LXC (physdev).")

        # Outbound правило (исходящие от LXC через physdev)
        out_check = subprocess.run(
            ["iptables", "-C", "FORWARD", "-m", "physdev", "--physdev-in", "veth+", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "LXC_CONN_OUT: "],
            capture_output=True
        )
        if out_check.returncode != 0:
            subprocess.run(
                ["iptables", "-I", "FORWARD", "-m", "physdev", "--physdev-in", "veth+", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "LXC_CONN_OUT: "],
                check=True
            )
            logging.info("Установлено iptables правило для ИСХОДЯЩЕГО трафика LXC (physdev).")

        # Host Inbound правило (входящие к хосту на порты управления 22, 8006)
        host_check = subprocess.run(
            ["iptables", "-C", "INPUT", "-p", "tcp", "-m", "multiport", "--dports", "22,8006", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "HOST_CONN: "],
            capture_output=True
        )
        if host_check.returncode != 0:
            subprocess.run(
                ["iptables", "-I", "INPUT", "-p", "tcp", "-m", "multiport", "--dports", "22,8006", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "HOST_CONN: "],
                check=True
            )
            logging.info("Установлено iptables правило для ВХОДЯЩЕГО трафика Хоста (ports 22, 8006).")
            
        # Host Outbound правило (исходящие от хоста на sensitive порты)
        host_out_check = subprocess.run(
            ["iptables", "-C", "OUTPUT", "-p", "tcp", "-m", "multiport", "--dports", "22,3389,3306,5432,27017,8006", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "HOST_CONN_OUT: "],
            capture_output=True
        )
        if host_out_check.returncode != 0:
            subprocess.run(
                ["iptables", "-I", "OUTPUT", "-p", "tcp", "-m", "multiport", "--dports", "22,3389,3306,5432,27017,8006", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "HOST_CONN_OUT: "],
                check=True
            )
            logging.info("Установлено iptables правило для ИСХОДЯЩЕГО трафика Хоста (ports 22, 3389, 3306, 5432, 27017, 8006).")
            
        # Настройка логирования внутренних процессов VPN контейнера
        setup_vpn_container_rules()
            
        return True
    except Exception as e:
        logging.error(f"Ошибка при установке iptables LOG правил: {e}")
        return False


def cleanup_iptables():
    """Удаление logging-правил из iptables при завершении работы."""
    if platform.system() != 'Linux' or os.geteuid() != 0:
        return
        
    try:
        # Удаляем входящее
        subprocess.run(
            ["iptables", "-D", "FORWARD", "-m", "physdev", "--physdev-out", "veth+", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "LXC_CONN: "],
            capture_output=True
        )
        # Удаляем исходящее
        subprocess.run(
            ["iptables", "-D", "FORWARD", "-m", "physdev", "--physdev-in", "veth+", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "LXC_CONN_OUT: "],
            capture_output=True
        )
        # Удаляем хостовое входящее
        subprocess.run(
            ["iptables", "-D", "INPUT", "-p", "tcp", "-m", "multiport", "--dports", "22,8006", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "HOST_CONN: "],
            capture_output=True
        )
        # Удаляем хостовое исходящее
        subprocess.run(
            ["iptables", "-D", "OUTPUT", "-p", "tcp", "-m", "multiport", "--dports", "22,3389,3306,5432,27017,8006", "-m", "conntrack", "--ctstate", "NEW", "-j", "LOG", "--log-prefix", "HOST_CONN_OUT: "],
            capture_output=True
        )
        
        # Удаляем внутренние правила VPN контейнера
        cleanup_vpn_container_rules()
        
        logging.info("Правила iptables для трафика LXC и Хоста успешно удалены.")
    except Exception as e:
        logging.error(f"Ошибка при удалении iptables правил: {e}")
