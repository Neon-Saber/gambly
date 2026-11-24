import asyncio
import random
import time
from datetime import datetime, timezone

import discord
from discord import Option
from discord.ext import commands

import cog_utils as cu
from casino_kit import Kit, bar

WEEKLY_AMT, WEEKLY_WAIT = 2_000, 7 * 86400
MONTHLY_AMT, MONTHLY_WAIT = 7_500, 30 * 86400
SPIN_WAIT = 86400
GATHER_WAIT = 600

SPIN_PRIZES = [(50, 30), (100, 25), (250, 18), (500, 12), (1_000, 8), (2_500, 4), (5_000, 2), (10_000, 1)]

LOOT = {
    "fish": [
        ("old boot", "🥾", 5, 18, "junk"), ("seaweed", "🌿", 10, 15, "junk"),
        ("sardine", "🐟", 40, 25, "common"), ("tropical fish", "🐠", 90, 16, "uncommon"),
        ("pufferfish", "🐡", 160, 10, "uncommon"), ("octopus", "🐙", 300, 7, "rare"),
        ('shark', '🦈', 650, 4, 'epic'), ('whale', '🐋', 1_400, 1.5, 'legendary'),
        ('golden koi', '🎏', 3_000, 0.5, 'mythic'),
    ],
    "mine": [
        ('rubble', '🪨', 5, 20, 'junk'), ('coal', '⚫', 35, 26, 'common'),
        ("iron", "🔩", 80, 18, "uncommon"), ("gold nugget", "🟡", 180, 12, "uncommon"),
        ('amethyst', '🟣', 320, 7, 'rare'), ('emerald', '🟢', 600, 4, 'epic'),
        ("diamond", "💎", 1_500, 1.5, "legendary"), ("neon crystal", "🔮", 3_200, 0.5, "mythic"),
    ],
    "hunt": [
        ("nothing but leaves", "🍂", 0, 15, "junk"), ("rabbit", "🐇", 45, 26, "common"),
        ('duck', '🦆', 70, 20, 'common'), ('fox', '🦊', 160, 12, 'uncommon'),
        ("deer", "🦌", 280, 8, "rare"), ("boar", "🐗", 420, 6, "rare"),
        ("bear", "🐻", 900, 3, "epic"), ("unicorn", "🦄", 3_000, 0.5, "mythic"),
    ],
}
GATHER_VERBS = {"fish": ("🎣", "cast your line and caught"), "mine": ("⛏️", "swung your pickaxe and found"),
                "hunt": ("🏹", "went hunting and came back with")}
RARITY_COLOR = {"junk": 0x777777, "common": 0xB5B5B5, "uncommon": 0x3BD671, "rare": 0x3B82F6,
                "epic": 0xB45CFF, "legendary": 0xF5C542, "mythic": 0xFF6AD5}

QUEST_POOL = [
    {"id": "play10", "label": "play 10 casino games", "kind": "play", "goal": 10, "reward": 600},
    {'id': 'play25', 'label': 'play 25 casino games', 'kind': 'play', 'goal': 25, 'reward': 1_500},
    {"id": "variety4", "label": "play 4 different games", "kind": "variety", "goal": 4, "reward": 800},
    {"id": "variety7", "label": "play 7 different games", "kind": "variety", "goal": 7, "reward": 1_600},
    {"id": "gather5", "label": "fish, mine or hunt 5 times", "kind": "gather", "goal": 5, "reward": 700},
    {'id': 'work3', 'label': 'use /work 3 times', 'kind': 'work', 'goal': 3, 'reward': 500},
    {"id": "daily1", "label": "claim your /daily", "kind": "daily", "goal": 1, "reward": 250},
    {"id": "trivia3", "label": "answer 3 trivia questions right", "kind": "trivia", "goal": 3, "reward": 900},
]

