from typing import Callable, Dict, Any, Awaitable, Union

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from sqlalchemy.orm import sessionmaker

from app.services.config import Config
from app.models.doc import User


class CommonMiddleware(BaseMiddleware):

    def __init__(self, db: sessionmaker, config: Config):
        self.db = db
        self.config = config

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        async with self.db() as session:
            user: User | None = await session.get(User, (data['event_from_user'].id,))


        data['config'] = self.config
        data['db_session'] = self.db
        data['user'] = user

        return await handler(event, data)


