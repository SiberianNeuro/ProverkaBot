from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, SmallInteger
from sqlalchemy.orm import declarative_base

Kazarma = declarative_base()


class KazarmaClient(Kazarma):
    __tablename__ = "crm_client"

    id = Column(Integer, primary_key=True)
    firstname = Column(String(50))
    lastname = Column(String(50))
    middlename = Column(String(50))
    is_send = Column('visited_military_office', Integer)
    send_date = Column('military_office_date', DateTime)

    @property
    def fullname(self):
        return f'{self.lastname} {self.firstname}{" " + self.middlename if self.middlename else ""}'


class KazarmaRole(Kazarma):
    __tablename__ = "crm_user_roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))


class KazarmaUser(Kazarma):
    __tablename__ = "crm_users"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey(f'{KazarmaRole.__tablename__}.id'))
    lastname = Column(String)
    firstname = Column(String)
    middlename = Column(String)
    email = Column(String(100))
    active = Column(Integer)


class KazarmaClientUser(Kazarma):
    __tablename__ = "crm_client_user"

    user_id = Column(Integer, ForeignKey(f"{KazarmaUser.__tablename__}.id"), primary_key=True)
    client_id = Column(Integer, ForeignKey(f"{KazarmaClient.__tablename__}.id"), primary_key=True)
    active = Column(SmallInteger)
