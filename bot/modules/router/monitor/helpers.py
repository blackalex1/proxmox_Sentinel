import logging

from core.config import settings
from core.runtime_state import active_proxy_checks, is_proxy_selection_in_progress
import core.sys_utils as _sys_utils
from core.sys_utils import get_host_local_ips, is_local_bot_process


async def check_is_bot_or_admin(src_ip, src_port, dst_host=None, dst_port=None):
    """Проверяет, является ли отправитель доверенным (администратором или легитимным процессом бота на хосте)."""
    try:
        if is_proxy_selection_in_progress():
            host_ips = get_host_local_ips()
            if src_ip in host_ips:
                logging.debug("check_is_bot_or_admin_match_found_during_proxy_selection: src=%s, dst=%s:%s", src_ip, dst_host, dst_port)
                return True
    except Exception as e:
        logging.error("check_is_bot_or_admin_error_checking_proxy_selection", e)

    if dst_host and dst_port:
        try:
            if active_proxy_checks.get((dst_host, dst_port), 0) > 0:
                logging.debug("check_is_bot_or_admin_match_found_in_active_proxy_checks_for", dst_host, dst_port)
                return True
        except Exception as e:
            logging.error("check_is_bot_or_admin_error_checking_active_proxy_checks", e)

    if settings.is_trusted_admin_ip(src_ip):
        return True

    if src_ip == settings.router_ssh_host:
        return True

    try:
        bot_pub_ip = await _sys_utils.get_bot_public_ip()
        if bot_pub_ip and src_ip == bot_pub_ip:
            return True
    except Exception:
        pass

    if dst_host and dst_port:
        host_ips = get_host_local_ips()
        is_bot_source = (
            src_ip in host_ips
            or src_ip in ("127.0.0.1", "::1")
            or (settings.proxmox_host and src_ip in settings.proxmox_host)
        )
        if is_bot_source:
            if dst_host == settings.router_ssh_host and dst_port == settings.router_ssh_port:
                return True
            remote_ips = settings.get_remote_server_ips()
            if dst_host in remote_ips and dst_port == 22:
                return True

    if src_port and await is_local_bot_process(src_port):
        return True

    return False
