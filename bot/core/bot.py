from aiogram import Bot, Dispatcher
from core.config import settings
import logging
from core.outbox import outbox

bot = Bot(token=settings.bot_token)
# Пропатчиваем бота исходящей очередью для отказоустойчивости сообщений
outbox.patch_bot(bot)

dp = Dispatcher()
