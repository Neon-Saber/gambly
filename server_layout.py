import cog_utils as cu

STYLES = {
    'dot':     {'label': 'Centered dot', 'sample': '💬・general'},
    "bar":     {"label": "Vertical bar", "sample": "💬｜general"},
    "angle":   {"label": "Double angle", "sample": "《💬》general"},
    'bracket': {'label': 'Lenticular bracket', 'sample': '【💬】general'},
    'corner':  {'label': 'Corner bracket', 'sample': '「💬」general'},
    'sparkle': {'label': 'Sparkle tree', 'sample': '┊✧・general'},
    'plain':   {'label': 'Dash', 'sample': '💬-general'},
    'custom':  {'label': 'Your own', 'sample': '꒰💬꒱general'},
}
DEFAULT_STYLE = "angle"

THEMES = {
    "emoji": {"label": "Emoji", "sample": "💬 🎲 📜", "accent": 0xFF6AD5},
    "unicode": {"label": "Unicode", "sample": "✦ ❀ ☾ ♡", "accent": 0xE8E8E8,
                "map": {"welcome": "❀", "rules": "✎", "announcements": "⚑", "server-updates": "⟳", "giveaways": "✰",
                        "roles": "✦", "faq": "?", "general": "☁", "media": "✿", "memes": "☺", "fan-art": "✐",
                        "self-promo": "➹", "bot-commands": "⌘", "suggestions": "⁂", "casino-guide": "♠", "level-ups": "★",
                        "big-wins": "♛", "open-a-ticket": "✆", "members": "∞", "general-vc": "♪", "chill-vc": "☾",
                        "gaming-vc": "⌁", "staff-chat": "⚜", "staff-commands": "⌘", "bot-status": "◉", "staff-call": "☏",
                        "message-logs": "✐", "mod-logs": "⚖", "report-logs": "⚑", "bank-logs": "$", "ticket-logs": "✆",
                        "card-tables": "♠", "slots-and-spins": "❖", "dice-games": "⚄", "crash-and-mines": "➶",
                        "quick-bets": "◎", "pvp-arena": "⚔"},
                "cats": {"start": "✿", "community": "☁", "casino": "♠", "support": "✆", "voice": "♪", "staff": "⚜", "logs": "⚖"},
                "pool": ["♠", "♣", "♥", "♦", "✦", "✧", "❖", "◆", "◇", "★", "☆", "⋆"]},
    "redblack": {"label": "Red & black", "sample": "🥀 🖤 ♠️ 🍷", "accent": 0xC0392B,
                 "map": {"welcome": "🌹", "rules": "📕", "announcements": "🚨", "server-updates": "⛓️", "giveaways": "🧧",
                         "roles": "♠️", "faq": "❗", "general": "🖤", "media": "🏮", "memes": "🌶️", "fan-art": "🥀",
                         "self-promo": "📌", "bot-commands": "🎱", "suggestions": "❣️", "casino-guide": "🃏",
                         "level-ups": "🔻", "big-wins": "🍷", "open-a-ticket": "📮", "members": "⚫", "general-vc": "🔴",
                         "chill-vc": "🕸️", "gaming-vc": "🥊", "staff-chat": "🦇", "staff-commands": "🗡️", "bot-status": "🛑",
                         "staff-call": "☎️", "message-logs": "🕷️", "mod-logs": "⛓️", "report-logs": "🚩", "bank-logs": "🍒",
                         "ticket-logs": "📮", "card-tables": "♠️", "slots-and-spins": "🍒", "dice-games": "🎲",
                         "crash-and-mines": "🧨", "quick-bets": "♦️", "pvp-arena": "🗡️"},
                 "cats": {"start": "🥀", "community": "🖤", "casino": "♠️", "support": "📮", "voice": "🔴", "staff": "🦇", "logs": "🕷️"},
                 "pool": ["♠️", "♣️", "♥️", "♦️", "🃏", "🎴", "🍒", "🍷", "🎱", "🔻", "🩸", "🌹"]},
    "ribbon": {"label": "Ribbons & pastel", "sample": "🎀 🌸 💗 🧸", "accent": 0xFF9ED8,
               "map": {"welcome": "🎀", "rules": "🩰", "announcements": "💌", "server-updates": "🫧", "giveaways": "🎁",
                       "roles": "🌷", "faq": "🍥", "general": "🌸", "media": "📸", "memes": "🍓", "fan-art": "🖍️",
                       "self-promo": "💗", "bot-commands": "🧸", "suggestions": "💭", "casino-guide": "🎀", "level-ups": "✨",
                       "big-wins": "💖", "open-a-ticket": "🧁", "members": "🩷", "general-vc": "🎧", "chill-vc": "☁️",
                       "gaming-vc": "🎮", "staff-chat": "🍰", "staff-commands": "🧸", "bot-status": "🫧", "staff-call": "📞",
                       "message-logs": "💌", "mod-logs": "🎀", "report-logs": "🍓", "bank-logs": "🐷", "ticket-logs": "🧁"},
               "cats": {"start": "🎀", "community": "🌸", "casino": "💗", "support": "💌", "voice": "🎧", "staff": "🧸", "logs": "🍰"},
               "pool": ["🎀", "🌸", "💗", "🩷", "🍓", "🧸", "💌", "🫧", "🍰", "🌷", "✨", "💞", "🍡", "🦢"]},
    "text": {"label": "Text only", "sample": "no icons", "accent": 0x99AAB5},
}
DEFAULT_THEME = "emoji"


