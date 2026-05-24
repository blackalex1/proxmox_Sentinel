from aiogram import Bot, Dispatcher
from core.config import BOT_TOKEN
import logging

if not BOT_TOKEN:
    raise ValueError("Пожалуйста, укажите валидный BOT_TOKEN в файле .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
