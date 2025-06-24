import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os

STARBOARD_CHANNEL_ID = 1385586183844663366
STATS_FILE = "data/stats.json"

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_stats = defaultdict(lambda: defaultdict(int))
        self.voice_stats = defaultdict(lambda: defaultdict(int))
        self.voice_tracking = {}
        self.join_logs = defaultdict(list)
        self.leave_logs = defaultdict(list)

        self.load_stats()

        self.save_loop.start()
        # NE PAS démarrer la boucle starboard ici pour éviter les erreurs au démarrage

    def load_stats(self):
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r") as f:
                data = json.load(f)
                self.message_stats.update({
                    k: defaultdict(int, v) for k, v in data.get("message", {}).items()
                })
                self.voice_stats.update({
                    k: defaultdict(int, v) for k, v in data.get("voice", {}).items()
                })

    def save_stats(self):
        data = {
            "message": {k: dict(v) for k, v in self.message_stats.items()},
            "voice": {k: dict(v) for k, v in self.voice_stats.items()}
        }
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @tasks.loop(minutes=2)
    async def save_loop(self):
        self.save_stats()

    async def send_starboard(self):
        channel = self.bot.get_channel(STARBOARD_CHANNEL_ID)
        if not channel:
            print(f"[Stats] Channel {STARBOARD_CHANNEL_ID} introuvable ou inaccessible.")
            return

        embed = discord.Embed(
            title="🌟 Starboard Global",
            description="Classement général des serveurs (messages, vocal, membres)",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        for guild in self.bot.guilds:
            gid = str(guild.id)
            msg_count = sum(self.message_stats.get(gid, {}).values())
            voc_sec = sum(self.voice_stats.get(gid, {}).values())
            voc_time = str(timedelta(seconds=voc_sec))

            now = datetime.utcnow()
            joined = sum(1 for t in self.join_logs[gid] if now - datetime.fromisoformat(t) <= timedelta(days=14))
            left = sum(1 for t in self.leave_logs[gid] if now - datetime.fromisoformat(t) <= timedelta(days=14))

            embed.add_field(
                name=f"🛡️ {guild.name}",
                value=(
                    f"💬 Messages : `{msg_count}`\n"
                    f"🎙️ Vocal : `{voc_time}`\n"
                    f"📥 Rejoints (14j) : `{joined}`\n"
                    f"📤 Quittés (14j) : `{left}`"
                ),
                inline=False
            )

        await channel.send(embed=embed)

    @tasks.loop(hours=1)
    async def starboard_loop(self):
        await self.send_starboard()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.starboard_loop.is_running():
            self.starboard_loop.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return
        gid = str(message.guild.id)
        uid = str(message.author.id)
        self.message_stats[gid][uid] += 1

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.guild is None:
            return
        uid = str(member.id)
        gid = str(member.guild.id)

        if before.channel is None and after.channel is not None:
            self.voice_tracking[uid] = datetime.utcnow().isoformat()

        elif before.channel is not None and after.channel is None:
            if uid in self.voice_tracking:
                start_time = datetime.fromisoformat(self.voice_tracking.pop(uid))
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.voice_stats[gid][uid] += int(duration)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild:
            self.join_logs[str(member.guild.id)].append(datetime.utcnow().isoformat())

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild:
            self.leave_logs[str(member.guild.id)].append(datetime.utcnow().isoformat())

    @commands.command(name="m", help="Top 10 messages")
    async def top_messages(self, ctx):
        gid = str(ctx.guild.id)
        data = self.message_stats.get(gid, {})
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

        embed = discord.Embed(title="🏆 Top Messages", color=discord.Color.blue())
        for i, (uid, count) in enumerate(sorted_data, 1):
            user = ctx.guild.get_member(int(uid))
            embed.add_field(name=f"{i}. {user.display_name if user else uid}", value=f"{count} messages", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="v", help="Top 10 vocal")
    async def top_voice(self, ctx):
        gid = str(ctx.guild.id)
        data = self.voice_stats.get(gid, {})
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

        embed = discord.Embed(title="🎙️ Top Vocal", color=discord.Color.orange())
        for i, (uid, seconds) in enumerate(sorted_data, 1):
            user = ctx.guild.get_member(int(uid))
            duration = timedelta(seconds=int(seconds))
            embed.add_field(name=f"{i}. {user.display_name if user else uid}", value=str(duration), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="u", help="Stats d'un utilisateur")
    async def user_stats(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        gid = str(ctx.guild.id)
        uid = str(member.id)

        msg = self.message_stats.get(gid, {}).get(uid, 0)
        voc = self.voice_stats.get(gid, {}).get(uid, 0)

        embed = discord.Embed(title=f"📊 Stats de {member.display_name}", color=discord.Color.green())
        embed.add_field(name="Messages", value=f"{msg} messages")
        embed.add_field(name="Vocal", value=str(timedelta(seconds=voc)))

        await ctx.send(embed=embed)

    @commands.command(name="t", help="Stats globales serveur")
    async def total_stats(self, ctx):
        gid = str(ctx.guild.id)
        msgs = sum(self.message_stats.get(gid, {}).values())
        vocs = sum(self.voice_stats.get(gid, {}).values())

        embed = discord.Embed(title="📈 Stats Globales", color=discord.Color.purple())
        embed.add_field(name="Total Messages", value=str(msgs))
        embed.add_field(name="Total Vocal", value=str(timedelta(seconds=vocs)))

        await ctx.send(embed=embed)

    @commands.command(name="forcestarboard", help="Force l'envoi du starboard")
    @commands.has_permissions(administrator=True)
    async def forcestarboard(self, ctx):
        await self.send_starboard()
        await ctx.send("✅ Starboard envoyé.")

async def setup(bot):
    await bot.add_cog(Stats(bot))