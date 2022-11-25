from typing import Union, TypedDict
import datetime as dt

from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.orm import sessionmaker

from app.models.kazarma import KazarmaClient, KazarmaClientUser, KazarmaUser, TempClientUser
from app.models.doc import User, Ticket


class TicketInstance(TypedDict):
    id: int
    fullname: str
    doc_id: int
    law_id: int


class TicketHistoryInstance(TypedDict):
    ticket_id: int
    sender_id: int
    status_id: int


class TicketContainer(TypedDict):
    ticket: TicketInstance
    ticket_history: TicketHistoryInstance


async def validate_ticket(
        db_session: sessionmaker,
        ticket_id: Union[str, int],
        user: User
) -> Union[TicketContainer, str]:
    async with db_session() as session:
        temp_client: KazarmaClient = await session.get(KazarmaClient, ticket_id)
        if not temp_client:
            return "Клиент не найден в базе данных. Пожалуйста, проверь правильность ссылки или ID."
        # if temp_client.is_send == 0:
        #     return 'Метка "Отправлен в военкомат" не проставлена. Пожалуйста, поставь метку, потом отправь мне ' \
        #            'ссылку заново.'

        get_main_users = select(
            KazarmaClientUser.user_id,
            KazarmaUser.role_id
        ).join(KazarmaUser).where(and_(KazarmaClientUser.active == 1, KazarmaClientUser.client_id == ticket_id))

        get_transaction_process = select(
            TempClientUser.user_id,
            KazarmaUser.role_id
        ).join(KazarmaUser,  KazarmaUser.id == TempClientUser.user_id).where(TempClientUser.client_id == ticket_id)

        get_temp_users = select(
            TempClientUser.temp_user_id,
            KazarmaUser.role_id
        ).join(KazarmaUser,  KazarmaUser.id == TempClientUser.temp_user_id).where(TempClientUser.client_id == ticket_id)

        ticket_data = await session.execute(get_main_users)
        temp_ticket_data = await session.execute(get_transaction_process)
        temp_transaction = await session.execute(get_temp_users)
        main_users = ticket_data.mappings().all()
        temp_user_transaction_data = temp_ticket_data.mappings().all()
        temp_transaction_data = temp_transaction.mappings().all()

    user_in_main_list = tuple(filter(lambda x: x.user_id == user.kazarma_id, main_users))
    user_in_transaction_list = tuple(filter(lambda x: x.user_id == user.kazarma_id, temp_user_transaction_data))
    user_is_temp = tuple(filter(lambda x: x.temp_user_id == user.kazarma_id, temp_transaction_data))
    if not user_in_transaction_list and not user_in_main_list and not user_is_temp:
        return "Данный клиент не закреплен за тобой."

    law_id = None
    doc_id = None

    if user.role_id in (3, 8):
        if user_is_temp:
            main_user = tuple(filter(lambda x: x.role_id in (3, 8), temp_user_transaction_data))
            doc_id = main_user[0]['user_id']
        else:
            doc_id = user_in_main_list[0]['user_id']

        law_list = tuple(filter(lambda x: x.role_id in (2, 31), temp_user_transaction_data))
        if not law_list:
            law_list = tuple(filter(lambda x: x.role_id in (2, 31), main_users))
        law_id = law_list[0]['user_id']

    elif user.role_id in (2, 31):
        if user_is_temp:
            main_user = tuple(filter(lambda x: x.role_id in (2, 31), temp_user_transaction_data))
            law_id = main_user[0]['user_id']
        else:
            law_id = user_in_main_list[0]['user_id']

        doc_list = tuple(filter(lambda x: x.role_id in (3, 8), temp_user_transaction_data))
        if not doc_list:
            doc_list = tuple(filter(lambda x: x.role_id in (3, 8), main_users))
        doc_id = doc_list[0]['user_id']
    # law_id = None
    # doc_id = None
    #
    # for employee in main_users:
    #     if employee.role_id in (2, 31):
    #         law_id = employee.user_id
    #     elif employee.role_id in (3, 8):
    #         doc_id = employee.user_id

    ticket = TicketInstance(
        id=temp_client.id,
        fullname=temp_client.fullname,
        doc_id=doc_id,
        law_id=law_id,
    )
    history_instance = TicketHistoryInstance(
        ticket_id=temp_client.id,
        sender_id=user.id,
        status_id=1
    )

    return TicketContainer(ticket=ticket, ticket_history=history_instance)


async def validate_appeal(db: sessionmaker, ticket_id: int) -> Union[Ticket, str]:
    async with db() as session:
        try:
            ticket = await session.get(Ticket, int(ticket_id))
        except Exception as e:
            logger.error(e)
            session.rollback()
            return "Ошибка в базе данных. Пожалуйста, попробуй снова."
    if ticket.status_id in (2, 5, 6, 7, 8):
        return f"⚠ Прямо сейчас по клиенту идет проверка.\n" \
               f"Время начала проверки: <b>{ticket.updated}</b>"
    if ticket.status_id == 12:
        return f'❗ По этому клиенту уже были отклонены и апелляция, и кассация.\n' \
               f'Дата проверки: <b>{ticket.updated}</b>\n\n' \
               f'Комментарий по проверке:\n{ticket.comment}'
    return ticket
