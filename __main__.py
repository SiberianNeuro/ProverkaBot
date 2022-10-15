import asyncio

from aiogram.types import BotCommand, BotCommandScopeDefault
from loguru import logger

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.pool import NullPool

from app.middlewares.acl import CommonMiddleware
from app.models.user import Base
from app.models.kazarma import Kazarma


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Вернутся в меню"),
        BotCommand(command="help", description="Получить помощь")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def main():
    logger.info('Loading config...')
    from app.services.config import load_config
    config = load_config(".env")

    logger.info('Configure storage...')
    if config.tg_bot.use_redis:
        logger.info("Configure redis...")
        from app.utils.redis import BaseRedis
        redis = BaseRedis(db=3)
        await redis.connect()
        storage = RedisStorage(redis=redis.redis)
        logger.info("Redis storage ready.")
    else:
        logger.info("Configure memory storage...")
        storage = MemoryStorage()
        logger.info('Memory storage ready.')

    logger.info('Configure databases...')

    main_engine = create_async_engine(
        f"postgresql+asyncpg://{config.main_db.user}:{config.main_db.password}@{config.main_db.host}/{config.main_db.name}",
        echo=True, poolclass=NullPool)
    kazarma_engine = create_async_engine(
        f"mysql+aiomysql://{config.kaz_db.user}:{config.kaz_db.password}@{config.kaz_db.host}/{config.kaz_db.name}",
        echo=True, poolclass=NullPool)
    try:
        async with main_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with kazarma_engine.begin() as conn:
            await conn.run_sync(Kazarma.metadata)
        logger.info('Done.')

    except Exception as e:
        logger.error(e)

    async_session = sessionmaker(expire_on_commit=False, class_=AsyncSession)
    async_session.configure(
        binds={
            Base: main_engine,
            Kazarma: kazarma_engine
        }
    )

    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
    dispatcher = Dispatcher(storage=storage)

    logger.info("Configure middleware...")
    dispatcher.update.outer_middleware(CommonMiddleware(config=config, db=async_session))

    from app.handlers.users import ticket, checking, register, common

    logger.info("Configure handlers...")

    dispatcher.include_router(common.router)
    dispatcher.include_router(ticket.router)
    dispatcher.include_router(checking.router)
    dispatcher.include_router(register.router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await dispatcher.storage.close()
        await bot.session.close()


if __name__ == '__main__':
    from app.services import logging

    logging.setup()

    asyncio.run(main())
