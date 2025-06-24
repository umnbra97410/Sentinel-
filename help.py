import discord
from discord.ext import commands

class HelpDropdown(discord.ui.Select):
    def __init__(self, bot, prefix, cogs_slice):
        self.bot = bot
        self.prefix = prefix

        options = [
            discord.SelectOption(
                label=cog_name,
                description=f"{len([cmd for cmd in cog.get_commands() if not cmd.hidden])} commande(s)",
                value=cog_name
            )
            for cog_name, cog in cogs_slice
            if len([cmd for cmd in cog.get_commands() if not cmd.hidden]) > 0
        ]

        super().__init__(
            placeholder="📂 Choisis une catégorie",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        cog_name = self.values[0]
        cog = self.bot.get_cog(cog_name)
        if not cog:
            await interaction.response.send_message("❌ Cette catégorie n'existe plus.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Aide - {cog_name}",
            description=f"Voici les commandes disponibles dans **{cog_name}** :",
            color=discord.Color.blurple()
        )

        for command in cog.get_commands():
            if not command.hidden:
                embed.add_field(
                    name=f"`{self.prefix}{command.name}`",
                    value=command.help or "Pas de description.",
                    inline=False
                )

        embed.set_image(url=" your logo link")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, bot, prefix):
        super().__init__(timeout=180)
        self.bot = bot
        self.prefix = prefix

        self.cogs = [(name, cog) for name, cog in bot.cogs.items()
                     if len([cmd for cmd in cog.get_commands() if not cmd.hidden]) > 0]

        self.pages = [self.cogs[i:i + 25] for i in range(0, len(self.cogs), 25)]
        self.current_page = 0

        self.select = HelpDropdown(bot, prefix, self.pages[self.current_page])
        self.add_item(self.select)

        self.prev_button = discord.ui.Button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
        self.next_button = discord.ui.Button(label="➡️ Suivant", style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page
        self.add_item(self.prev_button)
        self.add_item(self.next_button)

        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= len(self.pages) - 1

    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_view(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_view(interaction)

    async def update_view(self, interaction: discord.Interaction):
        self.clear_items()
        self.select = HelpDropdown(self.bot, self.prefix, self.pages[self.current_page])
        self.add_item(self.select)
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.update_buttons()
        await interaction.response.edit_message(view=self)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prefix = "!"  # Change ce prefix si nécessaire

    @commands.command(name="help")
    async def help_command(self, ctx, *, categorie: str = None):
        if categorie:
            # Si l'utilisateur demande une catégorie spécifique (ex: !help mod)
            cog = self.bot.get_cog(categorie.capitalize())
            if not cog:
                await ctx.send(f"❌ Aucune catégorie trouvée avec le nom : `{categorie}`.")
                return

            visible_commands = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            if not visible_commands:
                await ctx.send(f"❌ Aucune commande visible dans la catégorie : `{categorie}`.")
                return

            embed = discord.Embed(
                title=f"📘 Aide - {cog.qualified_name}",
                description=f"Voici les commandes disponibles dans **{cog.qualified_name}** :",
                color=discord.Color.blurple()
            )

            for cmd in visible_commands:
                embed.add_field(
                    name=f"`{self.prefix}{cmd.name}`",
                    value=cmd.help or "Pas de description.",
                    inline=False
                )

            embed.set_image(url=" other link ")
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            await ctx.send(embed=embed)

        else:
            # Menu déroulant normal
            total_commands = sum(len([cmd for cmd in cog.get_commands() if not cmd.hidden]) for cog in self.bot.cogs.values())
            embed = discord.Embed(
                title="📘 Aide - Menu principal",
                description="Utilise le menu déroulant ci-dessous pour naviguer entre les catégories de commandes.",
                color=discord.Color.blurple()
            )
            embed.add_field(name="🤖 Serveurs", value=f"{len(self.bot.guilds)}", inline=True)
            embed.add_field(name="🧠 Commandes", value=f"{total_commands}", inline=True)
            embed.add_field(name="📝 Prefix", value=f"`{self.prefix}`", inline=True)
            embed.set_image(url=" your banner link ")
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            view = HelpView(self.bot, self.prefix)
            await ctx.send(embed=embed, view=view)
        
    @commands.command(name="allcmds")
    async def all_commands(self, ctx):
        for cog_name, cog in self.bot.cogs.items():
            visible_commands = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            if not visible_commands:
                continue

            embed = discord.Embed(
                title=f"📚 Commandes - {cog_name}",
                description=f"Voici les commandes disponibles dans **{cog_name}** :",
                color=discord.Color.blurple()
            )

            for cmd in visible_commands:
                name = f"{self.prefix}{cmd.name}"
                description = cmd.help or "Pas de description."
                embed.add_field(name=name, value=description, inline=False)

            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed)

        # Commandes sans catégorie
        other_cmds = [cmd for cmd in self.bot.commands if not cmd.hidden and not cmd.cog_name]
        if other_cmds:
            embed = discord.Embed(
                title="📚 Commandes diverses",
                description="Commandes sans catégorie définie :",
                color=discord.Color.blurple()
            )
            for cmd in other_cmds:
                name = f"{self.prefix}{cmd.name}"
                description = cmd.help or "Pas de description."
                embed.add_field(name=name, value=description, inline=False)

            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