def icon_for(theme, base, default, idx=0):
    t = THEMES.get(theme) or THEMES["emoji"]
    if theme == "text":
        return ""
    if "map" not in t:
        return default
    return t["map"].get(base) or t["pool"][idx % len(t["pool"])]


def cat_icon(theme, key, default):
    t = THEMES.get(theme) or THEMES["emoji"]
    if theme == "text":
        return ""
    return (t.get("cats") or {}).get(key, default)


def clean_pattern(p, need):
    p = (p or "").strip()[:40]
    return p if need in p else None


def channel_name(style, emoji, base, pos=1, total=3, voice=False, pattern=None):
    if voice:
        base = base.replace("-", " ").title().replace(" Vc", " VC")
    if style == "custom" and pattern:
        return pattern.replace("{icon}", emoji).replace("{name}", base).strip() or base
    if not emoji:
        if style == "sparkle":
            return f"╭✦・{base}" if pos == 0 else (f"╰✦・{base}" if pos == total - 1 else f"┊✧・{base}")
        return {"dot": f"・{base}", "bar": f"｜{base}", "angle": f"《{base}》", "bracket": f"【{base}】",
                "corner": f"「{base}」"}.get(style, base)
    if style == 'dot':
        return f"{emoji}・{base}"
    if style == 'bar':
        return f"{emoji}｜{base}"
    if style == "angle":
        return f"《{emoji}》{base}"
    if style == "bracket":
        return f"【{emoji}】{base}"
    if style == "corner":
        return f"「{emoji}」{base}"
    if style == 'sparkle':
        if pos == 0:
            return f"╭✦{emoji}・{base}"
        if pos == total - 1:
            return f"╰✦・{base}"
        return f"┊✧・{base}"
    return f"{emoji}-{base}" if not voice else f"{emoji} {base}"


def category_name(style, emoji, title, pattern=None):
    if style == "custom" and pattern:
        out = pattern.replace("{icon}", emoji).replace("{TITLE}", title.upper()).replace("{title}", title)
        return " ".join(out.split()) or title.upper()
    if not emoji:
        if style in ("bar", "angle"):
            return f"─ {title.upper()} ─"
        if style == "corner":
            return f"「{title.upper()}」"
    if style in ("bar", "angle"):
        return f"{emoji} {title.upper()} {emoji}"
    if style == "dot":
        return f"{emoji} {title.title()}".strip()
    if style == "bracket":
        return f"— {title.lower()} —"
    if style == 'corner':
        return f"「{emoji}」{title.upper()}"
    if style == "sparkle":
        return f"──「✧」{title.lower()} !"
    return title.upper()

