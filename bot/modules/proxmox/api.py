import logging
from proxmoxer import ProxmoxAPI
from core.config import settings

class ProxmoxClient:
    def __init__(self):
        if not settings.proxmox_host:
            logging.warning("proxmox_host_is_not_set_work_with_proxmox")
            return
            
        if settings.proxmox_token_id and settings.proxmox_token_secret:
            token_name = settings.proxmox_token_id.split('!')[1] if '!' in settings.proxmox_token_id else settings.proxmox_token_id
            self.proxmox = ProxmoxAPI(
                settings.proxmox_host, 
                user=settings.proxmox_user, 
                token_name=token_name,
                token_value=settings.proxmox_token_secret, 
                verify_ssl=settings.proxmox_verify_ssl
            )
        else:
            logging.error("proxmox_token_id_or_proxmox_token_secret_not_set")

    def get_nodes(self):
        return self.proxmox.nodes.get()
        
    def get_vms(self, node_name):
        if not self.proxmox: return []
        try:
            # Получаем все ВМ и Контейнеры кластера разом (Proxmox API сам склеивает QEMU и LXC)
            # и возвращает стабильное поле 'type' ('qemu' или 'lxc')
            resources = self.proxmox.cluster.resources.get(type='vm')
            return [res for res in resources if res.get('node') == node_name]
        except Exception as e:
            logging.error("error_obtaining_machines_list", e)
            return []

    def get_lxc_ip(self, node_name, vm_id):
        if not self.proxmox: return None
        try:
            # Сначала пробуем получить через interfaces (для запущенных контейнеров)
            try:
                interfaces = self.proxmox.nodes(node_name).lxc(vm_id).interfaces.get()
                for iface in interfaces:
                    if iface.get('name') != 'lo':
                        inet = iface.get('inet')
                        if inet:
                            ip = inet.split('/')[0]
                            if ip and ip != '0.0.0.0':
                                return ip
            except Exception:
                pass

            # Если не получилось (например, контейнер выключен или нет прав на interfaces),
            # пробуем прочитать из конфига net0
            config = self.proxmox.nodes(node_name).lxc(vm_id).config.get()
            for k, v in config.items():
                if k.startswith('net'):
                    # name=eth0,bridge=vmbr0,firewall=1,hwaddr=...,ip=192.168.1.101/24,gw=...
                    for part in v.split(','):
                        if part.startswith('ip='):
                            ip_val = part.split('=')[1]
                            if '/' in ip_val:
                                ip = ip_val.split('/')[0]
                                if ip and ip != 'dhcp' and ip != 'manual':
                                    return ip
        except Exception as e:
            logging.error("error_obtaining_ip_for_lxc", vm_id, e)
        return None

    def start_vm(self, node_name, vm_id, is_lxc=False):
        vm_type = 'lxc' if is_lxc else 'qemu'
        return getattr(self.proxmox.nodes(node_name), vm_type)(vm_id).status.start.post()

    def stop_vm(self, node_name, vm_id, is_lxc=False):
        vm_type = 'lxc' if is_lxc else 'qemu'
        return getattr(self.proxmox.nodes(node_name), vm_type)(vm_id).status.stop.post()

    def shutdown_vm(self, node_name, vm_id, is_lxc=False):
        vm_type = 'lxc' if is_lxc else 'qemu'
        return getattr(self.proxmox.nodes(node_name), vm_type)(vm_id).status.shutdown.post()

    def reboot_vm(self, node_name, vm_id, is_lxc=False):
        vm_type = 'lxc' if is_lxc else 'qemu'
        return getattr(self.proxmox.nodes(node_name), vm_type)(vm_id).status.reboot.post()

    def get_vm_status(self, node_name, vm_id, is_lxc=False):
        vm_type = 'lxc' if is_lxc else 'qemu'
        return getattr(self.proxmox.nodes(node_name), vm_type)(vm_id).status.current.get()

    def get_node_status(self, node_name):
        if not self.proxmox: return {}
        try:
            return self.proxmox.nodes(node_name).status.get()
        except Exception as e:
            logging.error("error_obtaining_status_for_node", node_name, e)
            return {}

    def clone_vm(self, node_name, vm_id, new_id, new_name, is_lxc=False):
        vm_type = 'lxc' if is_lxc else 'qemu'
        return getattr(self.proxmox.nodes(node_name), vm_type)(vm_id).clone.post(
            newid=new_id, 
            name=new_name, 
            full=1
        )

proxmox = ProxmoxClient()
