import discord
from discord.ext import commands

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo", aliases=["whois"])
    async def user_info(self, ctx, member: discord.Member = None):
        """Affiche des infos détaillées sur un utilisateur"""
        member = member or ctx.author

        embed = discord.Embed(
            title=f"Informations sur {member}",
            color=member.color if member.color.value else discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="🆔 ID", value=member.id, inline=True)
        embed.add_field(name="🗓 Créé le", value=member.created_at.strftime('%d/%m/%Y %H:%M:%S'), inline=True)
        embed.add_field(name="📥 Rejoint le serveur", value=member.joined_at.strftime('%d/%m/%Y %H:%M:%S') if member.joined_at else "Inconnu", inline=True)

        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
        embed.add_field(name=f"📛 Rôles ({len(roles)})", value=", ".join(roles) if roles else "Aucun", inline=False)

        embed.add_field(name="💠 Statut", value=str(member.status).capitalize(), inline=True)

        activity = member.activity.name if member.activity else "Aucune"
        embed.add_field(name="🎮 Activité", value=activity, inline=True)

        badges = []
        # Extraction des badges
        flags = member.public_flags
        for badge_name, has_badge in flags:
            if has_badge:
                badges.append(badge_name.replace("_", " ").title())

        # Une méthode compatible alternative
        badges = []
        for flag, value in vars(flags).items():
            if value and not flag.startswith('_'):
                badges.append(flag.replace("_", " ").title())

        embed.add_field(name="🏅 Badges", value=", ".join(badges) if badges else "Aucun", inline=False)

        if member.premium_since:
            embed.add_field(name="🚀 Boost le serveur depuis", value=member.premium_since.strftime('%d/%m/%Y %H:%M:%S'), inline=False)

        # Bannière via API brute
        try:
            user_data = await self.bot.http.request(discord.http.Route("GET", f"/users/{member.id}"))
            banner = user_data.get("banner")
            if banner:
                ext = "gif" if banner.startswith("a_") else "png"
                url = f"https://cdn.discordapp.com/banners/{member.id}/{banner}.{ext}?size=1024"
                embed.set_image(url=url)
                embed.add_field(name="🖼 Bannière", value=f"[Voir]({url})", inline=False)
        except Exception:
            pass

        await ctx.send(embed=embed)

    @commands.command(name="serverinfo")
    async def server_info(self, ctx):
        """Affiche des infos sur le serveur"""
        guild = ctx.guild
        embed = discord.Embed(title=f"Infos sur {guild.name}", color=discord.Color.green())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)

        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        embed.add_field(name="👑 Propriétaire", value=str(guild.owner), inline=True)
        embed.add_field(name="🗓 Créé le", value=guild.created_at.strftime('%d/%m/%Y %H:%M:%S'), inline=True)

        embed.add_field(name="👥 Membres", value=guild.member_count, inline=True)
        embed.add_field(name="💬 Textuels", value=len(guild.text_channels), inline=True)
        embed.add_field(name="🔊 Vocaux", value=len(guild.voice_channels), inline=True)
        embed.add_field(name="📂 Catégories", value=len(guild.categories), inline=True)

        embed.add_field(name="🧩 Rôles", value=len(guild.roles), inline=True)
        embed.add_field(name="🎭 Emojis", value=len(guild.emojis), inline=True)
        embed.add_field(name="🚀 Boosts", value=guild.premium_subscription_count, inline=True)
        embed.add_field(name="💎 Niveau de boost", value=guild.premium_tier, inline=True)

        if guild.banner:
            embed.set_image(url=guild.banner.url)
            embed.add_field(name="🖼 Bannière du serveur", value=f"[Voir]({guild.banner.url})", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="avatar")
    async def avatar(self, ctx, member: discord.Member = None):
        """Affiche l'avatar d'un utilisateur"""
        member = member or ctx.author
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url

        embed = discord.Embed(title=f"Avatar de {member}", color=discord.Color.blurple())
        embed.set_image(url=avatar_url)

        await ctx.send(embed=embed)

    @commands.command(name="serverbanner")
    async def server_banner(self, ctx):
        """Affiche la bannière du serveur"""
        if ctx.guild.banner:
            await ctx.send(f"Bannière du serveur : {ctx.guild.banner.url}")
        else:
            await ctx.send("🚫 Ce serveur n'a pas de bannière.")

    @commands.command(name="serveravatar")
    async def server_avatar(self, ctx):
        """Affiche l'avatar du serveur"""
        if ctx.guild.icon:
            await ctx.send(f"Avatar du serveur : {ctx.guild.icon.url}")
        else:
            await ctx.send("🚫 Ce serveur n'a pas d'avatar.")

    @commands.command(name="banner")
    async def user_banner(self, ctx, member: discord.Member = None):
        """Affiche la bannière d’un utilisateur"""
        member = member or ctx.author
        try:
            user_data = await self.bot.http.request(discord.http.Route("GET", f"/users/{member.id}"))
            banner = user_data.get("banner")
            if banner:
                ext = "gif" if banner.startswith("a_") else "png"
                url = f"https://cdn.discordapp.com/banners/{member.id}/{banner}.{ext}?size=1024"
                await ctx.send(f"Bannière de {member.mention} : {url}")
            else:
                await ctx.send("🚫 Cet utilisateur n'a pas de bannière.")
        except Exception:
            await ctx.send("❌ Impossible de récupérer la bannière.")
            
    @commands.command(name="support")
    async def support(self, ctx):
        """Affiche le lien vers le serveur de support"""
        embed = discord.Embed(
            title="🛠️ Besoin d’aide ?",
            description=(
                "🤖 Bonjour ! Je suis ton assistant virtuel, toujours prêt à t’aider.\n\n"
                "Pour toute **question**, **problème** ou **suggestion**, rejoins notre **serveur support** !\n"
                "Notre équipe dédiée et notre communauté active sont là pour te répondre rapidement et t’accompagner.\n\n"
                "💡 N’hésite pas à venir discuter, partager tes idées ou signaler un bug.\n\n"
                f"[Rejoins-nous ici](https://discord.gg/DqsGFu8Wqw)"
            ),
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Info(bot))