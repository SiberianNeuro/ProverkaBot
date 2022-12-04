import asyncio
import datetime
import re
from contextlib import suppress

from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.orm import sessionmaker

from app.filters.common import CommonFilter
from app.keyboards.checking_kb import get_answer_keyboard
from app.models.doc import User, Ticket, TicketHistory
from app.services.config import Config
from app.utils.states import FSMTicket
from app.utils.statistic import get_user_statistic, get_rejected_clients
from app.utils.validator import validate_ticket, TicketContainer
from app.middlewares.configs import SendClientMessageMiddleware, SendClientCallbackMiddleware
from app.keyboards.load_kb import get_validate_keyboard, SendCallback, get_check_keyboard

router = Router()
router.message.filter(F.chat.type == 'private', F.content_type == "text", CommonFilter())
router.callback_query.filter(F.message.chat.type == 'private', CommonFilter())

send_client = Router()
send_client.message.filter(F.chat.type == 'private', F.content_type == "text", CommonFilter())
send_client.callback_query.filter(F.message.chat.type == 'private', CommonFilter())
send_client.message.middleware(SendClientMessageMiddleware())
send_client.callback_query.middleware(SendClientCallbackMiddleware())

router.include_router(send_client)


@router.message(Text(text='Мои клиенты 📊'))
async def get_my_metrics(msg: types.Message, db_session: sessionmaker, user: User):
    result = await get_user_statistic(db=db_session, user=user)
    if isinstance(result, str):
        await msg.answer(result)
        return
    await msg.answer_document(document=result.FSI)


@router.message(Text(text='Возможные обжалования 🛑'))
async def get_my_rejected(msg: types.Message, db_session: sessionmaker, user: User):
    clients = await get_rejected_clients(db=db_session, user=user)
    if isinstance(clients, str):
        await msg.answer(clients)
        return
    for client in clients:
        try:
            await msg.answer(f'<b><a href="https://clinica.legal-prod.ru/cabinet/v3/#/clients/{client.id}">'
                             f'{client.fullname}</a></b>:\n'
                             f'Была ли апелляция: {"да" if client.status_id == 11 else "нет"}\n\n'
                             f'<b>Комментарий проверяющиего:</b>\n'
                             f'{client.comment if client.comment else "-"}',
                             reply_markup=await get_answer_keyboard(ticket_id=client.id, new_status=client.status_id))
        except TelegramRetryAfter as e:
            logger.error(f'Floodcontrol - {e.retry_after}')
            await asyncio.sleep(e.retry_after)


@send_client.message(Text(text='Отправить клиента ▶️'))
async def start_sending(msg: types.Message, state: FSMContext):
    await msg.answer('Пришли мне ссылку или ID клиента. Если передумаешь, либо что-то будет неверно,'
                     ' напиши "отмена".')
    await state.set_state(FSMTicket.id)


@send_client.message(FSMTicket.id)
async def get_client_id(msg: types.Message, state: FSMContext, db_session: sessionmaker, user: User):
    ticket_id = re.search('\d+$', msg.text)
    if not ticket_id:
        await msg.answer('Не нашел ID клиента в сообщении. Проверь, пожалуйста, чтобы все было верно.')
        return
    ticket_id = int(ticket_id.group(0))
    async with db_session() as session:
        try:
            ticket = await session.get(Ticket, ticket_id)
        except Exception as e:
            logger.error(e)
            await msg.answer('Ошибка базы данных. Пожалуйста, попробуй снова.')
            return
        if ticket:
            await msg.answer('Этот клиент уже был загружен на проверку.')
            return
    await state.update_data(ticket_id=ticket_id)
    ticket: TicketContainer = await validate_ticket(db_session, ticket_id, user)
    if isinstance(ticket, str):
        await msg.answer(ticket)
    else:
        await state.update_data(ticket_info=ticket)
        await msg.answer(f'Клиент: <b>{ticket["ticket"]["fullname"]}</b>\n'
                         f'https://clinica.legal-prod.ru/cabinet/v3/#/clients/{ticket_id}\n'
                         f'Отправляется на проверку.\n\nНажимая кнопку "Подтвердить", ты '
                         f'даешь согласие на то, что клиент полностью соответствует всем критериям. '
                         f'Ознакомиться с критериями можно через команду <b>/help</b>',
                         reply_markup=await get_validate_keyboard())
        await state.set_state(FSMTicket.confirm)


@send_client.callback_query(FSMTicket.confirm, SendCallback.filter(F.param == 'validate'))
async def get_sending_confirm(call: types.CallbackQuery, state: FSMContext, db_session: sessionmaker,
                              callback_data: SendCallback, bot: Bot, config: Config, user: User):
    if not callback_data.value:
        with suppress(TelegramBadRequest):
            await call.message.edit_text('Валидация клиента отменена.', reply_markup=None)
    else:
        fsm_data = await state.get_data()
        ticket_info: TicketContainer = fsm_data['ticket_info']

        ticket = Ticket(**ticket_info["ticket"])

        ticket_history = TicketHistory(**ticket_info["ticket_history"])
        async with db_session() as session:
            try:
                session.add(ticket)
                session.add(ticket_history)
                await session.commit()
            except Exception as e:
                logger.error(e)
                await call.answer('Произошла ошибка при базы данных. Пожалуйста, попробуй снова.', show_alert=True)
                await session.rollback()
                return
        with suppress(TelegramBadRequest):
            await call.message.edit_text(
                f'Клиент: <b>{ticket_info["ticket"]["fullname"]}</b>\n'
                f'https://clinica.legal-prod.ru/cabinet/v3/#/clients/{ticket_info["ticket"]["id"]}\n'
                f'Отправлен на проверку.', reply_markup=None
            )
        await state.clear()

        successful = False
        while not successful:
            try:
                await bot.send_message(
                    chat_id=config.misc.checking_group,
                    text=f'🟢 <b>Новый клиент на проверку</b>:\n'
                         f'<b><a href="https://clinica.legal-prod.ru/cabinet/v3/#/clients/{ticket_info["ticket"]["id"]}">'
                         f'{ticket_info["ticket"]["fullname"]}</a></b>\n\n'
                         f'<u>Автор заявки:</u>\n{user.fullname} @{call.from_user.username}\n'
                         f'Когда отправил: <b>{datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</b>',
                    reply_markup=await get_check_keyboard(ticket_info["ticket"]["id"])
                )
                logger.opt(lazy=True).log('SEND', f'User {user.fullname} successfully sent client (ID: {ticket.id})')
                successful = True
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
