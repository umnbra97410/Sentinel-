import discord
from discord.ext import commands
import json
import os

PREFIX_FILE = "data/prefixes.json"

def load_prefixes():
    if not os.path.exists(PREFIX_FILE):
        return {}
    with open(PREFIX_FILE, "r") as f:
        return json.load(f)

def save_prefixes(prefixes):
    with open(PREFIX_FILE, "w") as f:
        json.dump(prefixes, f, indent=2)

def get_prefix(bot, message):
    if message.guild is None:
        return "!"
    
    prefixes = load_prefixes()
    return prefixes.get(str(message.guild.id), "!")

class CustomPrefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setprefix")
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, new_prefix: str):
        """Change le préfixe du bot pour ce serveur."""
        if len(new_prefix) > 5:
            return await ctx.send("❌ Le préfixe est trop long (max 5 caractères).")

        prefixes = load_prefixes()
        prefixes[str(ctx.guild.id)] = new_prefix
        save_prefixes(prefixes)

        await ctx.send(f"✅ Préfixe mis à jour : `{new_prefix}`")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Ajoute un préfixe par défaut quand le bot rejoint un serveur."""
        prefixes = load_prefixes()
        prefixes[str(guild.id)] = "!"
        save_prefixes(prefixes)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Supprime le préfixe quand le bot quitte un serveur."""
        prefixes = load_prefixes()
        if str(guild.id) in prefixes:
            del prefixes[str(guild.id)]
            save_prefixes(prefixes)

async def setup(bot):
    await bot.add_cog(CustomPrefix(bot))