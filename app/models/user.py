import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import relationship, declarative_base, sessionmaker

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, select, DateTime, func, inspect
from sqlalchemy.orm.strategy_options import selectinload

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, unique=True)
    fullname = Column(String(100), nullable=False)
    kazarma_id = Column(Integer, nullable=False)
    is_supervisor = Column(Boolean, default=False)
    clients_count = Column(Integer, nullable=False)
    target_count = Column(Integer, nullable=False)
    child = relationship("Child", backref="children", lazy='dynamic', primaryjoin="Child.user_id==User.id")



class Child(Base):
    __tablename__ = 'children'

    id = Column(Integer, primary_key=True, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    data = Column(Text, nullable=False)



class A(Base):
    __tablename__ = "a"

    id = Column(Integer, primary_key=True)
    data = Column(String(100))
    create_date = Column(DateTime, server_default=func.now())
    bs = relationship("B")

    # required in order to access columns with server defaults
    # or SQL expression defaults, subsequent to a flush, without
    # triggering an expired load
    __mapper_args__ = {"eager_defaults": True}


def object_as_dict(obj):
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}


class B(Base):
    __tablename__ = "b"
    id = Column(Integer, primary_key=True)
    a_id = Column(ForeignKey("a.id"))
    data = Column(String(100))


async def async_main():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres_te_usr:Dj2n82iV@151.248.121.212/postgres_test",
        echo=True,
    )
    # engine = create_async_engine(
    #     "mysql+aiomysql://test-db_usr:Dj2n82iV@151.248.121.212/test-db",
    #     echo=True,
    # )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # expire_on_commit=False will prevent attributes from being expired
    # after commit.
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        async with session.begin():
            user = session.add_all([
                User(child=[Child(data='123'), Child(data='456')], fullname='Nikita', kazarma_id=466, is_supervisor=True, clients_count=500, target_count=350),
                User(child=[Child(data='987'), Child(data='654')], fullname='Vasya', kazarma_id=100, is_supervisor=False, clients_count=100, target_count=200),
            ]


            )
            stmt = select(User.kazarma_id, func.count(Child.id)).join(Child).group_by(User.kazarma_id)
            print(stmt)

            result = await session.execute(stmt)
            print(result.mappings().all())
            # for a1 in result.scalars().all():
            #     print(a1.fullname, a1.id)
            #     print(f"created at: {a1.create_date}")
            # for b1 in a1.bs:
                # print(b1)
    #
    #     result = await session.execute(select(A).order_by(A.id))
    #
    #     a1 = result.scalars().first()
    #
    #     a1.data = "new data"
    #
    #     await session.commit()
    #
    #     # access attribute subsequent to commit; this is what
    #     # expire_on_commit=False allows
    #     print(a1.data)
    #
    # # for AsyncEngine created in function scope, close and
    # # clean-up pooled connections
    # await engine.dispose()


asyncio.run(async_main())