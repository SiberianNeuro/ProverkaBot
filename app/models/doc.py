from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, BigInteger, func, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression
from app.models.db import Base



class Cluster(Base):
    __tablename__ = 'doc_clusters'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))


class User(Base):
    __tablename__ = 'doc_users'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    fullname = Column(String(100), nullable=False)
    kazarma_id = Column(Integer, index=True)
    role_id = Column(Integer, nullable=False)
    role_name = Column(String(100), nullable=False)
    cluster_id = Column(Integer, ForeignKey(f"{Cluster.__tablename__}.id", ondelete="CASCADE", onupdate="CASCADE"))
    is_checking = Column(Boolean, server_default=expression.false())
    is_admin = Column(Boolean, server_default=expression.false())
    clients_count = Column(Integer, server_default='0')
    target_count = Column(Integer, server_default='0')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), server_onupdate=func.now())


class TicketStatus(Base):
    __tablename__ = "doc_lib_ticket_status"

    id = Column(Integer, primary_key=True)
    name = Column(String(45))


class Ticket(Base):
    __tablename__ = "doc_tickets"

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    doc_id = Column(Integer, index=True)
    law_id = Column(Integer, index=True)
    status_id = Column(Integer, ForeignKey(f"{TicketStatus.__tablename__}.id", onupdate='CASCADE', ondelete='CASCADE'),
                       server_default='1', index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), server_onupdate=func.now())
    appeal = relationship("Appeal")


class Appeal(Base):
    __tablename__ = "doc_ticket_appeal"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey(f"{Ticket.__tablename__}.id", onupdate="CASCADE", ondelete="CASCADE"))
    sender_id = Column(BigInteger, ForeignKey(f"{User.__tablename__}.id", onupdate="CASCADE", ondelete="CASCADE"),
                       index=True)
    comment = Column(Text)
    checker_id = Column(BigInteger, ForeignKey(f"{User.__tablename__}.id", onupdate="CASCADE", ondelete="CASCADE"),
                        index=True)
    status_id = Column(Integer, ForeignKey(f"{TicketStatus.__tablename__}.id", onupdate="CASCADE", ondelete="CASCADE"),
                       index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), server_onupdate=func.now())


class TicketHistory(Base):
    __tablename__ = "doc_ticket_status_history"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(BigInteger, ForeignKey(f"{Ticket.__tablename__}.id", onupdate="CASCADE", ondelete="CASCADE"))
    sender_id = Column(BigInteger, ForeignKey(f"{User.__tablename__}.id", onupdate="CASCADE", ondelete="CASCADE"))
    status_id = Column(Integer, ForeignKey(f"{TicketStatus.__tablename__}.id", onupdate="CASCADE", ondelete="CASCADE"),
                       index=True)
    comment = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

