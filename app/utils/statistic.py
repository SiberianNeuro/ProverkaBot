from typing import NamedTuple
import io

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


async def get_user_statistic(db: sessionmaker, user: User):
    stmt = select(
        func.CONCAT("https://infoclinica.legal-prod.ru/cabinet/v3/#/clients/", Ticket.id).label('Ссылка'),
        TicketStatus.name.label('Статус')
    ).join(TicketStatus).where(or_(Ticket.doc_id == user.kazarma_id, Ticket.law_id == user.kazarma_id))
    async with db() as session:
        result = await session.execute(stmt)
        clients = result.mappings().fetchall()
        await session.commit()

    df = pd.DataFrame(data=clients)
    df.index += 1

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index_label='№')
    writer.save()
    xlsx_data = output.getvalue()

    filename = f'{user.fullname.replace(" ", "_", 2)}_{date.today().isoformat()}.xlsx'
    filepath = Path(filename)
    fsi = types.FSInputFile(filepath, filename=filename)
    buf = types.BufferedInputFile(xlsx_data, filename=filename)
    return StatisticContainer(FSI=buf, filepath=filepath)
