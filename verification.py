import discord
from discord.ext import commands
import random
import string
import json
import os
import asyncio

CONFIG_FILE = "data/captcha_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def generate_captcha(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

class CaptchaPrivateChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.waiting = {}  # guild_id -> {user_id: captcha}

    @commands.command(help="Définir la catégorie où créer les salons captcha privés")
    @commands.has_permissions(administrator=True)
    async def setcaptchacat(self, ctx, category: discord.CategoryChannel):
        guild_id = str(ctx.guild.id)
        self.config.setdefault(guild_id, {})
        self.config[guild_id]["captcha_category"] = category.id
        save_config(self.config)
        await ctx.send(f"✅ Catégorie captcha définie sur {category.name}.")

    @commands.command(help="Définir le rôle à attribuer après vérification")
    @commands.has_permissions(administrator=True)
    async def setrole(self, ctx, role: discord.Role):
        guild_id = str(ctx.guild.id)
        self.config.setdefault(guild_id, {})
        self.config[guild_id]["verified_role"] = role.id
        save_config(self.config)
        await ctx.send(f"✅ Rôle vérifié défini sur {role.mention}.")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return  # Ne fait rien pour les bots

        guild_id = str(member.guild.id)
        guild_config = self.config.get(guild_id, {})
        category_id = guild_config.get("captcha_category")
        verified_role_id = guild_config.get("verified_role")

        if not category_id or not verified_role_id:
            return  # Configuration manquante

        category = member.guild.get_channel(category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            return  # Catégorie invalide

        captcha = generate_captcha()
        self.waiting.setdefault(guild_id, {})[member.id] = captcha

        overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        for role in member.guild.roles:
            perms = role.permissions
            if perms.administrator or perms.manage_guild or perms.manage_channels:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"captcha-{member.name}".lower()
        channel = await member.guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

        await channel.send(
            f"👋 Bienvenue {member.mention} !\nPour vérifier que tu n'es pas un robot, réponds avec ce code : **`{captcha}`**\n"
            "⏳ Tu as **2 minutes** pour répondre, sinon tu seras exclu automatiquement."
        )

        def check(m):
            return m.channel == channel and m.author == member

        try:
            msg = await self.bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            try:
                await member.send("⏰ Temps écoulé. Tu as été exclu. Rejoins à nouveau pour retenter la vérification.")
            except discord.Forbidden:
                pass
            await member.kick(reason="Captcha non complété à temps.")
            self.waiting[guild_id].pop(member.id, None)
            await channel.delete()
            return

        if msg.content.strip() == captcha:
            role = member.guild.get_role(verified_role_id)
            if role:
                await member.add_roles(role)
            try:
                await member.send("✅ Vérification réussie. Bienvenue !")
            except discord.Forbidden:
                pass
            await channel.send("✅ Captcha réussi ! Ce salon sera supprimé.")
        else:
            try:
                await member.send("❌ Code incorrect. Tu as été exclu. Rejoins pour retenter.")
            except discord.Forbidden:
                pass
            await member.kick(reason="Captcha échoué.")
            await channel.send("❌ Captcha incorrect. Salon supprimé.")

        self.waiting[guild_id].pop(member.id, None)
        await asyncio.sleep(5)
        await channel.delete()

async def setup(bot):
    await bot.add_cog(CaptchaPrivateChannel(bot))