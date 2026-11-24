import cog_utils as cu

STYLES = {
    'dot':     {'label': 'Centered dot', 'sample': '💬・general'},
    "bar":     {"label": "Vertical bar", "sample": "💬｜general"},
    "angle":   {"label": "Double angle", "sample": "《💬》general"},
    'bracket': {'label': 'Lenticular bracket', 'sample': '【💬】general'},
    'corner':  {'label': 'Corner bracket', 'sample': '「💬」general'},
    'sparkle': {'label': 'Sparkle tree', 'sample': '┊✧・general'},
    'plain':   {'label': 'Emoji dash', 'sample': '💬-general'},
}
DEFAULT_STYLE = "angle"

def channel_name(style, emoji, base, pos=1, total=3, voice=False):
    if voice:
        base = base.replace("-", " ").title().replace(" Vc", " VC")
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


def category_name(style, emoji, title):
    if style in ("bar", "angle"):
        return f"{emoji} {title.upper()} {emoji}"
    if style == "dot":
        return f"{emoji} {title.title()}"
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
        {"base": "faq", "emoji": "❓", "readonly": True},
    ]},
    {"key": "community", "title": "community", "emoji": "💭", "default": True, "channels": [
        {"base": "general", "emoji": "💬"},
        {'base': 'media', 'emoji': '📷'},
        {'base': 'memes', 'emoji': '🤣'},
        {'base': 'fan-art', 'emoji': '🎨'},
        {'base': 'self-promo', 'emoji': '🔗'},
        {"base": "bot-commands", "emoji": "🤖"},
        {'base': 'suggestions', 'emoji': '💡'},
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
    'scratch': '🎟️', 'jackpot': '💎',
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

def build_plan(style=DEFAULT_STYLE, sections=None, game_layout="grouped"):
    style = style if style in STYLES else DEFAULT_STYLE
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
            c["name"] = channel_name(style, c["emoji"], c["base"], i, total, voice=c["kind"] == "voice")
        plan.append({
            "key": sec["key"], "title": sec["title"], "emoji": sec["emoji"],
            "name": category_name(style, sec["emoji"], sec["title"]),
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
