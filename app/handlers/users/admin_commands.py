from aiogram import Router, F, types
from aiogram.filters import Command, CommandObject
from loguru import logger

from sqlalchemy import update, func
from sqlalchemy.orm import sessionmaker

from app.filters.common import AdminFilter
from app.models.doc import Ticket, User
from app.services.config import Config
from app.utils.change_settings import change_bot_settings

router = Router()
router.message.filter(F.chat.type == "private", AdminFilter())
router.callback_query.filter(F.message.chat.type == "private", AdminFilter())


@router.message(Command(commands="set", prefix="!", ignore_case=True))
async def set_bot_settings(msg: types.Message, command: CommandObject, config: Config):
    if command.args:
        response: str = await change_bot_settings(config, command.args)
        await msg.answer(response)
    else:
        await msg.answer(f'Нет аргументов команды.')


@router.message(Command(commands="complete_current_counter", prefix="!", ignore_case=True))
async def complete_current_counter(msg: types.Message, db_session: sessionmaker, user: User):
    stmt = update(Ticket).values(status_id=13, comment=None, updated_at=func.now())
    async with db_session() as session:
        try:
            await session.execute(stmt)
            await session.commit()
            logger.info(f'{user.fullname} complete current counter.')
        except Exception as e:
            logger.error(e)
            await session.rollback()
    await msg.answer('Статусы и комментарии текущих заявок очищены и готовы к новому заполнению.')
