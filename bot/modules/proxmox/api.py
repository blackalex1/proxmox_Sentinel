import logging
from proxmoxer import ProxmoxAPI
from core.config import settings

class ProxmoxClient:
    def __init__(self):
        if not settings.proxmox_host:
            logging.warning("PROXMOX_HOST не задан! Работа с Proxmox будет недоступна.")
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
            logging.error("Не заданы PROXMOX_TOKEN_ID или PROXMOX_TOKEN_SECRET!")

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
            logging.error(f"Ошибка получения списка машин: {e}")
            return []

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
            logging.error(f"Ошибка получения статуса ноды {node_name}: {e}")
            return {}

    def clone_vm(self, node_name, vm_id, new_id, new_name, is_lxc=False):
        vm_type = 'lxc' if is_lxc else 'qemu'
        return getattr(self.proxmox.nodes(node_name), vm_type)(vm_id).clone.post(
            newid=new_id, 
            name=new_name, 
            full=1
        )

proxmox = ProxmoxClient()
