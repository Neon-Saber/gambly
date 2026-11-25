import os

from discord.ext import commands

import config_schema as cfgschema
import server_layout as sl

TIERS = {
    0: "member", 1: "Trial Security", 2: "Junior Security", 3: "Security", 4: "Senior Security",
    5: "Head of Security", 6: "Floor Manager", 7: "Pit Boss", 8: "Co-Owner", 9: "Owner",
}

MOD_TIERS = {
    "warn": 1, "warnings": 1, "mute": 1, "unmute": 1, "purge": 1, "add-to-ticket": 1,
    "slowmode": 2,
    "kick": 3, "lock": 3, "unlock": 3,
    "clearwarns": 4,
    "ban": 5, "unban": 5,
    "diag": 6, "ticket-panel": 6, "setannounce": 6, "role": 6, "test-welcome": 6, "test-levelup": 6,
    "setprefix": 7,
    "setup": 9, "setmanager": 9, "testmode": 9, "wipe-economy": 9,
}
CASINO_CMDS = {"addchips", "removechips", "setbalance", "forgive", "banuser", "unbanuser", "reset"}
HOST_CMDS = {"giveaway"}
CASINO_TIER = 6

MUTE_CAP = {1: 3600, 2: 3600, 3: 86400, 4: 7 * 86400}
PURGE_CAP = {1: 25, 2: 25}

class Denied(commands.CheckFailure):
    pass


DANGER = ("administrator", "manage_guild", "manage_roles", "manage_channels", "manage_webhooks", "ban_members")


def owner_ids():
    raw = os.getenv("OWNER_IDS", "")
    return {int(x) for x in raw.replace(" ", "").split(",") if x.isdigit()}


def _cfg(guild):
    return cfgschema.ensure_guild(cfgschema.load_cfg(), guild.id)


def kit_ids(guild):
    return (_cfg(guild).get("role_kit") or {}).get("roles") or {}


def tier_of(member):
    guild = getattr(member, "guild", None)
    if guild is None or not hasattr(member, "roles"):
        return 0
    if member.id == guild.owner_id or member.id in owner_ids():
        return 9
    kr = kit_ids(guild)
    mine = {r.id for r in member.roles}
    brk = kr.get("crew:break")
    if brk and int(brk) in mine:
        return 0
    best = 0
    for gdef in sl.ROLE_KIT:
        for r in gdef["roles"]:
            t = r.get("tier")
            rid = kr.get(f"{gdef['key']}:{r['slug']}")
            if t and rid and int(rid) in mine:
                best = max(best, t)
    if best == 0 and getattr(member, "guild_permissions", None) and member.guild_permissions.administrator:
        best = 7
    return best


def sides(member):
    guild = getattr(member, "guild", None)
    if guild is None or not hasattr(member, "roles"):
        return set()
    kr = kit_ids(guild)
    mine = {r.id for r in member.roles}
    out = set()
    for gdef in sl.ROLE_KIT:
        for r in gdef["roles"]:
            rid = kr.get(f"{gdef['key']}:{r['slug']}")
            if r.get("side") and rid and int(rid) in mine:
                out.add(r["side"])
    return out


def on_break(member):
    guild = getattr(member, "guild", None)
    if guild is None or not hasattr(member, "roles"):
        return False
    brk = kit_ids(guild).get("crew:break")
    return bool(brk) and any(r.id == int(brk) for r in member.roles) and member.id != guild.owner_id


def allowed(member, cmd, default=None):
    if member is None or getattr(member, "guild", None) is None:
        return False, "that only works in the main server"
    t = tier_of(member)
    if cmd in CASINO_CMDS:
        if t >= CASINO_TIER or "dealer" in sides(member):
            return True, None
        return False, "only dealers and floor managers+ can touch people's chips"
    if cmd in HOST_CMDS:
        if t >= CASINO_TIER or "host" in sides(member) or "dealer" in sides(member):
            return True, None
        return False, "only event hosts, dealers and floor managers+ can run giveaways"
    need = MOD_TIERS.get(cmd, default)
    if need is None:
        return True, None
    if t >= need:
        return True, None
    if on_break(member):
        return False, "you're on break 😴 - take the On Break role off to use staff commands"
    if need >= 9:
        return False, "only the server owner can do that"
    return False, f"you need to be **{TIERS[need]}** or higher for that"


def outranks(actor, target):
    guild = actor.guild
    if actor.id == guild.owner_id or actor.id in owner_ids():
        return target.id != actor.id
    if target.id == guild.owner_id:
        return False
    return tier_of(actor) > tier_of(target) and target.top_role < actor.top_role


def mute_cap(member):
    return MUTE_CAP.get(tier_of(member), 28 * 86400)


def purge_cap(member):
    return PURGE_CAP.get(tier_of(member), 100)


def role_blocked(actor, role):
    if role.is_default() or role.managed:
        return "that role can't be handed out"
    if actor.id != actor.guild.owner_id and role >= actor.top_role:
        return "that role is above (or equal to) your highest role"
    if role >= actor.guild.me.top_role:
        return "that role is above mine, so I can't give it - drag my role higher"
    p = role.permissions
    if any(getattr(p, x, False) for x in DANGER) and tier_of(actor) < 8:
        return "that role has dangerous permissions - only co-owners and the owner can give it"
    kr = {int(v): k for k, v in kit_ids(actor.guild).items()}
    key = kr.get(role.id)
    if key:
        gkey, slug = key.split(":", 1)
        rdef = next((r for g in sl.ROLE_KIT if g["key"] == gkey for r in g["roles"] if r["slug"] == slug), {})
        if rdef.get("tier") and rdef["tier"] >= tier_of(actor):
            return "you can only hand out staff ranks below your own"
        if gkey in ("staff", "security", "crew") and tier_of(actor) < 7:
            return "only pit bosses and up can hand out staff roles"
    return None
