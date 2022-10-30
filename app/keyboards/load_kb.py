from typing import Union, Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton


class SendCallback(CallbackData, prefix='send'):
    param: str
    value: Union[bool, int]
    user_id: Optional[int]


async def get_validate_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text='Подтвердить ✅', callback_data=SendCallback(param='validate', value=True).pack()),
        InlineKeyboardButton(text='Отменить ❌', callback_data=SendCallback(param='validate', value=False).pack())
    )
    keyboard.adjust(2)
    return keyboard.as_markup()


async def get_check_keyboard(ticket_id: Union[str, int]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text='Начать проверку', callback_data=SendCallback(param='check', value=ticket_id).pack()
    )
    return keyboard.as_markup()
