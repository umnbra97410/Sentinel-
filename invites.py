import discord
from discord.ext import commands
import json
import os

INVITE_FILE = "data/invites.json"

def load_invites():
    if not os.path.exists(INVITE_FILE):
        with open(INVITE_FILE, "w") as f:
            json.dump({}, f)
    with open(INVITE_FILE, "r") as f:
        return json.load(f)

def save_invites(data):
    with open(INVITE_FILE, "w") as f:
        json.dump(data, f, indent=4)

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}
        self.data = load_invites()

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.invites[guild.id] = await guild.invites()

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        self.invites[invite.guild.id] = await invite.guild.invites()

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        self.invites[invite.guild.id] = await invite.guild.invites()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            guild = member.guild
            before = self.invites[guild.id]
            after = await guild.invites()
            self.invites[guild.id] = after

            used = None
            for old in before:
                for new in after:
                    if old.code == new.code and new.uses > old.uses:
                        used = new
                        break

            if not used:
                return

            inviter_id = str(used.inviter.id)
            guild_id = str(guild.id)

            self.data.setdefault(guild_id, {}).setdefault(inviter_id, 0)
            self.data[guild_id][inviter_id] += 1
            save_invites(self.data)

            # LOGS
            log_id = self.data.get(guild_id, {}).get("log_channel")
            if log_id:
                log_channel = guild.get_channel(log_id)
                if log_channel:
                    await log_channel.send(
                        f"📥 {member.mention} a été invité par {used.inviter.mention} (`{used.inviter}`)\n"
                        f"🎯 Total: **{self.data[guild_id][inviter_id]}** invites."
                    )

        except Exception as e:
            print(f"Invite tracking error: {e}")

    @commands.command(name="invites", aliases=['i'])
    async def invites(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        count = self.data.get(str(ctx.guild.id), {}).get(str(member.id), 0)
        await ctx.send(f"📨 {member.mention} a invité **{count}** membres.")

    @commands.command(name="topinvites", aliases=['ti'])
    async def topinvites(self, ctx):
        guild_id = str(ctx.guild.id)
        invites = self.data.get(guild_id, {})

        if not invites:
            return await ctx.send("❌ Aucun système d'invites détecté.")

        top = sorted(invites.items(), key=lambda x: x[1], reverse=True)
        embed = discord.Embed(title="🏆 Top Inviteurs", color=discord.Color.blurple())

        for i, (user_id, count) in enumerate(top[:10], start=1):
            user = ctx.guild.get_member(int(user_id))
            name = user.mention if user else f"Utilisateur {user_id}"
            embed.add_field(name=f"#{i} - {name}", value=f"{count} invites", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="setinvitelog", aliases=['inviteslogs'])
    @commands.has_permissions(administrator=True)
    async def setinvitelog(self, ctx, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        self.data.setdefault(guild_id, {})["log_channel"] = channel.id
        save_invites(self.data)
        await ctx.send(f"✅ Salon de logs d'invites défini sur {channel.mention}.")

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))