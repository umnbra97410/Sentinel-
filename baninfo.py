import discord
from discord.ext import commands

GUILD_ID = your server
DEMANDE_BAN_CHANNEL_ID = your channel ban
REVOQUE_BAN_CHANNEL_ID = your channel revoke ban

class BanManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="demandeban", help= "Demande de ban (Serveur Support)")
    async def demande_ban(self, ctx, user: discord.User, *, raison: str = "Aucune raison fournie"):
        """Demande un ban avec une preuve"""
        if not ctx.message.attachments:
            return await ctx.send("❌ Merci de joindre une **preuve (image)** en pièce jointe.")

        preuve_url = ctx.message.attachments[0].url
        salon = self.bot.get_channel(DEMANDE_BAN_CHANNEL_ID)
        if not salon:
            return await ctx.send("❌ Le salon de demande de ban est introuvable.")

        embed = discord.Embed(title="🚨 Nouvelle demande de ban", color=discord.Color.red(), timestamp=ctx.message.created_at)
        embed.add_field(name="👤 Utilisateur visé", value=f"{user.mention} (`{user.id}`)", inline=False)
        embed.add_field(name="📝 Raison", value=raison, inline=False)
        embed.add_field(name="📨 Demandé par", value=ctx.author.mention, inline=False)
        embed.set_image(url=preuve_url)

        await salon.send(embed=embed)
        await ctx.send("✅ Demande de ban envoyée avec succès.")

    @commands.command(name="revoqueban", help= "Demande de deban (Serveur Support)")
    async def revoque_ban(self, ctx, user_id: int):
        """Demande de révoque d’un ban"""
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return await ctx.send("❌ Serveur introuvable.")

        try:
            bans = [entry async for entry in guild.bans()]
        except discord.Forbidden:
            return await ctx.send("❌ Permission refusée pour lire les bans.")
        except discord.HTTPException:
            return await ctx.send("❌ Erreur lors de la récupération des bans.")

        ban_entry = discord.utils.find(lambda b: b.user.id == user_id, bans)
        if not ban_entry:
            return await ctx.send("❌ Cet utilisateur n'est pas banni.")

        user = ban_entry.user
        raison_ban = ban_entry.reason or "Aucune raison précisée"
        salon = self.bot.get_channel(REVOQUE_BAN_CHANNEL_ID)
        if not salon:
            return await ctx.send("❌ Le salon de révoque est introuvable.")

        embed = discord.Embed(title="📩 Demande de révoque de ban", color=discord.Color.green(), timestamp=ctx.message.created_at)
        embed.add_field(name="👤 Utilisateur", value=f"{user.mention} (`{user.id}`)", inline=False)
        embed.add_field(name="🔒 Raison du ban", value=raison_ban, inline=False)
        embed.add_field(name="📨 Demandé par", value=ctx.author.mention, inline=False)
        embed.set_footer(text="⚠️ 10 👍 nécessaires pour débannir automatiquement.")

        msg = await salon.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

        await ctx.send(f"✅ Demande de révoque envoyée pour {user.mention}.")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        message = reaction.message
        if message.channel.id != REVOQUE_BAN_CHANNEL_ID:
            return
        if not message.embeds or str(reaction.emoji) != "👍":
            return

        embed = message.embeds[0]
        user_field = discord.utils.get(embed.fields, name="👤 Utilisateur")
        if not user_field:
            return

        try:
            user_id = int(user_field.value.split("`")[1])
        except (IndexError, ValueError):
            return

        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        # Évite le déban multiple
        for react in message.reactions:
            if str(react.emoji) == "✅":
                return

        thumb_react = discord.utils.get(message.reactions, emoji="👍")
        if thumb_react and thumb_react.count >= 10:
            try:
                await guild.unban(discord.Object(id=user_id), reason="Déban automatique après 10 👍")
                await message.channel.send(f"✅ <@{user_id}> a été débanni automatiquement après 10 👍.")
                await message.add_reaction("✅")
            except Exception as e:
                await message.channel.send(f"❌ Erreur lors du débannissement de <@{user_id}> : {e}")

async def setup(bot):
    await bot.add_cog(BanManager(bot))
