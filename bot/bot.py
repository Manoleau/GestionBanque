import asyncio
import logging

import discord
from discord.ext import commands

from .config import get_config
from .db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MyBot(commands.Bot):
    def __init__(self, config, db: Database):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=config.prefix, intents=intents)
        self.config = config
        self.db = db

    async def setup_hook(self):
        from .cogs.budget import Budget
        await self.add_cog(Budget(self))
        try:
            await self.tree.sync()
            logger.info("App commands synchronized.")
        except Exception as e:
            logger.exception("Failed to sync app commands: %s", e)
        logger.info("Cogs loaded.")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")


def run():
    config = get_config()
    db = Database(config.database)

    bot = MyBot(config, db)

    async def main():
        async with bot:
            await db.connect()
            try:
                await bot.start(config.token)
            finally:
                await db.close()

    asyncio.run(main())
