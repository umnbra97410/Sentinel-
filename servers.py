import discord
from discord.ext import commands, tasks

class ServerStatsVoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.support_server_id = 1374803429259608165  # Serveur support
        self.category_id = 1385859704017653812        # Catégorie des salons vocaux
        self.channels = {}
        self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

    @tasks.loop(minutes=5)
    async def update_stats(self):
        guild = self.bot.get_guild(self.support_server_id)
        if not guild:
            print("Serveur support introuvable.")
            return

        category = discord.utils.get(guild.categories, id=self.category_id)
        if not category:
            print("Catégorie introuvable.")
            return

        # Statistiques
        guild_count = len(self.bot.guilds)
        total_humans = sum(1 for g in self.bot.guilds for m in g.members if not m.bot)
        support_humans = sum(1 for m in guild.members if not m.bot)

        names = {
            "servers": f"📡 | Serveurs : {guild_count}",
            "total_members": f"🌍 | Membres Totaux : {total_humans}",
            "support_members": f"👥 | Membres Support : {support_humans}"
        }

        # Créer ou mettre à jour les salons vocaux
        for key, name in names.items():
            if key not in self.channels or not self.channels[key].guild:
                # Vérifie si un salon existe déjà
                existing = discord.utils.find(
                    lambda c: c.name.startswith(name.split()[0]) and c.category_id == category.id,
                    guild.voice_channels
                )
                if existing:
                    self.channels[key] = existing
                    if existing.name != name:
                        await existing.edit(name=name)
                else:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(connect=False),
                        guild.me: discord.PermissionOverwrite(connect=True)
                    }
                    channel = await guild.create_voice_channel(name, overwrites=overwrites, category=category)
                    self.channels[key] = channel
            else:
                if self.channels[key].name != name:
                    await self.channels[key].edit(name=name)

    @update_stats.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(ServerStatsVoiceChannels(bot))