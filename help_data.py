HELP_TEXT = (
    "**money**\n"
    "`balance [user]` · `daily` (streak bonus, up to +45%) · `work` · `crime` (riskier, pays more) · `beg` · "
    "`stats [user]` · `profile [user]` · `achievements` · `hide` (hides your bank from !bal)\n\n"
    "**bank & loans**\n"
    "`deposit <amt>` / `withdraw <amt>` - bank chips can't be robbed and earn a bit of interest\n"
    "`loan <amt>` (20% interest, 24h) · `repay <amt>` · `invest <amt> <days>` - if a loan goes overdue the house "
    "takes what you have and the rest grows 5% a day\n\n"
    "**free chips**\n"
    "`/claim weekly` · `/claim monthly` · `/claim spin` (daily wheel) · `quests` (3 a day) · `trivia` · "
    "`/gather fish|mine|hunt` (10 min cooldown, loot sells instantly) · `/gather collection`\n\n"
    "**your data**\n"
    "`deletemydata` wipes your game account and level for good, no staff needed. warnings, other moderation records and unpaid loans stay\n\n"
    "**classic games**\n"
    "`coinflip <amt> <heads/tails>` · `slots <amt>` · `jackpot` · `dice <amt> <1-6>` · `roulette <amt> <red/black/green/0-36>` · "
    "`allin <red/black/green>` · `blackjack <amt>` · `war <amt>` · `hilo <amt>` · `crash <amt> <x>` · `mines <amt> [mines]` · "
    "`plinko <amt>` · `horserace <amt> <horse>` · `scratch` · `wheel <amt>` · `keno <amt> <numbers>` · "
    "`baccarat <amt> <player/banker/tie>` · `rps <amt> <pick>` · `ladder <amt> <1-6>`\n\n"
    "**/play games** (or just `!<game>`)\n"
    "cups · dragontiger · sicbo · sevens · revolver · chests · diceduel · cardguess · target · craps · threecard · "
    "bingo · towers · balloon · videopoker · rocket · penalty · doors - `/games` shows what each pays\n"
    "amounts take `250`, `15k`, `1.5m` or `all`. some games only work in their own channel, the bot tells you where\n\n"
    "**multiplayer** (main server only)\n"
    "`duel <user> <amt>` · `/play tictactoe` · `/play connect4` · `/play heist` · `lottery` · `buyticket <n>`\n\n"
    "**shop**\n"
    "`shop` · `buy <item>` · `use <item>` · `pawn <item>` (half back) · `inventory` · `craft vault`\n\n"
    "**business & upgrades**\n"
    "`business` · `buybusiness <tier>` · `collect` - income builds up by the hour\n"
    "`upgrades` · `buyupgrade <name>` - permanent boosts\n\n"
    "**rebirth**\n"
    "`rebirth` - once you're rich enough, reset for a permanent earnings + luck boost (7 max). badges stay\n\n"
    "**social** (main server only)\n"
    "`give <user> <amt>` · `rob <user>` · `bounty <user> <amt>` · `bounties` · `leaderboard` · `debtors`\n\n"
    "**levels**\n"
    "`rank [user]` · `levels` - you level up by chatting. rank roles unlock automatically\n\n"
    "**tickets & reports**\n"
    "open a ticket from the ticket panel · `close-ticket` inside it · `report <member> <reason>` or right click a "
    "message → Apps → Report Message\n\n"
    "**roles**\n"
    "grab colors, pings and pronouns from the buttons in the roles channel\n\n"
    "**security · trial+** (`/mod`)\n"
    "`warn` · `warnings` · `mute` · `unmute` · `purge` · `ticket-add` · `ranks`\n"
    "mutes max 1h and purges max 25 until security\n\n"
    "**security · junior+**\n"
    "`slowmode`\n\n"
    "**security · security+**\n"
    "`kick` · `lock` · `unlock` - mutes up to 1d (senior 7d, head 28d)\n\n"
    "**security · senior+**\n"
    "`clearwarns`\n\n"
    "**security · head+**\n"
    "`ban` · `unban`\n\n"
    "**casino staff** (`/casino` - dealers + floor managers)\n"
    "`addchips` · `removechips` · `setbalance` · `forgive` · `ban` / `unban` (from games) · `reset` · `giveaway` (hosts too)\n\n"
    "**admin** (`/admin` - floor managers+)\n"
    "`role give/take` (pit boss+ for staff ranks) · `ticket-panel` · `announce-channel` · `diag` · `test-welcome` · "
    "`test-levelup` · `prefix` (pit boss+)\n\n"
    "**owner** (`/owner` + `/setup` - the server owner only)\n"
    "`/setup build` · `/setup roles` · `/setup restyle` · `/setup preview` · `/setup undo` · `/setup onboarding` · `/owner managers` · "
    "`/owner testmode` · `/owner wipe-economy`\n\n"
    "**rules for staff**\n"
    "you can't act on anyone ranked the same as you or higher. 😴 On Break turns your staff commands off till you take it off. "
    "durations take `10m`, `2h`, `3d`, `1w` or combos like `1h30m`"
)

