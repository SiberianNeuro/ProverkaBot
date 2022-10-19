from typing import NamedTuple
from io import BytesIO

import pandas as pd
from datetime import date
from pathlib import Path

from sqlalchemy import select, func, or_
from sqlalchemy.orm import sessionmaker

from aiogram import types

from app.models.doc import Ticket, TicketStatus, User


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
        func.CONCAT("https://infoclinica.legal-prod.ru/cabinet/v3/#/clients/", Ticket.id).label('Ссылка'),
        TicketStatus.name.label('Статус'),
        Ticket.updated_at.label('Дата последнего изменения')
    ).join(TicketStatus).where(or_(Ticket.doc_id == user.kazarma_id, Ticket.law_id == user.kazarma_id))
    async with db() as session:
        result = await session.execute(stmt)
        clients = result.mappings().fetchall()
        await session.commit()

    df = pd.DataFrame(data=clients, columns=["Ссылка", "Статус", "Дата последнего изменения"])
    df.index += 1
    print(len(df.index))
    print(df.loc[df['Статус'] == 'залупа', 'Статус'].count())

    xlsx_data = await get_buffered_file(df)

    filename = f'{user.fullname.replace(" ", "_", 2)}_{date.today().isoformat()}.xlsx'
    filepath = Path(filename)
    buf = types.BufferedInputFile(xlsx_data, filename=filename)
    return StatisticContainer(FSI=buf, filepath=filepath)
