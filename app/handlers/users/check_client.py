from contextlib import suppress

from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker

from app.filters.common import CheckerFilter
from app.keyboards.checking_kb import CheckingCallback, get_choice_keyboard, get_answer_keyboard
from app.keyboards.load_kb import SendCallback
from app.models.doc import Ticket, User, TicketHistory
from app.utils.states import Checking

router = Router()
router.message.filter(F.chat.type == 'private', CheckerFilter())
router.callback_query.filter(CheckerFilter())


@router.callback_query(F.message.chat.type.in_({"group", "supergroup"}), SendCallback.filter(F.param == 'check'))
async def get_group_check_start(call: types.CallbackQuery, state: FSMContext, db_session: sessionmaker,
                                callback_data: SendCallback, user: User, bot: Bot):
    await state.clear()
    current_state = await state.get_state()
    if current_state and current_state.startswith('Checking'):
        await call.answer('Сначала тебе нужно закончить проверку текущей заявки.', show_alert=True)
        return
    answer_text = ''
    async with db_session() as session:
        ticket: Ticket = await session.get(Ticket, callback_data.value)
        type_ticket = 'Апелляция' if ticket.status_id == 5 else 'Заявка'
        if ticket.status_id == 2:
            answer_text = f'{type_ticket} <a href="{ticket.link}">{ticket.id}</a> уже на проверке'
        elif ticket.status_id in (3, 4):
            answer_text = f'{type_ticket} <a href="{ticket.link}">{ticket.id}</a> проверена'
        elif ticket.status_id in (1, 5):
            answer_text = f'{type_ticket} <a href="{ticket.link}">{ticket.id}</a> принята ' \
                          f'в работу проверяющим @{call.from_user.username}'
            try:
                session.add(
                    TicketHistory(
                        ticket_id=ticket.id,
                        sender_id=call.from_user.id,
                        status_id=2
                    )
                )
                await session.merge(Ticket(id=callback_data.value, status_id=2, updated_at=func.now()))

            except Exception as e:
                logger.error(e)
                await call.answer('Произошла ошибка в базе данных.Пожалуйста, попробуй снова', show_alert=True)
                await session.rollback()
                return
            await state.update_data(author_id=callback_data.user_id)
            await bot.send_message(
                call.from_user.id,
                f'Начнем проверку клиента.\nСсылка: {ticket.link}\n'
                f'После проверки карточки выбери один из двух вариантов:'
                f' "Одобрить" или "Отклонить".',
                reply_markup=await get_choice_keyboard(ticket.id)
            )
            await state.storage.set_state(
                bot, key=StorageKey(bot_id=bot.id, chat_id=call.from_user.id, user_id=call.from_user.id),
                state=Checking.choice
            )
            logger.opt(lazy=True).log('CHECK',
                                      f'User {user.fullname} started checking client (ID: {callback_data.value})')
        with suppress(TelegramBadRequest):
            await call.message.edit_text(answer_text, reply_markup=None)


@router.callback_query(CheckingCallback.filter(F.param == "choice"), Checking.choice)
async def get_check_choice(call: types.CallbackQuery, state: FSMContext, callback_data: CheckingCallback):
    await state.update_data(ticket_id=callback_data.ticket_id, choice=callback_data.choice)
    answer_text = 'Решение принял. Пожалуйста, оставь комментарий по проверке.'
    with suppress(TelegramBadRequest):
        await call.message.edit_text(answer_text, reply_markup=None)
    await state.set_state(Checking.comment)


@router.message(Checking.comment, F.chat.type == 'private')
async def get_check_comment(msg: types.Message, state: FSMContext, db_session: sessionmaker, user: User,
                            bot: Bot):
    if msg.content_type != 'text':
        await msg.answer('Я принимаю только текстовые сообщения, без файлов, фотографий и прочего.')
        return
    ticket_info = await state.get_data()
    ticket_id, choice = ticket_info['ticket_id'], ticket_info['choice']
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
                status_id=choice
            )

            session.add(ticket)
            await session.merge(Ticket(id=int(ticket_id), status_id=choice, updated_at=func.now()))
            await session.commit()
            logger.opt(lazy=True).log('CHECK',
                                      f'User {user.fullname} '
                                      f'{"approved" if choice == 3 else "rejected"} '
                                      f'client ticket (ID: {ticket_id})')
        except Exception as e:
            logger.error(e)
            await msg.answer('Произошла ошибка в базе данных.Пожалуйста, попробуй снова')
            await session.rollback()
            return
    await msg.answer('Результаты проверки и комментарий сохранены.')
    await state.clear()
    if choice == 4:
        for u in users:
            try:
                await bot.send_message(
                    chat_id=u,
                    text=f'Клиент отклонен 😒:\n{ticket.link}\n\n'
                         f'<i>Комментарий проверяющего</i>:\n{msg.text}',
                    reply_markup=await get_answer_keyboard(ticket_id, choice)
                )
            except (TelegramUnauthorizedError, TelegramForbiddenError):
                continue