GROUPS = [
    ("economy", "Economy", "everyone", ["money", "bank & loans", "free chips", "your data"]),
    ("games", "Games", "everyone", ["classic games", "/play games", "multiplayer"]),
    ("shop", "Shop & business", "everyone", ["shop", "business & upgrades", "rebirth"]),
    ("server", "Server", "members of the main server", ["social", "levels", "tickets & reports", "roles"]),
    ("security", "Security staff", "trial security and up", ["security"]),
    ("staff", "Casino staff & admins", "dealers, floor managers and up", ["casino staff", "admin", "rules for staff"]),
    ("owner", "Owner", "the server owner", ["owner"]),
]

FAQ = [
    ("Is any of this real money?",
     "No. Chips are a game currency with no real-world value. You can't buy them, sell them, or cash them out, and trading them for real money or real items is against the rules."),
    ("How do I get chips?",
     "Run /daily every day, spin /claim spin, finish your three /quests, answer /trivia, and /gather fish, mine or hunt every 10 minutes. /work and /crime pay too."),
    ("A game told me to play it somewhere else. Why?",
     "Staff can lock each game to a channel so chat doesn't fill up with bets. The bot tells you which channel to use. Staff can change this on the Games page."),
    ("I can't see some slash commands.",
     "Staff commands only show for people with the right rank. Personal app commands can take a few minutes to appear after the bot restarts. If a whole command is missing, ask staff to check the Games page, it might be switched off."),
    ("What's the personal app?",
     "You can add the bot to your own Discord account and play the games in DMs, group chats or other servers. That uses a separate personal wallet, so it never touches the main server's economy."),
    ("Who can use staff commands?",
     "It depends on your rank, from Trial Security up to the server owner. /mod ranks in Discord or the Staff & roles page here shows exactly what each rank can do. Nobody can act on someone ranked the same or higher."),
    ("How do I delete my data?",
     "Run /deletemydata in Discord, or use Delete my data on your Account page here. Both remove your balances and levels and can't be undone. Warnings and other moderation records are kept so staff can still enforce the rules, and so is any unpaid loan, so you'd start back at 0 owing it. If you think a warning is wrong, open a ticket."),
    ("Where do I use commands?",
     "In the bot commands channel, or the channel made for that thing: daily and quests in daily, work and crime in work, deposits and loans in bank, buying stuff in shop, and every game at its own table. If you use one in the wrong place the bot tells you where it goes."),
    ("Why did my command get deleted in general?",
     "Chat and media channels like general, media and memes are for talking, so commands there get removed and the bot points you to bot commands. Staff commands like warn and purge work anywhere, but games and earning go in their channels for everyone, staff included."),
    ("Can I add the bot to my own server?",
     "Not as a server bot. It's locked to one server and leaves anywhere else. You can still use the personal app to play anywhere."),
]


FAQ_SECTIONS = [
    ("💰 chips", ["Is any of this real money?", "How do I get chips?"]),
    ("📍 where things go", ["Where do I use commands?", "Why did my command get deleted in general?",
                           "A game told me to play it somewhere else. Why?", "I can't see some slash commands."]),
    ("🛡️ staff & rules", ["Who can use staff commands?"]),
    ("📱 the app & your data", ["What's the personal app?", "Can I add the bot to my own server?", "How do I delete my data?"]),
]


