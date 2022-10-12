import asyncio
from loguru import logger

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from app.middlewares.acl import CommonMiddleware
from app.models.base import Kazarma, Base


async def main():
    logger.info('Loading config...')
    from app.services.config import load_config
    config = load_config(".env")

    redis = None
    if config.tg_bot.use_redis:
        logger.info("Configure redis...")
        from app.utils.redis import BaseRedis
        redis = BaseRedis()
        await redis.connect()

    logger.info('Configure database...')
    main_engine = create_async_engine(
        f"postgresql+asyncpg://{config.main_db.main_db_user}:{config.main_db.main_db_pass}@{config.main_db.main_db_host}/{config.main_db.main_db_name} "
    )
    kazarma_engine = create_async_engine(
        f"mysql+aiomysql://{config.kazarma.kaz_user}:{config.kazarma.kaz_pass}@{config.kazarma.kaz_host}/{config.kazarma.kaz_name}"
    )
    async_session = sessionmaker()
    async_session.configure(binds={Base: main_engine, Kazarma: kazarma_engine})

    bot = Bot(token=config.tg_bot.token)
    storage = MemoryStorage() if config.tg_bot.use_redis else RedisStorage(redis=redis.redis)
    dispatcher = Dispatcher(storage=storage)

    logger.info("Configure middleware...")
    dispatcher.update.outer_middleware(CommonMiddleware(config=config, db=async_session))

    from app.handlers.users import ticket, supervisor, register, common

    logger.info("Configure handlers...")

    dispatcher.include_router(ticket.router)
    dispatcher.include_router(supervisor.router)
    dispatcher.include_router(register.router)
    dispatcher.include_router(common.router)

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
