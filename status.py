import discord
from discord.ext import commands, tasks
import datetime
import psutil
import time

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_launch_time = time.time()
        self.status_loop.start()

    def cog_unload(self):
        self.status_loop.cancel()

    @tasks.loop(hours=1)
    async def status_loop(self):
        await self.send_status()

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()
        # NE PAS envoyer de message ici

    async def send_status(self):
        channel_id = 1386704026636386334  # Remplace par ton ID
        channel = self.bot.get_channel(channel_id)
        if not channel:
            print("⚠️ Salon introuvable.")
            return

        uptime_seconds = int(time.time() - self.bot_launch_time)
        uptime_str = str(datetime.timedelta(seconds=uptime_seconds))

        embed = discord.Embed(
            title="✅ Le bot est en ligne",
            description=f"⏱️ Uptime : `{uptime_str}`",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Mise à jour automatique toutes les heures")

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))