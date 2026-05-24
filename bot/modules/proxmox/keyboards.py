from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.proxmox.api import proxmox

def get_node_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура: список нод"""
    nodes = proxmox.get_nodes()
    buttons = []
    for node in nodes:
        status = "🟢" if node['status'] == "online" else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {node['node']}", 
            callback_data=f"node_{node['node']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_vms_keyboard(node_name: str) -> InlineKeyboardMarkup:
    """Клавиатура: список ВМ на выбранной ноде"""
    vms = proxmox.get_vms(node_name)
    buttons = []
    
    # Сначала добавим сам Хост Proxmox VE
    buttons.append([InlineKeyboardButton(
        text="💻 [Хост] Proxmox VE", 
        callback_data=f"vm_{node_name}_0_host"
    )])
    
    for vm in sorted(vms, key=lambda x: x.get('vmid', 0)):
        status = "🟢" if vm.get('status') == "running" else "🔴"
        vmid = vm.get('vmid')
        name = vm.get('name', 'Unknown')
        vm_type = 'lxc' if vm.get('type') == 'lxc' else 'qemu'
        
        buttons.append([InlineKeyboardButton(
            text=f"{status} {vmid}: {name}", 
            callback_data=f"vm_{node_name}_{vmid}_{vm_type}"
        )])
        
    buttons.append([InlineKeyboardButton(text="🔙 Назад к серверам", callback_data="back_to_nodes")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_vm_control_keyboard(node_name: str, vmid: str, vm_type: str, is_running: bool) -> InlineKeyboardMarkup:
    """Клавиатура: Управление конкретной ВМ"""
    buttons = []
    
    if vm_type == 'host' or str(vmid) == '0':
        buttons.append([
            InlineKeyboardButton(text="🔒 Логи входа Хоста", callback_data=f"lxc_auth_{node_name}_{vmid}"),
            InlineKeyboardButton(text="🌐 Трафик Хоста", callback_data=f"lxc_ports_{node_name}_{vmid}")
        ])
        buttons.append([InlineKeyboardButton(text="🔄 Обновить статус", callback_data=f"vm_{node_name}_{vmid}_host")])
        buttons.append([InlineKeyboardButton(text="🔙 Назад к списку ВМ", callback_data=f"node_{node_name}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
        
    if is_running:
        buttons.append([
            InlineKeyboardButton(text="🔌 Мягко выключить", callback_data=f"cmd_shutdown_{node_name}_{vmid}_{vm_type}"),
            InlineKeyboardButton(text="🛑 Убить (Stop)", callback_data=f"cmd_stop_{node_name}_{vmid}_{vm_type}")
        ])
        buttons.append([InlineKeyboardButton(text="🔄 Перезагрузить", callback_data=f"cmd_reboot_{node_name}_{vmid}_{vm_type}")])
    else:
        buttons.append([InlineKeyboardButton(text="▶️ Запустить", callback_data=f"cmd_start_{node_name}_{vmid}_{vm_type}")])
        
    if vm_type == 'lxc' and is_running:
        buttons.append([
            InlineKeyboardButton(text="🔒 Логи входа", callback_data=f"lxc_auth_{node_name}_{vmid}"),
            InlineKeyboardButton(text="🌐 Трафик портов", callback_data=f"lxc_ports_{node_name}_{vmid}")
        ])

    buttons.append([InlineKeyboardButton(text="🔄 Обновить статус", callback_data=f"vm_{node_name}_{vmid}_{vm_type}")])
    buttons.append([InlineKeyboardButton(text="👯 Клонировать", callback_data=f"cmd_clone_{node_name}_{vmid}_{vm_type}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад к списку ВМ", callback_data=f"node_{node_name}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

