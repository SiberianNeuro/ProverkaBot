from contextlib import suppress
from datetime import datetime

from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError, TelegramForbiddenError
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import ForceReply
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker

from app.filters.common import CheckerFilter
from app.keyboards.checking_kb import CheckingCallback, get_choice_keyboard, get_answer_keyboard
from app.keyboards.load_kb import SendCallback, get_check_keyboard
from app.models.doc import Ticket, User, TicketHistory
from app.utils.states import Checking
from app.utils.statistic import get_for_checking_pool

router = Router()
router.message.filter(F.chat.type == 'private', CheckerFilter())
router.callback_query.filter(CheckerFilter())

template = {
    1: {'check_status': 2, 'type': 'Заявка', 'approved': 3, 'rejected': 4},
    5: {'check_status': 7, 'type': 'Апелляция', 'approved': 9, 'rejected': 11},
    6: {'check_status': 8, 'type': 'Кассация', 'approved': 10, 'rejected': 12},
}


@router.message(Text(text='Заявки на проверку 🏷'))
async def get_checking_pool(msg: types.Message, db_session: sessionmaker):
    db_answer = await get_for_checking_pool(db_session)
    if isinstance(db_answer, str):
        await msg.answer(db_answer)
        return

    for ticket in db_answer:
        text = f'<b>{template[ticket.status_id]["type"]}</b>\n\n' \
               f'<b><a href="{ticket.link}">{ticket.fullname}</a></b>\n' \
               f'Дата подачи: <b>{ticket.updated}</b>\n' \
               f'Комментарий:\n{ticket.comment if ticket.comment else "-"}'
        await msg.answer(text=text, reply_markup=await get_check_keyboard(ticket.id))


@router.callback_query(SendCallback.filter(F.param == 'check'))
async def get_group_check_start(call: types.CallbackQuery, state: FSMContext, db_session: sessionmaker,
                                callback_data: SendCallback, user: User, bot: Bot, config):
    group_state = await state.storage.get_state(
        bot,
        key=StorageKey(bot_id=bot.id, chat_id=config.misc.checking_group, user_id=call.from_user.id)
    )
    current_state = await state.get_state()
    if current_state and current_state.startswith('Checking') \
            and group_state and group_state.startswith('Checking'):
        await call.answer('Сначала тебе нужно закончить проверку текущей заявки.', show_alert=True)
        return

    answer_text = ''
    flag = False
    async with db_session() as session:
        ticket: Ticket = await session.get(Ticket, callback_data.value)
        raw_status = ticket.status_id
        if raw_status in (2, 7, 8):
            answer_text = f'❕ <u>Уже на проверке.</u>'
        elif raw_status in (3, 4):
            answer_text = f'❕ <u>Проверка уже завершена:</u> {"одобрен" if raw_status == 3 else "отклонен"}.'
        elif raw_status in (1, 5, 6):
            flag = True
            if call.message.chat.type in ("group", "supergroup"):
                answer_text = f'🔄 <i>Принят в работу проверяющим:</i>\n' \
                              f'{user.fullname} @{call.from_user.username}\n' \
                              f'Начало проверки: <b>{datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</b>'
            else:
                answer_text = f'Начало проверки: <b>{datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</b>'

        if not flag:
            with suppress(TelegramBadRequest):
                await call.message.edit_text(call.message.html_text + '\n\n' + answer_text, reply_markup=None)

                return
        try:
            session.add(
                TicketHistory(
                    ticket_id=ticket.id,
                    sender_id=call.from_user.id,
                    status_id=template[raw_status]["check_status"]
                )
            )
            await session.merge(Ticket(
                id=callback_data.value,
                status_id=template[raw_status]["check_status"],
                updated_at=datetime.now()
            ))
            await session.commit()
        except Exception as e:
            logger.error(e)
            await call.answer('Произошла ошибка в базе данных.Пожалуйста, попробуй снова', show_alert=True)
            await session.rollback()
            return

        with suppress(TelegramBadRequest):
            await call.message.edit_text(call.message.html_text + '\n\n' + answer_text, reply_markup=None)
        await bot.send_message(
            call.from_user.id,
            f'Начнем проверку клиента.\nСсылка: {ticket.link}\n'
            f'После проверки карточки выбери один из двух вариантов:'
            f' "Одобрить" или "Отклонить".',
            reply_markup=await get_choice_keyboard(ticket.id)
        )
        await state.set_state(Checking.choice)
        await state.storage.set_state(
            bot, key=StorageKey(bot_id=bot.id, chat_id=call.from_user.id, user_id=call.from_user.id),
            state=Checking.choice
        )
        await state.storage.update_data(bot,
                                        StorageKey(bot_id=bot.id, chat_id=call.from_user.id,
                                                   user_id=call.from_user.id),
                                        data={'ticket_type': template[raw_status]}
                                        )
        await state.update_data(ticket_type=template[raw_status])
        logger.opt(lazy=True).log('CHECK',
                                  f'User {user.fullname} started checking client (ID: {callback_data.value})')


