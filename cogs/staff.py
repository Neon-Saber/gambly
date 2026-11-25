import discord
from discord import Option
from discord.ext import commands

import cog_utils as cu
import perms
import server_layout as sl

MOVED = ["kick", "ban", "unban", "mute", "unmute", "warn", "warnings", "clearwarns", "purge", "slowmode",
         "lock", "unlock", "ticket-panel", "add-to-ticket", "diag", "welcome", "level", "setmanager", "setprefix",
         "addchips", "removechips", "banuser", "unbanuser", "reset", "setbalance", "setannounce", "forgive", "giveaway"]


async def gate(ctx, cmd):
    if ctx.guild is None:
        await ctx.respond("that only works in the main server", ephemeral=True)
        return False
    ok, why = perms.allowed(ctx.author, cmd)
    if not ok:
        await ctx.respond(why, ephemeral=True)
    return ok


async def target_ok(ctx, member, what):
    if isinstance(member, discord.Member) and not perms.outranks(ctx.author, member):
        await ctx.respond(f"can't {what} someone ranked the same or above you", ephemeral=True)
        return False
    return True


class Staff(commands.Cog):
    mod = discord.SlashCommandGroup("mod", "security team - mutes, warns, kicks, bans",
                                    default_member_permissions=discord.Permissions(moderate_members=True))
    casino = discord.SlashCommandGroup("casino", "dealers + floor managers - chips and giveaways",
                                       default_member_permissions=discord.Permissions(manage_events=True))
    admin = discord.SlashCommandGroup("admin", "floor managers and up",
                                      default_member_permissions=discord.Permissions(manage_threads=True))
    owner = discord.SlashCommandGroup("owner", "server owner only",
                                      default_member_permissions=discord.Permissions(administrator=True))
    role = admin.create_subgroup("role", "give or take a role")

    def __init__(self, bot):
        self.bot = bot
        self.c = bot.casino

    def m(self):
        return self.bot.get_cog("Moderation")

    @mod.command(name="warn", description="warn someone (logged)")
    async def warn(self, ctx, member: Option(discord.Member, "who"), reason: Option(str, "why", required=False) = None):
        if await gate(ctx, "warn") and await target_ok(ctx, member, "warn"):
            await self.m()._do_warn(ctx, member, reason)

    @mod.command(name="warnings", description="see someone's warnings")
    async def warnings(self, ctx, member: Option(discord.Member, "who")):
        if await gate(ctx, "warnings"):
            await self.m()._do_warnings(ctx, member)

    @mod.command(name="mute", description="timeout someone - how long depends on your rank")
    async def mute(self, ctx, member: Option(discord.Member, "who"),
                   duration: Option(str, "10m, 2h, 1d... bare number = minutes"),
                   reason: Option(str, "why", required=False) = None):
        if not (await gate(ctx, "mute") and await target_ok(ctx, member, "mute")):
            return
        try:
            seconds = cu.parse_duration(duration, default_unit="m")
        except ValueError as e:
            return await ctx.respond(str(e), ephemeral=True)
        await self.m()._do_mute(ctx, member, seconds, reason)

    @mod.command(name="unmute", description="take a timeout off")
    async def unmute(self, ctx, member: Option(discord.Member, "who")):
        if await gate(ctx, "unmute") and await target_ok(ctx, member, "unmute"):
            await self.m()._do_unmute(ctx, member)

    @mod.command(name="purge", description="bulk delete messages here")
    async def purge(self, ctx, amount: Option(int, "how many", min_value=1, max_value=100),
                    member: Option(discord.Member, "only this person's", required=False) = None):
        if await gate(ctx, "purge"):
            await self.m()._do_purge(ctx, amount, member)

    @mod.command(name="slowmode", description="set slowmode here (or 'off')")
    async def slowmode(self, ctx, duration: Option(str, "10s, 5m, 1h or off")):
        if not await gate(ctx, "slowmode"):
            return
        try:
            seconds = self.m()._parse_slowmode_duration(duration)
        except ValueError as e:
            return await ctx.respond(str(e), ephemeral=True)
        await self.m()._do_slowmode(ctx, seconds)

    @mod.command(name="kick", description="kick someone")
    async def kick(self, ctx, member: Option(discord.Member, "who"), reason: Option(str, "why", required=False) = None):
        if await gate(ctx, "kick") and await target_ok(ctx, member, "kick"):
            await self.m()._do_kick(ctx, member, reason)

    @mod.command(name="lock", description="stop everyone talking in this channel")
    async def lock(self, ctx, reason: Option(str, "why", required=False) = None):
        if await gate(ctx, "lock"):
            await self.m()._do_lock(ctx, reason)

    @mod.command(name="unlock", description="let everyone talk here again")
    async def unlock(self, ctx):
        if await gate(ctx, "unlock"):
            await self.m()._do_unlock(ctx)

    @mod.command(name="clearwarns", description="wipe someone's warnings")
    async def clearwarnings(self, ctx, member: Option(discord.Member, "who")):
        if await gate(ctx, "clearwarns") and await target_ok(ctx, member, "clear warnings for"):
            await self.m()._do_clearwarnings(ctx, member)

    @mod.command(name="ban", description="ban someone (mention, name or id)")
    async def ban(self, ctx, user: Option(str, "mention, username or user id"),
                  reason: Option(str, "why", required=False) = None,
                  delete_days: Option(int, "days of their messages to delete", min_value=0, max_value=7, required=False) = 0):
        if not await gate(ctx, "ban"):
            return
        mid = "".join(ch for ch in user if ch.isdigit())
        target = ctx.guild.get_member(int(mid)) if mid else None
        if target and not await target_ok(ctx, target, "ban"):
            return
        await self.m()._do_ban(ctx, user, reason, delete_days)

    @mod.command(name="unban", description="unban by user id")
    async def unban(self, ctx, user_id: Option(str, "their user id")):
        if await gate(ctx, "unban"):
            await self.m()._do_unban(ctx, user_id)

    @mod.command(name="ticket-add", description="add someone to this ticket")
    async def ticket_add(self, ctx, member: Option(discord.Member, "who")):
        if await gate(ctx, "add-to-ticket"):
            await self.bot.get_cog("Tickets")._do_add_to_ticket(ctx, member)

    @mod.command(name="ranks", description="the staff ladder and what each rank can do")
    async def ranks(self, ctx):
        mine = perms.tier_of(ctx.author) if ctx.guild else 0
        lines = []
        for t in range(9, 0, -1):
            cmds = sorted(k for k, v in perms.MOD_TIERS.items() if v == t)
            lines.append(f"{'➜ ' if t == mine else ''}**{perms.TIERS[t]}** - {', '.join(cmds) or 'everything below'}")
        e = discord.Embed(title="staff ladder", color=0xFF6AD5, description="\n".join(lines))
        e.add_field(name="side roles", value="🎰 Dealer - chips commands (`/casino`)\n🎤 Event Host - giveaways\n😴 On Break - blocks your staff cmds till you take it off", inline=False)
        e.add_field(name="caps", value="mutes: trial/junior 1h · security 1d · senior 7d · head+ 28d\npurge: trial/junior 25 · security+ 100", inline=False)
        e.set_footer(text=f"you: {perms.TIERS.get(mine, 'member')}")
        await ctx.respond(embed=e, ephemeral=True)

    @casino.command(name="addchips", description="give someone chips")
    async def addchips(self, ctx, user: Option(discord.Member, "who"), amount: Option(int, "how many", min_value=1)):
        if await gate(ctx, "addchips"):
            await self.c.do_addchips(ctx, user, amount)

    @casino.command(name="removechips", description="take chips from someone")
    async def removechips(self, ctx, user: Option(discord.Member, "who"), amount: Option(int, "how many", min_value=1)):
        if await gate(ctx, "removechips"):
            await self.c.do_removechips(ctx, user, amount)

    @casino.command(name="setbalance", description="set someone's wallet/bank directly")
    async def setbalance(self, ctx, user: Option(discord.Member, "who"),
                         wallet: Option(int, "wallet", required=False, min_value=0) = None,
                         bank: Option(int, "bank", required=False, min_value=0) = None):
        if not await gate(ctx, "setbalance"):
            return
        if wallet is None and bank is None:
            return await ctx.respond("give me a wallet or bank amount", ephemeral=True)
        await self.c.do_setbalance(ctx, user, wallet, bank)

    @casino.command(name="forgive", description="wipe someone's debt")
    async def forgive(self, ctx, user: Option(discord.Member, "who")):
        if await gate(ctx, "forgive"):
            await self.c.do_forgive(ctx, user)

    @casino.command(name="ban", description="block someone from the games")
    async def cban(self, ctx, user: Option(discord.Member, "who")):
        if await gate(ctx, "banuser") and await target_ok(ctx, user, "casino-ban"):
            await self.c.do_ban(ctx, user, True)

    @casino.command(name="unban", description="let someone play again")
    async def cunban(self, ctx, user: Option(discord.Member, "who")):
        if await gate(ctx, "unbanuser"):
            await self.c.do_ban(ctx, user, False)

    @casino.command(name="reset", description="reset one person's account")
    async def creset(self, ctx, user: Option(discord.Member, "who")):
        if await gate(ctx, "reset") and await target_ok(ctx, user, "reset"):
            await self.c.do_reset(ctx, user)

    @casino.command(name="giveaway", description="house-funded chip giveaway")
    async def giveaway(self, ctx, prize: Option(int, "chips per winner", min_value=1),
                       minutes: Option(int, "how long", min_value=1, max_value=10080),
                       winners: Option(int, "how many winners", min_value=1, max_value=20, required=False) = 1):
        if await gate(ctx, "giveaway"):
            await self.bot.get_cog("EconomyPlus")._giveaway(ctx, prize, minutes, winners)

    async def _role(self, ctx, member, role, give):
        if not (await gate(ctx, "role") and await target_ok(ctx, member, "change roles for")):
            return
        why = perms.role_blocked(ctx.author, role)
        if why:
            return await ctx.respond(why, ephemeral=True)
        try:
            if give:
                await member.add_roles(role, reason=f"/admin role give by {ctx.author}")
            else:
                await member.remove_roles(role, reason=f"/admin role take by {ctx.author}")
        except discord.Forbidden:
            return await ctx.respond("discord said no - my role probably isn't high enough", ephemeral=True)
        self.c.log_event(ctx.guild.name, f"{ctx.author.display_name} {'gave' if give else 'took'} {role.name} {'to' if give else 'from'} {member.display_name}")
        await ctx.respond(f"{'gave' if give else 'took'} {role.mention} {'to' if give else 'from'} {member.mention}",
                          allowed_mentions=discord.AllowedMentions.none())

    @role.command(name="give", description="give someone a role")
    async def role_give(self, ctx, member: Option(discord.Member, "who"), role: Option(discord.Role, "which role")):
        await self._role(ctx, member, role, True)

    @role.command(name="take", description="take a role off someone")
    async def role_take(self, ctx, member: Option(discord.Member, "who"), role: Option(discord.Role, "which role")):
        await self._role(ctx, member, role, False)

    @admin.command(name="ticket-panel", description="post the open-a-ticket panel here")
    async def ticket_panel(self, ctx, title: Option(str, "title", required=False) = "need help?",
                           description: Option(str, "text", required=False) = "click below to open a private ticket with staff."):
        if await gate(ctx, "ticket-panel"):
            await self.bot.get_cog("Tickets")._do_ticket_panel(ctx, title, description)

    @admin.command(name="announce-channel", description="where weekly tournament results go")
    async def setannounce(self, ctx, channel: Option(discord.TextChannel, "channel")):
        if await gate(ctx, "setannounce"):
            await self.c.do_setannounce(ctx, channel)

    @admin.command(name="prefix", description="change the ! prefix")
    async def setprefix(self, ctx, prefix: Option(str, "like ! ? or .")):
        if await gate(ctx, "setprefix"):
            await self.c.do_setprefix(ctx, prefix)

    @admin.command(name="diag", description="check every dashboard feature is set up right")
    async def diag(self, ctx):
        if await gate(ctx, "diag"):
            await cu.maybe_defer(ctx, ephemeral=True)
            await self.bot.get_cog("Diagnostics")._run(ctx)

    @admin.command(name="test-welcome", description="preview the welcome message")
    async def test_welcome(self, ctx):
        if await gate(ctx, "test-welcome"):
            await self.bot.get_cog("Welcome")._do_test(ctx)

    @admin.command(name="test-levelup", description="preview the level-up message")
    async def test_levelup(self, ctx):
        if await gate(ctx, "test-levelup"):
            await self.bot.get_cog("Leveling")._do_test(ctx)

    @owner.command(name="managers", description="pick casino managers (old system, Dealer role is easier)")
    async def setmanager(self, ctx):
        if await gate(ctx, "setmanager"):
            await ctx.respond("pick a user, pick a role, or make a 'Casino Staff' role:", view=self.c.ManagerPicker(ctx.author), ephemeral=True)

    @owner.command(name="testmode", description="your own bets always win while it's on (for testing payouts)")
    async def testmode(self, ctx):
        if await gate(ctx, "testmode"):
            await self.c.do_testmode(ctx)

    @owner.command(name="wipe-economy", description="reset EVERYONE's chips - asks first")
    async def wipe(self, ctx):
        if await gate(ctx, "wipe-economy"):
            await self.c.do_reset_all(ctx)


def strip_moved(bot):
    for cmd in list(bot.pending_application_commands):
        cog = getattr(cmd, "cog", None)
        if cmd.name in MOVED and (cog is None or cog.qualified_name != "Staff"):
            bot.remove_application_command(cmd)


def setup(bot):
    bot.add_cog(Staff(bot))
    strip_moved(bot)
