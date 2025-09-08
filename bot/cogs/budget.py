from datetime import datetime
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ..services.budget_service import BudgetService
from ..utils.money import parse_amount_to_cents, format_cents

if TYPE_CHECKING:
    from ..bot import MyBot


class Budget(commands.Cog):
    INFO_COLOR = 0x2B6CB0
    SUCCESS_COLOR = 0x2F855A
    WARN_COLOR = 0x975A16

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if text is None:
            return ""
        return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"

    @classmethod
    def _embed(cls, title: Optional[str] = None, description: Optional[str] = None, *,
               color: Optional[int] = None) -> discord.Embed:
        emb = discord.Embed(
            title=cls._truncate(title, 256) if title else None,
            description=cls._truncate(description, 4096) if description else None,
            color=color or cls.INFO_COLOR,
        )
        return emb

    def __init__(self, bot: 'MyBot'):
        self.bot = bot
        self.morning_channel_id: Optional[int] = None
        channel_id = getattr(self.bot.config, 'reminder_channel_id', None)
        if channel_id:
            try:
                self.morning_channel_id = int(channel_id)
            except ValueError:
                self.morning_channel_id = None
        self.reminder_task.start()

    def cog_unload(self):
        self.reminder_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        self.service = BudgetService(self.bot.db.conn)
        await self.service.ensure_schema()

    async def sub_id_autocomplete(self, interaction: discord.Interaction, current: str):
        try:
            subs = await self.service.list_subscriptions(interaction.user.id)
        except Exception:
            return []
        current_lower = (current or "").lower()
        choices = []
        for s in subs:
            label = f"{s.name} ({format_cents(s.amount_cents)})"
            if not current_lower or current_lower in s.name.lower() or current_lower in str(s.id):
                choices.append(app_commands.Choice(name=label[:100], value=int(s.id)))
            if len(choices) >= 25:
                break
        return choices

    async def expense_id_autocomplete(self, interaction: discord.Interaction, current: str):
        try:
            rows = await self.service.list_unpaid_expenses(interaction.user.id)
        except Exception:
            return []
        current_lower = (current or "").lower()
        choices = []
        for e in rows:
            label = f"{e.name} dû le {e.due_date} ({format_cents(e.amount_cents)})"
            if not current_lower or current_lower in e.name.lower() or current_lower in str(e.id):
                choices.append(app_commands.Choice(name=label[:100], value=int(e.id)))
            if len(choices) >= 25:
                break
        return choices

    group_sub = app_commands.Group(name="sub", description="Gérer vos abonnements")

    @group_sub.command(name="add", description="Ajouter un abonnement")
    @app_commands.describe(name="Nom de l'abonnement", amount="Montant (ex: 12.99)",
                           day_of_month="Jour du mois (1..28)")
    async def sub_add(self, interaction: discord.Interaction, name: str, amount: str,
                      day_of_month: app_commands.Range[int, 1, 28]):
        await interaction.response.defer(ephemeral=True)
        amount_cents = parse_amount_to_cents(amount)
        await self.service.add_subscription(interaction.user.id, name, amount_cents, int(day_of_month))
        emb = self._embed(title="Abonnement ajouté",
                          description=f"{name} {format_cents(amount_cents)} le {int(day_of_month)}",
                          color=self.SUCCESS_COLOR)
        await interaction.followup.send(embed=emb, ephemeral=True)

    @group_sub.command(name="list", description="Lister vos abonnements")
    async def sub_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        subs = await self.service.list_subscriptions(interaction.user.id)
        if not subs:
            emb = self._embed(title="Abonnements", description="Aucun abonnement.")
            await interaction.followup.send(embed=emb, ephemeral=True)
            return
        lines = [f"{s.name}: {format_cents(s.amount_cents)} le {s.day_of_month} ({'actif' if s.active else 'inactif'})"
                 for s in subs]
        emb = self._embed(title="Vos abonnements", description="\n".join(lines))
        await interaction.followup.send(embed=emb, ephemeral=True)

    @group_sub.command(name="del", description="Supprimer un abonnement par ID")
    @app_commands.describe(sub_id="Sélectionnez un abonnement")
    @app_commands.autocomplete(sub_id=sub_id_autocomplete)
    async def sub_delete(self, interaction: discord.Interaction, sub_id: int):
        await interaction.response.defer(ephemeral=True)
        await self.service.delete_subscription(interaction.user.id, sub_id)
        emb = self._embed(title="Abonnement supprimé", description=f"#{sub_id} supprimé (s'il existait).",
                          color=self.SUCCESS_COLOR)
        await interaction.followup.send(embed=emb, ephemeral=True)

    group_pay = app_commands.Group(name="pay", description="Gérer vos dépenses")

    @group_pay.command(name="add", description="Ajouter une dépense à payer")
    @app_commands.describe(name="Nom", amount="Montant (ex: 50)", due_date="Échéance AAAA-MM-JJ")
    async def pay_add(self, interaction: discord.Interaction, name: str, amount: str, due_date: str):
        await interaction.response.defer(ephemeral=True)
        amount_cents = parse_amount_to_cents(amount)
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            emb = self._embed(title="Date invalide", description="Format attendu AAAA-MM-JJ.", color=self.WARN_COLOR)
            await interaction.followup.send(embed=emb, ephemeral=True)
            return
        await self.service.add_expense(interaction.user.id, name, amount_cents, due_date)
        emb = self._embed(title="Dépense ajoutée",
                          description=f"{name} {format_cents(amount_cents)} pour le {due_date}",
                          color=self.SUCCESS_COLOR)
        await interaction.followup.send(embed=emb, ephemeral=True)

    @group_pay.command(name="list", description="Lister vos dépenses non payées")
    async def pay_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rows = await self.service.list_unpaid_expenses(interaction.user.id)
        if not rows:
            emb = self._embed(title="Dépenses", description="Aucune dépense à payer.")
            await interaction.followup.send(embed=emb, ephemeral=True)
            return
        lines = [f"{e.name}: {format_cents(e.amount_cents)} dû le {e.due_date}" for e in rows]
        emb = self._embed(title="À payer", description="\n".join(lines))
        await interaction.followup.send(embed=emb, ephemeral=True)

    @group_pay.command(name="done", description="Marquer une dépense comme payée")
    @app_commands.describe(expense_id="Sélectionnez une dépense")
    @app_commands.autocomplete(expense_id=expense_id_autocomplete)
    async def pay_done(self, interaction: discord.Interaction, expense_id: int):
        await interaction.response.defer(ephemeral=True)
        await self.service.mark_expense_paid(interaction.user.id, expense_id)
        emb = self._embed(title="Dépense payée", description=f"#{expense_id} marquée comme payée.",
                          color=self.SUCCESS_COLOR)
        await interaction.followup.send(embed=emb, ephemeral=True)

    @group_pay.command(name="del", description="Supprimer une dépense")
    @app_commands.describe(expense_id="Sélectionnez une dépense")
    @app_commands.autocomplete(expense_id=expense_id_autocomplete)
    async def pay_delete(self, interaction: discord.Interaction, expense_id: int):
        await interaction.response.defer(ephemeral=True)
        await self.service.delete_expense(interaction.user.id, expense_id)
        emb = self._embed(title="Dépense supprimée", description=f"#{expense_id} supprimée (si elle existait).",
                          color=self.SUCCESS_COLOR)
        await interaction.followup.send(embed=emb, ephemeral=True)

    @app_commands.command(name="reste", description="Voir le total restant à payer ce mois")
    async def remaining_month(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        total, subs_due, mans = await self.service.remaining_for_month(interaction.user.id)
        desc_lines = []
        if subs_due:
            desc_lines.append("Abonnements à venir:")
            for name, cents, dom in subs_due:
                desc_lines.append(f"- {name} le {dom}: {format_cents(cents)}")
        if mans:
            desc_lines.append("Dépenses à payer:")
            for name, cents, due in mans:
                desc_lines.append(f"- {name} pour le {due}: {format_cents(cents)}")
        desc_lines.append(f"Total restant ce mois: {format_cents(total)}")
        emb = self._embed(title="Reste à payer ce mois", description="\n".join(desc_lines))
        await interaction.followup.send(embed=emb, ephemeral=True)

    group_bank = app_commands.Group(name="bank", description="Gérer votre solde bancaire")

    group_reminder = app_commands.Group(name="reminder", description="Paramétrer votre rappel quotidien")

    @group_reminder.command(name="set", description="Définir le mode de rappel (mp ou channel)")
    @app_commands.describe(mode="Choisissez 'dm' pour message privé, 'channel' pour poster dans un salon",
                           channel="Salon où poster si mode=channel")
    @app_commands.choices(
        mode=[app_commands.Choice(name="dm", value="dm"), app_commands.Choice(name="channel", value="channel")])
    async def reminder_set(self, interaction: discord.Interaction, mode: app_commands.Choice[str],
                           channel: Optional[discord.TextChannel] = None):
        await interaction.response.defer(ephemeral=True)
        chosen = mode.value.lower()
        if chosen not in ("dm", "channel"):
            emb = self._embed(title="Mode invalide", description="Choisissez 'dm' ou 'channel'.", color=self.WARN_COLOR)
            await interaction.followup.send(embed=emb, ephemeral=True)
            return
        chan_id = None
        if chosen == 'channel':
            if channel is None:
                emb = self._embed(title="Salon requis", description="Vous devez fournir un salon si mode=channel.",
                                  color=self.WARN_COLOR)
                await interaction.followup.send(embed=emb, ephemeral=True)
                return
            chan_id = channel.id
        await self.service.set_reminder_pref(interaction.user.id, chosen, chan_id)
        if chosen == 'dm':
            emb = self._embed(title="Rappel configuré", description="Mode: message privé à 8h",
                              color=self.SUCCESS_COLOR)
            await interaction.followup.send(embed=emb, ephemeral=True)
        else:
            emb = self._embed(title="Rappel configuré", description=f"Mode: salon #{channel.name} à 8h",
                              color=self.SUCCESS_COLOR)
            await interaction.followup.send(embed=emb, ephemeral=True)

    @group_reminder.command(name="show", description="Afficher votre configuration de rappel")
    async def reminder_show(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        pref = await self.service.get_reminder_pref(interaction.user.id)
        if not pref:
            emb = self._embed(title="Rappel", description="Aucune configuration de rappel trouvée pour vous.")
            await interaction.followup.send(embed=emb, ephemeral=True)
            return
        mode, chan = pref
        if mode == 'dm':
            emb = self._embed(title="Rappel", description="Mode: message privé à 8h")
            await interaction.followup.send(embed=emb, ephemeral=True)
        else:
            emb = self._embed(title="Rappel", description=f"Mode: salon (channel_id={chan}) à 8h")
            await interaction.followup.send(embed=emb, ephemeral=True)

    @group_bank.command(name="show", description="Afficher votre solde actuel")
    async def bank_show(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        balance = await self.service.get_balance(interaction.user.id)
        emb = self._embed(title="Solde actuel", description=format_cents(balance))
        await interaction.followup.send(embed=emb, ephemeral=True)

    @group_bank.command(name="set", description="Définir votre solde")
    @app_commands.describe(amount="Montant à définir (ex: 1000.00)")
    async def bank_set(self, interaction: discord.Interaction, amount: str):
        await interaction.response.defer(ephemeral=True)
        cents = parse_amount_to_cents(amount)
        await self.service.set_balance(interaction.user.id, cents)
        emb = self._embed(title="Nouveau solde", description=format_cents(cents), color=self.SUCCESS_COLOR)
        await interaction.followup.send(embed=emb, ephemeral=True)

    @group_bank.command(name="add", description="Ajouter au solde")
    @app_commands.describe(amount="Montant à ajouter (ex: 50)")
    async def bank_add(self, interaction: discord.Interaction, amount: str):
        await interaction.response.defer(ephemeral=True)
        delta = parse_amount_to_cents(amount)
        new_balance = await self.service.add_to_balance(interaction.user.id, delta)
        emb = self._embed(title="Solde mis à jour", description=format_cents(new_balance), color=self.SUCCESS_COLOR)
        await interaction.followup.send(embed=emb, ephemeral=True)

    @group_bank.command(name="sub", description="Retirer du solde")
    @app_commands.describe(amount="Montant à retirer (ex: 25.50)")
    async def bank_sub(self, interaction: discord.Interaction, amount: str):
        await interaction.response.defer(ephemeral=True)
        delta = parse_amount_to_cents(amount)
        new_balance = await self.service.sub_from_balance(interaction.user.id, delta)
        emb = self._embed(title="Solde mis à jour", description=format_cents(new_balance), color=self.SUCCESS_COLOR)
        await interaction.followup.send(embed=emb, ephemeral=True)

    @tasks.loop(minutes=1)
    async def reminder_task(self):
        now = datetime.now()
        # Apply automatic subscription deductions at 00:05 to avoid rate limits and ensure once per day
        if now.minute == 5 and now.hour == 0:
            try:
                await self.service.ensure_schema()
                await self.service.apply_due_subscriptions_for_today()
            except Exception:
                pass
        if now.minute != 0 or now.hour != 8:
            return
        prefs = await self.service.list_reminder_prefs()
        if prefs:
            for user_id, mode, channel_id in prefs:
                try:
                    total, subs_due, mans = await self.service.remaining_for_month(user_id)
                    lines = ["Rappel budget:"]
                    if subs_due:
                        lines.append("- Abonnements à venir:")
                        for name, cents, dom in subs_due:
                            lines.append(f"  • {name} le {dom}: {format_cents(cents)}")
                    if mans:
                        lines.append("- Dépenses à payer:")
                        for name, cents, due in mans:
                            lines.append(f"  • {name} pour le {due}: {format_cents(cents)}")
                    lines.append(f"Total restant ce mois: {format_cents(total)}")
                    msg = "\n".join(lines)
                    if mode == 'dm':
                        user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(int(user_id))
                        if user:
                            await user.send(msg)
                    elif mode == 'channel' and channel_id:
                        ch = self.bot.get_channel(int(channel_id))
                        if isinstance(ch, (discord.TextChannel, discord.Thread)):
                            await ch.send(f"<@{user_id}>\n" + msg)
                except Exception:
                    continue
            return
        if not self.morning_channel_id:
            return
        channel = self.bot.get_channel(self.morning_channel_id)
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return
        await channel.send(
            "Rappel budget: utilisez /reste pour voir ce qu'il reste à payer, /sub list et /pay list pour les détails.")

    @reminder_task.before_loop
    async def before_reminder(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    cog = Budget(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.group_sub)
    bot.tree.add_command(cog.group_pay)
    bot.tree.add_command(cog.group_bank)
    bot.tree.add_command(cog.group_reminder)
