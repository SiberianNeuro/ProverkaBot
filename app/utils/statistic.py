from typing import NamedTuple, Union, Sequence, Iterable, Any
from io import BytesIO

import pandas as pd
from datetime import date
from pathlib import Path

from loguru import logger
from sqlalchemy import select, func, or_, and_, null, case
from sqlalchemy.orm import sessionmaker

from aiogram import types

from app.models.doc import Ticket, TicketStatus, User, TicketHistory


class StatisticContainer(NamedTuple):
    FSI: types.BufferedInputFile
    filepath: Path
    # stats_string: Optional[str]
    # df: Optional[pd.DataFrame]


async def get_buffered_file(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index_label="№")
    writer.save()
    return output.getvalue()


async def get_user_statistic(db: sessionmaker, user: User) -> Union[StatisticContainer, str]:
    stmt = select(
        func.CONCAT("https://clinica.legal-prod.ru/cabinet/v3/#/clients/", Ticket.id).label('Ссылка'),
        Ticket.fullname.label('ФИО клиента'),
        TicketStatus.name.label('Статус'),
        Ticket.comment.label("Комментарий"),
        Ticket.created_at.label('Дата подачи клиента'),
        Ticket.updated_at.label('Дата последнего изменения'),
    ). \
        join(TicketStatus). \
        where(or_(Ticket.doc_id == user.kazarma_id, Ticket.law_id == user.kazarma_id))
    async with db() as session:
        try:
            result = await session.execute(stmt)
            clients = result.mappings().fetchall()
            await session.commit()
        except Exception as e:
            logger.error(e)
            await session.rollback()
            return "Произошла ошибка базы данных. Пожалуйста, попробуй снова."

    df = pd.DataFrame(
        data=clients,
        columns=[
            "Ссылка",
            "ФИО клиента",
            "Статус",
            "Комментарий",
            "Дата подачи клиента",
            "Дата последнего изменения"
        ]
    )
    df.index += 1

    xlsx_data = await get_buffered_file(df)

    filename = f'{user.fullname.replace(" ", "_", 2)}_{date.today().isoformat()}.xlsx'
    filepath = Path(filename)
    buf = types.BufferedInputFile(xlsx_data, filename=filename)
    return StatisticContainer(FSI=buf, filepath=filepath)


async def get_rejected_clients(db: sessionmaker, user: User) -> Union[Sequence[Ticket], str]:
    query = select(Ticket.id, Ticket.fullname, Ticket.status_id, Ticket.comment). \
        filter(Ticket.status_id.in_((4, 11)),
               or_(Ticket.doc_id == user.kazarma_id, Ticket.law_id == user.kazarma_id))

    async with db() as session:
        try:
            res = await session.execute(query)
            re = res.mappings().fetchall()
        except Exception as e:
            logger.error(e)
            return "Ошибка базы данных. Пожалуйста, попробуй снова."
    if not re:
        return "Клиентов не найдено."
    return re


class HistoryContainer(NamedTuple):
    client: Ticket
    history: Iterable[Any]


async def get_history(db, client_id) -> Union[HistoryContainer, str]:
    stmt = select(
        TicketHistory.status_id, TicketStatus.name, TicketHistory.created_at,
        User.fullname, User.is_checking, TicketHistory.comment).\
        join(TicketStatus, TicketStatus.id == TicketHistory.status_id). \
        join(User, User.id == TicketHistory.sender_id). \
        where(TicketHistory.ticket_id == client_id). \
        order_by(TicketHistory.created_at)
    async with db() as session:
        try:
            client = await session.get(Ticket, int(client_id))
            result = await session.execute(stmt)
        except Exception as e:
            logger.error(e)
            await session.rollback()
            return "Произошла ошибка базы данных. Пожалуйста, попробуй снова."
        history = result.mappings().all()
    if not history:
        return "Среди отправленных мне клиентов такого ID нет. Пожалуйста, проверь корректность данных."
    return HistoryContainer(client, history)


async def get_for_checking_pool(db) -> Union[Iterable[Ticket], str]:
    stmt = select(Ticket).filter(Ticket.status_id.in_((1, 5, 6))).order_by(func.random()).limit(3)
    async with db() as session:
        try:
            result = await session.execute(stmt)
        except Exception as e:
            logger.error(e)
            await session.rollback()
            return "Произошла ошибка базы данных. Пожалуйста, попробуй снова."
    tickets = result.scalars().all()
    if not tickets:
        return "Все возможные заявки проверены."
    return tickets
