from typing import Union, TypedDict, NamedTuple, Iterable, Any

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
    status_id: int
    comment: str | None


class TicketHistoryInstance(TypedDict):
    ticket_id: int
    sender_id: int
    status_id: int


class TicketContainer(TypedDict):
    ticket: TicketInstance
    ticket_history: TicketHistoryInstance


class TicketEmployeesContainer(NamedTuple):
    doc_id: Union[int, None]
    law_id: Union[int, None]


class RawTicketDataContainer(NamedTuple):
    ticket: Ticket
    ticket_kazarma: KazarmaClient
    main_users: TicketEmployeesContainer
    transfer: TicketEmployeesContainer


async def _get_ticket_raw_data(db_session: sessionmaker, ticket_id: int) -> RawTicketDataContainer | str:
    get_main_users = select(
        KazarmaClientUser.user_id,
        KazarmaUser.role_id
    ).join(KazarmaUser).where(and_(KazarmaClientUser.active == 1, KazarmaClientUser.client_id == ticket_id))

    get_transaction_process = select(
        TempClientUser.user_id,
        KazarmaUser.role_id
    ).join(KazarmaUser, KazarmaUser.id == TempClientUser.user_id).where(TempClientUser.client_id == ticket_id)

    ticket_kazarma_data = None

    async with db_session() as session:
        try:
            ticket_db_data: Ticket = await session.get(Ticket, ticket_id)
        except Exception as e:
            logger.error(e)
            return "Произошла ошибка базы данных. Пожалуйста, попробуй снова."

        try:
            ticket_kazarma_data: KazarmaClient = await session.get(KazarmaClient, ticket_id)
        except Exception as e:
            logger.error(e)
            return "Произошла ошибка базы данных. Пожалуйста, попробуй снова."

        if not ticket_kazarma_data:
            return "Клиент не найден в базе данных. Пожалуйста, проверь правильность ссылки или ID."

        try:
            ticket_data = await session.execute(get_main_users)
            temp_ticket_data = await session.execute(get_transaction_process)
        except Exception as e:
            logger.error(e)
            return "Произошла ошибка базы данных. Пожалуйста, попробуй снова."

        main_users = ticket_data.mappings().all()
        temp_user_transaction_data = temp_ticket_data.mappings().all()

    main_users = await _sort_users(main_users)
    transfer_users = await _sort_users(temp_user_transaction_data)

    return RawTicketDataContainer(
        main_users=main_users,
        transfer=transfer_users,
        ticket=ticket_db_data,
        ticket_kazarma=ticket_kazarma_data
    )


async def _sort_users(users: Iterable[dict | Any]) -> TicketEmployeesContainer:
    doc = tuple(filter(lambda x: x.role_id in (3, 8), users))
    doc = doc[0]['user_id'] if doc else None
    law = tuple(filter(lambda x: x.role_id in (2, 31), users))
    law = law[0]['user_id'] if law else None
    return TicketEmployeesContainer(doc_id=doc, law_id=law)


async def validate_ticket(
        db_session: sessionmaker,
        ticket_id: Union[str, int],
        user: User
) -> Union[TicketContainer, str]:
    ticket_data = await _get_ticket_raw_data(db_session, ticket_id)
    if isinstance(ticket_data, str):
        return ticket_data

    if user.kazarma_id not in (ticket_data.main_users.law_id, ticket_data.main_users.doc_id):
        return "Этот клиент не закреплен за тобой."

    ticket = TicketInstance(
        id=ticket_data.ticket_kazarma.id,
        fullname=ticket_data.ticket_kazarma.fullname,
        doc_id=ticket_data.transfer.doc_id or ticket_data.main_users.doc_id,
        law_id=ticket_data.transfer.law_id or ticket_data.main_users.law_id,
        status_id=1,
        comment=''
    )
    history_instance = TicketHistoryInstance(
        ticket_id=ticket_data.ticket_kazarma.id,
        sender_id=user.id,
        status_id=1
    )
    already_loaded = True if not ticket_data.ticket or ticket_data.ticket.status_id == 13 else False
    if not already_loaded:
        return "Этот клиент уже загружен на проверку в этом отчетном периоде."
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
