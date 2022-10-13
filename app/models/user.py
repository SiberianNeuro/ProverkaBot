from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Cluster(Base):
    __tablename__ = 'doc_clusters'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))


class User(Base):
    __tablename__ = 'doc_users'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    fullname = Column(String(100), nullable=False)
    kazarma_id = Column(Integer, nullable=False)
    role_id = Column(Integer, nullable=False)
    role_name = Column(String(100), nullable=False)
    cluster_id = Column(Integer, ForeignKey(f"{Cluster.__tablename__}.id", ondelete="CASCADE", onupdate="CASCADE"))
    is_checking = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    clients_count = Column(Integer)
    target_count = Column(Integer)
