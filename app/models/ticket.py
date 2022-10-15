from sqlalchemy.orm import relationship

from .user import Base, User
from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, func, DateTime, Text


class TicketStatus(Base):
    __tablename__ = "doc_lib_ticket_status"

    id = Column(Integer, primary_key=True)
    name = Column(String(45))


class Ticket(Base):
    __tablename__ = "doc_tickets"

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    doc_id = Column(Integer, ForeignKey(f"{User.__tablename__}.id", onupdate='CASCADE', ondelete='CASCADE'), index=True)
    law_id = Column(Integer, ForeignKey(f"{User.__tablename__}.id", onupdate='CASCADE', ondelete='CASCADE'), index=True)
    status_id = Column(Integer, ForeignKey(f"{TicketStatus.__tablename__}.id", onupdate='CASCADE', ondelete='CASCADE'),
                       server_default='1', index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), server_onupdate=func.now())
    appeal = relationship("Appeal")


class Appeal(Base):
    __tablename__ = "doc_ticket_appeal"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(BigInteger, ForeignKey(f"{Ticket.__tablename__}.id", onupdate="CASCADE", ondelete="CASCADE"),
                       index=True)
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
    start_time = Column(DateTime, server_default=func.now())
    end_time = Column(DateTime, server_default=func.now(), server_onupdate=func.now())
