import discord
from discord.ext import commands
import os
import json

class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = "autorole_json"
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        self.autoroles = {}
        self.load_autoroles()

    def load_autoroles(self):
        for filename in os.listdir(self.data_folder):
            if filename.endswith(".json"):
                guild_id_str = filename[:-5]
                if guild_id_str.isdigit():
                    guild_id = int(guild_id_str)
                    with open(os.path.join(self.data_folder, filename), "r") as f:
                        data = json.load(f)
                        self.autoroles[guild_id] = data.get("autorole_id")

    def save_autorole(self, guild_id):
        filepath = os.path.join(self.data_folder, f"{guild_id}.json")
        with open(filepath, "w") as f:
            json.dump({"autorole_id": self.autoroles[guild_id]}, f)

    def delete_autorole_file(self, guild_id):
        filepath = os.path.join(self.data_folder, f"{guild_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

    @commands.command(name="autorole", help="Définit ou supprime le rôle attribué aux nouveaux membres")
    @commands.has_permissions(administrator=True)
    async def set_autorole(self, ctx, role: discord.Role = None):
        guild_id = ctx.guild.id
        if role:
            self.autoroles[guild_id] = role.id
            self.save_autorole(guild_id)
            await ctx.send(f"✅ Autorole configuré : {role.mention}")
        else:
            if guild_id in self.autoroles:
                del self.autoroles[guild_id]
                self.delete_autorole_file(guild_id)
                await ctx.send("❌ Autorole supprimé.")
            else:
                await ctx.send("Aucun autorole à supprimer.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role_id = self.autoroles.get(member.guild.id)
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    pass

async def setup(bot):
    await bot.add_cog(AutoRole(bot))
