from contextlib import suppress
from datetime import datetime

from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import ForceReply
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
    async with db_session() as session:
        ticket: Ticket = await session.get(Ticket, callback_data.value)
        type_ticket = 'Апелляция' if ticket.status_id == 5 else 'Заявка'
        if ticket.status_id == 2:
            answer_text = f'❕ <u>уже на проверке.</u>'
        elif ticket.status_id in (3, 4):
            answer_text = f'❕ <u>уже проверена:</u> {"одобрена" if ticket.status_id == 3 else "отклонена"}.'
        elif ticket.status_id in (1, 5):
            answer_text = f'🔄 <i>Принята в работу проверяющим</i> @{call.from_user.username}\n' \
                          f'Начало проверки: <b>{datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</b>'
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
            await session.merge(Ticket(id=int(ticket_id), status_id=choice, comment=msg.text, updated_at=func.now()))
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
    await state.storage.set_state(
        bot, key=StorageKey(bot_id=bot.id, chat_id=config.misc.checking_group, user_id=msg.from_user.id),
        state=None
    )
    await state.storage.set_data(bot,
                                 StorageKey(bot_id=bot.id, chat_id=config.misc.checking_group,
                                            user_id=msg.from_user.id),
                                 data={}
                                 )
    if choice == 4:
        for u in users:
            try:
                await bot.send_message(
                    chat_id=u,
                    text=f'Клиент отклонен 😒:\n{ticket.link}\n\n'
                         f'<i>Комментарий проверяющего</i>:\n{msg.text}',
                    reply_markup=await get_answer_keyboard(ticket_id)
                )
            except (TelegramUnauthorizedError, TelegramForbiddenError):
                continue
