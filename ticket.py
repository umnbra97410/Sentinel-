import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import asyncio

CONFIG_FOLDER = "ticket_configs"
if not os.path.exists(CONFIG_FOLDER):
    os.makedirs(CONFIG_FOLDER)

def get_config_path(guild_id):
    return os.path.join(CONFIG_FOLDER, f"{guild_id}.json")

def load_config(guild_id):
    path = get_config_path(guild_id)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_config(guild_id, data):
    path = get_config_path(guild_id)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


class TicketPanelButton(Button):
    def __init__(self):
        super().__init__(label="🎫 Ouvrir un ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_button")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        config = load_config(guild.id)
        if not config.get("ticket_category"):
            return await interaction.response.send_message("❌ Le système de ticket n'est pas configuré.", ephemeral=True)

        # Vérifier si user a déjà un ticket ouvert
        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.id}")
        if existing:
            return await interaction.response.send_message(f"❗ Vous avez déjà un ticket ouvert : {existing.mention}", ephemeral=True)

        category = guild.get_channel(config["ticket_category"])
        if not category:
            return await interaction.response.send_message("❌ La catégorie des tickets configurée n'existe plus.", ephemeral=True)

        support_roles = [guild.get_role(rid) for rid in config.get("support_roles", []) if guild.get_role(rid)]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role in support_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(f"ticket-{user.id}", category=category, overwrites=overwrites)

        embed = discord.Embed(
            title="🎟️ Ticket Ouvert",
            description=f"{user.mention}, un membre du support va bientôt prendre en charge votre ticket.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Ticket créé par {user}", icon_url=user.avatar.url if user.avatar else None)
        embed.timestamp = discord.utils.utcnow()

        view = TicketActionsView(user)

        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Ticket créé : {channel.mention}", ephemeral=True)

        # Log
        log_channel_id = config.get("log_channel")
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🎫 Ticket Ouvert",
                    description=f"{user.mention} a ouvert le ticket {channel.mention}",
                    color=discord.Color.green()
                )
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)


class ClaimButton(Button):
    def __init__(self):
        super().__init__(label="🛡️ Claim", style=discord.ButtonStyle.gray, custom_id="claim_ticket")

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        user = interaction.user
        guild = interaction.guild

        if not channel.name.startswith("ticket-"):
            return await interaction.response.send_message("Ce bouton ne peut être utilisé que dans un ticket.", ephemeral=True)

        # Récupérer config pour les rôles support
        config = load_config(guild.id)
        support_roles = [guild.get_role(rid) for rid in config.get("support_roles", []) if guild.get_role(rid)]

        # Vérifier si utilisateur est support
        if not any(role in user.roles for role in support_roles):
            return await interaction.response.send_message("❌ Vous devez être un membre du support pour réclamer un ticket.", ephemeral=True)

        # Modifier les permissions du channel pour que seul le claimant + support + user aient accès en enlevant les autres support qui n'ont pas claim
        overwrites = channel.overwrites
        ticket_owner_id = int(channel.name.split("-")[1])
        ticket_owner = guild.get_member(ticket_owner_id)
        if ticket_owner is None:
            return await interaction.response.send_message("Erreur : propriétaire du ticket introuvable.", ephemeral=True)

        # Retirer tous les rôles support à l'exception du claimant
        for role in support_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=False)

        # Laisser accès à claimant, propriétaire du ticket et @everyone restreint
        overwrites[user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        overwrites[ticket_owner] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)

        try:
            await channel.edit(overwrites=overwrites)
        except Exception as e:
            return await interaction.response.send_message(f"Erreur lors de la modification des permissions : {e}", ephemeral=True)

        await interaction.response.send_message(f"🛡️ {user.mention} a réclamé ce ticket.", ephemeral=False)


