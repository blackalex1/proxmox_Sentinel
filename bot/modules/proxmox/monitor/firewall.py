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
        logging.info("monitoring_vnutrennego_trafika_vpn-konteynera_otklyuchen_vpn_vmid_0")
        return False
    try:
        # Проверяем, запущен ли контейнер
        status_check = subprocess.run(
            ["pct", "status", str(VPN_VMID)],
            capture_output=True,
            text=True
        )
        if "status: running" not in status_check.stdout:
            logging.info("vpn_container_is_not_running_skipping_rules", VPN_VMID)
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
            logging.info("successfully_set_iptables_rule_for_local_processes", VPN_VMID)
        else:
            logging.info("rule_for_local_processes_is_already_set", VPN_VMID)
        return True
    except Exception as e:
        logging.error("error_setting_iptables_rules_in_vpn_container", VPN_VMID, e)
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
        logging.info("iptables_rules_successfully_removed_from_vpn_container", VPN_VMID)
    except Exception as e:
        logging.error("error_removing_iptables_rules_from_vpn_container", VPN_VMID, e)


def setup_iptables():
    """Установка logging-правил в iptables для захвата трафика LXC и Хоста."""
    if platform.system() != 'Linux':
        logging.warning("port_traffic_monitoring_is_only_available_on")
        return False
        
    try:
        # Проверяем, есть ли права root
        if os.geteuid() != 0:
            logging.error("trafik_portov_trebuyutsya_prava_root_sudo_dlya")
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
                logging.info("kernel_parameter_sysctl_net_bridge_bridge-nf-call-iptables_1")
            else:
                logging.info("yadernyy_parametr_net_bridge_bridge-nf-call-iptables_uzhe_vklyuchen")
        except Exception as sysctl_err:
            logging.warning("failed_to_configure_bridge-nf-call-iptables_automatically_make_sure", sysctl_err)

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
            logging.info("ustanovleno_iptables_pravilo_dlya_vkhodyaschego_trafika_lxc")

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
            logging.info("ustanovleno_iptables_pravilo_dlya_iskhodyaschego_trafika_lxc")

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
            logging.info("ustanovleno_iptables_pravilo_dlya_vkhodyaschego_trafika_khosta")
            
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
            logging.info("ustanovleno_iptables_pravilo_dlya_iskhodyaschego_trafika_khosta")
            
        # Настройка логирования внутренних процессов VPN контейнера
        setup_vpn_container_rules()
            
        return True
    except Exception as e:
        logging.error("error_setting_iptables_log_rules", e)
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
        
        logging.info("iptables_rules_for_lxc_and_host_traffic")
    except Exception as e:
        logging.error("error_removing_iptables_rules", e)
