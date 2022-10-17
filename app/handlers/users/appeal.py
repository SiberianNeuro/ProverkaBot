from aiogram import Router, F, Bot, types
from aiogram.fsm.context import FSMContext

from sqlalchemy.orm import sessionmaker

from app.filters.common import CommonFilter
from app.keyboards.checking_kb import CheckingCallback
from app.models.doc import TicketHistory, Ticket, User
from app.utils.states import Appeal

router = Router()
router.message.filter(F.chat.type == 'private', CommonFilter())
router.callback_query.filter(F.message.chat.type == 'private', CommonFilter())


@router.callback_query(CheckingCallback.filter(F.param == "appeal"), F.message.chat.type == 'private')
async def start_appeal(call: types.CallbackQuery, state: FSMContext, callback_data: CheckingCallback):
    await call.message.answer('Пожалуйста, напиши обоснование к апелляции.')
    await state.update_data(ticket_id=callback_data.ticket_id)
    await state.set_state(Appeal.comment)


# @router.message(Appeal.comment)