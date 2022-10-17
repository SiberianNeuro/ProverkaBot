from typing import NamedTuple

import pandas as pd
from datetime import date
from pathlib import Path

from sqlalchemy import select, func, or_
from sqlalchemy.orm import sessionmaker

from aiogram import types, Bot

from app.models.doc import Ticket, TicketStatus, User


class StatisticContainer(NamedTuple):
    FSI: types.FSInputFile
    filepath: Path



async def get_user_statistic(db: sessionmaker, user: User, bot: Bot):
    stmt = select(
        func.CONCAT("https://infoclinica.legal-prod.ru/cabinet/v3/#/clients/", Ticket.id).label('Ссылка'),
        TicketStatus.name.label('Статус')
    ).join(TicketStatus).where(or_(Ticket.doc_id == user.kazarma_id, Ticket.law_id == user.kazarma_id))
    print(stmt)
    async with db() as session:
        result = await session.execute(stmt)
        clients = result.mappings().fetchall()
        await session.commit()

    df = pd.DataFrame(data=clients)
    df.index += 1

    filename = f'{user.fullname}-{date.today().isoformat()}.xlsx'
    filepath = Path(filename)
    df.to_excel(filename, index_label='№')
    fsi = types.FSInputFile(filename, filename=filename)
    return StatisticContainer(FSI=fsi, filepath=filepath)
