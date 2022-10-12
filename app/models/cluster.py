from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Clusters = declarative_base()


class Common(Clusters):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    kazarma_id = Column(Integer)
    fullname = Column('fio', String(45))
    cluster = Column(String(45))
