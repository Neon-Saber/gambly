import asyncio
import time

import discord
from discord import Option
from discord.ext import commands, tasks

import config_schema as cfgschema
import embeds
import server_layout as sl
import store

async def update_cfg(guild_id, fn):
    async with store.locked(cfgschema.CFG_FILE):
        cfg = cfgschema.load_cfg()
        g = cfgschema.ensure_guild(cfg, guild_id)
        result = fn(g)
        cfgschema.save_cfg(cfg)
    return result


def read_cfg(guild_id):
    return cfgschema.ensure_guild(cfgschema.load_cfg(), guild_id)

CLEAR_KEYS = list(sl.ENABLE_FLAGS) + ["level_channel_id", "announce_channel", "ticket_category_id"]
STYLE_CHOICES = list(sl.STYLES)
THEME_CHOICES = list(sl.THEMES)
GAME_CHOICES = ["grouped", "per-game", "none"]


class SelfRoleView(discord.ui.View):
    def __init__(self, roles):
        super().__init__(timeout=None)
        for r in roles:
            b = discord.ui.Button(label=r['name'], emoji=r.get('emoji') or None, style=discord.ButtonStyle.secondary,
                                  custom_id=f"selfrole:{r['id']}")
            b.callback = self._make(int(r["id"]))
            self.add_item(b)

    def _make(self, role_id):
        async def cb(interaction):
            role = interaction.guild.get_role(role_id)
            if role is None:
                return await interaction.response.send_message("that role doesn't exist anymore", ephemeral=True)
            try:
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role, reason="self-role")
                    msg = f"removed **{role.name}**"
                else:
                    await interaction.user.add_roles(role, reason='self-role')
                    msg = f"gave you **{role.name}**"
            except discord.Forbidden:
                msg = "I can't manage that role - my role needs to be above it"
            await interaction.response.send_message(msg, ephemeral=True)
        return cb


