from typing import Union, TypedDict

from sqlalchemy import select, and_
from sqlalchemy.orm import sessionmaker

from app.models.kazarma import KazarmaClient, KazarmaClientUser, KazarmaUser
from app.models.doc import User


class TicketInstance(TypedDict):
    id: int
    doc_id: int
    law_id: int


class TicketHistoryInstance(TypedDict):
    ticket_id: int
    sender_id: int
    status_id: int


class ClientInstance(TypedDict):
    id: int
    fullname: str


class TicketContainer(TypedDict):
    ticket: TicketInstance
    ticket_history: TicketHistoryInstance
    client: ClientInstance


async def validate_ticket(
        db_session: sessionmaker,
        ticket_id: Union[str, int],
        user: User
) -> Union[TicketContainer, str]:
    async with db_session() as session:
        temp_client: KazarmaClient = await session.get(KazarmaClient, ticket_id)
        if not temp_client:
            return "Клиент не найден в базе данных. Пожалуйста, проверь правильность ссылки."
        # if temp_client.is_send == 0:
        #     return 'Метка "Отправлен в военкомат" не проставлена. Пожалуйста, поставь метку, а затем отправь мне ' \
        #            'ссылку заново.'

        stmt = select(
            KazarmaClientUser.user_id,
            KazarmaUser.role_id
        ).join(KazarmaUser).where(and_(KazarmaClientUser.active == 1, KazarmaClientUser.client_id == ticket_id))
        ticket_data = await session.execute(stmt)

        law_id = None
        doc_id = None
        for employee in ticket_data.mappings().all():
            if employee.role_id in (2, 31):
                law_id = employee.user_id
            elif employee.role_id in (3, 8):
                doc_id = employee.user_id
    if user.kazarma_id not in (law_id, doc_id):
        return "Данный клиент закреплен не за тобой. Ты можешь отправлять только собственных клиентов."

    ticket = TicketInstance(
        id=temp_client.id,
        doc_id=doc_id,
        law_id=law_id,
    )
    history_instance = TicketHistoryInstance(
        ticket_id=temp_client.id,
        sender_id=user.id,
        status_id=1
    )
    client = ClientInstance(
        id=temp_client.id,
        fullname=temp_client.fullname
    )
    return TicketContainer(ticket=ticket, ticket_history=history_instance, client=client)