@router.callback_query(CheckingCallback.filter(F.param == "choice"), Checking.choice)
async def get_check_choice(call: types.CallbackQuery, state: FSMContext, callback_data: CheckingCallback):
    await state.update_data(ticket_id=callback_data.ticket_id, choice=callback_data.choice)
    answer_text = 'Решение принял. Пожалуйста, оставь комментарий по проверке.'
    await call.message.delete()
    await call.message.answer(answer_text,
                              reply_markup=ForceReply(input_field_placeholder='Твой комментарий по проверке'))
    await state.set_state(Checking.comment)


@router.message(Checking.comment, F.chat.type == 'private')
async def get_check_comment(msg: types.Message, state: FSMContext, db_session: sessionmaker, user: User,
                            bot: Bot, config):
    if msg.content_type != 'text':
        await msg.answer('Я принимаю только текстовые сообщения, без файлов, фотографий и прочего.')
        return

    ticket_info = await state.get_data()
    ticket_id, choice, ticket_type_dict = ticket_info['ticket_id'], ticket_info['choice'], ticket_info['ticket_type']
    ticket_type = ticket_type_dict['type']
    new_status_id = ticket_type_dict['approved'] if choice else ticket_type_dict['rejected']

    async with db_session() as session:
        try:
            current_ticket: Ticket = await session.get(Ticket, int(ticket_id))
            result = await session.execute(select(User.id).filter(
                User.kazarma_id.in_((current_ticket.doc_id, current_ticket.law_id))
            ))
            users = result.scalars().all()
            ticket = TicketHistory(
                ticket_id=int(ticket_id),
                sender_id=msg.from_user.id,
                comment=msg.text,
                status_id=new_status_id
            )

            session.add(ticket)
            await session.merge(
                Ticket(id=int(ticket_id), status_id=new_status_id, comment=msg.text, updated_at=datetime.now()))
            logger.opt(lazy=True).log('CHECK',
                                      f'User {user.fullname} '
                                      f'{"approved" if choice == 3 else "rejected"} '
                                      f'client ticket (ID: {ticket_id})')
        except Exception as e:
            logger.error(e)
            await msg.answer('Произошла ошибка в базе данных. Пожалуйста, попробуй снова.')
            await session.rollback()
            return
    await msg.answer('Результаты проверки и комментарий сохранены.')
    await state.clear()
    await state.storage.set_state(
        bot, key=StorageKey(bot_id=bot.id, chat_id=config.misc.checking_group, user_id=msg.from_user.id),
        state=None
    )
    await state.storage.set_data(bot,
                                 StorageKey(bot_id=bot.id, chat_id=config.misc.checking_group,
                                            user_id=msg.from_user.id),
                                 data={}
                                 )
    if not choice:
        for usr in users:
            try:
                await bot.send_message(
                    chat_id=usr,
                    text=f'❌ <b>{ticket_type} отклонена</b>\n\n'
                         f'Клиент: {current_ticket.fullname}\n'
                         f'{ticket.link}\n\n'
                         f'Дата создания: <b>{current_ticket.updated}</b>\n'
                         f'{ticket_type} рассмотрена: <b>{datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</b>\n\n'
                         f'<i>Комментарий проверяющего</i>:\n{msg.text}',
                    reply_markup=await get_answer_keyboard(ticket_id, new_status_id)
                )
            except (TelegramUnauthorizedError, TelegramForbiddenError):
                continue
