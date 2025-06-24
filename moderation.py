import discord
import re
import asyncio
from discord.ext import commands
from discord.ext.commands import Context
from typing import Optional

MUTE_ROLE_NAME = "Muet"
MUTE_CHANNEL_ID = 1385941788329508874
BAN_CHANNEL_ID = 1385941862921146519
KICK_CHANNEL_ID = 1385941957506891918
DERANK_CHANNEL_ID = 1385942093754798201

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_sanction_log(self, *, guild: discord.Guild, channel_id: int, member: discord.Member, author: discord.Member, sanction_type: str, reason: str, duration: str = None):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title=f"\U0001F514 Sanction : {sanction_type}",
            description=f"**Membre sanctionné :** {member.mention}\n"
                        f"**Sanctionné par :** {author.mention}\n"
                        f"**Raison :** {reason}",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Serveur : {guild.name}")
        embed.timestamp = discord.utils.utcnow()

        if duration:
            embed.add_field(name="Durée", value=duration, inline=False)

        await channel.send(embed=embed)

    async def get_or_create_mute_role(self, guild: discord.Guild):
        muted_role = discord.utils.get(guild.roles, name=MUTE_ROLE_NAME)
        if not muted_role:
            try:
                muted_role = await guild.create_role(name=MUTE_ROLE_NAME, reason="Création automatique du rôle Muet")
                for channel in guild.channels:
                    await channel.set_permissions(muted_role, send_messages=False, speak=False, add_reactions=False)
            except discord.Forbidden:
                return None
        return muted_role

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def massrole(self, ctx: Context, role: discord.Role, target: str):
        if role >= ctx.guild.me.top_role:
            return await ctx.send("❌ Je ne peux pas gérer ce rôle.")

        if target.lower() not in ["all", "bot", "human"]:
            return await ctx.send("❌ Cible invalide. Utilise : `all`, `bot` ou `human`.")

        members = ctx.guild.members if target == "all" else [m for m in ctx.guild.members if m.bot == (target == "bot")]
        count_added = count_removed = 0
        msg = await ctx.send(f"⏳ Modification des rôles pour `{len(members)}` membres...")

        for member in members:
            try:
                if role in member.roles:
                    await member.remove_roles(role, reason="massrole command")
                    count_removed += 1
                else:
                    await member.add_roles(role, reason="massrole command")
                    count_added += 1
            except discord.Forbidden:
                continue

        await msg.edit(content=f"✅ Rôle `{role.name}` mis à jour :\n➕ Ajouté à {count_added} membres\n➖ Retiré de {count_removed} membres")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx: Context, member: discord.Member, role: discord.Role):
        if role in member.roles:
            return await ctx.send(f"{member.mention} a déjà le rôle {role.name}.")
        await member.add_roles(role, reason=f"Ajout par {ctx.author}")
        await ctx.send(f"✅ {role.name} ajouté à {member.mention}.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def delrole(self, ctx: Context, member: discord.Member, role: discord.Role):
        if role not in member.roles:
            return await ctx.send(f"{member.mention} n'a pas le rôle {role.name}.")
        await member.remove_roles(role, reason=f"Retrait par {ctx.author}")
        await ctx.send(f"✅ {role.name} retiré de {member.mention}.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx: Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
        await ctx.send("🔒 Ce salon a été caché.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unhide(self, ctx: Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
        await ctx.send("🔓 Ce salon est maintenant visible.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 Salon verrouillé.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("🔓 Salon déverrouillé.")

    @commands.command(aliases=["purge"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: Context, amount: int):
        if amount <= 0:
            return await ctx.send("❌ Le nombre doit être supérieur à 0.")
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"🧹 {len(deleted) - 1} messages supprimés.", delete_after=5)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: Context, member: discord.Member, *, reason="Aucune raison donnée."):
        await member.kick(reason=reason)
        await ctx.send(f"✅ {member} a été **expulsé** pour : {reason}")
        await self.send_sanction_log(guild=ctx.guild, channel_id=KICK_CHANNEL_ID, member=member, author=ctx.author, sanction_type="Expulsion", reason=reason)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: Context, member: discord.Member, *, reason="Aucune raison donnée."):
        await member.ban(reason=reason)
        await ctx.send(f"✅ {member} a été **banni** pour : {reason}")
        await self.send_sanction_log(guild=ctx.guild, channel_id=BAN_CHANNEL_ID, member=member, author=ctx.author, sanction_type="Bannissement", reason=reason)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: Context, *, user):
        try:
            name, discriminator = user.split("#")
        except ValueError:
            return await ctx.send("❌ Format invalide. Utilise `Nom#1234`.")

        banned_users = await ctx.guild.bans()
        for ban in banned_users:
            if (ban.user.name, ban.user.discriminator) == (name, discriminator):
                await ctx.guild.unban(ban.user)
                await ctx.send(f"✅ {ban.user} a été **débanni**.")
                return
        await ctx.send("❌ Utilisateur non trouvé.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx: Context, duration: str, member: discord.Member):
        muted_role = await self.get_or_create_mute_role(ctx.guild)
        if not muted_role:
            return await ctx.send("❌ Impossible de créer/trouver le rôle Muet.")

        if muted_role in member.roles:
            return await ctx.send(f"❌ {member.mention} est déjà muet.")

        match = re.match(r"^(\d+)([smhd])$", duration)
        if not match:
            return await ctx.send("❌ Format invalide. Utilise s, m, h, d (ex: `10m`).")

        amount, unit = match.groups()
        seconds = int(amount) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]

        await member.add_roles(muted_role, reason=f"Tempmute {duration} par {ctx.author}")
        await ctx.send(f"🔇 {member.mention} a été **muet pour {duration}**.")

        await self.send_sanction_log(guild=ctx.guild, channel_id=MUTE_CHANNEL_ID, member=member, author=ctx.author, sanction_type="Mute Temporaire", reason="Tempmute", duration=duration)

        await asyncio.sleep(seconds)

        if muted_role in member.roles:
            await member.remove_roles(muted_role, reason="Fin du tempmute")
            await self.send_sanction_log(guild=ctx.guild, channel_id=MUTE_CHANNEL_ID, member=member, author=self.bot.user, sanction_type="Fin de Mute", reason=f"Durée écoulée : {duration}")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx: Context, member: discord.Member):
        muted_role = discord.utils.get(ctx.guild.roles, name=MUTE_ROLE_NAME)
        if not muted_role or muted_role not in member.roles:
            return await ctx.send("❌ Ce membre n'est pas muet.")
        await member.remove_roles(muted_role, reason=f"Unmute par {ctx.author}")
        await ctx.send(f"🔊 {member.mention} a été **unmuet**.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def derank(self, ctx: Context, member: discord.Member):
        mute_role = await self.get_or_create_mute_role(ctx.guild)
        roles_to_remove = [r for r in member.roles if r != ctx.guild.default_role and r != mute_role]

        if not roles_to_remove:
            return await ctx.send("❌ Aucun rôle à retirer.")

        await member.remove_roles(*roles_to_remove, reason=f"Derank par {ctx.author}")
        await ctx.send(f"✅ Tous les rôles de {member.mention} ont été retirés.")
        await self.send_sanction_log(guild=ctx.guild, channel_id=DERANK_CHANNEL_ID, member=member, author=ctx.author, sanction_type="Derank", reason="Tous les rôles retirés sauf @everyone et Muet")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def renew(self, ctx: Context, channel: Optional[discord.TextChannel] = None):
        channel = channel or ctx.channel
        guild = ctx.guild

        overwrites = channel.overwrites
        name = channel.name
        category = channel.category
        topic = getattr(channel, 'topic', None)
        nsfw = getattr(channel, 'nsfw', False)
        slowmode_delay = getattr(channel, 'slowmode_delay', 0)

        await channel.delete(reason=f"Renew command by {ctx.author}")
        new_channel = await guild.create_text_channel(name=name, overwrites=overwrites, category=category, topic=topic, nsfw=nsfw, slowmode_delay=slowmode_delay, reason=f"Renew command by {ctx.author}")
        await ctx.send(f"✅ Salon {name} a été recréé : {new_channel.mention}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))