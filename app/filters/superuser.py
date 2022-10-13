from typing import Union

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.models.user import User


class IsSuperuserFilter(BaseFilter):

    async def __call__(self, obj: Union[Message, CallbackQuery], user: User | None) -> bool:
        if user:
            return user.is_checking

        return False