SECTIONS = [
    {"key": "start", "title": "start here", "emoji": "🌸", "default": True, "channels": [
        {"base": "welcome", "emoji": "👋", "readonly": True, "binds": ["welcome_channel_id"]},
        {'base': 'rules', 'emoji': '📜', 'readonly': True, 'panel': 'rules'},
        {'base': 'announcements', 'emoji': '📢', 'readonly': True, 'binds': ['announce_channel']},
        {"base": "server-updates", "emoji": "🛠️", "readonly": True},
        {"base": "giveaways", "emoji": "🎁", "readonly": True},
        {"base": "roles", "emoji": "🏷️", "readonly": True, "panel": "roles"},
        {"base": "faq", "emoji": "❓", "readonly": True, "panel": "faq"},
    ]},
    {"key": "community", "title": "community", "emoji": "💭", "default": True, "channels": [
        {"base": "general", "emoji": "💬", "quiet": True},
        {'base': 'media', 'emoji': '📷', 'quiet': True},
        {'base': 'memes', 'emoji': '🤣', 'quiet': True},
        {'base': 'fan-art', 'emoji': '🎨', 'quiet': True},
        {'base': 'self-promo', 'emoji': '🔗', 'quiet': True},
        {"base": "bot-commands", "emoji": "🤖", "binds": ["commands_channel"]},
        {'base': 'suggestions', 'emoji': '💡', 'quiet': True},
    ]},
    {"key": "earn", "title": "earn chips", "emoji": "💸", "default": True, "channels": [
        {"base": "daily", "emoji": "📅", "cmds": ["daily", "claim", "weekly", "monthly", "spin", "quests"]},
        {"base": "work", "emoji": "💼", "cmds": ["work", "crime", "beg"]},
        {"base": "gathering", "emoji": "🎣", "cmds": ["gather", "fish", "mine", "hunt", "collection"]},
        {"base": "trivia", "emoji": "🧠", "cmds": ["trivia"]},
        {"base": "bank", "emoji": "🏦", "cmds": ["deposit", "withdraw", "loan", "repay", "invest"]},
        {"base": "shop", "emoji": "🛒", "cmds": ["shop", "buy", "use", "pawn", "inventory", "craft", "business",
                                                "buybusiness", "collect", "upgrades", "buyupgrade", "rebirth"]},
    ]},
    {'key': 'casino', 'title': 'casino', 'emoji': '🎰', 'default': True, 'channels': [
        {"base": "casino-guide", "emoji": "📖", "readonly": True, "panel": "games"},
        {"base": "level-ups", "emoji": "⭐", "readonly": True, "binds": ["level_channel_id"]},
        {"base": "big-wins", "emoji": "🏆", "readonly": True},
    ]},
    {"key": "support", "title": "support", "emoji": "🎫", "default": True, "ticket_category": True, "channels": [
        {"base": "open-a-ticket", "emoji": "📩", "readonly": True, "panel": "tickets"},
    ]},
    {"key": "voice", "title": "voice", "emoji": "🔊", "default": True, "channels": [
        {"base": "members", "emoji": "👥", "kind": "voice", "locked": True, "binds": ["member_count_channel_id"]},
        {"base": "general-vc", "emoji": "🔊", "kind": "voice"},
        {'base': 'chill-vc', 'emoji': '🎧', 'kind': 'voice'},
        {"base": "gaming-vc", "emoji": "🎮", "kind": "voice"},
    ]},
    {"key": "staff", "title": "staff", "emoji": "🛡️", "default": True, "private": True, "channels": [
        {"base": "staff-guide", "emoji": "📘", "readonly": True, "panel": "staffguide"},
        {"base": "staff-chat", "emoji": "💬"},
        {'base': 'staff-commands', 'emoji': '🤖'},
        {"base": "bot-status", "emoji": "📡", "readonly": True, "binds": ["status_channel_id"]},
        {"base": "staff-call", "emoji": "📞", "kind": "voice"},
    ]},
    {'key': 'logs', 'title': 'logs', 'emoji': '🧾', 'default': True, 'private': True, 'channels': [
        {"base": "message-logs", "emoji": "✉️", "readonly": True, "binds": ["log_message_channel"]},
        {"base": "mod-logs", "emoji": "🔨", "readonly": True, "binds": ["log_mod_channel"]},
        {"base": "report-logs", "emoji": "🚩", "readonly": True, "binds": ["log_report_channel"]},
        {'base': 'bank-logs', 'emoji': '🏦', 'readonly': True, 'binds': ['log_withdraw_channel', 'log_deposit_channel']},
        {"base": "ticket-logs", "emoji": "🎟️", "readonly": True, "binds": ["log_ticket_channel"]},
    ]},
]
SECTION_KEYS = [s["key"] for s in SECTIONS]

