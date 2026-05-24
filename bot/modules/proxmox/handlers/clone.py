from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from modules.proxmox.api import proxmox

router = Router(name="proxmox_clone_router")

class ProxmoxCloneState(StatesGroup):
    waiting_for_new_id = State()
    waiting_for_new_name = State()

@router.callback_query(F.data.startswith("cmd_clone_"))
async def start_proxmox_clone(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    node_name = parts[2]
    vmid = parts[3]
    vm_type = parts[4]
    
    await state.update_data(
        node_name=node_name,
        src_vmid=vmid,
        vm_type=vm_type,
        is_lxc=(vm_type == 'lxc')
    )
    
    await state.set_state(ProxmoxCloneState.waiting_for_new_id)
    await callback.message.answer(
        f"📝 <b>Клонирование {vm_type.upper()} {vmid} ({node_name})</b>\n\n"
        f"Введите <b>ID</b> для новой машины (например, 105):",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ProxmoxCloneState.waiting_for_new_id)
async def process_clone_id(message: types.Message, state: FSMContext):
    new_id = message.text.strip()
    if not new_id.isdigit():
        await message.answer("❌ ID должен быть числом! Попробуйте еще раз:")
        return
        
    await state.update_data(new_id=new_id)
    await state.set_state(ProxmoxCloneState.waiting_for_new_name)
    await message.answer("Введите <b>имя</b> для новой машины (например, my-new-server):", parse_mode="HTML")

@router.message(ProxmoxCloneState.waiting_for_new_name)
async def process_clone_name(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    await state.clear()
    
    node_name = data['node_name']
    src_vmid = data['src_vmid']
    new_id = data['new_id']
    is_lxc = data['is_lxc']
    
    status_msg = await message.answer("⏳ Начинаю клонирование...")
    try:
        proxmox.clone_vm(node_name, src_vmid, new_id, new_name, is_lxc)
        await status_msg.edit_text(f"✅ Клонирование успешно запущено!\nНовая машина ID: {new_id}, Имя: {new_name}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка клонирования: {str(e)[:3500]}")
