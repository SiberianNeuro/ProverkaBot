from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, BigInteger, func, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import expression

Base = declarative_base()


class Cluster(Base):
    __tablename__ = 'doc_clusters'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))


class User(Base):
    __tablename__ = 'doc_users'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    fullname = Column(String(100), nullable=False)
    kazarma_id = Column(Integer, nullable=False, index=True)
    role_id = Column(Integer, nullable=False)
    role_name = Column(String(100), nullable=False)
    cluster_id = Column(Integer, ForeignKey(f"{Cluster.__tablename__}.id", ondelete="CASCADE", onupdate="CASCADE"))
    is_checking = Column(Boolean, server_default=expression.false())
    is_admin = Column(Boolean, server_default=expression.false())
    clients_count = Column(Integer, server_default='0')
    target_count = Column(Integer, server_default='0')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), server_onupdate=func.now())
