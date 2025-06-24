import discord
from discord.ext import commands
import platform
import datetime
import json
import os
import traceback
import psutil
import socket
import subprocess
import sys

AUTHORIZED_IDS = [ your id owner ]
BLACKLIST_FILE = "blacklist.json"
SUPPORT_GUILD_ID = your server
LOG_CHANNEL_ID = your logs id

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_blacklist(blacklist):
    with open(BLACKLIST_FILE, "w") as f:
        json.dump(list(blacklist), f)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.utcnow()
        self.blacklist = load_blacklist()
        self.error_list = []  # Pour stocker les erreurs

    def is_authorized(self, user_id):
        return user_id in AUTHORIZED_IDS

    def check_access(self, ctx):
        if ctx.author.id in self.blacklist:
            raise commands.CheckFailure("❌ Tu es blacklisté.")
        if not self.is_authorized(ctx.author.id):
            raise commands.CheckFailure("❌ Tu n'es pas autorisé à utiliser cette commande.")

    async def send_join_log(self, guild: discord.Guild):
        support_guild = self.bot.get_guild(SUPPORT_GUILD_ID)
        if not support_guild:
            return

        channel = support_guild.get_channel(LOG_CHANNEL_ID)
        if not channel:
            return

        invite_link = None
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).create_instant_invite:
                try:
                    invite = await ch.create_invite(max_age=0, max_uses=0, reason="Log d'ajout automatique")
                    invite_link = invite.url
                    break
                except:
                    continue

        embed = discord.Embed(
            title="📥 Nouveau serveur",
            description=f"Le bot a été ajouté au serveur **{guild.name}** (`{guild.id}`)",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.add_field(name="👑 Propriétaire", value=f"{guild.owner} (`{guild.owner_id}`)", inline=False)
        embed.add_field(name="👥 Membres", value=str(guild.member_count))
        embed.add_field(name="🔗 Invitation serveur", value=invite_link or "🔒 Aucune invitation disponible", inline=False)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.send_join_log(guild)

    # Blacklist group and commands
    @commands.group(name="blacklist", invoke_without_command=True)
    async def blacklist_group(self, ctx):
        self.check_access(ctx)
        if not self.blacklist:
            await ctx.send("⚠️ La blacklist est vide.")
        else:
            users = ", ".join(str(uid) for uid in self.blacklist)
            await ctx.send(f"🚫 Utilisateurs blacklistés : {users}")

    @blacklist_group.command(name="add")
    async def blacklist_add(self, ctx, user_id: int):
        self.check_access(ctx)
        if user_id in self.blacklist:
            return await ctx.send("❌ Cet utilisateur est déjà blacklisté.")
        self.blacklist.add(user_id)
        save_blacklist(self.blacklist)
        await ctx.send(f"✅ Utilisateur `{user_id}` ajouté à la blacklist.")

    @blacklist_group.command(name="remove")
    async def blacklist_remove(self, ctx, user_id: int):
        self.check_access(ctx)
        if user_id not in self.blacklist:
            return await ctx.send("❌ Cet utilisateur n'est pas dans la blacklist.")
        self.blacklist.remove(user_id)
        save_blacklist(self.blacklist)
        await ctx.send(f"✅ Utilisateur `{user_id}` retiré de la blacklist.")

    # Echo command
    @commands.command(name="echo", aliases=['say'])
    async def echo(self, ctx, *, message=None):
        self.check_access(ctx)
        if not message:
            return await ctx.send("❌ Tu dois fournir un message.")
        await ctx.message.delete()
        await ctx.send(message)

    # Manual join log
    @commands.command(name="declaré")
    @commands.has_permissions(administrator=True)
    async def manual_join_log(self, ctx):
        self.check_access(ctx)
        await self.send_join_log(ctx.guild)
        await ctx.send("📨 Log d'ajout envoyée au serveur support.")

    # Eval command
    @commands.command(name="eval")
    async def eval_command(self, ctx, *, code: str):
        self.check_access(ctx)
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'author': ctx.author,
            'guild': ctx.guild,
            'channel': ctx.channel,
            '__import__': __import__,
        }
        try:
            result = eval(code, env)
            if hasattr(result, "__await__"):
                result = await result
            await ctx.send(f"✅ Résultat : `{result}`")
        except Exception:
            tb = traceback.format_exc()
            self.error_list.append(tb)
            await ctx.send(f"❌ Erreur :\n```py\n{tb}```")

    # Load / Unload / Reload cogs
    @commands.command(name="load")
    async def load_cog(self, ctx, cog: str):
        self.check_access(ctx)
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await ctx.send(f"✅ Module `{cog}` chargé.")
        except Exception:
            tb = traceback.format_exc()
            self.error_list.append(tb)
            await ctx.send(f"❌ Erreur :\n```py\n{tb}```")

    @commands.command(name="unload")
    async def unload_cog(self, ctx, cog: str):
        self.check_access(ctx)
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await ctx.send(f"✅ Module `{cog}` déchargé.")
        except Exception:
            tb = traceback.format_exc()
            self.error_list.append(tb)
            await ctx.send(f"❌ Erreur :\n```py\n{tb}```")

    @commands.command(name="reload")
    async def reload_cog(self, ctx, cog: str):
        self.check_access(ctx)
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"♻️ Module `{cog}` rechargé.")
        except Exception:
            tb = traceback.format_exc()
            self.error_list.append(tb)
            await ctx.send(f"❌ Erreur :\n```py\n{tb}```")

    # Presence commands
    @commands.command(name="setpresence")
    async def set_presence(self, ctx, status: str):
        self.check_access(ctx)
        states = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.do_not_disturb,
            "invisible": discord.Status.invisible,
        }
        if status.lower() not in states:
            return await ctx.send("❌ Statut invalide. (online, idle, dnd, invisible)")
        await self.bot.change_presence(status=states[status.lower()])
        await ctx.send(f"✅ Présence changée : `{status}`")

    @commands.command(name="setactivity")
    async def set_activity(self, ctx, activity_type: str, *, text: str):
        self.check_access(ctx)
        types = {
            "playing": discord.Game(name=text),
            "listening": discord.Activity(type=discord.ActivityType.listening, name=text),
            "watching": discord.Activity(type=discord.ActivityType.watching, name=text),
            "competing": discord.Activity(type=discord.ActivityType.competing, name=text),
        }
        activity = types.get(activity_type.lower())
        if not activity:
            return await ctx.send("❌ Type invalide. (playing, listening, watching, competing)")
        await self.bot.change_presence(activity=activity)
        await ctx.send(f"✅ Activité mise à jour : **{activity_type.capitalize()} {text}**")

    # System info
    @commands.command(name="info")
    async def info(self, ctx):
        uptime = datetime.datetime.utcnow() - self.start_time
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")
        net_io = psutil.net_io_counters()
        process = psutil.Process(os.getpid())
        process_cpu = process.cpu_percent(interval=1)
        process_mem = process.memory_info().rss / 1024 / 1024
        python_version = platform.python_version()
        discord_version = discord.__version__
        os_name = platform.system()
        os_version = platform.version()
        architecture = platform.machine()
        hostname = socket.gethostname()

        embed = discord.Embed(title="🤖 Infos système et bot", color=discord.Color.blurple())
        embed.add_field(name="⏱️ Uptime du bot", value=str(uptime).split('.')[0], inline=False)
        embed.add_field(name="🖥️ CPU", value=f"Cœurs logiques: {cpu_count}\nFréquence: {cpu_freq.current:.2f} MHz\nUsage: {cpu_percent}%", inline=False)
        embed.add_field(name="💾 Mémoire RAM", value=f"Total: {mem.total // (1024**2)} Mo\nDisponible: {mem.available // (1024**2)} Mo\nUtilisée: {mem.percent}%", inline=False)
        embed.add_field(name="💽 Disque", value=f"Total: {disk.total // (1024**3)} Go\nUtilisé: {disk.used // (1024**3)} Go\nLibre: {disk.free // (1024**3)} Go\nUsage: {disk.percent}%", inline=False)
        embed.add_field(name="🔁 Swap", value=f"Total: {swap.total // (1024**2)} Mo\nUtilisé: {swap.used // (1024**2)} Mo\nLibre: {swap.free // (1024**2)} Mo\nUsage: {swap.percent}%", inline=False)
        embed.add_field(name="📡 Réseau", value=f"Envoyé: {net_io.bytes_sent // (1024**2)} Mo\nReçu: {net_io.bytes_recv // (1024**2)} Mo", inline=False)
        embed.add_field(name="⚙️ Processus du bot", value=f"CPU: {process_cpu}%\nMémoire: {process_mem:.2f} Mo", inline=False)
        embed.add_field(name="🐍 Python", value=python_version)
        embed.add_field(name="📦 discord.py", value=discord_version)
        embed.add_field(name="🖥️ OS", value=f"{os_name} {os_version} ({architecture})")
        embed.add_field(name="📛 Nom d'hôte", value=hostname)

        await ctx.send(embed=embed)

    # Shutdown command
    @commands.command(name="shutdown")
    async def shutdown(self, ctx):
        self.check_access(ctx)
        await ctx.send("🔌 Arrêt du bot...")
        await self.bot.close()

    # Restart command
    @commands.command(name="restart")
    async def restart(self, ctx):
        self.check_access(ctx)
        await ctx.send("🔄 Redémarrage du bot...")
        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # Update command
    @commands.command(name="update")
    async def update(self, ctx):
        self.check_access(ctx)
        try:
            subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            return await ctx.send("❌ Ce dossier n'est pas un dépôt git. Impossible de faire la mise à jour.")

        await ctx.send("⬇️ Mise à jour via git pull...")
        try:
            result = subprocess.run(["git", "pull"], capture_output=True, text=True, check=True)
            await ctx.send(f"✅ Mise à jour terminée.\n```diff\n{result.stdout}\n```Redémarrage...")
            await self.bot.close()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except subprocess.CalledProcessError as e:
            await ctx.send(f"❌ Erreur lors de la mise à jour :\n```diff\n{e.stderr}\n```")

    # Broadcast command
    @commands.command(name="broadcast")
    async def broadcast(self, ctx, *, message=None):
        self.check_access(ctx)
        if not message:
            return await ctx.send("❌ Tu dois fournir un message à diffuser.")
        success = 0
        fail = 0
        for guild in self.bot.guilds:
            channel = None
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break
            if not channel:
                fail += 1
                continue
            try:
                await channel.send(message)
                success += 1
            except Exception:
                fail += 1
        await ctx.send(f"✅ Message envoyé dans {success} serveurs.\n❌ Impossible dans {fail} serveurs.")

    # Sync slash commands
    @commands.command(name="syncro")
    async def syncro(self, ctx):
        self.check_access(ctx)
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Slash commands synchronisées ({len(synced)} commandes).")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la synchronisation : {e}")

async def setup(bot):
    await bot.add_cog(Admin(bot))
