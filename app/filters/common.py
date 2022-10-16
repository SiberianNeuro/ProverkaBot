from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.models.doc import User


class AdminFilter(BaseFilter):
    is_admin: bool = True

    async def __call__(self, obj: TelegramObject, user: User) -> bool:
        if user:
            return user.is_admin == self.is_admin

        return False


class CheckerFilter(BaseFilter):
    is_checking: bool = True

    async def __call__(self, obj: TelegramObject, user: User) -> bool:
        if user:
            return user.is_checking == self.is_checking

        return False


class CommonFilter(BaseFilter):
    is_common: bool = True

    async def __call__(self, obj: TelegramObject, user: User) -> bool:
        if user:
            return not user.is_checking and not user.is_admin

        return False
