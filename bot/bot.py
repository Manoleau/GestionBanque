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
        intents.message_content = True  # needed for reading message content in commands
        super().__init__(command_prefix=config.prefix, intents=intents)
        self.config = config
        self.db = db

    async def setup_hook(self):
        from .cogs.notes import Notes
        await self.add_cog(Notes(self))
        logger.info("Cogs loaded.")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")


def run():
    config = get_config()
    db = Database(config.database)

    bot = MyBot(config, db)

    @bot.command()
    async def ping(ctx: commands.Context):
        await ctx.reply("Pong!")

    async def main():
        async with bot:
            await db.connect()
            try:
                await bot.start(config.token)
            finally:
                await db.close()

    asyncio.run(main())
