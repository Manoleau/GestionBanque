import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    token: str
    prefix: str = "!"
    database: str = "bot.db"


def get_config() -> Config:
    token = os.getenv("DISCORD_TOKEN", "")
    prefix = os.getenv("COMMAND_PREFIX", "!")
    database = os.getenv("DATABASE_PATH", "bot.db")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set. Create a .env file with DISCORD_TOKEN=... or set the environment variable.")
    return Config(token=token, prefix=prefix, database=database)
