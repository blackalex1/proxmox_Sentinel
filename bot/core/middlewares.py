import logging
from aiogram import types
from aiogram.filters import BaseFilter
from core.config import settings

class AdminFilter(BaseFilter):
    """Глобальный фильтр: пропускает только администраторов из настроек."""
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        if not event.from_user:
            return False
        user_id = event.from_user.id
        if not settings.has_admins():
            logging.warning("access_attempt_from_but_admin_ids_is_not", user_id)
            return False
        return settings.is_admin(user_id)
