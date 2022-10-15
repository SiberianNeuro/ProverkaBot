from aiogram.utils.keyboard import KeyboardBuilder, KeyboardButton
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

from app.models.user import User


async def keyboard_generator(user: User) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    if not user:
        return ReplyKeyboardRemove()
    if user.is_checking is True:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Проверить')]], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Отправить')]], resize_keyboard=True)


async def cancel_button():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Отмена')]], resize_keyboard=True)
