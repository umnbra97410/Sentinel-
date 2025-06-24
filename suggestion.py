import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import asyncio

CONFIG_FILE = "suggestions_config.json"

# Chargement de la configuration du salon
def load_config(guild_id):
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
    return data.get(str(guild_id), {})

# Sauvegarde de la configuration du salon
def save_config(guild_id, config):
    data = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
    data[str(guild_id)] = config
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Vue avec les boutons "Valider" et "Refuser"
class SuggestionView(View):
    def __init__(self, bot, suggestion_author, suggestion_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.suggestion_author = suggestion_author
        self.suggestion_id = suggestion_id

    @discord.ui.button(label="✅ Valider", style=discord.ButtonStyle.green, custom_id="suggestion_validate")
    async def validate(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Vous n'avez pas la permission pour valider.", ephemeral=True)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text="Suggestion validée ✅")
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Suggestion validée.", ephemeral=True)

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.red, custom_id="suggestion_reject")
    async def reject(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Vous n'avez pas la permission pour refuser.", ephemeral=True)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_footer(text="Suggestion refusée ❌")
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Suggestion refusée.", ephemeral=True)

# Cog principal
class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Définit le salon où les suggestions seront postées.")
    @commands.has_permissions(administrator=True)
    async def setsuggestionschannel(self, ctx, channel: discord.TextChannel):
        config = load_config(ctx.guild.id)
        config["suggestions_channel"] = channel.id
        save_config(ctx.guild.id, config)
        await ctx.send(f"✅ Salon des suggestions défini sur {channel.mention}.")

    @commands.command(help="Envoie une suggestion. Usage : !suggest <votre suggestion>")
    async def suggest(self, ctx, *, suggestion_text: str):
        config = load_config(ctx.guild.id)
        channel_id = config.get("suggestions_channel")

        if not channel_id:
            return await ctx.send("❌ Le salon des suggestions n'est pas configuré sur ce serveur.")

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Le salon des suggestions configuré n'existe plus.")

        embed = discord.Embed(
            title="💡 Nouvelle suggestion",
            description=suggestion_text,
            color=discord.Color.blurple(),
            timestamp=ctx.message.created_at
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_footer(text=f"ID: {ctx.author.id}")

        await channel.send(embed=embed, view=SuggestionView(self.bot, ctx.author, ctx.message.id))

        confirm_msg = await ctx.send(f"✅ Suggestion envoyée dans {channel.mention}.")
        await asyncio.sleep(5)
        await confirm_msg.delete()
        await ctx.message.delete()

# Fonction pour charger la cog
async def setup(bot):
    await bot.add_cog(Suggestions(bot))