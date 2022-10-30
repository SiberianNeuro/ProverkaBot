from aiogram import Router, F, types
from aiogram.filters import Command, CommandObject

from sqlalchemy import select, and_
from sqlalchemy.orm import sessionmaker

from app.filters.common import AdminFilter

router = Router()
router.message.filter(F.chat.type == "private", AdminFilter())
router.callback_query.filter(F.message.chat.type == "private", AdminFilter())


# @router.message(Command(commands="стата", prefix="!", ignore_case=True))
# async def get_statistic(msg: types.Message, db_session: sessionmaker, command: CommandObject):
#     if command.args:
#         await msg.answer(f'{command.args} - какая-то срака.')
#     else:
#         await msg.answer(f'И где твои аргсы, пидор?')