def faq_embeds(color, guild=None):
    answers = dict(FAQ)
    out = []
    for i, (title, qs) in enumerate(FAQ_SECTIONS):
        e = discord_embed(title=title, color=color)
        if i == 0:
            e.description = "the stuff people ask the most. still stuck? open a ticket."
        for q in qs:
            if q in answers:
                e.add_field(name=q, value=answers[q][:1024], inline=False)
        out.append(e)
    out[-1].set_footer(text=(guild.name + " · " if guild else "") + "/help <command> explains any command")
    return out


STAFF_GUIDE = [
    ("📋 the basics", [
        ("before anything", "read the rules channel, you're the one enforcing it. be fair, be calm, and don't punish people you're arguing with, hand it to someone else."),
        ("on break", "grab the 😴 On Break role when you're away. it turns your staff commands off till you take it off, so nobody thinks you're ignoring them."),
        ("ranks", "you can't act on anyone ranked the same as you or higher. if someone above you is the problem, take it to the owner."),
    ]),
    ("🎫 tickets & reports", [
        ("tickets", "answer in the ticket itself, not in DMs, so there's a record. close it with the button once it's sorted. use `/mod ticket-add` to pull someone else in."),
        ("reports", "reports land in the report logs. check the message link before acting, and warn first unless it's serious."),
        ("appeals", "if someone appeals your action, let a different staff member look at it."),
    ]),
    ("🔨 handing out punishments", [
        ("usual order", "talk → `warn` → `mute` → `kick` → `ban`. skip steps for spam bots, slurs, NSFW or raids."),
        ("give a reason", "reasons are optional, but every action is logged in mod logs and a real reason saves arguments later. leave it out and it says \"no reason provided\"."),
        ("chips", "never give, take or reset chips as a punishment unless it's for cheating or alts. casino staff handle that with `/casino`."),
    ]),
    ("📍 where to run things", [
        ("staff commands", "your staff commands work in any channel. games and earning commands still go in their own channels, same as everyone else."),
        ("chat channels", "general, media, memes and the rest are command-free for members, the bot deletes theirs and points them to bot commands."),
        ("help", "`/help warn` (or any command) shows exactly how it works. `/mod ranks` lists what every rank can do."),
    ]),
]


def staff_guide_embeds(color, guild=None):
    import perms
    out = []
    ranks = discord_embed(title="🪜 what each rank can do", color=color,
                          description="each rank gets everything from the ranks below it too.")
    for t in range(1, 10):
        cmds = sorted(c for c, need in perms.MOD_TIERS.items() if need == t)
        if t == perms.CASINO_TIER:
            cmds += ["/casino " + c for c in sorted(perms.CASINO_CMDS)]
        if cmds:
            ranks.add_field(name=perms.TIERS[t], value=" · ".join(f"`{c}`" for c in cmds)[:1024], inline=False)
    for title, rows in STAFF_GUIDE:
        e = discord_embed(title=title, color=color)
        for name, text in rows:
            e.add_field(name=name, value=text, inline=False)
        out.append(e)
    out.insert(1, ranks)
    out[-1].set_footer(text="questions about this? ask in staff chat")
    return out


def discord_embed(**kw):
    import discord
    return discord.Embed(**kw)


def sections():
    import re
    secs = []
    for block in HELP_TEXT.split("\n\n"):
        m = re.match(r"\*\*(.+?)\*\*(.*)", block, re.S)
        if m:
            secs.append((m.group(1).strip(), m.group(2).strip()))
    out = []
    for key, title, who, wanted in GROUPS:
        items = []
        for name, body in secs:
            if any(name.lower().startswith(w) for w in wanted):
                first, _, rest = body.partition("\n")
                note = first.strip().replace("`", "") if first.strip().startswith("(") else ""
                text = rest if note else body
                cmds = re.findall(r"`([^`]+)`", text)
                items.append({"title": name, "note": note.strip("() "), "text": re.sub(r"`([^`]+)`", r"\1", text).strip(),
                              "cmds": cmds})
        out.append({"key": key, "title": title, "who": who, "items": items})
    return out
