import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta

ECONOMY_FOLDER = "economy_data"
if not os.path.exists(ECONOMY_FOLDER):
    os.makedirs(ECONOMY_FOLDER)

LOGS_FILE = "coins_logs.json"

def load_data(guild_id):
    path = f"{ECONOMY_FOLDER}/{guild_id}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_data(guild_id, data):
    path = f"{ECONOMY_FOLDER}/{guild_id}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def load_logs():
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_logs(data):
    with open(LOGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}
        self.logs = load_logs()  # guild_id (str) -> channel_id (int)
        self.load_all()
        self.save_loop.start()

    def load_all(self):
        for filename in os.listdir(ECONOMY_FOLDER):
            if filename.endswith(".json"):
                gid = int(filename[:-5])
                self.data[gid] = load_data(gid)

    def get_user_data(self, guild_id, user_id):
        guild_data = self.data.setdefault(guild_id, {})
        user_str = str(user_id)
        user_data = guild_data.setdefault(user_str, {
            "balance": 0,
            "daily_cooldown": None,
            "work_cooldown": None,
            "rank": None  # vip, premium, wl, or None
        })
        return user_data

    def save(self, guild_id):
        if guild_id in self.data:
            save_data(guild_id, self.data[guild_id])

    @tasks.loop(minutes=5)
    async def save_loop(self):
        for gid in self.data:
            self.save(gid)
        save_logs(self.logs)

    @save_loop.before_loop
    async def before_save(self):
        await self.bot.wait_until_ready()

    def can_use_daily(self, user_data):
        if not user_data["daily_cooldown"]:
            return True
        last = datetime.fromisoformat(user_data["daily_cooldown"])
        return datetime.utcnow() - last >= timedelta(days=1)

    def can_use_work(self, user_data):
        if not user_data["work_cooldown"]:
            return True
        last = datetime.fromisoformat(user_data["work_cooldown"])
        return datetime.utcnow() - last >= timedelta(hours=1)

    async def log_transaction(self, guild_id, message):
        """Envoie un message dans le salon de logs configuré."""
        channel_id = self.logs.get(str(guild_id))
        if not channel_id:
            return  # Pas de salon configuré
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(message)

    @commands.command(help="Configurer le salon de logs des transactions")
    @commands.has_permissions(administrator=True)
    async def setcoinslogs(self, ctx, channel: discord.TextChannel):
        self.logs[str(ctx.guild.id)] = channel.id
        save_logs(self.logs)
        await ctx.send(f"✅ Salon de logs configuré sur {channel.mention}")

    @commands.command(aliases=['bal'], help="Voir votre solde")
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user_data = self.get_user_data(ctx.guild.id, member.id)
        embed = discord.Embed(title=f"💰 Solde de {member.display_name}", color=discord.Color.green())
        embed.add_field(name="Argent", value=f"{user_data['balance']:,} €")
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        await ctx.send(embed=embed)

    @commands.command(aliases=['dy'], help="Réclame ta récompense quotidienne (100k €)")
    async def daily(self, ctx):
        user_data = self.get_user_data(ctx.guild.id, ctx.author.id)
        if not self.can_use_daily(user_data):
            last = datetime.fromisoformat(user_data["daily_cooldown"])
            next_time = last + timedelta(days=1)
            delta = next_time - datetime.utcnow()
            await ctx.send(f"❌ Tu as déjà pris ta récompense quotidienne. Reviens dans {str(delta).split('.')[0]} !")
            return

        user_data["balance"] += 100_000
        user_data["daily_cooldown"] = datetime.utcnow().isoformat()
        self.save(ctx.guild.id)

        await ctx.send(f"✅ Tu as reçu **100 000 €** de récompense quotidienne !")
        await self.log_transaction(ctx.guild.id, f"💰 {ctx.author} a reçu sa récompense quotidienne de 100 000 €.")

    @commands.command(help="Travaille et gagne 50k € (cooldown 1h)")
    async def work(self, ctx):
        user_data = self.get_user_data(ctx.guild.id, ctx.author.id)
        if not self.can_use_work(user_data):
            last = datetime.fromisoformat(user_data["work_cooldown"])
            next_time = last + timedelta(hours=1)
            delta = next_time - datetime.utcnow()
            await ctx.send(f"❌ Tu as déjà travaillé récemment. Reviens dans {str(delta).split('.')[0]} !")
            return

        user_data["balance"] += 50_000
        user_data["work_cooldown"] = datetime.utcnow().isoformat()
        self.save(ctx.guild.id)

        await ctx.send(f"✅ Tu as gagné **50 000 €** en travaillant !")
        await self.log_transaction(ctx.guild.id, f"💼 {ctx.author} a gagné 50 000 € en travaillant.")

    @commands.command(help="Afficher le shop")
    async def shop(self, ctx):
        embed = discord.Embed(title="🏪 Boutique", color=discord.Color.purple())
        embed.add_field(name="VIP", value="1 000 000 €", inline=False)
        embed.add_field(name="Premium", value="2 000 000 €", inline=False)
        embed.add_field(name="Whitelist (WL)", value="5 000 000 €", inline=False)
        embed.set_footer(text="Pour acheter, tape : !buy <rang>")
        await ctx.send(embed=embed)

    @commands.command(help="Acheter un rang (vip, premium, wl)")
    async def buy(self, ctx, rank: str):
        rank = rank.lower()
        user_data = self.get_user_data(ctx.guild.id, ctx.author.id)
        prices = {"vip": 1_000_000, "premium": 2_000_000, "wl": 5_000_000}
        if rank not in prices:
            return await ctx.send("❌ Rang inconnu. Choisis entre `vip`, `premium` ou `wl`.")

        price = prices[rank]
        if user_data["balance"] < price:
            return await ctx.send(f"❌ Tu n'as pas assez d'argent pour acheter `{rank}` (il te faut {price:,} €).")

        user_data["balance"] -= price
        user_data["rank"] = rank
        self.save(ctx.guild.id)

        await ctx.send(f"✅ Félicitations, tu as acheté le rang `{rank}` pour {price:,} € !")
        await self.log_transaction(ctx.guild.id, f"🛒 {ctx.author} a acheté le rang `{rank}` pour {price:,} €.")

    @commands.command(aliases=['ac'], help="Commande owner : Ajouter des coins à un utilisateur")
    @commands.is_owner()
    async def addcoins(self, ctx, member: discord.Member, amount: int):
        user_data = self.get_user_data(ctx.guild.id, member.id)
        user_data["balance"] += amount
        self.save(ctx.guild.id)
        await ctx.send(f"✅ Ajouté {amount:,} € à {member.mention}. Nouveau solde : {user_data['balance']:,} €")
        await self.log_transaction(ctx.guild.id, f"➕ Owner a ajouté {amount:,} € à {member}.")

    @commands.command(help="Joue à Pierre-Feuille-Ciseaux et gagne de l'argent")
    async def rps(self, ctx, choix: str):
        choix = choix.lower()
        options = ["pierre", "feuille", "ciseaux"]
        if choix not in options:
            return await ctx.send(f"❌ Choix invalide, choisis parmi {', '.join(options)}")

        bot_choice = random.choice(options)
        user_data = self.get_user_data(ctx.guild.id, ctx.author.id)

        if choix == bot_choice:
            result = "égalité"
            gain = 10_000
        elif (choix == "pierre" and bot_choice == "ciseaux") or \
             (choix == "feuille" and bot_choice == "pierre") or \
             (choix == "ciseaux" and bot_choice == "feuille"):
            result = "gagné"
            gain = 50_000
        else:
            result = "perdu"
            gain = -25_000

        user_data["balance"] = max(0, user_data["balance"] + gain)
        self.save(ctx.guild.id)

        embed = discord.Embed(title="Pierre-Feuille-Ciseaux", color=discord.Color.blurple())
        embed.add_field(name="Ton choix", value=choix.capitalize())
        embed.add_field(name="Choix du bot", value=bot_choice.capitalize())
        embed.add_field(name="Résultat", value=result.capitalize())
        embed.add_field(name="Gain/perte", value=f"{gain:,} €")
        await ctx.send(embed=embed)

        await self.log_transaction(ctx.guild.id, f"🎲 {ctx.author} a joué à RPS : choix={choix}, bot={bot_choice}, résultat={result}, gain/perte={gain:,} €")

    @commands.command(aliases=['bj'], help="Joue au blackjack")
    async def blackjack(self, ctx, mise: int):
        user_data = self.get_user_data(ctx.guild.id, ctx.author.id)
        if mise <= 0:
            return await ctx.send("❌ Mise invalide.")
        if user_data["balance"] < mise:
            return await ctx.send("❌ Tu n'as pas assez d'argent pour cette mise.")

        user_data["balance"] -= mise

        player_score = random.randint(2, 22)
        dealer_score = random.randint(2, 22)

        if player_score > 21:
            result = "Perdu (bust)"
            gain = 0
        elif dealer_score > 21 or player_score > dealer_score:
            result = "Gagné"
            gain = mise * 2
        elif player_score == dealer_score:
            result = "Égalité"
            gain = mise
        else:
            result = "Perdu"
            gain = 0

        user_data["balance"] += gain
        self.save(ctx.guild.id)

        embed = discord.Embed(title="Blackjack", color=discord.Color.dark_gold())
        embed.add_field(name="Ta main", value=str(player_score))
        embed.add_field(name="Main du dealer", value=str(dealer_score))
        embed.add_field(name="Résultat", value=result)
        embed.add_field(name="Gain/perte", value=f"{gain - mise:,} €")
        await ctx.send(embed=embed)

        await self.log_transaction(ctx.guild.id, f"🃏 {ctx.author} a joué au blackjack : mise={mise}, résultat={result}, gain/perte={gain - mise:,} €")

    @commands.command(aliases=['roll'], help="Joue à la roulette")
    async def roulette(self, ctx, mise: int, couleur: str):
        couleur = couleur.lower()
        user_data = self.get_user_data(ctx.guild.id, ctx.author.id)
        if mise <= 0:
            return await ctx.send("❌ Mise invalide.")
        if user_data["balance"] < mise:
            return await ctx.send("❌ Tu n'as pas assez d'argent pour cette mise.")
        if couleur not in ["rouge", "noir", "vert"]:
            return await ctx.send("❌ Choix de couleur invalide (rouge, noir, vert).")

        user_data["balance"] -= mise

        # Roulette simple avec 0 (vert) et nombre aléatoire 1-36 rouge/noir
        result_number = random.randint(0, 36)
        if result_number == 0:
            result_couleur = "vert"
        else:
            result_couleur = "rouge" if result_number % 2 == 0 else "noir"

        if couleur == result_couleur:
            if couleur == "vert":
                gain = mise * 14
            else:
                gain = mise * 2
            result = "Gagné"
        else:
            gain = 0
            result = "Perdu"

        user_data["balance"] += gain
        self.save(ctx.guild.id)

        embed = discord.Embed(title="Roulette", color=discord.Color.red() if result_couleur=="rouge" else discord.Color.black())
        embed.add_field(name="Mise", value=f"{mise:,} € sur {couleur}")
        embed.add_field(name="Résultat", value=f"{result_number} ({result_couleur}) - {result}")
        embed.add_field(name="Gain/perte", value=f"{gain - mise:,} €")
        await ctx.send(embed=embed)

        await self.log_transaction(ctx.guild.id, f"🎡 {ctx.author} a joué à la roulette : mise={mise} € sur {couleur}, résultat={result_number} {result_couleur}, {result}, gain/perte={gain - mise:,} €")

    @commands.command(help="Joue aux machines à sous")
    async def slot(self, ctx, mise: int):
        user_data = self.get_user_data(ctx.guild.id, ctx.author.id)
        if mise <= 0:
            return await ctx.send("❌ Mise invalide.")
        if user_data["balance"] < mise:
            return await ctx.send("❌ Tu n'as pas assez d'argent pour cette mise.")

        user_data["balance"] -= mise

        symbols = ["🍒", "🍋", "🍊", "⭐", "💎"]
        reel = [random.choice(symbols) for _ in range(3)]

        if reel[0] == reel[1] == reel[2]:
            gain = mise * 5
            result = "Jackpot !"
        elif reel[0] == reel[1] or reel[1] == reel[2] or reel[0] == reel[2]:
            gain = mise * 2
            result = "Gagné"
        else:
            gain = 0
            result = "Perdu"

        user_data["balance"] += gain
        self.save(ctx.guild.id)

        embed = discord.Embed(title="Machine à sous", color=discord.Color.gold())
        embed.add_field(name="Résultat", value=" | ".join(reel))
        embed.add_field(name="Gain/perte", value=f"{gain - mise:,} €")
        embed.add_field(name="Message", value=result)
        await ctx.send(embed=embed)

        await self.log_transaction(ctx.guild.id, f"🎰 {ctx.author} a joué au slot : mise={mise}, résultat={' '.join(reel)}, {result}, gain/perte={gain - mise:,} €")

async def setup(bot):
    await bot.add_cog(Economy(bot))