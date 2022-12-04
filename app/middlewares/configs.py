from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class SendClientMessageMiddleware(BaseMiddleware):

    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]], event: Message,
                       data: Dict[str, Any]) -> Any:

        config = data['config']

        if config.misc.send_client:
            return await handler(event, data)

        await event.answer('Отправка новых клиентов отключена. Чтобы вернуться в главное меню, напиши /start.')
        return


class SendClientCallbackMiddleware(BaseMiddleware):

    async def __call__(self, handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]], event: CallbackQuery,
                       data: Dict[str, Any]) -> Any:

        config = data['config']

        if config.misc.send_client:
            return await handler(event, data)

        await event.answer('Отправка новых клиентов отключена. Чтобы вернуться в главное меню, напиши /start.',
                           show_alert=True)

        return


class SendAppealCallbackMiddleware(BaseMiddleware):

    async def __call__(self, handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]], event: CallbackQuery,
                       data: Dict[str, Any]) -> Any:

        config = data['config']

        if config.misc.send_appeal:
            return await handler(event, data)

        await event.answer('Отправка обжалований отключена. Чтобы вернуться в главное меню, напиши /start.',
                           show_alert=True)
        return


class SendAppealMessageMiddleware(BaseMiddleware):

    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]], event: Message,
                       data: Dict[str, Any]) -> Any:

        config = data['config']

        if config.misc.send_appeal:
            return await handler(event, data)

        await event.answer('Отправка обжалований отключена. Чтобы вернуться в главное меню, напиши /start.')