ENABLE_FLAGS = {
    "welcome_channel_id": "welcome_enabled",
    "member_count_channel_id": "member_count_enabled",
    "status_channel_id": "status_enabled",
    "log_message_channel": "log_message_enabled",
    "log_mod_channel": "log_mod_enabled",
    "log_report_channel": "log_report_enabled",
    "log_withdraw_channel": "log_withdraw_enabled",
    "log_deposit_channel": "log_deposit_enabled",
    "log_ticket_channel": "log_ticket_enabled",
}

GAME_EMOJI = {
    "coinflip": "🪙", "slots": "🎰", "dice": "🎲", "roulette": "🎡", "blackjack": "🃏", "allin": "🔥",
    "war": "⚔️", "hilo": "↕️", "crash": "📈", "mines": "💣", "plinko": "🔻", "horserace": "🏇",
    'wheel': '🎡', 'keno': '🔢', 'baccarat': '🎴', 'rps': '✂️', 'ladder': '🪜', 'duel': '🤺',
    "towers": "🗼", "cups": "🥤", "dragontiger": "🐉", "sicbo": "🎲", "sevens": "7️⃣",
    "videopoker": "🂡", "revolver": "🔫", "balloon": "🎈", "chests": "🧰", "diceduel": "🎲",
    "cardguess": "🃏", "target": "🎯", "rocket": "🚀", "heist": "💰", "tictactoe": "⭕",
    'scratch': '🎟️', 'jackpot': '💎', 'craps': '🎲', 'threecard': '🃏', 'bingo': '🅱️',
    'penalty': '⚽', 'doors': '🚪', 'connect4': '🔴',
}


def game_channels(layout):
    if layout == 'none':
        return []
    if layout == "per-game":
        riders = {"jackpot": "slots", "allin": "roulette"}
        out = []
        for game in sorted(cu.GAME_CHANNEL_ALIASES):
            if game in riders:
                continue
            games = [game] + [r for r, host in riders.items() if host == game]
            out.append((game, GAME_EMOJI.get(game, "🎲"), games))
        return out
    return [(base, g["emoji"], g["games"]) for base, g in cu.GAME_GROUPS.items()]

