# bot/core/messages/ansible.py
"""
Шаблоны сообщений и карточек для модуля Ansible с поддержкой i18n.
"""

import html
from core.messages.i18n import _


def get_ansible_missing_dir_text(playbooks_dir: str) -> str:
    return _("ansible", "missing_dir", playbooks_dir=html.escape(playbooks_dir))


def get_ansible_playbooks_menu_text() -> str:
    return _("ansible", "playbooks_menu")


def get_ansible_ask_host_text(filename: str) -> str:
    return _("ansible", "ask_host", filename=html.escape(filename))


def get_ansible_setup_loading_text() -> str:
    return _("ansible", "setup_loading")


def get_ansible_setup_menu_text(status_text: str) -> str:
    return _("ansible", "setup_menu", status_text=status_text)


def get_ansible_setup_host_start_text() -> str:
    return _("ansible", "setup_host_start")


def get_ansible_setup_lxc_start_text() -> str:
    return _("ansible", "setup_lxc_start")


def get_ansible_setup_vps_start_text() -> str:
    return _("ansible", "setup_vps_start")


def get_ansible_setup_success_text(target_name: str) -> str:
    return _("ansible", "setup_success", target_name=html.escape(target_name))


def get_ansible_setup_failed_text(target_name: str, error_msg: str) -> str:
    return _("ansible", "setup_failed", target_name=html.escape(target_name), error_msg=html.escape(str(error_msg)))


def get_ansible_run_start_text(filename: str, target_text: str) -> str:
    return _("ansible", "run_start", filename=html.escape(filename), target_text=html.escape(target_text))


def get_ansible_run_success_text(filename: str, target_text: str) -> str:
    return _("ansible", "run_success", filename=html.escape(filename), target_text=html.escape(target_text))


def get_ansible_run_failed_text(filename: str, target_text: str, error_msg: str) -> str:
    return _("ansible", "run_failed", filename=html.escape(filename), target_text=html.escape(target_text), error_msg=html.escape(str(error_msg)))


def get_ansible_reboot_start_text(host_name: str) -> str:
    return _("ansible", "reboot_start", host_name=html.escape(host_name))


def get_ansible_reboot_success_text(host_name: str) -> str:
    return _("ansible", "reboot_success", host_name=html.escape(host_name))


def get_ansible_reboot_failed_text(host_name: str, error_msg: str) -> str:
    return _("ansible", "reboot_failed", host_name=html.escape(host_name), error_msg=html.escape(str(error_msg)))

