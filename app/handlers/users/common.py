from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from app.keyboards.main_kb import keyboard_generator
from app.keyboards.register_kb import start_button
from app.models.doc import User
from app.utils.statistic import get_user_statistic

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def start(msg: types.Message, user: User, state: FSMContext, db_session, bot: Bot, config):
    await state.clear()
    await state.storage.set_state(
        bot, key=StorageKey(bot_id=bot.id, chat_id=config.misc.checking_group, user_id=msg.from_user.id),
        state=None
    )
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
        await get_user_statistic(db_session, user)
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
async def command_help(msg: types.Message, user: User, config, bot: Bot):
    if not user.is_admin and not user.is_checking:
        await msg.answer('Что я умею:\n'
                         'Нажми <b>"Отправить клиента ▶️"</b>, чтобы загрузить клиента, '
                         'подходящего под условия, для будущей проверки, а я помогу тебе в процессе загрузки.\n\n'
                         'Нажми <b>"Возможные обжалования 🛑"</b>, чтобы получить список отклоненных клиентов, '
                         'по которым можно подать обжалование.\n\n'
                         'Нажми <b>"Моя статистика 📊"</b>, чтобы получить Excel-таблицу с уже отправленными клиентами '
                         'и их текущей ситуацией по проверке.')
    if user.is_checking:
        check_group = await bot.get_chat(config.misc.checking_group)
        await msg.answer(f'Для проверки клиентов тебе нужно зайти в специальную группу, куда я отправляю заявки.\n'
                         f'Ссылка на группу - {check_group.invite_link}\n\n'
                         f'Для начала проверки заявки тебе просто нужно нажать кнопку под любой из них. Помни, '
                         f'что <i>одновременно можно проверять только одну заявку!</i>\n'
                         f'Если кнопки под заявкой нет - её уже проверяет, либо проверил кто-то другой.')

    if user.is_admin:
        await msg.answer(f'Я регулярно обновляю дашборд, в котором визуализированы все необходимые данные.\n'
                         f'Ссылка на него здесь.\n')