def build_plan(style=DEFAULT_STYLE, sections=None, game_layout="grouped", theme=DEFAULT_THEME, pattern=None, cat_pattern=None):
    style = style if style in STYLES else DEFAULT_STYLE
    theme = theme if theme in THEMES else DEFAULT_THEME
    pattern = clean_pattern(pattern, "{name}") or "{icon}︱{name}"
    cat_pattern = clean_pattern(cat_pattern, "itle}") or "{icon} {TITLE} {icon}"
    wanted = set(sections) if sections else {s['key'] for s in SECTIONS if s.get('default')}
    plan = []
    for sec in SECTIONS:
        if sec['key'] not in wanted:
            continue
        chans = [dict(c) for c in sec['channels']]
        if sec["key"] == "casino":
            for base, emoji, games in game_channels(game_layout):
                chans.append({"base": base, "emoji": emoji, "games": games})
        total = len(chans)
        for i, c in enumerate(chans):
            c.setdefault('kind', 'text')
            c["key"] = f"{sec['key']}:{c['base']}"
            c["icon"] = icon_for(theme, c["base"], c["emoji"], i)
            c["name"] = channel_name(style, c["icon"], c["base"], i, total, voice=c["kind"] == "voice", pattern=pattern)
        ci = cat_icon(theme, sec["key"], sec["emoji"])
        plan.append({
            "key": sec["key"], "title": sec["title"], "emoji": sec["emoji"],
            "name": category_name(style, ci, sec["title"], cat_pattern),
            "private": sec.get("private", False), "ticket_category": sec.get("ticket_category", False),
            'channels': chans,
        })
    return plan

RULES_TEXT = [
    "be kind. no harassment, hate speech, or targeting other members.",
    "no spam, flooding, or unsolicited advertising (self-promo goes in its channel).",
    "keep it SFW - no NSFW, gore, or shock content anywhere.",
    'chips are a game currency with no real-world value. no buying, selling, or trading chips for real money.',
    'one account per person - alts used to farm chips will be wiped.',
    "don't exploit bugs - report them in a ticket and you might get a reward.",
    "listen to staff. if you disagree with a decision, open a ticket instead of arguing in chat.",
    "follow Discord's Terms of Service and Community Guidelines.",
]

PING_ROLES = [
    {"name": "Announcements", "emoji": "📢"},
    {'name': 'Giveaways', 'emoji': '🎉'},
    {"name": "Casino Events", "emoji": "🎲"},
    {"name": "Server Updates", "emoji": "🛠️"},
]

MOD_PERMS = ["kick_members", "ban_members", "moderate_members", "manage_messages", "manage_nicknames",
             "mute_members", "move_members", "view_audit_log"]
BOSS_PERMS = MOD_PERMS + ["manage_guild", "manage_channels", "manage_roles", "manage_events", "mention_everyone",
                          "manage_threads", "manage_emojis"]

