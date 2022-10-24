from typing import Union

from aiogram.utils.keyboard import KeyboardBuilder, KeyboardButton
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

from app.models.doc import User


async def keyboard_generator(user: User) -> Union[ReplyKeyboardMarkup, ReplyKeyboardRemove]:

    if not user:
        return ReplyKeyboardRemove()
    elif user.is_checking:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Проверить')]], resize_keyboard=True)
    elif user.is_admin:
        return ReplyKeyboardRemove()
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text='Отправить клиента ▶️'),
                    KeyboardButton(text='Мои клиенты 📊'),
                    #KeyboardButton(text='Отклоненные клиенты 🛑')
                ]
            ],
            resize_keyboard=True
        )


async def cancel_button():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Отмена')]], resize_keyboard=True)
