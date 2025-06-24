import discord
from discord.ext import commands
import json
import os

class ReactRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.react_roles = {}  # guild_id: {message_id: {emoji: role_id}}
        self.data_folder = "data/react_roles"
        os.makedirs(self.data_folder, exist_ok=True)
        self.load_all_data()

    def get_guild_file(self, guild_id):
        return os.path.join(self.data_folder, f"{guild_id}.json")

    def load_all_data(self):
        for filename in os.listdir(self.data_folder):
            if filename.endswith(".json"):
                guild_id = int(filename.replace(".json", ""))
                with open(self.get_guild_file(guild_id), "r", encoding="utf-8") as f:
                    self.react_roles[guild_id] = json.load(f)

    def save_guild_data(self, guild_id):
        data = self.react_roles.get(guild_id, {})
        with open(self.get_guild_file(guild_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    @commands.command(name="setreactrole")
    @commands.has_permissions(manage_roles=True)
    async def set_react_role(self, ctx, message_id: int, emoji: str, role: discord.Role):
        """Associe une réaction à un rôle pour un message donné."""
        channel = ctx.channel
        guild_id = ctx.guild.id

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send("❌ Message introuvable.")
        except discord.Forbidden:
            return await ctx.send("❌ Je n’ai pas la permission de voir ce message.")
        except discord.HTTPException:
            return await ctx.send("❌ Erreur en récupérant le message.")

        await message.add_reaction(emoji)

        if guild_id not in self.react_roles:
            self.react_roles[guild_id] = {}

        if str(message_id) not in self.react_roles[guild_id]:
            self.react_roles[guild_id][str(message_id)] = {}

        self.react_roles[guild_id][str(message_id)][emoji] = role.id
        self.save_guild_data(guild_id)

        await ctx.send(f"✅ Réaction `{emoji}` liée au rôle **{role.name}** sur le message `{message.id}`.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild_id = payload.guild_id
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)

        if guild_id in self.react_roles:
            if message_id in self.react_roles[guild_id]:
                role_id = self.react_roles[guild_id][message_id].get(emoji)
                if role_id:
                    guild = self.bot.get_guild(guild_id)
                    if guild is None:
                        return
                    member = guild.get_member(payload.user_id)
                    role = guild.get_role(role_id)
                    if member and role:
                        if role >= guild.me.top_role:
                            print(f"⚠️ Le rôle {role.name} est trop haut pour que le bot le donne.")
                            return
                        try:
                            await member.add_roles(role, reason="Reaction role")
                        except discord.Forbidden:
                            print(f"❌ Permission refusée pour ajouter le rôle {role.name} à {member.name}.")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild_id = payload.guild_id
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)

        if guild_id in self.react_roles:
            if message_id in self.react_roles[guild_id]:
                role_id = self.react_roles[guild_id][message_id].get(emoji)
                if role_id:
                    guild = self.bot.get_guild(guild_id)
                    if guild is None:
                        return
                    member = guild.get_member(payload.user_id)
                    role = guild.get_role(role_id)
                    if member and role:
                        if role >= guild.me.top_role:
                            print(f"⚠️ Le rôle {role.name} est trop haut pour que le bot le retire.")
                            return
                        try:
                            await member.remove_roles(role, reason="Reaction role removed")
                        except discord.Forbidden:
                            print(f"❌ Permission refusée pour retirer le rôle {role.name} de {member.name}.")

async def setup(bot):
    await bot.add_cog(ReactRoles(bot))