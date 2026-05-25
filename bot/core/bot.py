from aiogram import Bot, Dispatcher
from core.config import settings
import logging

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
