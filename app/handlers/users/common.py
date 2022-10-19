from aiogram import types, F, Bot

from aiogram import Router
from aiogram.filters import CommandStart, Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.types import ForceReply

from app.keyboards.main_kb import keyboard_generator
from app.keyboards.register_kb import start_button
from app.models.doc import User

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def start(msg: types.Message, user: User, state: FSMContext):
    current_state = await state.get_state()
    if current_state and current_state.startswith('Checking'):
        await msg.answer('Сначала тебе нужно закончить проверку заявки.')
        return
    await state.clear()
    if not user:
        await msg.answer('Пора регистрироваться!', reply_markup=await start_button())
    else:
        await msg.answer('Добро пожаловать.', reply_markup=await keyboard_generator(user))


@router.message(Command(commands=["cancel"]))
@router.message(Text(text="отмена", ignore_case=True))
async def cmd_cancel(msg: types.Message, state: FSMContext, user: User):
    current_state = await state.get_state()
    if current_state and current_state.startswith('Checking'):
        await msg.answer('Сначала тебе нужно закончить проверку заявки.')
        return
    await state.clear()
    await msg.answer(
        text="Действие отменено.",
        reply_markup=await keyboard_generator(user)
    )
