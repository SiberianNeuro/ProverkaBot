import re
from contextlib import suppress

from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.orm import sessionmaker

from app.filters.common import CommonFilter
from app.models.doc import User, Ticket, TicketHistory
from app.utils.states import FSMTicket
from app.utils.validator import validate_ticket, TicketContainer
from app.keyboards.load_kb import get_validate_keyboard, SendCallback

router = Router()
router.message.filter(F.chat.type == 'private', CommonFilter())
router.callback_query.filter(F.message.chat.type == 'private', CommonFilter())


@router.message(Text(text='Отправить клиента ▶️'))
async def start_sending(msg: types.Message, state: FSMContext):
    await msg.answer('Пришли мне ссылку или ID клиента.')
    await state.set_state(FSMTicket.id)


@router.message(FSMTicket.id)
async def get_client_id(msg: types.Message, state: FSMContext, db_session: sessionmaker, user: User):
    ticket_id = re.search('\d+$', msg.text)
    if not ticket_id:
        await msg.answer('Не нашел ID клиента в сообщении. Проверь, пожалуйста, чтобы все было верно.')
    else:
        ticket_id = int(ticket_id.group(0))
        async with db_session() as session:
            ticket = await session.get(Ticket, ticket_id)
            if ticket:
                await msg.answer('Этот клиент уже был загружен на проверку.')
                return
        await state.update_data(ticket_id=ticket_id)
        ticket: TicketContainer = await validate_ticket(db_session, ticket_id, user)
        if isinstance(ticket, str):
            await msg.answer(ticket)
        else:
            await state.update_data(ticket_info=ticket)
            await msg.answer(f'Клиент: <b>{ticket["client"]["fullname"]}</b>\n'
                             f'{"https://infoclinica.legal-prod.ru/cabinet/v3/#/clients/" + ticket_id}\n'
                             f'Будет отправлен как посетивший военкомат.\n\nНажимая кнопку "Подтвердить", ты '
                             f'даешь согласие на то, что клиент полностью соответствует всем критериям. '
                             f'Ознакомиться с условиями по отправленным можно через команду <b>/help</b>',
                             reply_markup=await get_validate_keyboard())
            await state.set_state(FSMTicket.confirm)


@router.callback_query(FSMTicket.confirm, SendCallback.filter(F.param == 'validate'))
async def get_sending_confirm(call: types.CallbackQuery, state: FSMContext, db_session: sessionmaker,
                              callback_data: SendCallback):
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
                await call.message.answer('Произошла ошибка при добавлении в базу данных. Пожалуйста, попробуй снова.')
                await state.clear()
                await session.rollback()
                return
        with suppress(TelegramBadRequest):
            await call.message.edit_text(
                f'Клиент: <b>{ticket_info["client"]["fullname"]}</b>\n'
                f'{"https://infoclinica.legal-prod.ru/cabinet/v3/#/clients/" + str(ticket_info["client"]["id"])}\n'
                f'Отправлен на проверку.', reply_markup=None
            )
        await state.clear()
