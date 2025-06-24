import discord
from discord.ext import commands, tasks
import json
import os
import asyncio

CONFIG_FOLDER = "security_configs"

if not os.path.exists(CONFIG_FOLDER):
    os.makedirs(CONFIG_FOLDER)

def load_config(guild_id):
    path = f"{CONFIG_FOLDER}/{guild_id}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {
        "modules": {
            "antispam": {"enabled": False, "punishment": "mute"},
            "antiban": {"enabled": False, "punishment": "ban"},
            "antichannel": {"enabled": False, "punishment": "kick"},
            "antirole": {"enabled": False, "punishment": "derank"},
            "antimention": {"enabled": False, "punishment": "mute", "limit": 5}
        },
        "whitelist": [],
        "log_channel": None,
        "blocked_channels": []
    }

def save_config(guild_id, config):
    path = f"{CONFIG_FOLDER}/{guild_id}.json"
    with open(path, "w") as f:
        json.dump(config, f, indent=4)

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.configs = {}
        self.load_all_configs()
        self.save_loop.start()

    def load_all_configs(self):
        for filename in os.listdir(CONFIG_FOLDER):
            if filename.endswith(".json"):
                guild_id = int(filename[:-5])
                self.configs[guild_id] = load_config(guild_id)

    def get_config(self, guild_id):
        if guild_id not in self.configs:
            self.configs[guild_id] = load_config(guild_id)
        return self.configs[guild_id]

    def save_config(self, guild_id):
        if guild_id in self.configs:
            save_config(guild_id, self.configs[guild_id])

    @tasks.loop(minutes=5)
    async def save_loop(self):
        for guild_id in self.configs:
            self.save_config(guild_id)

    def is_whitelisted(self, guild_id, user_id):
        config = self.get_config(guild_id)
        return str(user_id) in config.get("whitelist", [])

    async def log_action(self, guild, config, description):
        channel_id = config.get("log_channel")
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                embed = discord.Embed(description=description, color=discord.Color.blue())
                embed.set_author(name="Log Sécurité")
                embed.timestamp = discord.utils.utcnow()
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def cog_check(self, ctx):
        config = self.get_config(ctx.guild.id)
        if str(ctx.channel.id) in config.get("blocked_channels", []):
            if self.is_whitelisted(ctx.guild.id, ctx.author.id):
                return True
            else:
                msg = await ctx.send(f"🚫 Les commandes sont désactivées dans ce salon, {ctx.author.mention}.")
                await asyncio.sleep(300)
                try:
                    await msg.delete()
                except:
                    pass
                return False
        return True

    @commands.command(help="Affiche la configuration actuelle de la sécurité.")
    @commands.has_permissions(administrator=True)
    async def config(self, ctx):
        config = self.get_config(ctx.guild.id)
        modules = config.get("modules", {})
        whitelist = config.get("whitelist", [])
        log_channel_id = config.get("log_channel")
        blocked_channels = config.get("blocked_channels", [])

        embed = discord.Embed(title=f"Configuration de sécurité pour {ctx.guild.name}", color=discord.Color.blue())

        modules_status = ""
        for mod_name, mod_info in modules.items():
            enabled = "✅" if mod_info.get("enabled") else "❌"
            punishment = mod_info.get("punishment", "N/A")
            limit = mod_info.get("limit", None)
            line = f"**{mod_name}** : {enabled} | Sanction : `{punishment}`"
            if limit is not None:
                line += f" | Limite : `{limit}`"
            modules_status += line + "\n"
        embed.add_field(name="Modules", value=modules_status or "Aucun module configuré.", inline=False)

        if whitelist:
            wl_mentions = []
            for uid in whitelist:
                member = ctx.guild.get_member(int(uid))
                wl_mentions.append(member.mention if member else f"<@{uid}>")
            embed.add_field(name="Whitelist", value=", ".join(wl_mentions), inline=False)
        else:
            embed.add_field(name="Whitelist", value="Aucun membre whitelisté.", inline=False)

        if log_channel_id:
            log_channel = ctx.guild.get_channel(int(log_channel_id))
            embed.add_field(name="Salon de logs", value=log_channel.mention if log_channel else "Salon introuvable", inline=False)
        else:
            embed.add_field(name="Salon de logs", value="Non défini", inline=False)

        if blocked_channels:
            blocked_mentions = []
            for cid in blocked_channels:
                ch = ctx.guild.get_channel(int(cid))
                blocked_mentions.append(ch.mention if ch else f"Salon supprimé (`{cid}`)")
            embed.add_field(name="Salons bloqués", value=", ".join(blocked_mentions), inline=False)
        else:
            embed.add_field(name="Salons bloqués", value="Aucun", inline=False)

        await ctx.send(embed=embed)

    @commands.command(help="Active ou désactive un module de sécurité")
    @commands.has_permissions(administrator=True)
    async def toggle(self, ctx, module: str = None, state: str = None):
        if not module or not state:
            return await ctx.send("❌ Utilisation : `!toggle <module> <on/off>`")

        config = self.get_config(ctx.guild.id)
        module = module.lower()
        state = state.lower()

        if module not in config["modules"]:
            modules_list = ", ".join(config["modules"].keys())
            return await ctx.send(f"❌ Module inconnu.\nModules disponibles : `{modules_list}`")

        if state not in ["on", "off"]:
            return await ctx.send("❌ L'état doit être `on` ou `off`.")

        config["modules"][module]["enabled"] = (state == "on")
        self.save_config(ctx.guild.id)
        await ctx.send(f"✅ Module `{module}` {'activé ✅' if state == 'on' else 'désactivé ❌'}.")
        await self.log_action(ctx.guild, config, f"🔧 {ctx.author.mention} a {'activé' if state == 'on' else 'désactivé'} le module `{module}`.")

    @commands.command(help="Change la sanction d'un module de sécurité")
    @commands.has_permissions(administrator=True)
    async def punish(self, ctx, module: str, sanction: str):
        module = module.lower()
        sanction = sanction.lower()
        config = self.get_config(ctx.guild.id)

        if module not in config["modules"]:
            return await ctx.send("❌ Module invalide.")
        if sanction not in ["ban", "kick", "mute", "derank"]:
            return await ctx.send("❌ Sanction invalide. Choix : ban, kick, mute, derank")

        config["modules"][module]["punishment"] = sanction
        self.save_config(ctx.guild.id)
        await ctx.send(f"✅ Sanction du module `{module}` changée en `{sanction}`.")
        await self.log_action(ctx.guild, config, f"⚠️ {ctx.author.mention} a changé la sanction de `{module}` en `{sanction}`.")

    @commands.command(help="Ajoute un membre à la whitelist")
    @commands.has_permissions(administrator=True)
    async def wl(self, ctx, member: discord.Member):
        config = self.get_config(ctx.guild.id)
        uid = str(member.id)

        if uid in config["whitelist"]:
            return await ctx.send(f"{member.mention} est déjà whitelisté.")

        config["whitelist"].append(uid)
        self.save_config(ctx.guild.id)

        await ctx.send(f"✅ {member.mention} ajouté à la whitelist.")
        await self.log_action(ctx.guild, config, f"🛡️ {ctx.author.mention} a ajouté {member.mention} à la whitelist.")

    @commands.command(help="Retire un membre de la whitelist")
    @commands.has_permissions(administrator=True)
    async def unwl(self, ctx, member: discord.Member):
        config = self.get_config(ctx.guild.id)
        uid = str(member.id)

        if uid not in config["whitelist"]:
            return await ctx.send(f"{member.mention} n'est pas whitelisté.")

        config["whitelist"].remove(uid)
        self.save_config(ctx.guild.id)

        await ctx.send(f"✅ {member.mention} retiré de la whitelist.")
        await self.log_action(ctx.guild, config, f"🚫 {ctx.author.mention} a retiré {member.mention} de la whitelist.")

    @commands.command(help="Définit la limite de mentions avant sanction")
    @commands.has_permissions(administrator=True)
    async def mentionlimit(self, ctx, nombre: int):
        config = self.get_config(ctx.guild.id)
        config["modules"]["antimention"]["limit"] = nombre
        self.save_config(ctx.guild.id)
        await ctx.send(f"✅ Limite de mentions définie à {nombre}.")
        await self.log_action(ctx.guild, config, f"🔢 {ctx.author.mention} a défini la limite de mentions à `{nombre}`.")

    @commands.command(help="Définit le salon pour les logs de sécurité")
    @commands.has_permissions(administrator=True)
    async def logs(self, ctx, channel: discord.TextChannel):
        config = self.get_config(ctx.guild.id)
        config["log_channel"] = channel.id
        self.save_config(ctx.guild.id)
        await ctx.send(f"✅ Salon de logs défini sur {channel.mention}.")
        await self.log_action(ctx.guild, config, f"📋 {ctx.author.mention} a défini le salon de logs à {channel.mention}.")

    @commands.command(help="Empêche ou autorise l’utilisation des commandes dans un salon.")
    @commands.has_permissions(administrator=True)
    async def block(self, ctx, mode: str = None, channel: discord.TextChannel = None):
        if mode not in ["on", "off"] or channel is None:
            return await ctx.send("❌ Utilisation : `!block <on/off> <#salon>`")

        config = self.get_config(ctx.guild.id)
        channel_id = str(channel.id)

        if "blocked_channels" not in config:
            config["blocked_channels"] = []

        if mode == "on":
            if channel_id in config["blocked_channels"]:
                return await ctx.send(f"🚫 Les commandes sont déjà bloquées dans {channel.mention}.")

            config["blocked_channels"].append(channel_id)
            self.save_config(ctx.guild.id)

            await ctx.send(f"✅ Les commandes sont maintenant **bloquées** dans {channel.mention}.")
            await self.log_action(ctx.guild, config, f"🔒 {ctx.author.mention} a **bloqué** les commandes dans {channel.mention}.")

        elif mode == "off":
            if channel_id not in config["blocked_channels"]:
                return await ctx.send(f"ℹ️ Les commandes ne sont pas bloquées dans {channel.mention}.")

            config["blocked_channels"].remove(channel_id)
            self.save_config(ctx.guild.id)

            await ctx.send(f"🔓 Les commandes sont maintenant **autorisées** dans {channel.mention}.")
            await self.log_action(ctx.guild, config, f"🔓 {ctx.author.mention} a **débloqué** les commandes dans {channel.mention}.")

async def setup(bot):
    await bot.add_cog(Security(bot))