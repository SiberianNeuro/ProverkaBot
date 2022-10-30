import asyncio
import re

from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.filters import CommandStart, Command, Text, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from sqlalchemy.orm import sessionmaker

from app.keyboards.main_kb import keyboard_generator
from app.keyboards.register_kb import start_button
from app.models.doc import User

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
    check_group = await bot.get_chat(config.misc.checking_group)
    if not user.is_admin and not user.is_checking:
        await msg.answer('Что я умею:\n'
                         'Нажми <b>"Отправить клиента ▶️"</b>, чтобы загрузить клиента, '
                         'подходящего под условия, для будущей проверки, а я помогу тебе в процессе загрузки.\n\n'
                         'Нажми <b>"Возможные обжалования 🛑"</b>, чтобы получить список отклоненных клиентов, '
                         'по которым можно подать обжалование.\n\n'
                         'Нажми <b>"Моя статистика 📊"</b>, чтобы получить Excel-таблицу с уже отправленными клиентами '
                         'и их текущей ситуацией по проверке.\n\n'
                         'Информацию о проверке ты можешь найти в дашборде.\n'
                         '<a href="https://datastudio.google.com/reporting/3c3ddd97-6589-4304-ad33-0cbf4e690b75">'
                         'Ссылка на него</a>.')
    if user.is_checking:
        await msg.answer(f'Для проверки клиентов тебе нужно зайти в специальную группу, куда я отправляю заявки.\n'
                         f'Ссылка на группу - {check_group.invite_link}\n\n'
                         f'Для начала проверки заявки тебе просто нужно нажать кнопку под любой из них. Помни, '
                         f'что <i>одновременно можно проверять только одну заявку!</i>\n'
                         f'Если кнопки под заявкой нет - её уже проверяет, либо проверил кто-то другой.\n'
                         f'Если в групповом чате не осталось ни одной заявки, ты можешь проверить возможные заявки '
                         f'на проверку, нажав кнопку <b>"Заявки на проверку 🏷"</b>. '
                         f'Я верну тебе 3 самые старые заявки.')

    if user.is_admin:
        await msg.answer(f'На самом деле, я очень самостоятельный, поэтому тебе остаётся только наблюдать за работой '
                         f'сотрудников с моей помощью 😏'
                         f'Вся информация по моей работе аггрегируется в дашборд. '
                         f'Вот <a href="https://datastudio.google.com/reporting/343994ec-faad-4bf1-8e2e-71ee8c398ff9">'
                         f'ссылка</a> на него.\n\n'
                         f'И на всякий случай дублирую ссылку на группу для проверки - {check_group.invite_link}')

    await msg.answer('Кроме того, можно посмотреть историю изменений по конкретному клиенту. '
                     'Для этого тебе нужно написать команду <b>"!история"</b> и через пробел ввести ID клиента.\n'
                     '<i>Например, !история 41256</i>')


@router.message(Command(commands='история', prefix='!', ignore_case=True))
async def get_ticket_history(msg: types.Message, db_session: sessionmaker, command: CommandObject):
    if not command.args:
        await msg.answer('После команды нужно ввести ID клиента.\n\n'
                         '<i>Например, !история 41000</i>')
    else:
        ticket_id = re.search('\d+$', command.args)
        if not ticket_id:
            await msg.answer('Не нашел ID клиента в команде. Проверь, пожалуйста, чтобы все было верно.')
            return
        ticket_id = int(ticket_id.group(0))
        from app.utils.statistic import get_history
        client_history = await get_history(db_session, ticket_id)
        if isinstance(client_history, str):
            await msg.answer(client_history)
            return
        history_text = []
        text_string = f'<b><a href="{client_history.client.link}">{client_history.client.fullname}</a></b>\n\n'
        for num, status in enumerate(client_history.history, 1):
            new_string = f'<b>{num}. {status.name}</b>\n' \
                         f'<i>{status.created_at.strftime("%d.%m.%Y %H:%M:%S")}</i>\n\n' \
                         f'Комментарий:\n{status.comment if status.comment else "-"}\n\n'
            if len(new_string) + len(text_string) >= 4000:
                history_text.append(text_string)
                text_string = f'<b><a href="{client_history.client.link}">{client_history.client.fullname}</a></b>\n\n'
                text_string += new_string
            else:
                text_string += new_string
        history_text.append(text_string)
        for mess in history_text:
            try:
                await msg.answer(mess)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
