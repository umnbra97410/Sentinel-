import discord
from discord.ext import commands

class Delete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(help="Synchronise les permissions d'un salon ou d'une catégorie avec sa catégorie parente : !sync <id>")
    @commands.has_permissions(manage_channels=True)
    async def sync(self, ctx, target_id: int):
        target = ctx.guild.get_channel(target_id)

        if not target:
            return await ctx.send("❌ Aucun salon ou catégorie trouvé avec cet ID.")

        # Si c'est une catégorie
        if isinstance(target, discord.CategoryChannel):
            count = 0
            for channel in target.channels:
                try:
                    await channel.edit(sync_permissions=True)
                    count += 1
                except discord.Forbidden:
                    await ctx.send(f"⚠️ Impossible de synchroniser {channel.name} (permissions manquantes).")
            await ctx.send(f"✅ Permissions synchronisées pour `{count}` salons dans la catégorie `{target.name}`.")

        # Si c'est un salon texte ou vocal
        elif isinstance(target, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
            if target.category is None:
                return await ctx.send("❌ Ce salon n'a pas de catégorie parente à synchroniser.")
            try:
                await target.edit(sync_permissions=True)
                await ctx.send(f"✅ Permissions de `{target.name}` synchronisées avec sa catégorie parente `{target.category.name}`.")
            except discord.Forbidden:
                await ctx.send("❌ Je n'ai pas la permission de modifier ce salon.")
        else:
            await ctx.send("❌ Ce type de salon n'est pas supporté.")

    @commands.command(help="Supprime tous les salons d'une catégorie + la catégorie elle-même : !delcat <id_catégorie>")
    @commands.has_permissions(manage_channels=True)
    async def delcat(self, ctx, category_id: int):
        category = discord.utils.get(ctx.guild.categories, id=category_id)
        if not category:
            return await ctx.send("❌ Catégorie introuvable.")

        # Supprimer tous les salons de la catégorie
        for channel in category.channels:
            try:
                await channel.delete()
            except discord.Forbidden:
                await ctx.send(f"❌ Impossible de supprimer {channel.name} (permissions manquantes).")

        # Supprimer la catégorie elle-même
        try:
            await category.delete()
            await ctx.send(f"✅ Tous les salons et la catégorie `{category.name}` ont été supprimés.")
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de supprimer la catégorie.")

    @commands.command(help="Supprime un salon texte ou vocal : !delsalon <#salon ou id>")
    @commands.has_permissions(manage_channels=True)
    async def delsalon(self, ctx, channel: discord.abc.GuildChannel):
        try:
            await channel.delete()
            await ctx.send(f"✅ Salon `{channel.name}` supprimé.")
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de supprimer ce salon.")
        except Exception as e:
            await ctx.send(f"❌ Erreur : {e}")

    @commands.command(help="Supprime un salon vocal uniquement : !delvoc <id>")
    @commands.has_permissions(manage_channels=True)
    async def delvoc(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)
        if not isinstance(channel, discord.VoiceChannel):
            return await ctx.send("❌ Ce n'est pas un salon vocal.")
        try:
            await channel.delete()
            await ctx.send(f"✅ Salon vocal `{channel.name}` supprimé.")
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de supprimer ce salon.")
        except Exception as e:
            await ctx.send(f"❌ Erreur : {e}")

async def setup(bot):
    await bot.add_cog(Delete(bot))