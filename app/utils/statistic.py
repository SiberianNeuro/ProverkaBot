from typing import NamedTuple, Union, Sequence
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


async def get_user_statistic(db: sessionmaker, user: User):
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
    print(stmt)
    async with db() as session:
        result = await session.execute(stmt)
        clients = result.mappings().fetchall()
        await session.commit()

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
    query = select(Ticket.id, Ticket.fullname, Ticket.status_id, Ticket.comment).\
        filter(Ticket.status_id.in_((4, 11)),
               or_(Ticket.doc_id == user.kazarma_id, Ticket.law_id == user.kazarma_id))
    # in_query = select(
    #     Ticket.id,
    #     Ticket.comment,
    #     func.COUNT(case((TicketHistory.status_id == 5, 1))).label('c')
    # ).\
    #     filter(Ticket.status_id == 4, or_(Ticket.doc_id == user.kazarma_id, Ticket.law_id == user.kazarma_id)).\
    #     join(TicketHistory).group_by(Ticket.id, Ticket.comment)
    # in_query = in_query.cte('tickets')
    # out_query = select(in_query).filter(in_query.c.c < 2)
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
