from aiogram import Router, F, types
from aiogram.filters import Command, CommandObject

from app.filters.common import AdminFilter
from app.services.config import Config
from app.utils.change_settings import change_bot_settings

router = Router()
router.message.filter(F.chat.type == "private", AdminFilter())
router.callback_query.filter(F.message.chat.type == "private", AdminFilter())


@router.message(Command(commands="set", prefix="!", ignore_case=True))
async def get_statistic(msg: types.Message, command: CommandObject, config: Config):
    if command.args:
        response: str = await change_bot_settings(config, command.args)
        await msg.answer(response)
    else:
        await msg.answer(f'Нет аргументов команды.')