TRIVIA = [
    ("how many sides does a hexagon have?", "6", ["5", "7", "8"]),
    ("what planet is known as the red planet?", "Mars", ["Venus", "Jupiter", "Mercury"]),
    ("what's the largest ocean on earth?", "Pacific", ["Atlantic", "Indian", "Arctic"]),
    ("how many cards are in a standard deck (no jokers)?", "52", ["48", "54", "56"]),
    ("in roulette, what color is the 0 pocket?", "green", ["red", "black", "blue"]),
    ("what's the chemical symbol for gold?", "Au", ["Ag", "Gd", "Go"]),
    ("how many players are on a soccer team on the field?", "11", ["9", "10", "12"]),
    ("what's 12 × 12?", "144", ["124", "132", "148"]),
    ('which animal is known as the king of the jungle?', 'lion', ['tiger', 'elephant', 'gorilla']),
    ("what gas do plants absorb from the air?", "carbon dioxide", ["oxygen", "nitrogen", "helium"]),
    ("how many continents are there?", "7", ["5", "6", "8"]),
    ("what's the fastest land animal?", "cheetah", ["lion", "pronghorn", "greyhound"]),
    ("in blackjack, what total are you trying to reach?", "21", ["20", "22", "24"]),
    ("what's the smallest prime number?", "2", ["1", "3", "0"]),
    ("which instrument has 88 keys?", "piano", ["organ", "accordion", "harp"]),
    ("what's the capital of japan?", "Tokyo", ["Kyoto", "Osaka", "Seoul"]),
    ("how many minutes are in a day?", "1440", ["1240", "1400", "1600"]),
    ('what do bees make?', 'honey', ['wax only', 'milk', 'silk']),
    ("what's the hardest natural substance?", "diamond", ["quartz", "iron", "granite"]),
    ("how many dots are on a standard six-sided die in total?", "21", ["18", "20", "24"]),
    ("which color do you get mixing blue and yellow?", "green", ["purple", "orange", "brown"]),
    ("what's the boiling point of water in °C at sea level?", "100", ["90", "110", "212"]),
    ("what's the largest planet in our solar system?", "Jupiter", ["Saturn", "Neptune", "Earth"]),
    ('how many legs does a spider have?', '8', ['6', '10', '12']),
    ('what is the square root of 81?', '9', ['8', '7', '11']),
]


def today_key():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def fmt_wait(seconds):
    return cu.format_duration(max(int(seconds), 1))


def daily_quests(a, uid):
    q = a.get("quests")
    if not q or q.get("day") != today_key():
        rng = random.Random(f"{uid}:{today_key()}")
        picks = rng.sample(QUEST_POOL, 3)
        q = {"day": today_key(), "variety": [],
             "list": [dict(p, progress=0, claimed=False) for p in picks]}
        a["quests"] = q
    return q


def bump_quests(a, uid, kind, amount=1, game=None):
    q = daily_quests(a, uid)
    if kind == "play" and game and game not in q["variety"]:
        q["variety"].append(game)
    for item in q['list']:
        if item['kind'] == kind:
            item['progress'] = min(item['goal'], item['progress'] + amount)
        elif item["kind"] == "variety" and kind == "play":
            item["progress"] = min(item["goal"], len(q["variety"]))

class QuestClaim(discord.ui.View):
    def __init__(self, cog, owner):
        super().__init__(timeout=120)
        self.cog, self.owner = cog, owner
    @discord.ui.button(label="claim rewards", emoji="🎁", style=discord.ButtonStyle.success)
    async def claim(self, button, interaction):
        if interaction.user.id != self.owner.id:
            return await interaction.response.send_message("these aren't your quests", ephemeral=True)
        space = self.cog.kit.c.get_space(interaction) if interaction.guild is None else interaction.guild
        got = {'v': 0}
        def fn(a):
            q = daily_quests(a, str(interaction.user.id))
            for item in q["list"]:
                if item["progress"] >= item["goal"] and not item["claimed"]:
                    item["claimed"] = True
                    got["v"] += item["reward"]
            a['bal'] += got['v']
            return q
        q = await self.cog.kit.with_account(space, interaction.user, fn)
        msg = f"claimed {self.cog.kit.chips(got['v'])}!" if got["v"] else "nothing finished to claim yet"
        await interaction.response.edit_message(embed=quests_embed(q, interaction.user, self.cog.kit.chips, msg), view=self)

def quests_embed(q, member, chips, footer=''):
    e = discord.Embed(title=f"📜 {member.display_name}'s daily quests", color=0xFF6AD5)
    for item in q['list']:
        state = '✅ claimed' if item['claimed'] else ('🎁 ready to claim' if item['progress'] >= item['goal'] else '')
        e.add_field(name=f"{item['label']} · {chips(item['reward'])}",
                    value=f"{bar(item['progress'], item['goal'])} {item['progress']}/{item['goal']} {state}", inline=False)
    e.set_footer(text=(footer + " · " if footer else "") + "resets at midnight UTC")
    return e


