import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import relationship, declarative_base, sessionmaker

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, select, DateTime, func, inspect
from sqlalchemy.orm.strategy_options import selectinload

Base = declarative_base()


class Cluster(Base):
    __tablename__ = 'doc_users_clusters'

    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String(5))


class User(Base):
    __tablename__ = 'doc_users'

    id = Column(Integer, primary_key=True, unique=True)
    fullname = Column(String(100), nullable=False)
    kazarma_id = Column(Integer, nullable=False)
    cluster_id = Column(Integer, ForeignKey(f"{Cluster.__tablename__}.id", ondelete="CASCADE", onupdate="CASCADE"))
    is_supervisor = Column(Boolean, default=False)
    clients_count = Column(Integer, nullable=False)
    target_count = Column(Integer, nullable=False)
