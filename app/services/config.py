from dataclasses import dataclass

from environs import Env


@dataclass
class KazarmaConfig:
    kaz_host: str
    kaz_user: str
    kaz_pass: str
    kaz_name: str


@dataclass
class MainDBConfig:
    main_db_host: str
    main_db_user: str
    main_db_pass: str
    main_db_name: str

@dataclass
class TgBot:
    token: str
    use_redis: bool


@dataclass
class Misc:
    pass


@dataclass
class Config:
    tg_bot: TgBot
    kazarma: KazarmaConfig
    main_db: MainDBConfig
    misc: Misc


def load_config(path: str = None) -> Config:

    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            use_redis=env.bool("USE_REDIS")
        ),
        kazarma=KazarmaConfig(
            kaz_host=env.str("KAZ_DB_HOST"),
            kaz_user=env.str("KAZ_DB_USER"),
            kaz_pass=env.str("KAZ_DB_PASS"),
            kaz_name=env.str("KAZ_DB_NAME")
        ),
        main_db=MainDBConfig(
            main_db_host=env.str("MAIN_DB_HOST"),
            main_db_user=env.str("MAIN_DB_USER"),
            main_db_pass=env.str("MAIN_DB_PASS"),
            main_db_name=env.str("MAIN_DB_NAME")
        ),
        misc=Misc()
    )
