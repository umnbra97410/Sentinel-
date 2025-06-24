import discord
from discord.ext import commands
import os
import json
import datetime

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = "log_data"
        os.makedirs(self.data_folder, exist_ok=True)
        self.log_channels = self.load_all_logs()

        # Cache des invites par serveur
        self.invites = {}

        # Lance la tâche asynchrone pour cache les invites au démarrage
        self.bot.loop.create_task(self.cache_invites())

    async def cache_invites(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except (discord.Forbidden, discord.HTTPException):
                self.invites[guild.id] = []

    def get_log_channel(self, guild: discord.Guild, category: str):
        guild_channels = self.log_channels.get(str(guild.id), {})
        channel_id = guild_channels.get(category)
        if channel_id:
            return guild.get_channel(channel_id)
        return None

    def format_time(self):
        return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    def get_guild_filepath(self, guild_id):
        return os.path.join(self.data_folder, f"{guild_id}.json")

    def load_all_logs(self):
        data = {}
        for filename in os.listdir(self.data_folder):
            if filename.endswith(".json"):
                with open(os.path.join(self.data_folder, filename), "r") as f:
                    guild_id = filename.replace(".json", "")
                    data[guild_id] = json.load(f)
        return data

    def save_logs(self, guild_id):
        filepath = self.get_guild_filepath(guild_id)
        with open(filepath, "w") as f:
            json.dump(self.log_channels[str(guild_id)], f, indent=4)

    @commands.command(name="setlogs", help="Définit le salon pour une catégorie de logs")
    @commands.has_permissions(administrator=True)
    async def setlogs(self, ctx, category: str, channel: discord.TextChannel):
        category = category.lower()
        guild_id_str = str(ctx.guild.id)
        if guild_id_str not in self.log_channels:
            self.log_channels[guild_id_str] = {}

        self.log_channels[guild_id_str][category] = channel.id
        self.save_logs(ctx.guild.id)

        await ctx.send(f"✅ Salon de logs pour `{category}` défini sur {channel.mention}")

    @commands.command(name="showlogs", help="Affiche les salons de logs configurés")
    @commands.has_permissions(administrator=True)
    async def showlogs(self, ctx):
        guild_id_str = str(ctx.guild.id)
        guild_logs = self.log_channels.get(guild_id_str, {})
        categories = ["message", "ban", "mute", "role", "member", "emoji", "sticker", "channel", "server", "invites"]
        embed = discord.Embed(title="📋 Configuration des logs", color=discord.Color.blue())

        for cat in categories:
            channel_id = guild_logs.get(cat)
            channel_mention = ctx.guild.get_channel(channel_id).mention if channel_id else "*non défini*"
            embed.add_field(name=cat.capitalize(), value=channel_mention, inline=True)

        embed.set_footer(text="Utilisez la commande !setlogs <catégorie> <#salon> pour définir un salon.")
        await ctx.send(embed=embed)

    # ---------- Listeners ----------

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        channel = self.get_log_channel(message.guild, "message")
        if channel:
            embed = discord.Embed(title="🗑️ Message supprimé", color=discord.Color.red())
            embed.add_field(name="Auteur", value=message.author.mention)
            embed.add_field(name="Salon", value=message.channel.mention)
            embed.add_field(name="Contenu", value=message.content or "*vide*")
            embed.set_footer(text=self.format_time())
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
        channel = self.get_log_channel(before.guild, "message")
        if channel:
            embed = discord.Embed(title="✏️ Message édité", color=discord.Color.orange())
            embed.add_field(name="Auteur", value=before.author.mention, inline=False)
            embed.add_field(name="Avant", value=before.content or "*vide*", inline=False)
            embed.add_field(name="Après", value=after.content or "*vide*", inline=False)
            embed.add_field(name="Salon", value=before.channel.mention)
            embed.set_footer(text=self.format_time())
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        channel = self.get_log_channel(guild, "ban")
        if channel:
            embed = discord.Embed(title="🔨 Membre banni", color=discord.Color.dark_red())
            embed.add_field(name="Utilisateur", value=f"{user} ({user.id})")
            embed.set_footer(text=self.format_time())
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        channel = self.get_log_channel(guild, "ban")
        if channel:
            embed = discord.Embed(title="✅ Membre débanni", color=discord.Color.green())
            embed.add_field(name="Utilisateur", value=f"{user} ({user.id})")
            embed.set_footer(text=self.format_time())
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            channel = self.get_log_channel(after.guild, "mute")  # catégorie mute
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]

            mute_role_names = ["Muted", "Mute"]  # à adapter

            added_mute = [r for r in added if r.name in mute_role_names]
            removed_mute = [r for r in removed if r.name in mute_role_names]

            if channel and (added_mute or removed_mute):
                embed = discord.Embed(title="🔇 Changement de mute", color=discord.Color.dark_gray())
                embed.add_field(name="Membre", value=after.mention, inline=False)
                if added_mute:
                    embed.add_field(name="🔇 Muté", value=", ".join(r.mention for r in added_mute), inline=False)
                if removed_mute:
                    embed.add_field(name="🔊 Unmute", value=", ".join(r.mention for r in removed_mute), inline=False)
                embed.set_footer(text=self.format_time())
                await channel.send(embed=embed)
            else:
                channel_roles = self.get_log_channel(after.guild, "role")
                if channel_roles:
                    added_roles = [r for r in added if r.name not in mute_role_names]
                    removed_roles = [r for r in removed if r.name not in mute_role_names]
                    if added_roles or removed_roles:
                        embed = discord.Embed(title="🎭 Changement de rôle", color=discord.Color.purple())
                        embed.add_field(name="Membre", value=after.mention, inline=False)
                        if added_roles:
                            embed.add_field(name="✅ Ajouté", value=", ".join([r.mention for r in added_roles]), inline=False)
                        if removed_roles:
                            embed.add_field(name="❌ Retiré", value=", ".join([r.mention for r in removed_roles]), inline=False)
                        embed.set_footer(text=self.format_time())
                        await channel_roles.send(embed=embed)

        # Log pseudo et avatar modifiés
        if before.display_name != after.display_name or before.avatar != after.avatar:
            channel = self.get_log_channel(after.guild, "member")
            if channel:
                embed = discord.Embed(title="📝 Membre modifié", color=discord.Color.teal())
                embed.add_field(name="Utilisateur", value=after.mention)
                if before.display_name != after.display_name:
                    embed.add_field(name="Pseudo", value=f"`{before.display_name}` → `{after.display_name}`", inline=False)
                if before.avatar != after.avatar:
                    before_avatar = before.avatar.url if before.avatar else "Aucun"
                    after_avatar = after.avatar.url if after.avatar else "Aucun"
                    embed.set_image(url=after_avatar)
                    embed.add_field(name="Avatar modifié", value="[Voir nouvel avatar]({})".format(after_avatar), inline=False)
                embed.set_footer(text=self.format_time())
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = self.get_log_channel(member.guild, "member")
        if channel:
            embed = discord.Embed(title="👢 Membre quitté ou kick", color=discord.Color.gold())
            embed.add_field(name="Utilisateur", value=f"{member} ({member.id})")
            embed.set_footer(text=self.format_time())
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        channel = self.get_log_channel(guild, "emoji")
        if channel:
            added = [e for e in after if e not in before]
            removed = [e for e in before if e not in after]
            for e in added:
                embed = discord.Embed(title="🆕 Emoji ajouté", description=f"{e} ({e.name})", color=discord.Color.green())
                embed.set_footer(text=self.format_time())
                await channel.send(embed=embed)
            for e in removed:
                embed = discord.Embed(title="❌ Emoji supprimé", description=f"{e.name}", color=discord.Color.red())
                embed.set_footer(text=self.format_time())
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):
        channel = self.get_log_channel(guild, "sticker")
        if channel:
            added = [s for s in after if s not in before]
            removed = [s for s in before if s not in after]
            for s in added:
                embed = discord.Embed(title="🆕 Sticker ajouté", description=f"{s.name}", color=discord.Color.green())
                embed.set_footer(text=self.format_time())
                await channel.send(embed=embed)
            for s in removed:
                embed = discord.Embed(title="❌ Sticker supprimé", description=f"{s.name}", color=discord.Color.red())
                embed.set_footer(text=self.format_time())
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_channel = self.get_log_channel(channel.guild, "channel")
        if log_channel:
            embed = discord.Embed(title="📁 Nouveau salon créé", description=channel.mention, color=discord.Color.green())
            embed.set_footer(text=self.format_time())
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_channel = self.get_log_channel(channel.guild, "channel")
        if log_channel:
            embed = discord.Embed(title="🗑️ Salon supprimé", description=channel.name, color=discord.Color.red())
            embed.set_footer(text=self.format_time())
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        log_channel = self.get_log_channel(after.guild, "channel")
        if not log_channel:
            return

        embed = discord.Embed(title="✏️ Salon modifié", color=discord.Color.blue())
        changes = []

        # Changement de nom
        if before.name != after.name:
            changes.append(f"Nom : `{before.name}` → `{after.name}`")

        # Changement de topic (uniquement si TextChannel)
        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            before_topic = before.topic or "Aucun"
            after_topic = after.topic or "Aucun"
            if before_topic != after_topic:
                changes.append(f"Topic : `{before_topic}` → `{after_topic}`")

        # Changement de position
        if before.position != after.position:
            changes.append(f"Position : `{before.position}` → `{after.position}`")

        # Changement de type
        if before.type != after.type:
            changes.append(f"Type : `{before.type.name}` → `{after.type.name}`")

        if changes:
            embed.description = "\n".join(changes)
            embed.set_footer(text=self.format_time())
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # Cacher les invites quand on rejoint un serveur
        try:
            self.invites[guild.id] = await guild.invites()
        except (discord.Forbidden, discord.HTTPException):
            self.invites[guild.id] = []

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.get_log_channel(member.guild, "member")
        if not channel:
            return

        # Tentative de récupérer qui a invité le membre
        inviter = None
        try:
            invites_before = self.invites.get(member.guild.id, [])
            invites_after = await member.guild.invites()
            self.invites[member.guild.id] = invites_after

            for inv_before in invites_before:
                inv_after = discord.utils.get(invites_after, code=inv_before.code)
                if inv_after and inv_after.uses > inv_before.uses:
                    inviter = inv_after.inviter
                    break
        except (discord.Forbidden, discord.HTTPException):
            pass

        embed = discord.Embed(title="👋 Nouveau membre", color=discord.Color.green())
        embed.add_field(name="Membre", value=member.mention)
        embed.add_field(name="Date d'arrivée", value=self.format_time())
        if inviter:
            embed.add_field(name="Invité par", value=inviter.mention)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))