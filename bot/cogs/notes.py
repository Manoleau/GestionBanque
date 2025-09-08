from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..bot import MyBot

class Notes(commands.Cog):
    def __init__(self, bot: 'MyBot'):
        self.bot = bot

    @commands.command(name="addnote")
    async def add_note(self, ctx: commands.Context, *, note: str):
        """Add a note stored in SQLite for the invoking user.
        Usage: !addnote your text here
        """
        await self.bot.db.add_note(ctx.author.id, note)
        await ctx.reply("Note added.")

    @commands.command(name="notes")
    async def list_notes(self, ctx: commands.Context):
        """List your notes stored in SQLite."""
        rows = await self.bot.db.list_notes(ctx.author.id)
        if not rows:
            await ctx.reply("No notes yet.")
            return
        content = "\n".join(f"- {note} (at {ts})" for note, ts in rows[:10])
        await ctx.reply(f"Your last {min(10, len(rows))} notes:\n{content}")
