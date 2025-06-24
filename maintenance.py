import discord
from discord.ext import commands
import json
import os

SUPPORT_GUILD_ID = 1374803429259608165
CHANNEL_ID = 1385262713256808680

FILE_PATH = "commands_added.json"


class Maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Crée le fichier JSON s'il n'existe pas ou a une mauvaise structure
        if not os.path.exists(FILE_PATH):
            data = {
                "all_commands": [],
                "notified_commands": []
            }
            with open(FILE_PATH, "w") as f:
                json.dump(data, f, indent=4)

        # Lance la tâche d'envoi automatique au démarrage
        self.bot.loop.create_task(self.scan_and_notify_on_ready())

    def load_data(self):
        with open(FILE_PATH, "r") as f:
            data = json.load(f)
        # Vérifie la structure
        if not isinstance(data, dict) or "all_commands" not in data or "notified_commands" not in data:
            data = {
                "all_commands": [],
                "notified_commands": []
            }
            self.save_data(data)
        return data

    def save_data(self, data):
        with open(FILE_PATH, "w") as f:
            json.dump(data, f, indent=4)

    def get_current_command_names(self):
        # Récupère la liste des noms de commandes actives dans le bot
        return [command.name for command in self.bot.commands]

    async def send_maintenance_message_in_channel(self):
        guild = self.bot.get_guild(SUPPORT_GUILD_ID)
        if not guild:
            print("Serveur support introuvable.")
            return False

        channel = guild.get_channel(CHANNEL_ID)
        if not channel:
            print("Salon support introuvable.")
            return False

        data = self.load_data()
        all_cmds = set(data["all_commands"])
        notified_cmds = set(data["notified_commands"])

        new_cmds = list(all_cmds - notified_cmds)

        if not new_cmds:
            print("Aucune nouvelle commande à notifier.")
            return False

        message = "**🛠️ Maintenance - Nouvelles commandes ajoutées 🛠️**\n\n"
        for cmd in new_cmds:
            message += f"- {cmd}\n"

        await channel.send(message)

        data["notified_commands"].extend(new_cmds)
        self.save_data(data)

        print(f"Message de maintenance envoyé dans {channel} avec {len(new_cmds)} nouvelles commandes.")
        return True

    async def scan_and_notify_on_ready(self):
        await self.bot.wait_until_ready()

        data = self.load_data()
        current_commands = set(self.get_current_command_names())
        saved_commands = set(data["all_commands"])

        new_commands = current_commands - saved_commands
        if new_commands:
            data["all_commands"].extend(new_commands)
            self.save_data(data)
            print(f"{len(new_commands)} nouvelle(s) commande(s) détectée(s) et ajoutée(s) automatiquement.")

        await self.send_maintenance_message_in_channel()

    @commands.command(name="scancommands")
    @commands.has_permissions(administrator=True)
    async def scan_commands(self, ctx):
        """Scanne les commandes du bot et ajoute les nouvelles"""
        data = self.load_data()
        current_commands = set(self.get_current_command_names())
        saved_commands = set(data["all_commands"])

        new_commands = current_commands - saved_commands

        if not new_commands:
            await ctx.send("Aucune nouvelle commande détectée.")
            return

        data["all_commands"].extend(new_commands)
        self.save_data(data)

        await ctx.send(f"{len(new_commands)} nouvelle(s) commande(s) détectée(s) et ajoutée(s) automatiquement :\n" + "\n".join(new_commands))

    @commands.command(name="maintenance")
    @commands.has_permissions(administrator=True)
    async def maintenance_command(self, ctx):
        """Envoie manuellement la notification des nouvelles commandes"""
        sent = await self.send_maintenance_message_in_channel()
        if sent:
            await ctx.send("Message de maintenance envoyé.")
        else:
            await ctx.send("Aucune nouvelle commande à notifier.")

    @commands.command(name="clearcommands")
    @commands.has_permissions(administrator=True)
    async def clear_commands(self, ctx):
        """Vide la liste des commandes ajoutées et notifiées"""
        data = {
            "all_commands": [],
            "notified_commands": []
        }
        self.save_data(data)
        await ctx.send("Liste des commandes ajoutées et notifiées vidée.")


async def setup(bot):
    await bot.add_cog(Maintenance(bot))