import discord
from discord.ext import commands
import json
import os

BACKUP_FOLDER = "backups"

class Backup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="backupcreate", help= "Créer une backup de ton serveur")
    async def backup_create(self, ctx):
        if ctx.author != ctx.guild.owner:
            return await ctx.send("❌ Seul le propriétaire du serveur peut utiliser cette commande.")

        guild = ctx.guild
        data = {
            "guild_name": guild.name,
            "roles": [],
            "categories": []
        }

        for role in guild.roles:
            if role.name != "@everyone":
                data["roles"].append({
                    "name": role.name,
                    "color": role.color.value,
                    "permissions": role.permissions.value,
                    "mentionable": role.mentionable,
                    "hoist": role.hoist
                })

        for category in guild.categories:
            cat = {
                "name": category.name,
                "channels": []
            }
            for channel in category.channels:
                if isinstance(channel, discord.TextChannel):
                    chan_type = "text"
                elif isinstance(channel, discord.VoiceChannel):
                    chan_type = "voice"
                else:
                    continue
                cat["channels"].append({
                    "name": channel.name,
                    "type": chan_type
                })
            data["categories"].append(cat)

        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER)

        filename = f"{BACKUP_FOLDER}/backup_{ctx.guild.id}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        await ctx.send(f"✅ Sauvegarde enregistrée sur le serveur sous `{filename}`.")

    @commands.command(name="backupload", help= "Charge la backup créer précédemment")
    async def backup_load(self, ctx, filename: str):
        if ctx.author != ctx.guild.owner:
            return await ctx.send("❌ Seul le propriétaire du serveur peut utiliser cette commande.")

        path = os.path.join(BACKUP_FOLDER, filename)
        if not os.path.isfile(path):
            return await ctx.send("❌ Fichier de sauvegarde introuvable.")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return await ctx.send(f"❌ Erreur de lecture du fichier : {e}")

        # Suppression des salons
        for channel in ctx.guild.channels:
            try:
                await channel.delete()
            except:
                continue

        # Suppression des rôles
        for role in ctx.guild.roles:
            if role.name != "@everyone":
                try:
                    await role.delete()
                except:
                    continue

        # Création des rôles
        role_map = {}
        for r in data.get("roles", []):
            try:
                new_role = await ctx.guild.create_role(
                    name=r["name"],
                    color=discord.Color(r["color"]),
                    permissions=discord.Permissions(r["permissions"]),
                    mentionable=r["mentionable"],
                    hoist=r["hoist"]
                )
                role_map[r["name"]] = new_role
            except:
                continue

        # Création des catégories et canaux
        for cat in data.get("categories", []):
            try:
                category = await ctx.guild.create_category(cat["name"])
                for chan in cat["channels"]:
                    if chan["type"] == "text":
                        await ctx.guild.create_text_channel(chan["name"], category=category)
                    elif chan["type"] == "voice":
                        await ctx.guild.create_voice_channel(chan["name"], category=category)
            except:
                continue

        await ctx.send("✅ Serveur restauré à partir du fichier.")

async def setup(bot):
    await bot.add_cog(Backup(bot))
