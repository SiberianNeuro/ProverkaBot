from typing import Union, Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class CheckingCallback(CallbackData, prefix='checking'):
    param: str
    ticket_id: Optional[Union[str, int]]
    choice: Optional[Union[bool, int]]


async def get_choice_keyboard(ticket_id: Union[str, int]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text='Одобрить 👍', callback_data=CheckingCallback(param='choice', ticket_id=ticket_id, choice=3).pack()
    )
    keyboard.button(
        text='Отклонить 👎', callback_data=CheckingCallback(param='choice', ticket_id=ticket_id, choice=4).pack()
    )
    return keyboard.as_markup()


async def get_answer_keyboard(ticket_id: Union[str, int]) -> Union[InlineKeyboardMarkup, None]:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text='Подать апелляцию', callback_data=CheckingCallback(param='appeal', ticket_id=ticket_id).pack()
    )

    return keyboard.as_markup()