class TriviaView(discord.ui.View):
    def __init__(self, cog, owner, question, answer, options, reward):
        super().__init__(timeout=20)
        self.cog, self.owner, self.answer, self.reward = cog, owner, answer, reward
        self.question = question
        self.message = None
        self.done = False
        for opt in options:
            b = discord.ui.Button(label=opt[:80], style=discord.ButtonStyle.secondary)
            b.callback = self._make(opt, b)
            self.add_item(b)

    def _make(self, opt, button):
        async def cb(interaction):
            if interaction.user.id != self.owner.id:
                return await interaction.response.send_message("not your question", ephemeral=True)
            if self.done:
                return await interaction.response.defer()
            self.done = True
            for item in self.children:
                item.disabled = True
                if item.label == self.answer:
                    item.style = discord.ButtonStyle.success
            space = interaction.guild or self.cog.kit.c.get_space(interaction)
            if opt == self.answer:
                def fn(a):
                    a["bal"] += self.reward
                    bump_quests(a, str(interaction.user.id), 'trivia')
                await self.cog.kit.with_account(space, interaction.user, fn)
                text = f"✅ correct! +{self.cog.kit.chips(self.reward)}"
            else:
                button.style = discord.ButtonStyle.danger
                text = f"❌ nope - it was **{self.answer}**"
            await interaction.response.edit_message(content=f"🧠 {self.question}\n{text}", view=self)
            self.stop()
        return cb

    async def on_timeout(self):
        if not self.done and self.message:
            try:
                await self.message.edit(content=f"🧠 {self.question}\n⏱️ time's up - it was **{self.answer}**", view=None)
            except discord.HTTPException:
                pass


class GiveawayView(discord.ui.View):
    def __init__(self, prize, winners, ends):
        super().__init__(timeout=None)
        self.prize, self.winners, self.ends = prize, winners, ends
        self.entrants = {}
        self.message = None
        self.closed = False

    @discord.ui.button(label="enter", emoji="🎉", style=discord.ButtonStyle.primary)
    async def enter(self, button, interaction):
        if self.closed:
            return await interaction.response.send_message("this giveaway's over", ephemeral=True)
        if interaction.user.id in self.entrants:
            return await interaction.response.send_message("you're already entered", ephemeral=True)
        self.entrants[interaction.user.id] = interaction.user
        await interaction.response.send_message(f"you're in! ({len(self.entrants)} entered)", ephemeral=True)