class CloseButton(Button):
    def __init__(self):
        super().__init__(label="🔒 Close", style=discord.ButtonStyle.red, custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        user = interaction.user

        if not channel.name.startswith("ticket-"):
            return await interaction.response.send_message("Ce bouton ne peut être utilisé que dans un ticket.", ephemeral=True)

        await interaction.response.send_message("Fermeture du ticket dans 5 secondes...", ephemeral=True)
        await asyncio.sleep(5)

        try:
            await channel.delete(reason=f"Ticket fermé par {user}")
        except Exception as e:
            await interaction.followup.send(f"Erreur lors de la fermeture : {e}", ephemeral=True)


class TranscriptButton(Button):
    def __init__(self):
        super().__init__(label="📜 Transcript", style=discord.ButtonStyle.blurple, custom_id="transcript_ticket")

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user

        if not channel.name.startswith("ticket-"):
            return await interaction.response.send_message("Ce bouton ne peut être utilisé que dans un ticket.", ephemeral=True)

        config = load_config(guild.id)
        log_channel_id = config.get("log_channel")
        if not log_channel_id:
            return await interaction.response.send_message("❌ Aucun salon de logs configuré pour ce serveur.", ephemeral=True)

        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return await interaction.response.send_message("❌ Le salon de logs configuré n'existe plus.", ephemeral=True)

        # Récupérer messages du channel (limite 1000)
        messages = []
        async for msg in channel.history(limit=1000, oldest_first=True):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M")
            author = msg.author
            content = msg.content
            # Ne pas inclure messages bots ?
            if content or msg.attachments:
                messages.append(f"[{timestamp}] {author} : {content}")
                for att in msg.attachments:
                    messages[-1] += f" [Attachment: {att.url}]"

        if not messages:
            return await interaction.response.send_message("Aucun message à transcrire.", ephemeral=True)

        transcript_text = "\n".join(messages)
        # Discord limite 2000 caractères par message, on split si besoin
        chunks = [transcript_text[i:i+1990] for i in range(0, len(transcript_text), 1990)]

        await interaction.response.send_message(f"📜 Transcription envoyée dans {log_channel.mention}.", ephemeral=True)
        for chunk in chunks:
            await log_channel.send(f"**Transcription du ticket {channel.name} :**\n```txt\n{chunk}\n```")


class TicketActionsView(View):
    def __init__(self, ticket_owner):
        super().__init__(timeout=None)
        self.ticket_owner = ticket_owner
        self.add_item(ClaimButton())
        self.add_item(CloseButton())
        self.add_item(TranscriptButton())

class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketPanelButton())

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(TicketPanelView())    # Pour que le bouton fonctionne après reboot
        bot.add_view(TicketActionsView(None)) # Nécessaire pour persistence, ticket_owner pas utilisé ici

    @commands.command(help="Définit la catégorie où seront créés les tickets.")
    @commands.has_permissions(administrator=True)
    async def setticketcategory(self, ctx, category: discord.CategoryChannel):
        config = load_config(ctx.guild.id)
        config["ticket_category"] = category.id
        save_config(ctx.guild.id, config)
        await ctx.send(f"✅ Catégorie des tickets définie sur {category.name}.")

    @commands.command(help="Définit le salon où les logs des tickets seront envoyés.")
    @commands.has_permissions(administrator=True)
    async def setticketlog(self, ctx, channel: discord.TextChannel):
        config = load_config(ctx.guild.id)
        config["log_channel"] = channel.id
        save_config(ctx.guild.id, config)
        await ctx.send(f"📝 Salon de logs défini sur {channel.mention}.")

    @commands.command(help="Ajoute un ou plusieurs rôles support pour les tickets (mentionnez-les).")
    @commands.has_permissions(administrator=True)
    async def addticketroles(self, ctx, *roles: discord.Role):
        config = load_config(ctx.guild.id)
        existing_roles = config.get("support_roles", [])

        added = []
        already = []
        for role in roles:
            if role.id not in existing_roles:
                existing_roles.append(role.id)
                added.append(role.mention)
            else:
                already.append(role.mention)
        config["support_roles"] = existing_roles
        save_config(ctx.guild.id, config)

        msg = ""
        if added:
            msg += f"✅ Rôles ajoutés au support : {', '.join(added)}\n"
        if already:
            msg += f"⚠️ Rôles déjà présents : {', '.join(already)}"
        await ctx.send(msg)

    @commands.command(help="Retire un ou plusieurs rôles support des tickets (mentionnez-les).")
    @commands.has_permissions(administrator=True)
    async def removeticketroles(self, ctx, *roles: discord.Role):
        config = load_config(ctx.guild.id)
        existing_roles = config.get("support_roles", [])

        removed = []
        not_found = []
        for role in roles:
            if role.id in existing_roles:
                existing_roles.remove(role.id)
                removed.append(role.mention)
            else:
                not_found.append(role.mention)
        config["support_roles"] = existing_roles
        save_config(ctx.guild.id, config)

        msg = ""
        if removed:
            msg += f"🗑️ Rôles retirés du support : {', '.join(removed)}\n"
        if not_found:
            msg += f"❌ Rôles non trouvés : {', '.join(not_found)}"
        await ctx.send(msg)

    @commands.command(help="Affiche les rôles support actuels pour les tickets.")
    async def showticketroles(self, ctx):
        config = load_config(ctx.guild.id)
        roles = config.get("support_roles", [])
        if not roles:
            return await ctx.send("⚠️ Aucun rôle support configuré.")
        role_mentions = [f"<@&{rid}>" for rid in roles]
        await ctx.send(f"📋 Rôles support : {', '.join(role_mentions)}")

    @commands.command(help="Envoie le panneau d'ouverture de ticket avec le bouton.")
    async def ticketpanel(self, ctx):
        view = TicketPanelView()
        await ctx.send("🎫 Cliquez sur le bouton ci-dessous pour ouvrir un ticket :", view=view)


async def setup(bot):
    await bot.add_cog(Tickets(bot))