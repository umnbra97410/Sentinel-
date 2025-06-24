import discord
from discord.ext import commands
import asyncio
from customprefix import get_prefix
from datetime import datetime, timedelta, timezone

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

initial_extensions = [
    'moderation', 'economie', 'backup', 'help', 'admin', 'security', 'autorole',
    'stats', 'welcome', 'dmall', 'logs', 'giveaway', 'ticket', 'verification',
    'bump', 'suggestion', 'maintenance', 'voice', 'info', 'premium', 'customprefix',
    'servers', 'managers', 'invites', 'delete', 'baninfo', 'status',
    'reactroles'
]

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

    reunion_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")

    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name=f"Dev By Zeyrox"
    )

    await bot.change_presence(status=discord.Status.dnd, activity=activity)

    for ext in initial_extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Extension chargée : {ext}")
        except Exception as e:
            print(f"❌ Erreur chargement extension {ext} : {e}")
            
bot.run("")            