class EconomyPlus(commands.Cog):
    claim = discord.SlashCommandGroup('claim', 'weekly, monthly and the daily lucky spin')
    gather = discord.SlashCommandGroup('gather', 'fish, mine, hunt and your collection')
    def __init__(self, bot):
        self.bot = bot
        self.kit = Kit(bot)
        self.trivia_cd = {}
        all_games = set(bot.casino.GAME_COMMANDS) | set(cu.GAME_CHANNEL_ALIASES)
        all_games.discard("jackpot")
        self.game_names = all_games

    async def _track(self, ctx):
        cmd = ctx.command.name if ctx.command else None
        if not cmd:
            return
        if cmd in self.game_names:
            kind = "play"
        elif cmd in ('work', 'daily'):
            kind = cmd
        else:
            return
        space = self.kit.c.get_space(ctx)
        try:
            await self.kit.with_account(space, ctx.author, lambda a: bump_quests(a, str(ctx.author.id), kind, game=cmd))
        except Exception as e:
            print(f"[quests] couldn't track {cmd}: {e}")

    @commands.Cog.listener()
    async def on_application_command_completion(self, ctx):
        await self._track(ctx)
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        await self._track(ctx)
    async def _timed_claim(self, ctx, key, wait, amount, label):
        space = self.kit.c.get_space(ctx)
        out = {}

        def fn(a):
            last = a.get(key, 0)
            left = last + wait - time.time()
            if left > 0:
                out['left'] = left
                return
            a[key] = time.time()
            a["bal"] += amount
            out["bal"] = a["bal"]
        await self.kit.with_account(space, ctx.author, fn)
        if "left" in out:
            return await self.kit.reply(ctx, content=f"your {label} isn't ready - come back in **{fmt_wait(out['left'])}**", ephemeral=True)
        e = discord.Embed(title=f"🎁 {label} claimed", color=0x3BD671,
                          description=f"+{self.kit.chips(amount)}\nwallet: {self.kit.chips(out['bal'])}")
        await self.kit.reply(ctx, embed=e)
    @claim.command(name="weekly", description=f"claim {WEEKLY_AMT:,} chips once a week")
    async def weekly(self, ctx):
        await self._timed_claim(ctx, "last_weekly", WEEKLY_WAIT, WEEKLY_AMT, "weekly")
    @commands.command(name="weekly")
    async def weekly_cmd(self, ctx):
        await self._timed_claim(ctx, "last_weekly", WEEKLY_WAIT, WEEKLY_AMT, "weekly")
    @claim.command(name="monthly", description=f"claim {MONTHLY_AMT:,} chips once a month")
    async def monthly(self, ctx):
        await self._timed_claim(ctx, "last_monthly", MONTHLY_WAIT, MONTHLY_AMT, "monthly")
    @commands.command(name="monthly")
    async def monthly_cmd(self, ctx):
        await self._timed_claim(ctx, "last_monthly", MONTHLY_WAIT, MONTHLY_AMT, "monthly")
    async def _spin(self, ctx):
        space = self.kit.c.get_space(ctx)
        out = {}
        def fn(a):
            left = a.get('last_spin', 0) + SPIN_WAIT - time.time()
            if left > 0:
                out['left'] = left
                return
            prize = random.choices([p for p, _ in SPIN_PRIZES], weights=[w for _, w in SPIN_PRIZES])[0]
            a["last_spin"] = time.time()
            a["bal"] += prize
            out.update(prize=prize, bal=a["bal"])
        await self.kit.with_account(space, ctx.author, fn)
        if "left" in out:
            return await self.kit.reply(ctx, content=f"you already spun today - next spin in **{fmt_wait(out['left'])}**", ephemeral=True)
        wheel = " ".join(("**[" + f"{p:,}" + "]**") if p == out["prize"] else f"{p:,}" for p, _ in SPIN_PRIZES)
        e = discord.Embed(title="🎡 daily lucky spin", color=0xFF6AD5,
                          description=f"{wheel}\n\nyou won **{self.kit.chips(out['prize'])}**!\nwallet: {self.kit.chips(out['bal'])}")
        await self.kit.reply(ctx, embed=e)
    @claim.command(name="spin", description="free daily lucky wheel spin")
    async def spin(self, ctx):
        await self._spin(ctx)

    @commands.command(name="spin")
    async def spin_cmd(self, ctx):
        await self._spin(ctx)

    async def _gather(self, ctx, kind):
        space = self.kit.c.get_space(ctx)
        if self.kit.c.is_banned(ctx.author, space):
            return await self.kit.reply(ctx, content="you're banned from the economy here", ephemeral=True)
        table = LOOT[kind]
        out = {}
        rebirth_mult = self.kit.c.rebirth_mult

        def fn(a):
            key = f"last_{kind}"
            left = a.get(key, 0) + GATHER_WAIT - time.time()
            if left > 0:
                out["left"] = left
                return
            name, emoji, value, _, rarity = random.choices(table, weights=[t[3] for t in table])[0]
            value = int(value * rebirth_mult(a))
            a[key] = time.time()
            a["bal"] += value
            col = a.setdefault('collection', {})
            col[name] = col.get(name, 0) + 1
            bump_quests(a, str(ctx.author.id), "gather")
            out.update(name=name, emoji=emoji, value=value, rarity=rarity, bal=a['bal'], count=col[name])
        await self.kit.with_account(space, ctx.author, fn)
        if 'left' in out:
            return await self.kit.reply(ctx, content=f"you're tired - try again in **{fmt_wait(out['left'])}**", ephemeral=True)
        icon, verb = GATHER_VERBS[kind]
        e = discord.Embed(title=f"{icon} {kind}", color=RARITY_COLOR[out["rarity"]],
                          description=f"you {verb} **{out['emoji']} {out['name']}** ({out['rarity']})\n"
                                      f"sold for {self.kit.chips(out['value'])} · you've found {out['count']} of these\n"
                                      f"wallet: {self.kit.chips(out['bal'])}")
        await self.kit.reply(ctx, embed=e)

    @gather.command(name='fish', description='go fishing - loot sells instantly (10m cooldown)')
    async def fish(self, ctx):
        await self._gather(ctx, "fish")

    @commands.command(name="fish")
    async def fish_cmd(self, ctx):
        await self._gather(ctx, "fish")

    @gather.command(name="mine", description="go mining - loot sells instantly (10m cooldown)")
    async def mine(self, ctx):
        await self._gather(ctx, "mine")

    @commands.command(name="mine")
    async def mine_cmd(self, ctx):
        await self._gather(ctx, 'mine')
    @gather.command(name="hunt", description="go hunting - loot sells instantly (10m cooldown)")
    async def hunt(self, ctx):
        await self._gather(ctx, 'hunt')

    @commands.command(name='hunt')
    async def hunt_cmd(self, ctx):
        await self._gather(ctx, "hunt")
    async def _collection(self, ctx, who):
        who = who or ctx.author
        space = self.kit.c.get_space(ctx)
        econ = self.kit.c.loadEcon(self.kit.c.econ_file_for(space))
        col = self.kit.c.acct(econ, space, who).get('collection', {})
        e = discord.Embed(title=f"🗃️ {who.display_name}'s collection", color=0xFF6AD5)
        for kind, table in LOOT.items():
            lines = [f"{emoji} {name} ×{col[name]}" if col.get(name) else f"❔ ??? ({rarity})"
                     for name, emoji, _, _, rarity in table]
            found = sum(1 for t in table if col.get(t[0]))
            e.add_field(name=f"{GATHER_VERBS[kind][0]} {kind} · {found}/{len(table)}", value="\n".join(lines))
        await self.kit.reply(ctx, embed=e)

    @gather.command(name="collection", description="everything you've fished, mined and hunted")
    async def collection(self, ctx, user: Option(discord.Member, "who", required=False) = None):
        await self._collection(ctx, user)
    @commands.command(name="collection", aliases=["col"])
    async def collection_cmd(self, ctx, user: discord.Member = None):
        await self._collection(ctx, user)
    async def _quests(self, ctx):
        space = self.kit.c.get_space(ctx)
        q = await self.kit.with_account(space, ctx.author, lambda a: daily_quests(a, str(ctx.author.id)))
        await self.kit.reply(ctx, embed=quests_embed(q, ctx.author, self.kit.chips), view=QuestClaim(self, ctx.author))

    @commands.slash_command(name='quests', description='your 3 daily quests and their rewards')
    async def quests(self, ctx):
        await self._quests(ctx)

    @commands.command(name='quests', aliases=['quest'])
    async def quests_cmd(self, ctx):
        await self._quests(ctx)
    async def _trivia(self, ctx):
        left = self.trivia_cd.get(ctx.author.id, 0) + 90 - time.time()
        if left > 0:
            return await self.kit.reply(ctx, content=f"brain needs a break - next question in **{fmt_wait(left)}**", ephemeral=True)
        self.trivia_cd[ctx.author.id] = time.time()
        q, ans, wrong = random.choice(TRIVIA)
        opts = [ans] + wrong
        random.shuffle(opts)
        reward = random.randint(100, 300)
        view = TriviaView(self, ctx.author, q, ans, opts, reward)
        await self.kit.reply(ctx, content=f"🧠 {q}\n*20 seconds · worth {self.kit.chips(reward)}*", view=view)
    @commands.slash_command(name="trivia", description="answer a trivia question for chips")
    async def trivia(self, ctx):
        await self._trivia(ctx)
    @commands.command(name='trivia')
    async def trivia_cmd(self, ctx):
        await self._trivia(ctx)

    async def _profile(self, ctx, who):
        who = who or ctx.author
        space = self.kit.c.get_space(ctx)
        econ = self.kit.c.loadEcon(self.kit.c.econ_file_for(space))
        a = self.kit.c.acct(econ, space, who)
        users = econ.get(str(space.id), {}).get('users', {})
        ranked = sorted(users.items(), key=lambda kv: -(kv[1].get('bal', 0) + kv[1].get('bank', 0)))
        rank = next((i + 1 for i, (uid, _) in enumerate(ranked) if uid == str(who.id)), None)
        net = a["bal"] + a.get("bank", 0)
        loan = a.get("loan")
        biz = (a.get('business') or {}).get('tier')
        e = discord.Embed(title=f"🪪 {who.display_name}", color=0xFF6AD5)
        e.set_thumbnail(url=who.display_avatar.url)
        e.add_field(name="wallet", value=self.kit.chips(a["bal"]))
        e.add_field(name="bank", value="hidden" if a.get("hide_bank") and who.id != ctx.author.id else self.kit.chips(a.get("bank", 0)))
        e.add_field(name="rank", value=f"#{rank} of {len(ranked)}" if rank else "-")
        e.add_field(name='rebirths', value=str(a.get('rebirths', 0)))
        e.add_field(name="daily streak", value=f"{a.get('daily_streak', 0)} days")
        e.add_field(name="win streak", value=str(a.get("win_streak", 0)))
        e.add_field(name="business", value=biz or "none")
        e.add_field(name='debt', value=self.kit.chips(loan['owed']) if loan else 'debt free ✨')
        e.add_field(name="collection", value=f"{len(a.get('collection', {}))} unique finds")
        badges = a.get("badges", [])
        e.add_field(name=f"badges ({len(badges)})", value=", ".join(badges)[:1000] or "none yet", inline=False)
        if a.get('hide_bank') and who.id != ctx.author.id:
            net = a["bal"]
        e.set_footer(text=f"net worth {net:,} chips")
        await self.kit.reply(ctx, embed=e)
    @commands.slash_command(name="profile", description="a player's whole casino profile on one card")
    async def profile(self, ctx, user: Option(discord.Member, "who", required=False) = None):
        await self._profile(ctx, user)
    @commands.command(name="profile", aliases=["p"])
    async def profile_cmd(self, ctx, user: discord.Member = None):
        await self._profile(ctx, user)

    async def _giveaway(self, ctx, prize, minutes, winners):
        if not ctx.guild:
            return await self.kit.reply(ctx, content='giveaways need a server', ephemeral=True)
        if not self.kit.c.is_manager(ctx.author, ctx.guild):
            return await self.kit.reply(ctx, content="only casino managers can run giveaways", ephemeral=True)
        if prize <= 0 or not 1 <= minutes <= 10_080 or not 1 <= winners <= 20:
            return await self.kit.reply(ctx, content="prize > 0, 1-10080 minutes, 1-20 winners", ephemeral=True)
        ends = int(time.time() + minutes * 60)
        view = GiveawayView(prize, winners, ends)
        e = discord.Embed(title='🎉 chip giveaway!', color=0xFF6AD5,
                          description=f"**{self.kit.chips(prize)}** for **{winners}** winner(s)\nends <t:{ends}:R>\n\nhit 🎉 to enter")
        e.set_footer(text=f"hosted by {ctx.author.display_name}")
        await self.kit.reply(ctx, embed=e, view=view)
        self.kit.c.log_event(ctx.guild.name, f"{ctx.author.display_name} started a {prize:,}-chip giveaway ({winners} winners)")
        asyncio.create_task(self._finish_giveaway(ctx.guild, view, minutes * 60, e))
    async def _finish_giveaway(self, guild, view, seconds, embed):
        await asyncio.sleep(seconds)
        view.closed = True
        pool = list(view.entrants.values())
        picked = random.sample(pool, min(view.winners, len(pool)))
        for m in picked:
            await self.kit.credit(guild, m, view.prize, reason="won a giveaway")
        embed.description = (f"**{self.kit.chips(view.prize)}** each to: " + ", ".join(m.mention for m in picked)
                             if picked else "nobody entered 😢")
        embed.title = '🎉 giveaway ended'
        if view.message:
            try:
                await view.message.edit(embed=embed, view=None)
                if picked:
                    await view.message.reply(f"congrats {' '.join(m.mention for m in picked)}! 🎉")
            except discord.HTTPException:
                pass
    @commands.slash_command(name="giveaway", description="manager - start a house-funded chip giveaway")
    async def giveaway(self, ctx, prize: Option(int, 'chips per winner', min_value=1),
                       minutes: Option(int, "how long it runs", min_value=1, max_value=10080),
                       winners: Option(int, "how many winners", min_value=1, max_value=20, required=False) = 1):
        await self._giveaway(ctx, prize, minutes, winners)

    @commands.command(name="giveaway", aliases=["gstart"])
    async def giveaway_cmd(self, ctx, prize: int, minutes: int, winners: int = 1):
        await self._giveaway(ctx, prize, minutes, winners)


def setup(bot):
    bot.add_cog(EconomyPlus(bot))
