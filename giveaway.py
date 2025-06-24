import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime, timedelta
import random

GIVEAWAYS_FILE = "giveaways.json"

def save_giveaways(data):
    with open(GIVEAWAYS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_giveaways():
    if not os.path.exists(GIVEAWAYS_FILE):
        return []
    with open(GIVEAWAYS_FILE, "r") as f:
        return json.load(f)

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaways = load_giveaways()
        self.active_tasks = {}
        self.bot.loop.create_task(self.restore_giveaways())

    async def restore_giveaways(self):
        await self.bot.wait_until_ready()
        now = datetime.utcnow()
        to_remove = []
        for giveaway in self.giveaways:
            end_time = datetime.fromisoformat(giveaway["end_time"])
            if end_time > now:
                delay = (end_time - now).total_seconds()
                self.active_tasks[giveaway["message_id"]] = self.bot.loop.create_task(
                    self.end_giveaway_task(
                        giveaway["guild_id"], giveaway["channel_id"], giveaway["message_id"], delay
                    )
                )
            else:
                to_remove.append(giveaway)
        for g in to_remove:
            self.giveaways.remove(g)
        if to_remove:
            save_giveaways(self.giveaways)

    @commands.command(help="Créer un giveaway : !giveaway <temps ex: 10s/5m/1h/2d> <emoji> <nombre de gagnants> [#salon] <titre>")
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx, time: str, emoji: str, winners: int, channel: discord.TextChannel = None, *, title: str):
        channel = channel or ctx.channel

        # Parse time avec gestion des jours 'd'
        try:
            amount = int(time[:-1])
            unit = time[-1].lower()
            if unit == "s":
                seconds = amount
            elif unit == "m":
                seconds = amount * 60
            elif unit == "h":
                seconds = amount * 3600
            elif unit == "d":
                seconds = amount * 86400
            else:
                return await ctx.send("❌ Format du temps invalide (ex: 10s, 5m, 1h, 2d)")
        except:
            return await ctx.send("❌ Format du temps invalide (ex: 10s, 5m, 1h, 2d)")

        embed = discord.Embed(title="🎉 Giveaway ! 🎉", description=title, color=discord.Color.gold())
        embed.add_field(name="Durée", value=time)
        embed.add_field(name="Nombre de gagnants", value=str(winners))
        embed.set_footer(text=f"Lancé par {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        message = await channel.send(embed=embed)
        await message.add_reaction(emoji)

        end_time = datetime.utcnow() + timedelta(seconds=seconds)
        giveaway_data = {
            "guild_id": ctx.guild.id,
            "channel_id": channel.id,
            "message_id": message.id,
            "title": title,
            "end_time": end_time.isoformat(),
            "emoji": emoji,
            "winners": winners,
            "creator_id": ctx.author.id
        }

        self.giveaways.append(giveaway_data)
        save_giveaways(self.giveaways)

        self.active_tasks[message.id] = self.bot.loop.create_task(
            self.end_giveaway_task(ctx.guild.id, channel.id, message.id, seconds)
        )

        await ctx.send(f"✅ Giveaway lancé dans {channel.mention} ! ID: {message.id}")

    async def end_giveaway_task(self, guild_id, channel_id, message_id, delay):
        await asyncio.sleep(delay)
        await self.end_giveaway_manual(guild_id, channel_id, message_id)

    async def end_giveaway_manual(self, guild_id, channel_id, message_id):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(message_id)
        except:
            return

        giveaway = next((g for g in self.giveaways if g["message_id"] == message_id), None)
        if not giveaway:
            return

        reaction = discord.utils.get(message.reactions, emoji=giveaway["emoji"])
        if not reaction:
            await channel.send("Aucune réaction trouvée, pas de gagnant.")
            return

        users = [user async for user in reaction.users() if not user.bot]
        if not users:
            await channel.send("Personne n'a participé au giveaway.")
            return

        winners_number = min(giveaway["winners"], len(users))
        winners = random.sample(users, winners_number)
        winner_mentions = ", ".join(w.mention for w in winners)

        embed = message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "🎉 Giveaway terminé ! 🎉"
        embed.description += f"\n\n🏆 Gagnant(s) : {winner_mentions}"

        await message.edit(embed=embed)
        await channel.send(f"🏆 Félicitations à : {winner_mentions} !")

        self.giveaways.remove(giveaway)
        save_giveaways(self.giveaways)

        task = self.active_tasks.pop(message_id, None)
        if task:
            task.cancel()

    @commands.command(help="Termine un giveaway manuellement : !end_giveaway <message_id>")
    @commands.has_permissions(manage_guild=True)
    async def end_giveaway(self, ctx, message_id: int):
        giveaway = next((g for g in self.giveaways if g["message_id"] == message_id), None)
        if not giveaway:
            return await ctx.send("Giveaway introuvable ou déjà terminé.")
        await self.end_giveaway_manual(giveaway["guild_id"], giveaway["channel_id"], message_id)
        await ctx.send(f"✅ Giveaway {message_id} terminé manuellement.")

    @commands.command(help="Relance un tirage pour un giveaway : !reroll <message_id>")
    @commands.has_permissions(manage_guild=True)
    async def reroll(self, ctx, message_id: int):
        await ctx.send("La fonction reroll n'est pas encore implémentée pour les giveaways terminés.")

async def setup(bot):
    await bot.add_cog(Giveaway(bot))