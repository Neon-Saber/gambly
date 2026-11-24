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
    "`deletemydata` wipes your account and warnings for good, no staff needed\n\n"
    "**classic games**\n"
    "`coinflip <amt> <heads/tails>` · `slots <amt>` · `jackpot` · `dice <amt> <1-6>` · `roulette <amt> <red/black/green/0-36>` · "
    "`allin <red/black>` · `blackjack <amt>` · `war <amt>` · `hilo <amt>` · `crash <amt> <x>` · `mines <amt> [mines]` · "
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
    "grab colors, pings, pronouns and platforms from the buttons in the roles channel\n\n"
    "**security · trial+** (`/mod`)\n"
    "`warn` · `warnings` · `mute` · `unmute` · `purge` · `ticket-add` · `ranks`\n"
    "mutes max 1h and purges max 25 until security\n\n"
    "**security · junior+**\n"
    "`slowmode`\n\n"
    "**security · security+**\n"
    "`kick` · `lock` · `unlock` - mutes up to 1d (senior 7d, head 28d)\n\n"
    "**security · senior+**\n"
    "`clearwarnings`\n\n"
    "**security · head+**\n"
    "`ban` · `unban`\n\n"
    "**casino staff** (`/casino` - dealers + floor managers)\n"
    "`addchips` · `removechips` · `setbalance` · `forgive` · `ban` / `unban` (from games) · `reset` · `giveaway` (hosts too)\n\n"
    "**admin** (`/admin` - floor managers+)\n"
    "`role give/take` (pit boss+ for staff ranks) · `ticket-panel` · `announce-channel` · `diag` · `test-welcome` · "
    "`test-levelup` · `prefix` (pit boss+)\n\n"
    "**owner** (`/owner` + `/setup` - the server owner only)\n"
    "`/setup build` · `/setup roles` · `/setup restyle` · `/setup preview` · `/setup undo` · `/owner managers` · "
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
     "Run /deletemydata in Discord, or use Delete my data on your Account page here. Both remove your balances, levels and warnings and can't be undone."),
    ("Can I add the bot to my own server?",
     "Not as a server bot. It's locked to one server and leaves anywhere else. You can still use the personal app to play anywhere."),
]


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
