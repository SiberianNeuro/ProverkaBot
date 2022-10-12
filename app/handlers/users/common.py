from aiogram import types

from aiogram import Router
from aiogram.filters import CommandStart

from app.models.user import User

router = Router()


@router.message(CommandStart(), state="*")
async def start(msg: types.Message, user: User):
    pass
