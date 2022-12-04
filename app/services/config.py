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
class RedisConfig:
    host: str
    port: int
    db: int


@dataclass
class TgBot:
    token: str
    use_redis: bool


@dataclass
class Misc:
    checking_group: str
    send_client: bool
    send_appeal: bool


@dataclass
class Config:
    tg_bot: TgBot
    redis: RedisConfig
    kaz_db: KazarmaConfig
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
        redis=RedisConfig(
         host=env.str("REDIS_HOST"),
         port=env.int("REDIS_PORT"),
         db=env.int("REDIS_DB")
        ),
        misc=Misc(
            checking_group=env.str("CHECKING_GROUP_ID"),
            send_client=env.bool("SEND_CLIENT"),
            send_appeal=env.bool("SEND_APPEAL")
        )
    )
