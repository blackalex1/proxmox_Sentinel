from aiogram.fsm.state import State, StatesGroup

class AddClientState(StatesGroup):
    inbound_id = State() # Сохраняем ID инбаунда невидимо
    email = State()      # Ввод email
    limit_ip = State()   # Ввод лимита IP (0 - без лимита)
    total_gb = State()   # Ввод лимита трафика в ГБ (0 - без лимита)
    expiry_days = State()# Ввод дней активации (0 - навсегда)

class EditClientState(StatesGroup):
    inbound_id = State()
    client_id = State()  # UUID или пароль клиента для редактирования
    email = State()      
    limit_ip = State()   
    total_gb = State()   
    expiry_days = State()
