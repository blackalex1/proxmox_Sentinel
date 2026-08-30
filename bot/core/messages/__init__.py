# bot/core/messages/__init__.py
"""
Централизованный пакет шаблонов сообщений и уведомлений.
Разбит на логические модули для удобства сопровождения и редактирования.
Экспортирует все функции построения Rich Messages для обратной совместимости.
"""

from .auth import (
    get_vps_ssh_login_alert,
    get_pve_web_login_alert,
    get_pve_web_fail_alert,
    get_ssh_login_alert,
    get_ssh_fail_alert,
    get_sudo_alert,
    get_ssh_close_alert,
)
from .nodes import (
    get_vps_offline_alert,
    get_vps_online_alert,
    get_node_offline_alert,
    get_node_online_alert,
    get_system_status_table,
)
from .resources import (
    get_vps_cpu_alert,
    get_vps_ram_alert,
    get_vps_disk_alert,
    get_lxc_state_alert,
    get_lxc_cpu_alert,
    get_lxc_ram_alert,
    get_lxc_disk_alert,
)
from .traffic import (
    get_ips_investigation_success_alert,
    get_ips_investigation_failed_alert,
    get_ips_sensitive_access_alert,
    get_ips_hysteria_attack_alert,
    get_ips_xray_attack_alert,
    get_ips_whitelisted_alert,
    get_ips_process_killed_alert,
    get_ips_process_warning_alert,
    get_local_traffic_alert,
)
from .router import (
    get_router_recovery_alert,
    get_router_unknown_block_alert,
    get_router_autoblock_alert,
    get_router_port_alert,
    get_router_clients_list_text,
    get_router_client_details_card,
)
from .spectre import (
    get_new_ip_alert,
    get_session_activity_card,
    get_client_disconnected_alert,
    get_ips_autoblock_alert_audit,
    get_login_success_alert,
    get_spectre_2fa_alert,
    get_top_traffic_table,
    get_panel_status_message,
)
from .proxy import (
    get_proxy_switch_alert,
    get_proxy_restored_alert,
)
from .whitelist import (
    get_whitelist_view_table,
    get_whitelist_view_all_table,
)
from .ban_center import (
    get_ban_center_table,
)
from .ansible import (
    get_ansible_missing_dir_text,
    get_ansible_playbooks_menu_text,
    get_ansible_ask_host_text,
    get_ansible_setup_loading_text,
    get_ansible_setup_menu_text,
    get_ansible_setup_host_start_text,
    get_ansible_setup_lxc_start_text,
    get_ansible_setup_vps_start_text,
    get_ansible_setup_success_text,
    get_ansible_setup_failed_text,
    get_ansible_run_start_text,
    get_ansible_run_success_text,
    get_ansible_run_failed_text,
    get_ansible_reboot_start_text,
    get_ansible_reboot_success_text,
    get_ansible_reboot_failed_text,
)
from .threats import (
    get_threats_table,
)
from core.rich import build_rich_message, parse_to_rich_text
from core.sender import (
    send_rich_message,
    edit_rich_message,
    send_rich_message_draft,
    send_alert_to_admins,
)

__all__ = [
    # Auth alerts
    "get_vps_ssh_login_alert",
    "get_pve_web_login_alert",
    "get_pve_web_fail_alert",
    "get_ssh_login_alert",
    "get_ssh_fail_alert",
    "get_sudo_alert",
    "get_ssh_close_alert",
    
    # Nodes/VPS connection alerts
    "get_vps_offline_alert",
    "get_vps_online_alert",
    "get_node_offline_alert",
    "get_node_online_alert",
    "get_system_status_table",
    
    # Resource metrics alerts
    "get_vps_cpu_alert",
    "get_vps_ram_alert",
    "get_vps_disk_alert",
    "get_lxc_state_alert",
    "get_lxc_cpu_alert",
    "get_lxc_ram_alert",
    "get_lxc_disk_alert",
    
    # Traffic/IPS alerts
    "get_ips_investigation_success_alert",
    "get_ips_investigation_failed_alert",
    "get_ips_sensitive_access_alert",
    "get_ips_hysteria_attack_alert",
    "get_ips_xray_attack_alert",
    "get_ips_whitelisted_alert",
    "get_ips_process_killed_alert",
    "get_ips_process_warning_alert",
    "get_local_traffic_alert",
    
    # Router alerts & UI
    "get_router_recovery_alert",
    "get_router_unknown_block_alert",
    "get_router_autoblock_alert",
    "get_router_port_alert",
    "get_router_clients_list_text",
    "get_router_client_details_card",
    
    # Spectre Panel alerts & tables
    "get_new_ip_alert",
    "get_session_activity_card",
    "get_client_disconnected_alert",
    "get_ips_autoblock_alert_audit",
    "get_login_success_alert",
    "get_spectre_2fa_alert",
    "get_top_traffic_table",
    "get_panel_status_message",
    
    # Proxy alerts
    "get_proxy_switch_alert",
    "get_proxy_restored_alert",
    
    # Whitelist templates
    "get_whitelist_view_table",
    "get_whitelist_view_all_table",
    
    # Ban Center templates
    "get_ban_center_table",
    
    # Ansible templates
    "get_ansible_missing_dir_text",
    "get_ansible_playbooks_menu_text",
    "get_ansible_ask_host_text",
    "get_ansible_setup_loading_text",
    "get_ansible_setup_menu_text",
    "get_ansible_setup_host_start_text",
    "get_ansible_setup_lxc_start_text",
    "get_ansible_setup_vps_start_text",
    "get_ansible_setup_success_text",
    "get_ansible_setup_failed_text",
    "get_ansible_run_start_text",
    "get_ansible_run_success_text",
    "get_ansible_run_failed_text",
    "get_ansible_reboot_start_text",
    "get_ansible_reboot_success_text",
    "get_ansible_reboot_failed_text",
    
    # Threats table
    "get_threats_table",
    
    # Rich Message Engine
    "build_rich_message",
    "parse_to_rich_text",
    
    # Sender functions
    "send_rich_message",
    "edit_rich_message",
    "send_rich_message_draft",
    "send_alert_to_admins",
]

