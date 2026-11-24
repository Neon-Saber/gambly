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
    @commands.Cog.listener()
    async def on_ready(self):
        if not self._views_done:
            self._views_done = True
            for g in self.bot.guilds:
                roles = (read_cfg(g.id).get("self_roles") or [])
                if roles:
                    self.bot.add_view(SelfRoleView(roles))
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
        staff, new = await self.ensure_role(guild, "staff_role_id", "Staff", accent, hoist=True,
                                       perms=discord.Permissions(manage_messages=True, kick_members=True,
                                                                 moderate_members=True, mute_members=True))
        if new: made_roles.append(str(staff.id))
        manager, new = await self.ensure_role(guild, "manager_role", "Casino Manager", 0xF5C542)
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

    def undo_counts(self, guild):
        layout = read_cfg(guild.id).get('server_layout') or {}
        chans = [c for c in (layout.get('channels') or {}) if guild.get_channel(int(c))]
        cats = [c for c in (layout.get('categories') or {}) if guild.get_channel(int(c))]
        roles = [r for r in (layout.get('created_roles') or []) if guild.get_role(int(r))]
        return len(chans), len(cats), len(roles)

    async def undo(self, guild, progress=None):
        if guild.id in self.building:
            return "something is already running for this server, wait for it to finish"
        layout = read_cfg(guild.id).get('server_layout') or {}
        if not layout.get('channels') and not layout.get('categories'):
            return "nothing to undo - `/setup build` hasn't made anything here"
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
            for rid in layout.get('created_roles') or []:
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
        if not (ch or cats):
            return await ctx.respond("nothing to undo - `/setup build` hasn't made anything here", ephemeral=True)
        await ctx.respond(f"⚠️ this deletes **{ch}** channels, **{cats}** categories and **{roles}** roles that `/setup build` made, "
                          "**including every message in those channels**. channels and roles that were already here stay. "
                          "this can't be reversed.", view=ConfirmUndo(self, ctx.author), ephemeral=True)

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_cmd(self, ctx, style: str = sl.DEFAULT_STYLE, icons: str = sl.DEFAULT_THEME, games: str = "grouped"):
        if style == "undo":
            ch, cats, roles = self.undo_counts(ctx.guild)
            if not (ch or cats):
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