ROLE_KIT = [
    {"key": "staff", "title": "Management", "emoji": "👑", "divider": "──── ⋆ management ⋆ ────", "roles": [
        {"slug": "house", "name": "👑 The House", "color": 0xFFD43B, "hoist": True},
        {"slug": "coowner", "name": "💎 Co-Owner", "color": 0xB197FC, "hoist": True, "tier": 8,
         "perms": BOSS_PERMS + ["manage_webhooks"]},
        {"slug": "pitboss", "name": "🎩 Pit Boss", "color": 0xFF6B6B, "hoist": True, "tier": 7, "perms": BOSS_PERMS,
         "aliases": ["Head Admin"]},
        {"slug": "floor", "name": "💼 Floor Manager", "color": 0xFF922B, "hoist": True, "tier": 6,
         "perms": MOD_PERMS + ["manage_events", "mention_everyone", "manage_threads"], "aliases": ["Admin"]},
    ]},
    {"key": "security", "title": "Security", "emoji": "🛡️", "divider": "──── ⋆ security ⋆ ────", "roles": [
        {"slug": "head", "name": "🛡️ Head of Security", "color": 0x4DABF7, "hoist": True, "tier": 5,
         "perms": MOD_PERMS, "aliases": ["Head Moderator", "Head Mod"]},
        {"slug": "senior", "name": "🕶️ Senior Security", "color": 0x74C0FC, "hoist": True, "tier": 4,
         "perms": ["kick_members", "moderate_members", "manage_messages", "manage_nicknames", "mute_members",
                   "move_members", "view_audit_log"], "aliases": ["Senior Moderator", "Senior Mod"]},
        {"slug": "sec", "name": "🔦 Security", "color": 0x63E6BE, "hoist": True, "tier": 3,
         "perms": ["kick_members", "moderate_members", "manage_messages", "mute_members", "move_members"],
         "aliases": ["Moderator"]},
        {"slug": "junior", "name": "🪪 Junior Security", "color": 0x96F2D7, "hoist": True, "tier": 2,
         "perms": ["moderate_members", "manage_messages"], "aliases": ["Junior Moderator", "Junior Mod"]},
        {"slug": "trial", "name": "🎟️ Trial Security", "color": 0xC3FAE8, "hoist": True, "tier": 1,
         "perms": ["moderate_members"], "aliases": ["Trial Mod", "Trial Moderator"]},
    ]},
    {"key": "crew", "title": "Floor crew", "emoji": "🎰", "divider": "──── ⋆ floor crew ⋆ ────", "roles": [
        {"slug": "dealer", "name": "🎰 Dealer", "color": 0xF5C542, "side": "dealer", "perms": ["manage_events"],
         "cfg": "manager_role", "aliases": ["Casino Manager", "Casino Staff"]},
        {"slug": "host", "name": "🎤 Event Host", "color": 0xDA77F2, "side": "host",
         "perms": ["manage_events", "mention_everyone"], "aliases": ["Event Host"]},
        {"slug": "partners", "name": "🤝 Partner Manager", "color": 0x38D9A9, "side": "partners"},
        {"slug": "media", "name": "📸 Media Team", "color": 0xF783AC, "side": "media"},
        {"slug": "team", "name": "🃏 Staff Team", "color": 0xFF6AD5, "cfg": "staff_role_id", "aliases": ["Staff"]},
        {"slug": "break", "name": "😴 On Break", "color": 0xADB5BD},
    ]},
    {"key": "special", "divider": "──── ⋆ special ⋆ ────", "title": "Special", "emoji": "💎", "roles": [
        {"slug": "vip", "name": "VIP", "color": 0xF1C40F, "hoist": True},
        {"slug": "partner", "name": "Partner", "color": 0x1ABC9C},
        {"slug": "creator", "name": "Content Creator", "color": 0xE91E63},
        {"slug": "og", "name": "OG", "color": 0xA569BD},
        {"slug": "bots", "name": "Bots", "color": 0x7289DA, "hoist": True},
    ]},
    {"key": "colors", "divider": "──── ⋆ colors ⋆ ────", "title": "Name colors", "emoji": "🎨", "self": True, "exclusive": True,
     "blurb": "pick a color for your name - picking a new one swaps it", "roles": [
        {"slug": "red", "name": "Red", "color": 0xFF4D4D, "emoji": "🔴"},
        {"slug": "orange", "name": "Orange", "color": 0xFF9F43, "emoji": "🟠"},
        {"slug": "yellow", "name": "Yellow", "color": 0xFFE066, "emoji": "🟡"},
        {"slug": "green", "name": "Green", "color": 0x2ECC71, "emoji": "🟢"},
        {"slug": "mint", "name": "Mint", "color": 0x7DFFCB, "emoji": "🩵"},
        {"slug": "blue", "name": "Blue", "color": 0x4DA3FF, "emoji": "🔵"},
        {"slug": "purple", "name": "Purple", "color": 0xA66CFF, "emoji": "🟣"},
        {"slug": "pink", "name": "Pink", "color": 0xFF7AD9, "emoji": "🩷"},
        {"slug": "white", "name": "White", "color": 0xFDFDFD, "emoji": "⚪"},
        {"slug": "black", "name": "Black", "color": 0x111111, "emoji": "⚫"},
    ]},
    {"key": "rebirths", "divider": "──── ⋆ ranks ⋆ ────", "title": "Rebirth ranks", "emoji": "♻️", "bind": "rebirth_roles", "roles": [
        {"slug": "r1", "name": "Rebirth I", "color": 0xB2F2BB, "at": 1},
        {"slug": "r2", "name": "Rebirth II", "color": 0x8CE99A, "at": 2},
        {"slug": "r3", "name": "Rebirth III", "color": 0x63E6BE, "at": 3},
        {"slug": "r4", "name": "Rebirth IV", "color": 0x3BC9DB, "at": 4},
        {"slug": "r5", "name": "Rebirth V", "color": 0x4DABF7, "at": 5},
        {"slug": "r6", "name": "Rebirth VI", "color": 0x9775FA, "at": 6},
        {"slug": "r7", "name": "Rebirth VII", "color": 0xF783AC, "at": 7},
    ]},
    {"key": "levels", "title": "Level ranks", "emoji": "⭐", "bind": "level_roles", "roles": [
        {"slug": "l5", "name": "Lv 5 · Rookie", "color": 0xCED4DA, "at": 5},
        {"slug": "l10", "name": "Lv 10 · Regular", "color": 0xA9E34B, "at": 10},
        {"slug": "l20", "name": "Lv 20 · Gambler", "color": 0x69DB7C, "at": 20},
        {"slug": "l30", "name": "Lv 30 · High Roller", "color": 0x38D9A9, "at": 30},
        {"slug": "l50", "name": "Lv 50 · Shark", "color": 0x339AF0, "at": 50},
        {"slug": "l75", "name": "Lv 75 · Whale", "color": 0x845EF7, "at": 75},
        {"slug": "l100", "name": "Lv 100 · Legend", "color": 0xFCC419, "at": 100},
    ]},
    {"key": "pings", "divider": "──── ⋆ pings ⋆ ────", "title": "Pings", "emoji": "🔔", "self": True,
     "blurb": "pick what you want to get pinged for - tap again to remove", "roles": [
        {"slug": "announce", "name": "Announcements", "color": 0xFF8787, "emoji": "📢"},
        {"slug": "giveaways", "name": "Giveaways", "color": 0xFFD43B, "emoji": "🎉"},
        {"slug": "events", "name": "Casino Events", "color": 0xB197FC, "emoji": "🎲"},
        {"slug": "updates", "name": "Server Updates", "color": 0x74C0FC, "emoji": "🛠️"},
        {"slug": "polls", "name": "Polls", "color": 0x63E6BE, "emoji": "📊"},
        {"slug": "revive", "name": "Chat Revive", "color": 0x8CE99A, "emoji": "💬"},
        {"slug": "partners", "name": "Partnerships", "color": 0xFFA94D, "emoji": "🤝"},
        {"slug": "gamenight", "name": "Game Night", "color": 0xF783AC, "emoji": "🎮"},
    ]},
    {"key": "pronouns", "divider": "──── ⋆ about me ⋆ ────", "title": "Pronouns", "emoji": "🏷️", "self": True, "blurb": "optional - pick any that fit", "roles": [
        {"slug": "he", "name": "he/him", "emoji": "💙"},
        {"slug": "she", "name": "she/her", "emoji": "💗"},
        {"slug": "they", "name": "they/them", "emoji": "💜"},
        {"slug": "any", "name": "any pronouns", "emoji": "🤍"},
        {"slug": "ask", "name": "ask my pronouns", "emoji": "💬"},
    ]},
    {"key": "platforms", "title": "Platforms", "emoji": "🎮", "self": True, "blurb": "what do you play on?", "roles": [
        {"slug": "pc", "name": "PC", "emoji": "🖥️"},
        {"slug": "console", "name": "Console", "emoji": "🎮"},
        {"slug": "mobile", "name": "Mobile", "emoji": "📱"},
    ]},
]
ROLE_KIT_KEYS = [g["key"] for g in ROLE_KIT]
ROLE_ORDER = ["staff", "security", "crew", "special", "colors", "rebirths", "levels", "pings", "pronouns", "platforms"]
