from dataclasses import dataclass

from environs import Env


@dataclass
class KazarmaConfig:
    host: str
    user: str
    password: str
    name: str

    @property
    def mysql_url(self):
        return f'{self.user}:{self.password}@{self.host}/{self.name}'


@dataclass
class MainDBConfig:
    host: str
    user: str
    password: str
    name: str

    @property
    def postgresql_url(self):
        return f'{self.user}:{self.password}@{self.host}/{self.name}'


@dataclass
class CmDBConfig:
    host: str
    user: str
    password: str
    name: str


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
    kaz_db: KazarmaConfig
    main_db: MainDBConfig
    cm_db: CmDBConfig
    misc: Misc


def load_config(path: str = None) -> Config:

    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            use_redis=env.bool("USE_REDIS")
        ),
        kaz_db=KazarmaConfig(
            host=env.str("KAZ_DB_HOST"),
            user=env.str("KAZ_DB_USER"),
            password=env.str("KAZ_DB_PASS"),
            name=env.str("KAZ_DB_NAME")
        ),
        main_db=MainDBConfig(
            host=env.str("MAIN_DB_HOST"),
            user=env.str("MAIN_DB_USER"),
            password=env.str("MAIN_DB_PASS"),
            name=env.str("MAIN_DB_NAME")
        ),
        cm_db=CmDBConfig(
            host=env.str("CM_DB_HOST"),
            user=env.str("CM_DB_USER"),
            password=env.str("CM_DB_PASS"),
            name=env.str("CM_DB_NAME")
        ),
        misc=Misc(),
    )