class ConfirmBuild(discord.ui.View):
    def __init__(self, cog, author, opts):
        super().__init__(timeout=120)
        self.cog, self.author, self.opts = cog, author, opts
    @discord.ui.button(label="build it", emoji="🏗️", style=discord.ButtonStyle.success)
    async def go(self, button, interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("not your setup", ephemeral=True)
        await interaction.response.edit_message(content="🏗️ building… this can take a minute (Discord rate-limits channel creation)",
                                                embed=None, view=None)
        self.stop()
        async def progress(line):
            try:
                await interaction.edit_original_response(content=f"🏗️ {line}")
            except discord.HTTPException:
                pass
        summary = await self.cog.build(interaction.guild, progress=progress, **self.opts)
        await interaction.edit_original_response(content=summary)
    @discord.ui.button(label="cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, button, interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("not your setup", ephemeral=True)
        await interaction.response.edit_message(content="cancelled", embed=None, view=None)
        self.stop()


class KitView(discord.ui.View):
    def __init__(self, group, roles, exclusive=False):
        super().__init__(timeout=None)
        self.group, self.exclusive = group, exclusive
        for r in roles[:25]:
            b = discord.ui.Button(label=r['name'][:80], emoji=r.get('emoji') or None, style=discord.ButtonStyle.secondary,
                                  custom_id=f"kit:{group}:{r['id']}", row=min(len(self.children) // 5, 4))
            b.callback = self._make(int(r['id']))
            self.add_item(b)

    def _make(self, rid):
        async def cb(interaction):
            role = interaction.guild.get_role(rid)
            if role is None:
                return await interaction.response.send_message("that role doesn't exist anymore, ask staff to run /setup roles", ephemeral=True)
            member = interaction.user
            try:
                if role in member.roles:
                    await member.remove_roles(role, reason="role panel")
                    msg = f"removed **{role.name}**"
                else:
                    if self.exclusive:
                        kit = (read_cfg(interaction.guild.id).get('role_kit') or {}).get('roles') or {}
                        same = {int(v) for k, v in kit.items() if k.startswith(self.group + ':')}
                        old = [r for r in member.roles if r.id in same and r.id != rid]
                        if old:
                            await member.remove_roles(*old, reason="role panel swap")
                    await member.add_roles(role, reason="role panel")
                    msg = f"gave you **{role.name}**"
            except discord.Forbidden:
                msg = "I can't hand that role out - my role has to be above it in server settings"
            await interaction.response.send_message(msg, ephemeral=True)
        return cb


def kit_panel_roles(group, kit_roles):
    gdef = next(g for g in sl.ROLE_KIT if g['key'] == group)
    out = []
    for r in gdef['roles']:
        rid = kit_roles.get(f"{group}:{r['slug']}")
        if rid:
            out.append({"id": str(rid), "name": r['name'], "emoji": r.get('emoji')})
    return gdef, out


def kit_panel_embed(gdef, roles, accent):
    e = discord.Embed(title=f"{gdef['emoji']} {gdef['title'].lower()}", color=accent,
                      description=gdef.get('blurb', '') + "\n\n" + "\n".join(f"{r.get('emoji') or '•'} <@&{r['id']}>" for r in roles))
    return e


class ConfirmRoles(discord.ui.View):
    def __init__(self, cog, author, groups, channel_id):
        super().__init__(timeout=120)
        self.cog, self.author, self.groups, self.channel_id = cog, author, groups, channel_id
    @discord.ui.button(label="create missing + post panels", emoji="✨", style=discord.ButtonStyle.success)
    async def go(self, button, interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("not yours", ephemeral=True)
        await interaction.response.edit_message(content="✨ working on roles…", embed=None, view=None)
        self.stop()
        async def progress(line):
            try:
                await interaction.edit_original_response(content=f"✨ {line}")
            except discord.HTTPException:
                pass
        res = await self.cog.apply_kit(interaction.guild, self.groups, self.channel_id, progress)
        try:
            await interaction.edit_original_response(content=res)
        except discord.HTTPException:
            pass
    @discord.ui.button(label="cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, button, interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("not yours", ephemeral=True)
        await interaction.response.edit_message(content="ok, nothing changed", embed=None, view=None)
        self.stop()


class ConfirmUndo(discord.ui.View):
    def __init__(self, cog, author):
        super().__init__(timeout=60)
        self.cog, self.author = cog, author
    @discord.ui.button(label="yes, delete it all", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def go(self, button, interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("not yours", ephemeral=True)
        await interaction.response.edit_message(content="🗑️ undoing…", embed=None, view=None)
        self.stop()
        async def progress(line):
            try:
                await interaction.edit_original_response(content=f"🗑️ {line}")
            except discord.HTTPException:
                pass
        res = await self.cog.undo(interaction.guild, progress)
        try:
            await interaction.edit_original_response(content=res)
        except discord.HTTPException:
            pass
    @discord.ui.button(label="nevermind", style=discord.ButtonStyle.secondary)
    async def cancel(self, button, interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("not yours", ephemeral=True)
        await interaction.response.edit_message(content="ok, nothing deleted", embed=None, view=None)
        self.stop()


def preview_embed(style, sections=None, game_layout="grouped", theme=sl.DEFAULT_THEME, pattern=None, cat_pattern=None):
    plan = sl.build_plan(style, sections, game_layout, theme, pattern, cat_pattern)
    e = discord.Embed(title=f"server layout · {sl.STYLES[style]['label']} · {sl.THEMES[theme]['label']}",
                      color=sl.THEMES[theme]['accent'])
    for cat in plan:
        lines = [("🔊 " if c["kind"] == "voice" else "# ") + c["name"] for c in cat["channels"]]
        text = "\n".join(lines)
        if len(text) > 1000:
            text = text[:990] + "\n…"
        e.add_field(name=cat['name'] + (' 🔒' if cat['private'] else ''), value=text, inline=True)
    n = sum(len(c['channels']) for c in plan)
    e.set_footer(text=f"{len(plan)} categories · {n} channels · existing channels are never deleted · /setup undo removes it again")
    return e

class ServerSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.building = set()
        self._views_done = False
    def cog_unload(self):
        self.request_loop.cancel()

    async def cog_check(self, ctx):
        import perms
        if ctx.guild is not None and perms.tier_of(ctx.author) >= 9:
            return True
        msg = "only the server owner can use the server builder"
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(msg, ephemeral=True)
        else:
            await ctx.send(msg)
        raise perms.Denied()
    @commands.Cog.listener()
    async def on_ready(self):
        if not self._views_done:
            self._views_done = True
            for g in self.bot.guilds:
                gc = read_cfg(g.id)
                roles = (gc.get("self_roles") or [])
                if roles:
                    self.bot.add_view(SelfRoleView(roles))
                kr = (gc.get("role_kit") or {}).get("roles") or {}
                for gdef in sl.ROLE_KIT:
                    if gdef.get("self"):
                        _, rs = kit_panel_roles(gdef["key"], kr)
                        if rs:
                            self.bot.add_view(KitView(gdef["key"], rs, gdef.get("exclusive", False)))
        if not self.request_loop.is_running():
            self.request_loop.start()

    async def ensure_role(self, guild, cfg_key, name, color, perms=None, hoist=False):
        rid = read_cfg(guild.id).get(cfg_key)
        role = guild.get_role(int(rid)) if rid and str(rid).isdigit() else None
        if role is None:
            role = discord.utils.get(guild.roles, name=name)
        if role is None:
            role = await guild.create_role(name=name, colour=discord.Colour(color), hoist=hoist,
                                           permissions=perms or discord.Permissions.none(), reason="/setup")
            return role, True
        return role, False
    async def build(self, guild, style=sl.DEFAULT_STYLE, sections=None, game_layout="grouped",
                    theme=sl.DEFAULT_THEME, pattern=None, cat_pattern=None, post_panels=True, progress=None):
        if guild.id in self.building:
            return "something is already running for this server, wait for it to finish"
        me = guild.me
        if not (me.guild_permissions.manage_channels and me.guild_permissions.manage_roles):
            return '❌ I need **Manage Channels** and **Manage Roles** to build the server'
        style = style if style in sl.STYLES else sl.DEFAULT_STYLE
        theme = theme if theme in sl.THEMES else sl.DEFAULT_THEME
        self.building.add(guild.id)
        async def say(line):
            if progress:
                await progress(line)
        try:
            return await self._build(guild, style, sections, game_layout, theme, pattern, cat_pattern, post_panels, say)
        except discord.Forbidden as e:
            return f"❌ Discord refused part of the build (missing permission?): {e}"
        finally:
            self.building.discard(guild.id)
    async def _build(self, guild, style, sections, game_layout, theme, pattern, cat_pattern, post_panels, say):
        plan = sl.build_plan(style, sections, game_layout, theme, pattern, cat_pattern)
        accent = sl.THEMES[theme]['accent']
        created = reused = 0
        made_roles = []
        await say('making roles…')
        staff, new = await self.ensure_role(guild, "staff_role_id", "🃏 Staff Team", accent, hoist=True,
                                       perms=discord.Permissions(manage_messages=True, kick_members=True,
                                                                 moderate_members=True, mute_members=True))
        if new: made_roles.append(str(staff.id))
        manager, new = await self.ensure_role(guild, "manager_role", "🎰 Dealer", 0xF5C542)
        if new: made_roles.append(str(manager.id))
        ping_roles = []
        existing_pings = {r["name"]: r for r in (read_cfg(guild.id).get("self_roles") or [])}
        for i, pr in enumerate(sl.PING_ROLES):
            role = None
            if pr["name"] in existing_pings:
                role = guild.get_role(int(existing_pings[pr['name']]['id']))
            role = role or discord.utils.get(guild.roles, name=pr["name"])
            if role is None:
                role = await guild.create_role(name=pr['name'], mentionable=True, reason='/setup ping role')
                made_roles.append(str(role.id))
            emo = pr["emoji"] if theme == "emoji" else (sl.icon_for(theme, "", pr["emoji"], i) if theme in ("redblack", "ribbon") else None)
            ping_roles.append({"id": str(role.id), "name": pr["name"], "emoji": emo})
        def save_roles(g):
            g['staff_role_id'] = str(staff.id)
            g["manager_role"] = manager.id
            g["self_roles"] = ping_roles
        await update_cfg(guild.id, save_roles)
        everyone = guild.default_role
        layout = read_cfg(guild.id).get("server_layout") or {}
        known = {v["key"]: int(cid) for cid, v in (layout.get("channels") or {}).items()}
        known_cats = {v["key"]: int(cid) for cid, v in (layout.get("categories") or {}).items()}
        new_layout = {'style': style, 'theme': theme, 'pattern': pattern, 'cat_pattern': cat_pattern,
                      'game_layout': game_layout, 'channels': dict(layout.get('channels') or {}),
                      'categories': dict(layout.get('categories') or {}),
                      'created_roles': sorted(set(layout.get('created_roles') or []) | set(made_roles)),
                      'panels': layout.get('panels') or {}}
        binds, game_map, panels = {}, {}, {}
        for cat_plan in plan:
            await say(f"building **{cat_plan['name']}**…")
            cat_over = {}
            if cat_plan["private"]:
                cat_over = {everyone: discord.PermissionOverwrite(view_channel=False),
                            staff: discord.PermissionOverwrite(view_channel=True),
                            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
            cat = guild.get_channel(known_cats.get(cat_plan['key'], 0))
            if cat is None:
                cat = await guild.create_category(cat_plan['name'], overwrites=cat_over, reason='/setup')
                created += 1
            else:
                reused += 1
                if cat.name != cat_plan['name']:
                    await cat.edit(name=cat_plan['name'])
            new_layout["categories"][str(cat.id)] = {"key": cat_plan["key"], "title": cat_plan["title"],
                                                     "emoji": cat_plan["emoji"]}
            if cat_plan['ticket_category']:
                binds["ticket_category_id"] = str(cat.id)
            for i, ch in enumerate(cat_plan['channels']):
                over = dict(cat_over)
                if ch.get("readonly"):
                    base = discord.PermissionOverwrite(**{k: v for k, v in over[everyone]}) if everyone in over \
                        else discord.PermissionOverwrite()
                    base.update(send_messages=False, create_public_threads=False, add_reactions=True)
                    over[everyone] = base
                    over[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True)
                    over[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                if ch.get("locked"):
                    over[everyone] = discord.PermissionOverwrite(connect=False)
                    over[guild.me] = discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)
                existing = guild.get_channel(known.get(ch["key"], 0))
                if existing is None:
                    if ch["kind"] == "voice":
                        existing = await guild.create_voice_channel(ch["name"], category=cat, overwrites=over, reason="/setup")
                    else:
                        existing = await guild.create_text_channel(ch["name"], category=cat, overwrites=over, reason="/setup")
                    created += 1
                    await asyncio.sleep(0.4)
                else:
                    reused += 1
                    if existing.name != ch['name']:
                        try:
                            await existing.edit(name=ch["name"])
                        except discord.HTTPException:
                            pass
                new_layout['channels'][str(existing.id)] = {
                    "key": ch["key"], "base": ch["base"], "emoji": ch["emoji"], "kind": ch["kind"],
                    'section': cat_plan['key'], 'pos': i, 'total': len(cat_plan['channels'])}
                for b in ch.get("binds", []):
                    binds[b] = existing.id if b == 'announce_channel' else str(existing.id)
                for game in ch.get("games", []):
                    game_map[game] = str(existing.id)
                if ch.get("panel"):
                    panels[ch["panel"]] = existing

        def save_all(g):
            for k, v in binds.items():
                g[k] = v
                flag = sl.ENABLE_FLAGS.get(k)
                if flag:
                    g[flag] = True
            if game_map:
                g.setdefault('game_channels', {}).update(game_map)
            g['server_layout'] = new_layout
        await update_cfg(guild.id, save_all)

        posted = []
        if post_panels:
            await say('posting panels…')
            posted = await self._post_panels(guild, panels, ping_roles, new_layout['panels'], accent)
        self.bot.add_view(SelfRoleView(ping_roles))
        self.bot.casino.log_event(guild.name, f"/setup built the server ({style}/{theme}): {created} created, {reused} reused")
        return (f"✅ done! **{created}** created, **{reused}** already existed.\n"
                f"style: {sl.STYLES[style]['label']} · icons: {sl.THEMES[theme]['label']} · games: {game_layout} · "
                f"wired up {len(binds)} settings and {len(game_map)} game channels"
                + (f"\nposted: {', '.join(posted)}" if posted else "")
                + "\nchanged your mind? `/setup undo` removes everything this made")
    async def _post_panels(self, guild, panels, ping_roles, already, accent=0xFF6AD5):
        posted, record = [], dict(already)
        for kind, channel in panels.items():
            if record.get(kind) == str(channel.id):
                continue
            try:
                if kind == 'rules':
                    e = discord.Embed(title=f"{guild.name} rules", color=accent,
                                      description="\n\n".join(f"**{i + 1}.** {r}" for i, r in enumerate(sl.RULES_TEXT)))
                    e.set_footer(text="breaking these can get you warned, muted, kicked, or banned")
                    await channel.send(embed=e)
                elif kind == "roles":
                    e = discord.Embed(title="pick your pings", color=accent,
                                      description="tap a button to toggle a role. tap again to remove it.\n\n" +
                                                  "\n".join(f"{r.get('emoji') or '•'} **{r['name']}**" for r in ping_roles))
                    await channel.send(embed=e, view=SelfRoleView(ping_roles))
                elif kind == 'tickets':
                    from cogs.tickets import TicketPanelView
                    e = discord.Embed(title='need help?', color=accent,
                                      description="click below to open a private ticket with staff - "
                                                  "questions, reports, appeals, bug bounties, anything.")
                    await channel.send(embed=e, view=TicketPanelView())
                elif kind == "games":
                    from cogs.games_plus import games_embed
                    e = games_embed()
                    e.color = accent
                    e.description += ("\n\nstart with `/daily`, `/claim spin` and `/quests` for free chips, "
                                      'then check `/profile`. every game has its own channel - '
                                      "playing in the wrong one tells you where to go.")
                    await channel.send(embed=e)
                record[kind] = str(channel.id)
                posted.append(kind)
            except discord.HTTPException as e:
                print(f"[setup] couldn't post {kind} panel: {e}")

        def save(g):
            g.setdefault("server_layout", {})["panels"] = record
        await update_cfg(guild.id, save)
        return posted

    async def restyle(self, guild, style, progress=None, theme=None, pattern=None, cat_pattern=None):
        layout = read_cfg(guild.id).get('server_layout') or {}
        if not layout.get('channels'):
            return "nothing to restyle - run `/setup build` first"
        style = style if style in sl.STYLES else layout.get('style') or sl.DEFAULT_STYLE
        theme = theme if theme in sl.THEMES else layout.get('theme') or sl.DEFAULT_THEME
        pattern = sl.clean_pattern(pattern, "{name}") or layout.get('pattern')
        cat_pattern = sl.clean_pattern(cat_pattern, "itle}") or layout.get('cat_pattern')
        p = sl.clean_pattern(pattern, "{name}") or "{icon}︱{name}"
        cp = sl.clean_pattern(cat_pattern, "itle}") or "{icon} {TITLE} {icon}"
        renamed = 0
        for cid, info in (layout.get("categories") or {}).items():
            cat = guild.get_channel(int(cid))
            if cat:
                name = sl.category_name(style, sl.cat_icon(theme, info.get("key"), info["emoji"]), info["title"], cp)
                if cat.name != name:
                    await cat.edit(name=name)
                    renamed += 1
        for cid, info in layout['channels'].items():
            ch = guild.get_channel(int(cid))
            if not ch:
                continue
            icon = sl.icon_for(theme, info["base"], info["emoji"], info["pos"])
            name = sl.channel_name(style, icon, info["base"], info["pos"], info["total"],
                                   voice=info["kind"] == "voice", pattern=p)
            if ch.name != name:
                try:
                    await ch.edit(name=name)
                    renamed += 1
                    if progress and renamed % 5 == 0:
                        await progress(f"renamed {renamed}…")
                except discord.HTTPException as e:
                    print(f"[setup] couldn't rename {ch.id}: {e}")
        def save(g):
            lay = g.setdefault('server_layout', {})
            lay.update(style=style, theme=theme, pattern=pattern, cat_pattern=cat_pattern)
        await update_cfg(guild.id, save)
        return (f"✅ restyled {renamed} channels/categories to **{sl.STYLES[style]['label']}** "
                f"with **{sl.THEMES[theme]['label']}** icons")

    def kit_status(self, guild, groups):
        gc = read_cfg(guild.id)
        kr = (gc.get("role_kit") or {}).get("roles") or {}
        by_name = {r.name.lower(): r for r in guild.roles}
        out = []
        for gdef in sl.ROLE_KIT:
            if gdef["key"] not in groups:
                continue
            rows = []
            for r in gdef["roles"]:
                key = f"{gdef['key']}:{r['slug']}"
                role = None
                if kr.get(key):
                    role = guild.get_role(int(kr[key]))
                if role is None and r.get("cfg") and str(gc.get(r["cfg"]) or "").isdigit():
                    role = guild.get_role(int(gc.get(r["cfg"])))
                if role is None:
                    for nm in [r["name"]] + r.get("aliases", []):
                        role = by_name.get(nm.lower())
                        if role is not None:
                            break
                rows.append((key, r, role))
            if gdef.get("divider"):
                dk = f"div:{gdef['key']}"
                drole = guild.get_role(int(kr[dk])) if kr.get(dk) else None
                drole = drole or by_name.get(gdef["divider"].lower())
                rows.insert(0, (dk, {"name": gdef["divider"], "slug": dk, "divider": True}, drole))
            out.append((gdef, rows))
        return out

    def kit_embed(self, status, channel_id):
        have = sum(1 for _, rows in status for *_, role in rows if role)
        total = sum(len(rows) for _, rows in status)
        e = discord.Embed(title="role check", color=0xFF6AD5,
                          description=f"**{have}/{total}** roles already exist · **{total - have}** will be made\n"
                                      "existing roles are kept (uncolored ones get their color), nothing gets deleted")
        for gdef, rows in status:
            lines = [("✅ " if role else "➕ ") + r["name"] for _, r, role in rows]
            e.add_field(name=f"{gdef['emoji']} {gdef['title']}", value="\n".join(lines)[:1024], inline=True)
        e.set_footer(text=("panels go in " + (f"#{self.bot.get_channel(channel_id)}" if channel_id and self.bot.get_channel(channel_id) else "no channel - pass panel_channel"))
                     + " · level/rebirth ranks get wired up automatically")
        return e

    def default_panel_channel(self, guild):
        lay = read_cfg(guild.id).get("server_layout") or {}
        for cid, info in (lay.get("channels") or {}).items():
            if info.get("key") == "start:roles" and guild.get_channel(int(cid)):
                return int(cid)
        return None

    async def apply_kit(self, guild, groups, channel_id=None, progress=None):
        if guild.id in self.building:
            return "something is already running for this server, wait for it to finish"
        if not guild.me.guild_permissions.manage_roles:
            return "❌ I need **Manage Roles** for this"
        self.building.add(guild.id)
        try:
            return await self._apply_kit(guild, groups, channel_id, progress)
        finally:
            self.building.discard(guild.id)

    async def _apply_kit(self, guild, groups, channel_id, progress):
        status = {gdef["key"]: rows for gdef, rows in self.kit_status(guild, groups)}
        kit = dict(read_cfg(guild.id).get("role_kit") or {})
        kr = dict(kit.get("roles") or {})
        made = list(kit.get("created") or [])
        ours = set(made) | set((read_cfg(guild.id).get("server_layout") or {}).get("created_roles") or [])
        new = recolored = failed = renamed = 0
        top = guild.me.top_role
        for gkey in sl.ROLE_ORDER:
            if gkey not in status:
                continue
            if progress:
                await progress(f"roles: {gkey}…")
            for key, r, role in reversed(status[gkey]):
                if role is not None and role.name != r["name"] and not r.get("divider") and str(role.id) in ours and role < top and not role.managed:
                    try:
                        await role.edit(name=r["name"], reason="/setup roles rename")
                        renamed += 1
                    except discord.HTTPException:
                        pass
                if role is None and r.get("divider"):
                    try:
                        role = await guild.create_role(name=r["name"], reason="/setup roles divider")
                        made.append(str(role.id))
                        new += 1
                    except discord.HTTPException:
                        failed += 1
                        continue
                if role is None:
                    perms = discord.Permissions.none()
                    for p in r.get("perms", []):
                        if hasattr(perms, p):
                            setattr(perms, p, True)
                    try:
                        role = await guild.create_role(name=r["name"], colour=discord.Colour(r.get("color", 0)),
                                                       hoist=r.get("hoist", False), permissions=perms, reason="/setup roles")
                    except discord.Forbidden:
                        try:
                            role = await guild.create_role(name=r["name"], colour=discord.Colour(r.get("color", 0)),
                                                           hoist=r.get("hoist", False), reason="/setup roles")
                        except discord.HTTPException:
                            failed += 1
                            continue
                    made.append(str(role.id))
                    new += 1
                    await asyncio.sleep(0.3)
                elif r.get("color") and role.colour.value == 0 and role < top and not role.managed:
                    try:
                        await role.edit(colour=discord.Colour(r["color"]), reason="/setup roles color")
                        recolored += 1
                    except discord.HTTPException:
                        pass
                kr[key] = str(role.id)

        valid = {f"{g['key']}:{r['slug']}" for g in sl.ROLE_KIT for r in g["roles"]} | {f"div:{g['key']}" for g in sl.ROLE_KIT}
        kr = {k: v for k, v in kr.items() if k in valid}
        if progress:
            await progress("putting roles in order…")
        moved, stuck = await self.fix_role_order(guild, kr)
        house = guild.get_role(int(kr["staff:house"])) if kr.get("staff:house") else None
        own = guild.get_member(guild.owner_id) if hasattr(guild, "get_member") else None
        if house and own and house not in own.roles and house < top:
            try:
                await own.add_roles(house, reason="/setup roles")
            except discord.HTTPException:
                pass

        def save(g):
            k = g.setdefault("role_kit", {})
            k["roles"] = kr
            k["created"] = sorted(set(made))
            for gdef in sl.ROLE_KIT:
                for r in gdef["roles"]:
                    rid = kr.get(f"{gdef['key']}:{r['slug']}")
                    if not rid:
                        continue
                    if r.get("cfg") and not g.get(r["cfg"]):
                        g[r["cfg"]] = int(rid) if r["cfg"] == "manager_role" else rid
                    if gdef.get("bind") and r.get("at"):
                        g.setdefault(gdef["bind"], {}).setdefault(str(r["at"]), rid)
        await update_cfg(guild.id, save)

        posted = []
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is not None:
            if progress:
                await progress("posting role panels…")
            posted = await self._post_kit_panels(guild, channel, groups, kr)
        msg = (f"✅ roles done - **{new}** made, **{renamed}** renamed, **{recolored}** recolored, "
               f"**{sum(len(v) for v in status.values()) - new - failed}** already there, **{moved}** moved into place")
        if stuck:
            msg += f"\n⚠️ {stuck} are above my role so I couldn't move them - drag my role to the top in Server Settings → Roles and run this again"
        if failed:
            msg += f"\n⚠️ {failed} couldn't be made"
        if posted:
            msg += f"\npanels in {channel.mention}: {', '.join(posted)}"
        elif channel is None and any(g.get("self") and g["key"] in groups for g in sl.ROLE_KIT):
            msg += "\nno panel channel - run it again with `panel_channel:` to post the pick-a-role buttons"
        self.bot.casino.log_event(guild.name, f"/setup roles made {new} roles")
        return msg

    async def fix_role_order(self, guild, kr):
        top = guild.me.top_role
        want = []
        for gkey in sl.ROLE_ORDER:
            gdef = next(g for g in sl.ROLE_KIT if g["key"] == gkey)
            if gdef.get("divider") and kr.get(f"div:{gkey}"):
                want.append(int(kr[f"div:{gkey}"]))
            for r in gdef["roles"]:
                rid = kr.get(f"{gkey}:{r['slug']}")
                if rid:
                    want.append(int(rid))
        roles = [guild.get_role(i) for i in want]
        roles = [r for r in roles if r is not None]
        movable = [r for r in roles if r < top and not r.managed]
        stuck = len(roles) - len(movable)
        if not movable:
            return 0, stuck
        others = [r for r in guild.roles if r < top and not r.is_default() and r not in movable]
        ordered = movable + sorted(others, key=lambda r: r.position, reverse=True)
        positions = {}
        pos = top.position - 1
        for r in ordered:
            if pos < 1:
                break
            positions[r] = pos
            pos -= 1
        changed = sum(1 for r, ps in positions.items() if r.position != ps and r in movable)
        if changed:
            try:
                await guild.edit_role_positions(positions=positions, reason="/setup roles order")
            except discord.HTTPException as e:
                print(f"[setup] role reorder failed: {e}")
                return 0, stuck
        return changed, stuck

    async def _post_kit_panels(self, guild, channel, groups, kr):
        kit = read_cfg(guild.id).get("role_kit") or {}
        panels = dict(kit.get("panels") or {})
        accent = sl.THEMES.get((read_cfg(guild.id).get("server_layout") or {}).get("theme") or "emoji", sl.THEMES["emoji"])["accent"]
        old_pings = None
        if "pings" in groups:
            try:
                async for m in channel.history(limit=50):
                    if m.author.id == guild.me.id and m.embeds and (m.embeds[0].title or "").endswith("pick your pings"):
                        old_pings = m
                        break
            except discord.HTTPException:
                pass
        posted = []
        for gdef in sl.ROLE_KIT:
            if not gdef.get("self") or gdef["key"] not in groups:
                continue
            gdef, roles = kit_panel_roles(gdef["key"], kr)
            if not roles:
                continue
            view = KitView(gdef["key"], roles, gdef.get("exclusive", False))
            emb = kit_panel_embed(gdef, roles, accent)
            msg = None
            prev = panels.get(gdef["key"])
            if prev and int(prev[0]) == channel.id:
                try:
                    msg = await channel.fetch_message(int(prev[1]))
                except discord.HTTPException:
                    msg = None
            if msg is None and gdef["key"] == "pings" and old_pings is not None:
                msg = old_pings
            try:
                if msg is not None:
                    await msg.edit(embed=emb, view=view)
                else:
                    msg = await channel.send(embed=emb, view=view)
                panels[gdef["key"]] = [str(channel.id), str(msg.id)]
                self.bot.add_view(view)
                posted.append(gdef["key"])
            except discord.HTTPException as e:
                print(f"[setup] role panel {gdef['key']} failed: {e}")

        def save(g):
            g.setdefault("role_kit", {})["panels"] = panels
        await update_cfg(guild.id, save)
        return posted

    def undo_counts(self, guild):
        layout = read_cfg(guild.id).get('server_layout') or {}
        chans = [c for c in (layout.get('channels') or {}) if guild.get_channel(int(c))]
        cats = [c for c in (layout.get('categories') or {}) if guild.get_channel(int(c))]
        kit = (read_cfg(guild.id).get('role_kit') or {}).get('created') or []
        roles = {r for r in list(layout.get('created_roles') or []) + list(kit) if guild.get_role(int(r))}
        return len(chans), len(cats), len(roles)

    async def undo(self, guild, progress=None):
        if guild.id in self.building:
            return "something is already running for this server, wait for it to finish"
        layout = read_cfg(guild.id).get('server_layout') or {}
        kit_made = (read_cfg(guild.id).get('role_kit') or {}).get('created') or []
        if not layout.get('channels') and not layout.get('categories') and not kit_made:
            return "nothing to undo - `/setup` hasn't made anything here"
        self.building.add(guild.id)
        gone_ch, gone_roles, failed = set(), set(), 0
        try:
            for cid in list((layout.get('channels') or {})) + list((layout.get('categories') or {})):
                ch = guild.get_channel(int(cid))
                if ch is None:
                    gone_ch.add(str(cid))
                    continue
                try:
                    await ch.delete(reason="/setup undo")
                    gone_ch.add(str(cid))
                    if progress and len(gone_ch) % 8 == 0:
                        await progress(f"deleted {len(gone_ch)}…")
                except discord.HTTPException:
                    failed += 1
            for rid in sorted(set(list(layout.get('created_roles') or []) + list(kit_made))):
                role = guild.get_role(int(rid))
                if role is None:
                    gone_roles.add(str(rid))
                    continue
                try:
                    await role.delete(reason="/setup undo")
                    gone_roles.add(str(rid))
                except discord.HTTPException:
                    failed += 1
        finally:
            self.building.discard(guild.id)

        def clear(g):
            for k in CLEAR_KEYS:
                if g.get(k) is not None and str(g.get(k)) in gone_ch:
                    g[k] = None
                    flag = sl.ENABLE_FLAGS.get(k)
                    if flag:
                        g[flag] = False
            g['game_channels'] = {k: v for k, v in (g.get('game_channels') or {}).items() if str(v) not in gone_ch}
            if str(g.get('staff_role_id')) in gone_roles:
                g['staff_role_id'] = None
            if str(g.get('manager_role')) in gone_roles:
                g['manager_role'] = None
            g['self_roles'] = [r for r in (g.get('self_roles') or []) if str(r.get('id')) not in gone_roles]
            g['server_layout'] = {}
            for bk in ('level_roles', 'rebirth_roles'):
                g[bk] = {k: v for k, v in (g.get(bk) or {}).items() if str(v) not in gone_roles}
            g['role_kit'] = {}
            g['status_message_id'] = None
        await update_cfg(guild.id, clear)
        self.bot.casino.log_event(guild.name, f"/setup undo removed {len(gone_ch)} channels and {len(gone_roles)} roles")
        msg = f"✅ undone - removed **{len(gone_ch)}** channels/categories and **{len(gone_roles)}** roles it had made"
        if failed:
            msg += f"\n⚠️ {failed} couldn't be deleted (check my role is high enough / I can see them)"
        return msg

    setup_group = discord.SlashCommandGroup('setup', 'build, restyle or undo the whole server',
                                            default_member_permissions=discord.Permissions(administrator=True))
    @setup_group.command(name='build', description='create all categories, channels, roles and panels')
    async def setup_build(self, ctx,
                          style: Option(str, 'divider style', choices=STYLE_CHOICES, required=False) = sl.DEFAULT_STYLE,
                          icons: Option(str, 'emoji, unicode symbols, red & black, ribbons or no icons', choices=THEME_CHOICES, required=False) = sl.DEFAULT_THEME,
                          games: Option(str, "game channel layout", choices=GAME_CHOICES, required=False) = "grouped",
                          skip: Option(str, "sections to leave out, e.g. 'voice logs'", required=False) = "",
                          pattern: Option(str, "only for style 'custom' - e.g. ꒰{icon}꒱{name}", required=False) = None,
                          category_pattern: Option(str, "only for style 'custom' - e.g. ⋆ {title} ⋆", required=False) = None):
        skip_set = set(skip.lower().replace(",", " ").split())
        sections = [k for k in sl.SECTION_KEYS if k not in skip_set]
        opts = {"style": style, "sections": sections, "game_layout": games, "theme": icons,
                "pattern": pattern, "cat_pattern": category_pattern}
        await ctx.respond("here's what I'll build - nothing gets deleted, and anything I made before gets reused:",
                          embed=preview_embed(style, sections, games, icons, pattern, category_pattern),
                          view=ConfirmBuild(self, ctx.author, opts), ephemeral=True)
    @setup_group.command(name="restyle", description="rename every channel /setup made to a new style or icon set")
    async def setup_restyle(self, ctx, style: Option(str, 'divider style', choices=STYLE_CHOICES),
                            icons: Option(str, 'icon set', choices=THEME_CHOICES, required=False) = None,
                            pattern: Option(str, "only for style 'custom' - e.g. ꒰{icon}꒱{name}", required=False) = None,
                            category_pattern: Option(str, "only for style 'custom' - e.g. ⋆ {title} ⋆", required=False) = None):
        await ctx.defer(ephemeral=True)
        await ctx.followup.send(await self.restyle(ctx.guild, style, None, icons, pattern, category_pattern), ephemeral=True)
    @setup_group.command(name='preview', description='see a style before using it')
    async def setup_preview(self, ctx,
                            style: Option(str, 'divider style', choices=STYLE_CHOICES),
                            icons: Option(str, 'icon set', choices=THEME_CHOICES, required=False) = sl.DEFAULT_THEME,
                            games: Option(str, "game channel layout", choices=GAME_CHOICES, required=False) = "grouped",
                            pattern: Option(str, "only for style 'custom'", required=False) = None,
                            category_pattern: Option(str, "only for style 'custom'", required=False) = None):
        await ctx.respond(embed=preview_embed(style, None, games, icons, pattern, category_pattern), ephemeral=True)
    @setup_group.command(name='undo', description='delete every channel, category and role /setup build made')
    async def setup_undo(self, ctx):
        ch, cats, roles = self.undo_counts(ctx.guild)
        if not (ch or cats or roles):
            return await ctx.respond("nothing to undo - `/setup` hasn't made anything here", ephemeral=True)
        await ctx.respond(f"⚠️ this deletes **{ch}** channels, **{cats}** categories and **{roles}** roles that `/setup` made, "
                          "**including every message in those channels**. channels and roles that were already here stay. "
                          "this can't be reversed.", view=ConfirmUndo(self, ctx.author), ephemeral=True)

    async def _roles_prompt(self, ctx, groups_raw, channel, send):
        raw = (groups_raw or "all").lower().replace(",", " ").split()
        groups = sl.ROLE_KIT_KEYS if not raw or "all" in raw else [k for k in sl.ROLE_KIT_KEYS if k in raw]
        if not groups:
            return await send("groups: " + ", ".join(f"`{k}`" for k in sl.ROLE_KIT_KEYS) + " (or `all`)")
        cid = channel.id if channel else self.default_panel_channel(ctx.guild)
        await send("here's what I found:", embed=self.kit_embed(self.kit_status(ctx.guild, groups), cid),
                   view=ConfirmRoles(self, ctx.author, groups, cid))

    @setup_group.command(name='roles', description='check for missing roles, make them, and post pick-a-role panels')
    async def setup_roles(self, ctx,
                          groups: Option(str, "which sets, e.g. 'colors pings' - default all", required=False) = "all",
                          panel_channel: Option(discord.TextChannel, "where the pick-a-role buttons go", required=False) = None):
        await self._roles_prompt(ctx, groups, panel_channel, lambda *a, **k: ctx.respond(*a, ephemeral=True, **k))

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_cmd(self, ctx, style: str = sl.DEFAULT_STYLE, icons: str = sl.DEFAULT_THEME, games: str = "grouped"):
        if style == "roles":
            ch = ctx.message.channel_mentions[0] if ctx.message.channel_mentions else None
            grp = " ".join(w for w in ctx.message.content.split()[2:] if not w.startswith("<#"))
            return await self._roles_prompt(ctx, grp, ch, ctx.send)
        if style == "undo":
            ch, cats, roles = self.undo_counts(ctx.guild)
            if not (ch or cats or roles):
                return await ctx.send("nothing to undo")
            return await ctx.send(f"⚠️ this deletes **{ch}** channels, **{cats}** categories and **{roles}** roles "
                                  "`/setup build` made, including all messages in them. can't be reversed.",
                                  view=ConfirmUndo(self, ctx.author))
        if style not in sl.STYLES or style == "custom":
            names = ', '.join('`' + k + '` ' + v['sample'] for k, v in sl.STYLES.items() if k != 'custom')
            return await ctx.send('styles: ' + names + '\nicons: ' + ', '.join(f'`{k}`' for k in sl.THEMES)
                                  + '\n(custom patterns are slash-only: `/setup build style:custom`)')
        if icons not in sl.THEMES:
            icons = sl.DEFAULT_THEME
        if games not in GAME_CHOICES:
            games = 'grouped'
        opts = {'style': style, 'sections': None, 'game_layout': games, 'theme': icons}
        await ctx.send("here's what I'll build - nothing gets deleted:", embed=preview_embed(style, None, games, icons),
                       view=ConfirmBuild(self, ctx.author, opts))
    @tasks.loop(seconds=10)
    async def request_loop(self):
        cfg = cfgschema.load_cfg()
        for guild in self.bot.guilds:
            req = (cfg.get(str(guild.id)) or {}).get("setup_request")
            if not req:
                continue

            def take(g):
                g["setup_request"] = None
                g['setup_status'] = {'state': 'running', 'log': [], 'ts': time.time(), 'action': req.get('action')}
            await update_cfg(guild.id, take)
            lines = []

            async def progress(line):
                lines.append(line)

                def save(g):
                    g["setup_status"] = {"state": "running", "log": lines[-15:], "ts": time.time(), "action": req.get("action")}
                await update_cfg(guild.id, save)
            try:
                style = req.get('style') if req.get('style') in sl.STYLES else sl.DEFAULT_STYLE
                theme = req.get('theme') if req.get('theme') in sl.THEMES else sl.DEFAULT_THEME
                if req.get("action") == "restyle":
                    result = await self.restyle(guild, style, progress, theme, req.get('pattern'), req.get('cat_pattern'))
                elif req.get("action") == "undo":
                    result = await self.undo(guild, progress)
                elif req.get("action") == "roles":
                    pc = req.get("panel_channel")
                    pc = int(pc) if pc and str(pc).isdigit() else self.default_panel_channel(guild)
                    result = await self.apply_kit(guild, req.get("groups") or sl.ROLE_KIT_KEYS, pc, progress)
                else:
                    result = await self.build(guild, style=style, sections=req.get('sections') or None,
                                              game_layout=req.get('game_layout', 'grouped'), theme=theme,
                                              pattern=req.get('pattern'), cat_pattern=req.get('cat_pattern'),
                                              progress=progress)
                state = "error" if result.startswith("❌") else "done"
            except Exception as e:
                result, state = f"❌ {e}", "error"
            lines.append(result)

            def finish(g):
                g["setup_status"] = {"state": state, "log": lines[-15:], "ts": time.time(), "action": req.get("action")}
            await update_cfg(guild.id, finish)

    @request_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(ServerSetup(bot))
