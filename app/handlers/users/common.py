from aiogram import types, F

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from app.keyboards.register_kb import start_button
from app.models.user import User

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def start(msg: types.Message, user: User, state: FSMContext):
    await state.clear()
    if not user:
        await msg.answer('Пора регистрироваться!', reply_markup=await start_button())
    else:
        await msg.answer('Добро пожаловать.')
