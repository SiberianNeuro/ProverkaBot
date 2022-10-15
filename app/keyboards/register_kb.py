from typing import Optional, Any, Union

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.user import Cluster


class RegCallback(CallbackData, prefix='register'):
    param: Optional[str]
    value: Optional[int]


async def start_button():
    button = InlineKeyboardBuilder()
    button.button(text='Зарегистрироваться', callback_data=RegCallback(param='register'))
    return button.as_markup()


async def get_clusters_keyboard(db: sessionmaker):
    async with db.begin() as session:
        query = await session.execute(select(Cluster).where(Cluster.id != 18))
        clusters = query.scalars().all()
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        *[
            InlineKeyboardButton(
                text=cluster.name, callback_data=RegCallback(param='cluster', value=cluster.id).pack()
            ) for cluster in clusters[:11]
        ]
    )
    keyboard.adjust(4)
    keyboard.row(
        *[
            InlineKeyboardButton(
                text=cluster.name, callback_data=RegCallback(param='cluster', value=cluster.id).pack()
            ) for cluster in clusters[11:14]
        ]
    )
    keyboard.row(
        *[
            InlineKeyboardButton(
                text=cluster.name, callback_data=RegCallback(param='cluster', value=cluster.id).pack()
            ) for cluster in clusters[14:]
        ]
    )
    return keyboard.as_markup()


async def get_confirm(users: Union[list, Any]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if isinstance(users, list):
        for num, user in enumerate(users, 1):
            builder.button(text=num, callback_data=RegCallback(param='confirm', value=user['id']).pack())
    else:
        builder.button(text='Да, это я', callback_data=RegCallback(param='confirm', value=users['id']).pack())
        builder.button(text='Нет, это не я', callback_data=RegCallback(param='confirm', value=0).pack())
    return builder.as_markup()
