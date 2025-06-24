import discord
from discord.ext import commands
import os
import json

class Bump(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.support_channel_id = 1385553331220647996
        self.bump_folder = "bump"
        if not os.path.exists(self.bump_folder):
            os.makedirs(self.bump_folder)

    def get_bump_file(self, guild_id):
        return os.path.join(self.bump_folder, f"{guild_id}.json")

    async def save_embed(self, guild_id, title, description):
        data = {
            "title": title,
            "description": description
        }
        with open(self.get_bump_file(guild_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    async def load_embed(self, guild_id):
        path = self.get_bump_file(guild_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    @commands.command(name="customembed", help="Enregistre un embed personnalisé pour le bump. Usage : !customembed Titre ; Description")
    async def customembed(self, ctx, *, content: str):
        support_channel = self.bot.get_channel(self.support_channel_id)
        if support_channel is None:
            await ctx.send("❌ Le salon support est introuvable, vérifie l'ID dans le cog.")
            return

        # Séparation avec un point-virgule (;)
        if ";" not in content:
            await ctx.send("❌ Format invalide. Utilise : `!customembed Titre ; Description`")
            return

        title, description = map(str.strip, content.split(";", 1))

        await self.save_embed(ctx.guild.id, title, description)

        await ctx.send(f"✅ Embed personnalisé enregistré pour ce serveur et sera utilisé au prochain bump.")

    @commands.command(name="bump", help="Envoie l'embed personnalisé + bouton invitation dans le salon support.")
    async def bump(self, ctx):
        support_channel = self.bot.get_channel(self.support_channel_id)
        if support_channel is None:
            await ctx.send("❌ Le salon support est introuvable, vérifie l'ID dans le cog.")
            return

        embed_data = await self.load_embed(ctx.guild.id)

        if embed_data is None:
            embed = discord.Embed(
                title=f"{ctx.guild.name} a bumpé le serveur !",
                description="Merci pour votre soutien.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title=embed_data.get("title", f"{ctx.guild.name} a bumpé le serveur !"),
                description=embed_data.get("description", "Merci pour votre soutien."),
                color=discord.Color.green()
            )
        embed.set_footer(text=f"Envoyé par {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        invites = await ctx.guild.invites()
        invite_url = None
        if invites:
            invite_url = invites[0].url
        else:
            try:
                invite = await ctx.channel.create_invite(max_age=3600, max_uses=1, unique=True)
                invite_url = invite.url
            except discord.Forbidden:
                await ctx.send("❌ Je n'ai pas la permission de créer une invitation.")
                return

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=ctx.guild.name, url=invite_url))

        await support_channel.send(embed=embed, view=view)
        await ctx.send(f"✅ Merci pour le bump, {ctx.author.mention} !")

async def setup(bot):
    await bot.add_cog(Bump(bot))