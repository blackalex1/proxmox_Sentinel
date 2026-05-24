import logging
from proxmoxer import ProxmoxAPI
from core.config import (
    PROXMOX_HOST, PROXMOX_USER, PROXMOX_TOKEN_ID, 
    PROXMOX_TOKEN_SECRET, PROXMOX_VERIFY_SSL
)

class ProxmoxClient:
    def __init__(self):
        if not PROXMOX_HOST:
            logging.warning("PROXMOX_HOST не задан! Работа с Proxmox будет недоступна.")
            return
            
        if PROXMOX_TOKEN_ID and PROXMOX_TOKEN_SECRET:
            token_name = PROXMOX_TOKEN_ID.split('!')[1] if '!' in PROXMOX_TOKEN_ID else PROXMOX_TOKEN_ID
            self.proxmox = ProxmoxAPI(
                PROXMOX_HOST, 
                user=PROXMOX_USER, 
                token_name=token_name,
                token_value=PROXMOX_TOKEN_SECRET, 
                verify_ssl=PROXMOX_VERIFY_SSL
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
