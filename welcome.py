import discord
from discord.ext import commands
import json
import os

CONFIG_PATH = "welcome_configs"
if not os.path.exists(CONFIG_PATH):
    os.makedirs(CONFIG_PATH)

def load_config(guild_id):
    path = f"{CONFIG_PATH}/{guild_id}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"channel_id": None, "welcome_message": None}

def save_config(guild_id, config):
    with open(f"{CONFIG_PATH}/{guild_id}.json", "w") as f:
        json.dump(config, f, indent=4)

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setwelcome", help="Définit le salon de bienvenue")
    @commands.has_permissions(administrator=True)
    async def set_welcome(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            return await ctx.send("❌ Merci de mentionner un salon valide.")
        config = load_config(ctx.guild.id)
        config["channel_id"] = channel.id
        save_config(ctx.guild.id, config)
        await ctx.send(f"✅ Salon de bienvenue défini sur {channel.mention}")

    @commands.command(name="setwelcomemsg", help="Définit le message de bienvenue personnalisé (utilise {member} pour mentionner)")
    @commands.has_permissions(administrator=True)
    async def set_welcome_msg(self, ctx, *, message=None):
        if message is None:
            return await ctx.send("❌ Merci de fournir un message de bienvenue.")
        config = load_config(ctx.guild.id)
        config["welcome_message"] = message
        save_config(ctx.guild.id, config)
        await ctx.send("✅ Message de bienvenue personnalisé défini.")

    @commands.command(name="showwelcome", help="Affiche la configuration actuelle de bienvenue")
    async def show_welcome(self, ctx):
        config = load_config(ctx.guild.id)
        channel = ctx.guild.get_channel(config.get("channel_id")) if config.get("channel_id") else None
        welcome_msg = config.get("welcome_message") or "Aucun message défini."

        embed = discord.Embed(title="Configuration Bienvenue", color=discord.Color.green())
        embed.add_field(name="Salon de bienvenue", value=channel.mention if channel else "Non défini", inline=False)
        embed.add_field(name="Message de bienvenue", value=welcome_msg, inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = load_config(member.guild.id)
        channel_id = config.get("channel_id")
        if channel_id is None:
            return
        channel = member.guild.get_channel(channel_id)
        if channel is None:
            return

        # Message personnalisé ou message par défaut
        welcome_msg = config.get("welcome_message") or "Bienvenue {member} sur **{guild}** !"
        welcome_msg = welcome_msg.replace("{member}", member.mention).replace("{guild}", member.guild.name)

        embed = discord.Embed(title="Nouveau membre ! 🎉", description=welcome_msg, color=discord.Color.blue())
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text=f"Membre rejoint • {member.guild.name}")
        embed.timestamp = discord.utils.utcnow()

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))