from discord.ext import commands
import discord

class DMAll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dmall", help= "Dm tout un serveurs")
    @commands.has_permissions(administrator=True)
    async def dmall(self, ctx, *, message: str):
        count = 0
        for member in ctx.guild.members:
            if member.bot:
                continue
            try:
                await member.send(message)
                count += 1
            except Exception:
                pass
        await ctx.send(f"✅ Message envoyé en DM à {count} membres.")

    @commands.command(name="dm", help= "Envoie un message à un membre particulier")
    @commands.has_permissions(administrator=True)
    async def dm(self, ctx, member: discord.Member, *, message: str):
        try:
            await member.send(message)
            await ctx.send(f"✅ Message envoyé en DM à {member.display_name}.")
        except Exception:
            await ctx.send(f"❌ Impossible d'envoyer un DM à {member.display_name}.")

    @commands.command(name="dmrole", help= "Envoie un DM aux utilisateurs ayant un rôle spécifique")
    @commands.has_permissions(administrator=True)
    async def dmrole(self, ctx, role: discord.Role, *, message: str):
        count = 0
        for member in role.members:
            if member.bot:
                continue
            try:
                await member.send(message)
                count += 1
            except Exception:
                pass
        await ctx.send(f"✅ Message envoyé en DM à {count} membres avec le rôle {role.name}.")

async def setup(bot):
    await bot.add_cog(DMAll(bot))