from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton


class SendCallback(CallbackData, prefix='send'):
    param: str
    value: bool

async def get_validate_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text='Подтвердить ✅', callback_data=SendCallback(param='validate', value=True).pack()),
        InlineKeyboardButton(text='Отменить ❌', callback_data=SendCallback(param='validate', value=False).pack())
    )
    keyboard.adjust(2)
    return keyboard.as_markup()