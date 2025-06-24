import discord
from discord.ext import commands

class VoiceManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="move")
    @commands.has_permissions(move_members=True)
    async def move_member(self, ctx, member: discord.Member, channel: discord.VoiceChannel):
        """Déplace un membre dans un salon vocal"""
        if not member.voice or not member.voice.channel:
            await ctx.send(f"❌ {member.display_name} n'est pas dans un salon vocal.")
            return
        try:
            await member.move_to(channel)
            await ctx.send(f"✅ {member.display_name} déplacé dans {channel.name}.")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors du déplacement : {e}")

    @commands.command(name="find")
    async def find_member(self, ctx, member: discord.Member):
        """Trouve dans quel salon vocal est un membre"""
        if member.voice and member.voice.channel:
            await ctx.send(f"🔍 {member.display_name} est dans le salon vocal : **{member.voice.channel.name}**")
        else:
            await ctx.send(f"❌ {member.display_name} n'est pas dans un salon vocal.")

    @commands.command(name="join")
    @commands.has_permissions(move_members=True)
    async def join_user_channel(self, ctx, target: discord.Member):
        """Déplace l'auteur de la commande dans le salon vocal du membre mentionné"""
        author = ctx.author

        if not target.voice or not target.voice.channel:
            return await ctx.send(f"❌ {target.display_name} n'est pas dans un salon vocal.")

        if not author.voice or not author.voice.channel:
            return await ctx.send(f"❌ Tu dois être dans un salon vocal pour être déplacé.")

        try:
            await author.move_to(target.voice.channel)
            await ctx.send(f"🚀 Tu as été déplacé dans **{target.voice.channel.name}** avec {target.display_name}.")
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de te déplacer.")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors du déplacement : {e}")

    @commands.command(name="bringall")
    @commands.has_permissions(move_members=True)
    async def bring_all(self, ctx, channel_from: discord.VoiceChannel, channel_to: discord.VoiceChannel):
        """Déplace tous les membres d'un salon vocal vers un autre"""
        members = channel_from.members
        if not members:
            await ctx.send(f"❌ Aucun membre à déplacer dans {channel_from.name}.")
            return

        errors = []
        for member in members:
            try:
                await member.move_to(channel_to)
            except Exception as e:
                errors.append(f"{member.display_name} : {e}")

        await ctx.send(f"✅ {len(members) - len(errors)} membre(s) déplacé(s) de {channel_from.name} vers {channel_to.name}.")

        if errors:
            await ctx.send("⚠️ Erreurs lors du déplacement :\n" + "\n".join(errors))


async def setup(bot):
    await bot.add_cog(VoiceManager(bot))