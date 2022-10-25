from aiogram import types, F

from aiogram import Router
from aiogram.filters import CommandStart, Command, Text
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from app.keyboards.main_kb import keyboard_generator
from app.keyboards.register_kb import start_button
from app.models.doc import User
from app.models.kazarma import KazarmaUser
from app.utils.statistic import get_rejected_clients

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def start(msg: types.Message, user: User, state: FSMContext, db_session):
    current_state = await state.get_state()
    if current_state and current_state.startswith('Checking'):
        await msg.answer('Сначала тебе нужно закончить проверку заявки.')
        return
    await state.clear()
    if not user:
        await msg.answer('Привет 🖖\n'
                         'Я - бот, помогающий с проверкой клиентов.\n'
                         'Вижу, что ты еще не регистрировался, давай это исправлять!',
                         reply_markup=await start_button())
    else:
        await get_rejected_clients(db_session, user)
        await msg.answer(f'Привет, {user.fullname.split()[1]} 🖖\n'
                         f'Для получения помощи напиши /help', reply_markup=await keyboard_generator(user))


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


@router.message(Command(commands=["help"]))
async def command_help(msg: types.Message, user: User):
    if not user.is_admin and not user.is_checking:
        await msg.answer('Что я умею:\n'
                         'Нажми <b>"Отправить клиента ▶️"</b>, чтобы загрузить клиента, '
                         'подходящего под условия, я помогу тебе в процессе загрузки\n'
                         'Кнопка <b>"Отклоненные клиенты 🔻"</b> вернет тебе список отклоненных клиентов\n'
                         'Кнопка <b>"Моя статистика 📊"</b> вернет тебе Excel-табличку со списком твоих клиентов '
                         'и их текущими статусами')
    if user.is_checking:
        await msg.answer('Что я умею:\n'
                         '')