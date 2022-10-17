from contextlib import suppress

from aiogram import Router, F, Bot, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy import select, func, and_

from sqlalchemy.orm import sessionmaker

from app.filters.common import CommonFilter
from app.keyboards.checking_kb import CheckingCallback
from app.keyboards.load_kb import get_check_keyboard
from app.models.doc import TicketHistory, Ticket, User
from app.services.config import Config
from app.utils.states import Appeal

router = Router()
router.message.filter(F.chat.type == 'private', CommonFilter())
router.callback_query.filter(F.message.chat.type == 'private', CommonFilter())


@router.callback_query(CheckingCallback.filter(F.param == "appeal"), F.message.chat.type == 'private')
async def start_appeal(call: types.CallbackQuery, state: FSMContext, callback_data: CheckingCallback,
                       db_session: sessionmaker):
    async with db_session() as session:
        result = await session.execute(select(func.COUNT(TicketHistory.id).where(
            and_((TicketHistory.ticket_id == callback_data.ticket_id, TicketHistory.status_id == 5)
                 ))))
        appeal_count = result.scalar().one()
        if appeal_count > 2:
            with suppress(TelegramBadRequest):
                await call.message.edit_text('Количество апелляций по этому клиенту превышено.', reply_markup=None)
                return
    with suppress(TelegramBadRequest):
        await call.message.edit_text('Пожалуйста, напиши обоснование к апелляции, и я отправлю её на проверку.',
                                     reply_markup=None)
    await state.update_data(ticket_id=callback_data.ticket_id)
    await state.set_state(Appeal.comment)


@router.message(Appeal.comment)
async def send_appeal(msg: types.Message, state: FSMContext, user: User, db_session: sessionmaker, config: Config,
                      bot: Bot):
    state_data = await state.get_data()
    ticket_id = state_data['ticket_id']
    appeal_text = msg.text
    async with db_session() as session:
        try:
            ticket = TicketHistory(
                ticket_id=ticket_id,
                sender_id=msg.from_user.id,
                status_id=5,
                comment=appeal_text
            )
            await session.add(ticket)
            await session.commit()
        except Exception as e:
            logger.error(e)
            await msg.answer('Произошла ошибка при добавлении в базу данных. Пожалуйста, попробуй снова.')
            await session.rollback()
            return

    await bot.send_message(
        chat_id=config.misc.checking_group,
        text=f'🔴 <b>Апелляция по клиенту</b>\n'
             f'{ticket.link}\n\n'
             f'Обоснование:\n{appeal_text}',
        reply_markup=await get_check_keyboard(ticket_id, user.id)
    )
