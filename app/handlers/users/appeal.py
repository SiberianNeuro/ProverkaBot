import asyncio
from contextlib import suppress
from datetime import datetime
from typing import Union

from aiogram import Router, F, Bot, types
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import ForceReply
from loguru import logger
from sqlalchemy import select, func, and_

from sqlalchemy.orm import sessionmaker

from app.filters.common import CommonFilter
from app.keyboards.checking_kb import CheckingCallback
from app.keyboards.load_kb import get_check_keyboard
from app.keyboards.main_kb import keyboard_generator
from app.models.doc import TicketHistory, Ticket, User
from app.services.config import Config
from app.utils.states import Appeal
from app.utils.validator import validate_appeal

router = Router()
router.message.filter(F.chat.type == 'private', CommonFilter())
router.callback_query.filter(F.message.chat.type == 'private', CommonFilter())


@router.callback_query(CheckingCallback.filter(F.param == "appeal"), F.message.chat.type == 'private')
async def start_appeal(call: types.CallbackQuery, state: FSMContext, callback_data: CheckingCallback,
                       db_session: sessionmaker):
    appeal: Union[Ticket, str] = await validate_appeal(db_session, callback_data.ticket_id)
    if isinstance(appeal, str):
        with suppress(TelegramBadRequest):
            await call.message.edit_text(call.message.html_text + '\n\n' + appeal, reply_markup=None)
        return
    await call.message.delete()
    await call.message.answer(f'{"Апелляция" if appeal.status_id == 4 else "Кассация"} по клиенту:\n'
                              f'<a href="{appeal.link}">{appeal.fullname}</a>\n\n'
                              f'Пожалуйста, напиши обоснование к апелляции (не более 4000 символов).',
                              reply_markup=ForceReply(input_field_placeholder='Текст апелляции'))
    await state.update_data(
        ticket_id=callback_data.ticket_id,
        new_status=5 if appeal.status_id == 4 else 6
    )
    await state.set_state(Appeal.comment)


@router.message(Appeal.comment)
async def send_appeal(msg: types.Message, state: FSMContext, user: User, db_session: sessionmaker, config: Config,
                      bot: Bot):
    if msg.content_type != 'text':
        await msg.answer('Я принимаю только текстовые сообщения, без файлов, фотографий и прочего.')
        return
    state_data = await state.get_data()
    ticket_id, new_status_id = list(map(int, state_data.values()))

    appeal_text = msg.text
    async with db_session() as session:
        try:
            ticket = await session.get(Ticket, ticket_id)
            if ticket.status_id in (5, 6):
                await msg.answer("Во время составления твоей апелляции твой коллега по клиенту уже успел её подать.")
                return
            session.add(TicketHistory(
                ticket_id=ticket_id,
                sender_id=msg.from_user.id,
                status_id=new_status_id,
                comment=appeal_text
            ))
            ticket.status_id = new_status_id
            ticket.comment = appeal_text
            ticket.updated_at = func.now()

            await session.commit()
        except Exception as e:
            logger.error(e)
            await msg.answer('Произошла ошибка при добавлении в базу данных. Пожалуйста, попробуй снова.')
            await session.rollback()
            return
    await msg.answer(f'Обжалование по клиенту:\n<b><a href="{ticket.link}">{ticket.fullname}</a></b>\n\n'
                     f'Отправлено на проверку', reply_markup=await keyboard_generator(user))
    successful = False
    await state.clear()
    appeal_type = "🟡 Апелляция" if new_status_id == 5 else "🔴 Кассация"
    while not successful:
        try:
            await bot.send_message(
                chat_id=config.misc.checking_group,
                text=f' <b>{appeal_type} по клиенту</b>:\n'
                     f'<b><a href="{ticket.link}">{ticket.fullname}</a></b>\n\n'
                     f'<u>Автор:</u>\n{user.fullname} @{msg.from_user.username}\n'
                     f'Поступление: <b>{datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</b>\n\n'
                     f'<i>Обоснование:</i>\n{appeal_text}',
                reply_markup=await get_check_keyboard(ticket_id)
            )
            logger.opt(lazy=True).log('APPEAL', f'User {user.fullname} sent appeal for client (type: {appeal_type} |'
                                                f'ID: {ticket.id})')
            successful = True
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)



