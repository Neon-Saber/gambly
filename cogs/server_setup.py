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


class SelfRoleView(discord.ui.View):
    def __init__(self, roles):
        super().__init__(timeout=None)
        for r in roles:
            b = discord.ui.Button(label=r['name'], emoji=r.get('emoji'), style=discord.ButtonStyle.secondary,
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

def preview_embed(style, sections=None, game_layout="grouped"):
    plan = sl.build_plan(style, sections, game_layout)
    e = discord.Embed(title=f"server layout · {sl.STYLES[style]['label']}", color=0xFF6AD5)
    for cat in plan:
        lines = [("🔊 " if c["kind"] == "voice" else "# ") + c["name"] for c in cat["channels"]]
        text = "\n".join(lines)
        if len(text) > 1000:
            text = text[:990] + "\n…"
        e.add_field(name=cat['name'] + (' 🔒' if cat['private'] else ''), value=text, inline=True)
    n = sum(len(c['channels']) for c in plan)
    e.set_footer(text=f"{len(plan)} categories · {n} channels · existing channels are never deleted")
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
        return role
    async def build(self, guild, style=sl.DEFAULT_STYLE, sections=None, game_layout="grouped",
                    post_panels=True, progress=None):
        if guild.id in self.building:
            return "a build is already running for this server"
        me = guild.me
        if not (me.guild_permissions.manage_channels and me.guild_permissions.manage_roles):
            return '❌ I need **Manage Channels** and **Manage Roles** to build the server'
        self.building.add(guild.id)
        log = []
        async def say(line):
            log.append(line)
            if progress:
                await progress(line)
        try:
            return await self._build(guild, style, sections, game_layout, post_panels, say, log)
        except discord.Forbidden as e:
            return f"❌ Discord refused part of the build (missing permission?): {e}"
        finally:
            self.building.discard(guild.id)
    async def _build(self, guild, style, sections, game_layout, post_panels, say, log):
        plan = sl.build_plan(style, sections, game_layout)
        created = reused = 0
        await say('making roles…')
        staff = await self.ensure_role(guild, "staff_role_id", "Staff", 0xFF6AD5, hoist=True,
                                       perms=discord.Permissions(manage_messages=True, kick_members=True,
                                                                 moderate_members=True, mute_members=True))
        manager = await self.ensure_role(guild, "manager_role", "Casino Manager", 0xF5C542)
        ping_roles = []
        existing_pings = {r["name"]: r for r in (read_cfg(guild.id).get("self_roles") or [])}
        for pr in sl.PING_ROLES:
            role = None
            if pr["name"] in existing_pings:
                role = guild.get_role(int(existing_pings[pr['name']]['id']))
            role = role or discord.utils.get(guild.roles, name=pr["name"])
            if role is None:
                role = await guild.create_role(name=pr['name'], mentionable=True, reason='/setup ping role')
            ping_roles.append({"id": str(role.id), "name": pr["name"], "emoji": pr["emoji"]})
        def save_roles(g):
            g['staff_role_id'] = str(staff.id)
            g["manager_role"] = manager.id
            g["self_roles"] = ping_roles
        await update_cfg(guild.id, save_roles)
        everyone = guild.default_role
        layout = read_cfg(guild.id).get("server_layout") or {}
        known = {v["key"]: int(cid) for cid, v in (layout.get("channels") or {}).items()}
        known_cats = {v["key"]: int(cid) for cid, v in (layout.get("categories") or {}).items()}
        new_layout = {'style': style, 'game_layout': game_layout, 'channels': dict(layout.get('channels') or {}),
                      'categories': dict(layout.get('categories') or {})}
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
            posted = await self._post_panels(guild, panels, ping_roles, layout.get('panels') or {})
        self.bot.add_view(SelfRoleView(ping_roles))
        self.bot.casino.log_event(guild.name, f"/setup built the server ({style} style): {created} created, {reused} reused")
        return (f"✅ done! **{created}** created, **{reused}** already existed.\n"
                f"style: {sl.STYLES[style]['label']} · games: {game_layout} · "
                f"wired up {len(binds)} settings and {len(game_map)} game channels"
                + (f"\nposted: {', '.join(posted)}" if posted else ""))
    async def _post_panels(self, guild, panels, ping_roles, already):
        posted, record = [], dict(already)
        for kind, channel in panels.items():
            if record.get(kind) == str(channel.id):
                continue
            try:
                if kind == 'rules':
                    e = discord.Embed(title=f"📜 {guild.name} rules", color=0xFF6AD5,
                                      description="\n\n".join(f"**{i + 1}.** {r}" for i, r in enumerate(sl.RULES_TEXT)))
                    e.set_footer(text="breaking these can get you warned, muted, kicked, or banned")
                    await channel.send(embed=e)
                elif kind == "roles":
                    e = discord.Embed(title="🏷️ pick your pings", color=0xFF6AD5,
                                      description="tap a button to toggle a role. tap again to remove it.\n\n" +
                                                  "\n".join(f"{r['emoji']} **{r['name']}**" for r in ping_roles))
                    await channel.send(embed=e, view=SelfRoleView(ping_roles))
                elif kind == 'tickets':
                    from cogs.tickets import TicketPanelView
                    e = discord.Embed(title='📩 need help?', color=embeds.COLOR_INFO,
                                      description="click below to open a private ticket with staff - "
                                                  "questions, reports, appeals, bug bounties, anything.")
                    await channel.send(embed=e, view=TicketPanelView())
                elif kind == "games":
                    from cogs.games_plus import games_embed
                    e = games_embed()
                    e.description += ("\n\nstart with `/daily`, `/spin` and `/quests` for free chips, "
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

    async def restyle(self, guild, style, progress=None):
        layout = read_cfg(guild.id).get('server_layout') or {}
        if not layout.get('channels'):
            return "nothing to restyle - run `/setup build` first"
        renamed = 0
        for cid, info in (layout.get("categories") or {}).items():
            cat = guild.get_channel(int(cid))
            if cat:
                name = sl.category_name(style, info["emoji"], info["title"])
                if cat.name != name:
                    await cat.edit(name=name)
                    renamed += 1
        for cid, info in layout['channels'].items():
            ch = guild.get_channel(int(cid))
            if not ch:
                continue
            name = sl.channel_name(style, info["emoji"], info["base"], info["pos"], info["total"],
                                   voice=info["kind"] == "voice")
            if ch.name != name:
                try:
                    await ch.edit(name=name)
                    renamed += 1
                    if progress and renamed % 5 == 0:
                        await progress(f"renamed {renamed}…")
                except discord.HTTPException as e:
                    print(f"[setup] couldn't rename {ch.id}: {e}")
        def save(g):
            g.setdefault('server_layout', {})['style'] = style
        await update_cfg(guild.id, save)
        return f"✅ restyled {renamed} channels/categories to **{sl.STYLES[style]['label']}** ({sl.STYLES[style]['sample']})"
    setup_group = discord.SlashCommandGroup('setup', 'build or restyle the whole server',
                                            default_member_permissions=discord.Permissions(administrator=True))
    @setup_group.command(name='build', description='create all categories, channels, roles and panels')
    async def setup_build(self, ctx,
                          style: Option(str, 'divider style', choices=list(sl.STYLES), required=False) = sl.DEFAULT_STYLE,
                          games: Option(str, "game channel layout", choices=["grouped", "per-game", "none"], required=False) = "grouped",
                          skip: Option(str, "sections to leave out, e.g. 'voice logs'", required=False) = ""):
        skip_set = set(skip.lower().replace(",", " ").split())
        sections = [k for k in sl.SECTION_KEYS if k not in skip_set]
        opts = {"style": style, "sections": sections, "game_layout": games}
        await ctx.respond("here's what I'll build - nothing gets deleted, and anything I made before gets reused:",
                          embed=preview_embed(style, sections, games),
                          view=ConfirmBuild(self, ctx.author, opts), ephemeral=True)
    @setup_group.command(name="restyle", description="rename every channel /setup made to a new divider style")
    async def setup_restyle(self, ctx, style: Option(str, 'divider style', choices=list(sl.STYLES))):
        await ctx.defer(ephemeral=True)
        await ctx.followup.send(await self.restyle(ctx.guild, style), ephemeral=True)
    @setup_group.command(name='preview', description='see a divider style before using it')
    async def setup_preview(self, ctx,
                            style: Option(str, 'divider style', choices=list(sl.STYLES)),
                            games: Option(str, "game channel layout", choices=["grouped", "per-game", "none"], required=False) = "grouped"):
        await ctx.respond(embed=preview_embed(style, None, games), ephemeral=True)
    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_cmd(self, ctx, style: str = sl.DEFAULT_STYLE, games: str = "grouped"):
        if style not in sl.STYLES:
            names = ', '.join('`' + k + '` ' + v['sample'] for k, v in sl.STYLES.items())
            return await ctx.send('styles: ' + names)
        if games not in ("grouped", "per-game", "none"):
            games = 'grouped'
        opts = {'style': style, 'sections': None, 'game_layout': games}
        await ctx.send("here's what I'll build - nothing gets deleted:", embed=preview_embed(style, None, games),
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
                if req.get("action") == "restyle":
                    result = await self.restyle(guild, style, progress)
                else:
                    result = await self.build(guild, style=style, sections=req.get('sections') or None,
                                              game_layout=req.get('game_layout', 'grouped'), progress=progress)
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
