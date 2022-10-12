from typing import Callable, Dict, Any, Awaitable, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from sqlalchemy.orm import sessionmaker

from app.services.config import Config
from app.models.user import User


class CommonMiddleware(BaseMiddleware):

    def __init__(self, db: sessionmaker, config: Config):
        self.db = db
        self.config = config

    async def __call__(
            self,
            handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
            event: Union[Message, CallbackQuery],
            data: Dict[str, Any]
    ) -> Any:
        async with self.db.begin() as ses:
            user = await ses.get(User, event.from_user.id)
