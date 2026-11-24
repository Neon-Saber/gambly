import asyncio
import random
from collections import Counter

import discord
from discord import Option
from discord.ext import commands

import casino_kit as ck
from casino_kit import Kit, card_str, new_deck, RANKS, SUITS

ck.GAME_TITLES.update({
    "cups": "🥤 Cups", "dragontiger": "🐉 Dragon Tiger", "sicbo": "🎲 Sic Bo", "sevens": "7️⃣ Sevens",
    'revolver': '🔫 Revolver', 'chests': '🧰 Treasure Chests', 'diceduel': '🎲 Dice Duel',
    "cardguess": "🃏 Card Guess", "target": "🎯 Target", "towers": "🗼 Towers", "balloon": "🎈 Balloon",
    'videopoker': '🂡 Video Poker', 'rocket': '🚀 Rocket', 'tictactoe': '❌⭕ Tic-Tac-Toe', 'heist': '💰 Heist',
    'craps': '🎲 Craps', 'threecard': '🃏 Three Card Poker', 'bingo': '🅱️ Bingo', 'penalty': '⚽ Penalty',
    'doors': '🚪 Doors', 'connect4': '🔴🟡 Connect 4',
})

DIE = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}
EDGE = 0.96

def owner_only_view_check(owner_id):
    async def check(interaction):
        if interaction.user.id != owner_id:
            await interaction.response.send_message("that's not your game", ephemeral=True)
            return False
        return True
    return check

def roll_cups(amount, pick):
    ball = random.randint(1, 3)
    row = " ".join("🟡" if i == ball else "🥤" for i in (1, 2, 3))
    text = f"{row}\nyou picked cup **{pick}** - the ball was under cup **{ball}**"
    return (amount * 2.88 if pick == ball else 0), text


def roll_dragontiger(amount, side):
    d, t = random.randint(1, 13), random.randint(1, 13)
    ds, ts = random.choice(list(SUITS)), random.choice(list(SUITS))
    text = f"🐉 dragon {card_str((d, ds))}   vs   🐯 tiger {card_str((t, ts))}"
    if d == t:
        if side == "tie":
            return amount * 12.5, text + "\n**tie!** that's a 12.5x hit"
        return amount * 0.5, text + "\n**tie** - you get half your bet back"
    winner = 'dragon' if d > t else 'tiger'
    return (amount * 2 if side == winner else 0), text + f"\n**{winner}** wins"


def roll_sicbo(amount, bet):
    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)
    triple = len(set(dice)) == 1
    text = f"{' '.join(DIE[x] for x in dice)}  = **{total}**" + ("  (triple!)" if triple else "")
    if bet == "triple":
        return (amount * 35 if triple else 0), text
    if triple:
        return 0, text + "\ntriples beat every even-money bet"
    win = {"big": total >= 11, "small": total <= 10, "odd": total % 2 == 1, "even": total % 2 == 0}[bet]
    return (amount * 2 if win else 0), text


def roll_sevens(amount, bet):
    a, b = random.randint(1, 6), random.randint(1, 6)
    s = a + b
    text = f"{DIE[a]} {DIE[b]}  = **{s}**"
    if bet == "seven":
        return (amount * 5.75 if s == 7 else 0), text
    win = s < 7 if bet == "under" else s > 7
    return (amount * 2.3 if win else 0), text


def roll_revolver(amount, bullets):
    chamber = random.randint(1, 6)
    mult = 6 / (6 - bullets) * EDGE
    if chamber <= bullets:
        return 0, f"{bullets} bullet(s) loaded... 💥 **bang.** the house takes it"
    return amount * mult, f"{bullets} bullet(s) loaded... *click.* you survive - **{mult:.2f}x**"


CHEST_MULTS = [0, 0.4, 1, 1.5, 1.9]


def roll_chests(amount, pick):
    mults = CHEST_MULTS[:]
    random.shuffle(mults)
    row = "  ".join(f"{'**' if i + 1 == pick else ''}#{i + 1} {m}x{'**' if i + 1 == pick else ''}" for i, m in enumerate(mults))
    return amount * mults[pick - 1], f"🧰 you opened chest **#{pick}** → **{mults[pick - 1]}x**\n{row}"


def roll_diceduel(amount):
    you = [random.randint(1, 6) for _ in range(2)]
    house = [random.randint(1, 6) for _ in range(2)]
    text = f"you {DIE[you[0]]}{DIE[you[1]]} **{sum(you)}**   vs   house {DIE[house[0]]}{DIE[house[1]]} **{sum(house)}**"
    if sum(you) == sum(house):
        return amount, text
    return (amount * 1.92 if sum(you) > sum(house) else 0), text

def parse_cardguess(raw):
    raw = raw.strip().lower()
    if raw in ("red", "black"):
        return "color", raw
    for suit in SUITS:
        if raw in (suit, suit[:-1]):
            return 'suit', suit
    rank = raw.upper()
    if rank in RANKS:
        return "rank", RANKS.index(rank) + 1
    return None, None

def roll_cardguess(amount, kind, value):
    r, s = random.randint(1, 13), random.choice(list(SUITS))
    color = "red" if s in ("hearts", "diamonds") else "black"
    text = f"the card was {card_str((r, s))}"
    if kind == 'color':
        return (amount * 1.92 if color == value else 0), text
    if kind == "suit":
        return (amount * 3.84 if s == value else 0), text
    return (amount * 12.5 if r == value else 0), text


def roll_target(amount, under):
    roll = random.randint(0, 9999) / 100
    mult = 96 / under
    text = f"🎯 rolled **{roll:.2f}** - needed under **{under}** ({mult:.2f}x)"
    return (amount * mult if roll < under else 0), text

TOWER_FLOORS = 8
TOWER_MODES = {"easy": (4, 1), "medium": (3, 1), "hard": (2, 1)}

def tower_mult(mode, floors_cleared):
    tiles, bombs = TOWER_MODES[mode]
    p = (tiles - bombs) / tiles
    return round(EDGE / (p ** floors_cleared), 2) if floors_cleared else 1.0


class TowersView(discord.ui.View):
    def __init__(self, kit, space, member, amount, mode):
        super().__init__(timeout=90)
        self.kit, self.space, self.member, self.amount, self.mode = kit, space, member, amount, mode
        self.tiles, self.bombs = TOWER_MODES[mode]
        self.floor = 0
        self.history = []
        self.done = False
        self.lock = asyncio.Lock()
        self.message = None
        self.interaction_check = owner_only_view_check(member.id)
        self._build()

    def _build(self):
        self.clear_items()
        if self.done:
            return
        for i in range(self.tiles):
            b = discord.ui.Button(label=f"tile {i + 1}", style=discord.ButtonStyle.secondary, row=0)
            b.callback = self._make_pick(i)
            self.add_item(b)
        cash = discord.ui.Button(label=f"cash out {tower_mult(self.mode, self.floor)}x",
                                 style=discord.ButtonStyle.success, row=1, disabled=self.floor == 0)
        cash.callback = self._cashout
        self.add_item(cash)

    def render(self, footer=""):
        lines = []
        for f in range(TOWER_FLOORS - 1, -1, -1):
            mult = tower_mult(self.mode, f + 1)
            if f < len(self.history):
                pick, bombs = self.history[f]
                cells = ''.join(('💥' if i == pick else '💣') if i in bombs else ('✅' if i == pick else '⬛')
                                for i in range(self.tiles))
            elif f == self.floor and not self.done:
                cells = "🟪" * self.tiles
            else:
                cells = '⬜' * self.tiles
            lines.append(f"`{mult:>6.2f}x` {cells}")
        e = discord.Embed(title=f"🗼 Towers · {self.mode}", color=0xB45CFF,
                          description="\n".join(lines) + (f"\n\n{footer}" if footer else ""))
        e.set_footer(text=f"bet {self.amount:,} · pick a tile on the glowing floor")
        return e
    def _make_pick(self, idx):
        async def cb(interaction):
            async with self.lock:
                if self.done:
                    return await interaction.response.defer()
                bombs = set(random.sample(range(self.tiles), self.bombs))
                rig = self.kit.c.pop_rig(self.space, self.member) == "win"
                if rig and idx in bombs:
                    bombs = set(random.sample([i for i in range(self.tiles) if i != idx], self.bombs))
                self.history.append((idx, bombs))
                if idx in bombs:
                    self.done = True
                    net, bal = await self.kit.payout(self.space, self.member, self.amount, 0, 'towers')
                    self._build()
                    return await interaction.response.edit_message(
                        embed=self.render(f"💥 bomb on floor {self.floor + 1}. lost {self.kit.chips(self.amount)} · wallet {self.kit.chips(bal)}"),
                        view=self)
                self.floor += 1
                if self.floor >= TOWER_FLOORS:
                    return await self._finish(interaction, '🏆 reached the top!')
                self._build()
                await interaction.response.edit_message(embed=self.render(), view=self)
        return cb
    async def _cashout(self, interaction):
        async with self.lock:
            if self.done:
                return await interaction.response.defer()
            await self._finish(interaction, '💰 cashed out')
    async def _finish(self, interaction, why):
        self.done = True
        mult = tower_mult(self.mode, self.floor)
        net, bal = await self.kit.payout(self.space, self.member, self.amount, int(self.amount * mult), "towers")
        self._build()
        embed = self.render(f"{why} at **{mult}x** - profit {self.kit.chips(net)} · wallet {self.kit.chips(bal)}")
        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

    async def on_timeout(self):
        async with self.lock:
            if self.done:
                return
            if self.floor == 0:
                self.done = True
                await self.kit.payout(self.space, self.member, self.amount, self.amount)
                if self.message:
                    await self.message.edit(embed=self.render('timed out before the first pick - bet refunded'), view=None)
                return
            await self._finish(None, "⏱️ timed out - auto cashed out")

BALLOON_POP = 0.12


def balloon_mult(pumps):
    return round(EDGE / ((1 - BALLOON_POP) ** pumps), 2) if pumps else 1.0


class BalloonView(discord.ui.View):
    def __init__(self, kit, space, member, amount):
        super().__init__(timeout=60)
        self.kit, self.space, self.member, self.amount = kit, space, member, amount
        self.pumps = 0
        self.done = False
        self.lock = asyncio.Lock()
        self.message = None
        self.interaction_check = owner_only_view_check(member.id)
    def render(self, footer=''):
        size = min(self.pumps, 12)
        art = "🎈" + "💨" * size if not self.done or "pop" not in footer else "💥"
        e = discord.Embed(title="🎈 Balloon", color=0xFF6AD5,
                          description=f"{art}\n\npumps: **{self.pumps}** · current: **{balloon_mult(self.pumps)}x** "
                                      f"· next: **{balloon_mult(self.pumps + 1)}x**\n"
                                      f"each pump has a {int(BALLOON_POP * 100)}% chance to pop" +
                                      (f"\n\n{footer}" if footer else ""))
        e.set_footer(text=f"bet {self.amount:,}")
        return e

    @discord.ui.button(label='pump', emoji='💨', style=discord.ButtonStyle.primary)
    async def pump(self, button, interaction):
        async with self.lock:
            if self.done:
                return await interaction.response.defer()
            popped = random.random() < BALLOON_POP
            if self.kit.c.pop_rig(self.space, self.member) == 'win':
                popped = False
            if popped:
                self.done = True
                net, bal = await self.kit.payout(self.space, self.member, self.amount, 0, "balloon")
                return await interaction.response.edit_message(
                    embed=self.render(f"💥 pop! lost {self.kit.chips(self.amount)} · wallet {self.kit.chips(bal)}"), view=None)
            self.pumps += 1
            await interaction.response.edit_message(embed=self.render(), view=self)

    @discord.ui.button(label="cash out", emoji="💰", style=discord.ButtonStyle.success)
    async def cash(self, button, interaction):
        async with self.lock:
            if self.done:
                return await interaction.response.defer()
            await self._finish(interaction)
    async def _finish(self, interaction, why="💰 cashed out"):
        self.done = True
        mult = balloon_mult(self.pumps)
        net, bal = await self.kit.payout(self.space, self.member, self.amount, int(self.amount * mult), 'balloon')
        embed = self.render(f"{why} at **{mult}x** · {'profit' if net >= 0 else 'loss'} {self.kit.chips(abs(net))} · wallet {self.kit.chips(bal)}")
        if interaction:
            await interaction.response.edit_message(embed=embed, view=None)
        elif self.message:
            await self.message.edit(embed=embed, view=None)
    async def on_timeout(self):
        async with self.lock:
            if not self.done:
                await self._finish(None, "⏱️ timed out - auto cashed out")


VP_PAYS = [
    ("royal flush", 250), ("straight flush", 50), ("four of a kind", 25), ("full house", 8),
    ("flush", 5), ("straight", 4), ("three of a kind", 3), ("two pair", 2), ("jacks or better", 1),
]

def vp_evaluate(hand):
    ranks = [r for r, _ in hand]
    suits = [s for _, s in hand]
    counts = sorted(Counter(ranks).values(), reverse=True)
    flush = len(set(suits)) == 1
    uniq = sorted(set(ranks))
    straight = len(uniq) == 5 and (uniq[-1] - uniq[0] == 4 or uniq == [1, 10, 11, 12, 13])
    if straight and flush:
        return "royal flush" if uniq == [1, 10, 11, 12, 13] else "straight flush"
    if counts[0] == 4:
        return 'four of a kind'
    if counts == [3, 2]:
        return "full house"
    if flush:
        return "flush"
    if straight:
        return 'straight'
    if counts[0] == 3:
        return "three of a kind"
    if counts == [2, 2, 1]:
        return 'two pair'
    if counts[0] == 2:
        pair = [r for r, c in Counter(ranks).items() if c == 2][0]
        if pair in (1, 11, 12, 13):
            return "jacks or better"
    return None


class VideoPokerView(discord.ui.View):
    def __init__(self, kit, space, member, amount):
        super().__init__(timeout=90)
        self.kit, self.space, self.member, self.amount = kit, space, member, amount
        self.deck = new_deck()
        self.hand = [self.deck.pop() for _ in range(5)]
        self.held = [False] * 5
        self.done = False
        self.lock = asyncio.Lock()
        self.message = None
        self.interaction_check = owner_only_view_check(member.id)
        for i in range(5):
            b = discord.ui.Button(label=f"hold {i + 1}", style=discord.ButtonStyle.secondary, row=0)
            b.callback = self._make_hold(i, b)
            self.add_item(b)
        draw = discord.ui.Button(label="draw", emoji="🔁", style=discord.ButtonStyle.primary, row=1)
        draw.callback = self._draw
        self.add_item(draw)
    def render(self, footer=''):
        cards = "  ".join(f"{card_str(c)}{'🔒' if self.held[i] else ''}" for i, c in enumerate(self.hand))
        current = vp_evaluate(self.hand)
        pays = "\n".join(f"{'**' if n == current else ''}{n}: {m}x{'**' if n == current else ''}" for n, m in VP_PAYS)
        e = discord.Embed(title="🂡 Video Poker · jacks or better", color=0x5865F2,
                          description=f"{cards}\n\n{footer or 'hold the cards you want to keep, then draw'}")
        e.add_field(name="paytable", value=pays)
        e.set_footer(text=f"bet {self.amount:,}")
        return e

    def _make_hold(self, i, button):
        async def cb(interaction):
            if self.done:
                return await interaction.response.defer()
            self.held[i] = not self.held[i]
            button.style = discord.ButtonStyle.success if self.held[i] else discord.ButtonStyle.secondary
            button.label = f"held {i + 1}" if self.held[i] else f"hold {i + 1}"
            await interaction.response.edit_message(embed=self.render(), view=self)
        return cb

    async def _draw(self, interaction):
        async with self.lock:
            if self.done:
                return await interaction.response.defer()
            await self._settle(interaction)
    async def _settle(self, interaction):
        self.done = True
        rig = self.kit.c.pop_rig(self.space, self.member) == 'win'
        for _ in range(300 if rig else 1):
            deck = self.deck[:]
            random.shuffle(deck)
            new = [c if self.held[i] else deck.pop() for i, c in enumerate(self.hand)]
            if not rig or vp_evaluate(new):
                break
        self.hand = new
        result = vp_evaluate(self.hand)
        mult = dict(VP_PAYS).get(result, 0)
        net, bal = await self.kit.payout(self.space, self.member, self.amount, self.amount * mult, "videopoker")
        footer = (f"**{result}** pays {mult}x - " if result else "no hand - ") + \
                 f"{'profit' if net > 0 else 'result'} {self.kit.chips(net) if net >= 0 else '-' + self.kit.chips(-net)} · wallet {self.kit.chips(bal)}"
        embed = self.render(footer)
        if interaction:
            await interaction.response.edit_message(embed=embed, view=None)
        elif self.message:
            await self.message.edit(embed=embed, view=None)
    async def on_timeout(self):
        async with self.lock:
            if not self.done:
                await self._settle(None)


ROCKET_MAX = 50.0


def rocket_crash_point():
    u = random.random()
    point = EDGE / max(u, 1e-9)
    return 1.0 if point < 1.01 else min(point, ROCKET_MAX)


class RocketView(discord.ui.View):
    def __init__(self, kit, space, member, amount, auto):
        super().__init__(timeout=None)
        self.kit, self.space, self.member, self.amount, self.auto = kit, space, member, amount, auto
        self.crash = rocket_crash_point()
        if kit.c.pop_rig(space, member) == "win":
            self.crash = max(self.crash, 5.0)
        self.mult = 1.0
        self.done = False
        self.lock = asyncio.Lock()
        self.message = None
        self.interaction_check = owner_only_view_check(member.id)
    def render(self, footer=""):
        height = min(int((self.mult - 1) * 4), 14)
        e =discord.Embed(title="🚀 Rocket", color=0xFF8C42,
                          description=f"**{self.mult:.2f}x**  ·  {self.kit.chips(int(self.amount * self.mult))}\n"
                                      f"{'🌌' * min(height, 10)}🚀" + (f"\n\n{footer}" if footer else ""))
        e.set_footer(text=f"bet {self.amount:,}" + (f" · auto cash-out at {self.auto}x" if self.auto else ""))
        return e

    async def fly(self):
        await asyncio.sleep(1.2)
        while True:
            async with self.lock:
                if self.done:
                    return
                nxt = round(self.mult * 1.09 + 0.01, 2)
                if nxt >= self.crash:
                    self.done = True
                    self.mult = self.crash
                    net, bal = await self.kit.payout(self.space, self.member, self.amount, 0, 'rocket')
                    await self._edit(self.render(f"💥 crashed at **{self.crash:.2f}x** - lost {self.kit.chips(self.amount)} · wallet {self.kit.chips(bal)}"), None)
                    return
                self.mult = nxt
                if self.auto and self.mult >= self.auto:
                    self.mult = self.auto
                    await self._cash(None, "🤖 auto cashed out")
                    return
                await self._edit(self.render(), self)
            await asyncio.sleep(1.4)

    async def _edit(self, embed, view):
        try:
            if self.message:
                await self.message.edit(embed=embed, view=view)
        except discord.HTTPException:
            pass
    @discord.ui.button(label="cash out", emoji="💰", style=discord.ButtonStyle.success)
    async def cash_btn(self, button, interaction):
        async with self.lock:
            if self.done:
                return await interaction.response.defer()
            await interaction.response.defer()
            await self._cash(None, "💰 cashed out")
    async def _cash(self, interaction, why):
        self.done = True
        net, bal = await self.kit.payout(self.space, self.member, self.amount, int(self.amount * self.mult), 'rocket')
        await self._edit(self.render(f"{why} at **{self.mult:.2f}x** (it would have crashed at {self.crash:.2f}x) · "
                                     f"profit {self.kit.chips(net)} · wallet {self.kit.chips(bal)}"), None)
        self.stop()


TTT_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]

class TTTChallenge(discord.ui.View):
    def __init__(self, cog, space, p1, p2, amount):
        super().__init__(timeout=60)
        self.cog, self.space, self.p1, self.p2, self.amount = cog, space, p1, p2, amount
        self.message = None
        self.answered = False

    @discord.ui.button(label="accept", emoji="✅", style=discord.ButtonStyle.success)
    async def accept(self, button, interaction):
        if interaction.user.id != self.p2.id:
            return await interaction.response.send_message("this challenge isn't for you", ephemeral=True)
        if self.answered:
            return await interaction.response.defer()
        self.answered = True
        kit = self.cog.kit
        if not await self.cog.try_deduct(self.space, self.p1, self.amount):
            return await interaction.response.edit_message(content=f"{self.p1.mention} can't cover the bet anymore - cancelled", view=None)
        if not await self.cog.try_deduct(self.space, self.p2, self.amount):
            await kit.credit(self.space, self.p1, self.amount)
            return await interaction.response.edit_message(content=f"{self.p2.mention} can't cover the bet - cancelled", view=None)
        game = TTTGame(kit, self.space, self.p1, self.p2, self.amount)
        await interaction.response.edit_message(content=game.header(), view=game)
        game.message = self.message
        self.stop()
    @discord.ui.button(label='decline', emoji='✖️', style=discord.ButtonStyle.danger)
    async def decline(self, button, interaction):
        if interaction.user.id != self.p2.id:
            return await interaction.response.send_message("this challenge isn't for you", ephemeral=True)
        self.answered = True
        await interaction.response.edit_message(content=f"{self.p2.display_name} declined.", view=None)
        self.stop()

    async def on_timeout(self):
        if not self.answered and self.message:
            try:
                await self.message.edit(content='challenge expired', view=None)
            except discord.HTTPException:
                pass

class TTTGame(discord.ui.View):
    def __init__(self, kit, space, p1, p2, amount):
        super().__init__(timeout=180)
        self.kit, self.space, self.p1, self.p2, self.amount = kit, space, p1, p2, amount
        self.board = [None] * 9
        self.turn = random.choice([p1, p2])
        self.done = False
        self.lock = asyncio.Lock()
        self.message = None
        for i in range(9):
            b = discord.ui.Button(label='​', style=discord.ButtonStyle.secondary, row=i // 3)
            b.callback = self._make_move(i, b)
            self.add_item(b)

    def mark(self, member):
        return "❌" if member.id == self.p1.id else "⭕"
    def header(self, extra=""):
        return (f"**tic-tac-toe** · {self.p1.mention} ❌ vs ⭕ {self.p2.mention} · pot {self.kit.chips(self.amount * 2)}\n"
                + (extra or f"{self.turn.mention}'s turn ({self.mark(self.turn)})"))
    def winner(self):
        for a, b, c in TTT_LINES:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return "draw" if all(self.board) else None
    def _make_move(self, i, button):
        async def cb(interaction):
            async with self.lock:
                if self.done:
                    return await interaction.response.defer()
                if interaction.user.id not in (self.p1.id, self.p2.id):
                    return await interaction.response.send_message("you're not in this game", ephemeral=True)
                if interaction.user.id != self.turn.id:
                    return await interaction.response.send_message("not your turn", ephemeral=True)
                if self.board[i]:
                    return await interaction.response.send_message("that square's taken", ephemeral=True)
                self.board[i] = self.turn.id
                button.label = None
                button.emoji = self.mark(self.turn)
                button.disabled = True
                button.style = discord.ButtonStyle.danger if self.turn.id == self.p1.id else discord.ButtonStyle.primary
                w = self.winner()
                if w is None:
                    self.turn = self.p2 if self.turn.id == self.p1.id else self.p1
                    return await interaction.response.edit_message(content=self.header(), view=self)
                self.done = True
                for item in self.children:
                    item.disabled = True
                text = await self._settle(w)
                await interaction.response.edit_message(content=self.header(text), view=self)
        return cb
    async def _settle(self, w):
        if w == "draw":
            await self.kit.payout(self.space, self.p1, self.amount, self.amount, "tictactoe")
            await self.kit.payout(self.space, self.p2, self.amount, self.amount, 'tictactoe')
            return "🤝 draw - both bets refunded"
        win, lose = (self.p1, self.p2) if w == self.p1.id else (self.p2, self.p1)
        net, _ = await self.kit.payout(self.space, win, self.amount, self.amount * 2, "tictactoe")
        await self.kit.payout(self.space, lose, self.amount, 0, "tictactoe")
        return f"🏆 {win.mention} wins {self.kit.chips(net)}!"
    async def on_timeout(self):
        async with self.lock:
            if self.done:
                return
            self.done = True
            w = self.p2.id if self.turn.id == self.p1.id else self.p1.id
            text = await self._settle(w)
            if self.message:
                try:
                    await self.message.edit(content=self.header(f"⏱️ {self.turn.mention} took too long. {text}"), view=None)
                except discord.HTTPException:
                    pass

HEIST_LINES_WIN = [
    "the crew slipped past the lasers and cleaned out the vault 💎",
    "the getaway driver hit every green light 🚗💨",
    'the hacker looped the cameras and nobody saw a thing 📹',
]
HEIST_LINES_LOSE = [
    "someone tripped the silent alarm 🚨",
    "the vault was a decoy full of monopoly money 🎲",
    "the getaway car wouldn't start 🚗💀",
]

def heist_chance(crew):
    return min(0.35 + 0.08 * (crew - 1), 0.80)


class HeistLobby(discord.ui.View):
    def __init__(self, cog, space, leader, amount, seconds):
        super().__init__(timeout=seconds + 5)
        self.cog, self.space, self.leader, self.amount = cog, space, leader, amount
        self.crew = [leader]
        self.message = None
        self.closed = False
    def render(self, footer=""):
        n = len(self.crew)
        e = discord.Embed(title="💰 Heist", color=0xF5C542,
                          description=f"{self.leader.mention} is planning a heist. entry: {self.cog.kit.chips(self.amount)}\n"
                                      f"crew: {', '.join(m.mention for m in self.crew)}\n\n"
                                      f"success chance: **{int(heist_chance(n) * 100)}%** · payout: **{EDGE / heist_chance(n):.2f}x** each"
                                      + (f"\n\n{footer}" if footer else ""))
        return e
    @discord.ui.button(label="join the crew", emoji="🕶️", style=discord.ButtonStyle.primary)
    async def join(self, button, interaction):
        if self.closed:
            return await interaction.response.send_message("too late, they already left", ephemeral=True)
        if any(m.id == interaction.user.id for m in self.crew):
            return await interaction.response.send_message("you're already in", ephemeral=True)
        if len(self.crew) >= 10:
            return await interaction.response.send_message("crew's full", ephemeral=True)
        if self.cog.kit.c.is_banned(interaction.user, self.space):
            return await interaction.response.send_message("you're banned from gambling here", ephemeral=True)
        if not await self.cog.try_deduct(self.space, interaction.user, self.amount):
            return await interaction.response.send_message("you can't cover the entry", ephemeral=True)
        self.crew.append(interaction.user)
        await interaction.response.edit_message(embed=self.render(), view=self)
    async def run(self, seconds):
        await asyncio.sleep(seconds)
        self.closed = True
        self.stop()
        kit = self.cog.kit
        n = len(self.crew)
        p = heist_chance(n)
        success = random.random() < p
        if any(kit.c.pop_rig(self.space, m) == "win" for m in self.crew[:1]):
            success = True
        lines = []
        if success:
            mult = EDGE / p
            for m in self.crew:
                net, _ = await kit.payout(self.space, m, self.amount, int(self.amount * mult), 'heist')
                lines.append(f"{m.mention} +{kit.chips(net)}")
            footer = f"✅ {random.choice(HEIST_LINES_WIN)}\n" + "\n".join(lines)
        else:
            for m in self.crew:
                await kit.payout(self.space, m, self.amount, 0, "heist")
            footer = f"❌ {random.choice(HEIST_LINES_LOSE)} - everyone lost their entry"
        if self.message:
            try:
                await self.message.edit(embed=self.render(footer), view=None)
            except discord.HTTPException:
                pass


def roll_craps(amount, side):
    rolls = []
    def r():
        a, b = random.randint(1, 6), random.randint(1, 6)
        rolls.append(f"{DIE[a]}{DIE[b]} {a + b}")
        return a + b
    first = r()
    if first in (7, 11):
        res = "pass"
    elif first in (2, 3, 12):
        res = "bar12" if first == 12 else "dont"
    else:
        point = first
        while True:
            x = r()
            if x == point:
                res = "pass"
                break
            if x == 7:
                res = "dont"
                break
    text = "rolls: " + " → ".join(rolls[:12]) + (" …" if len(rolls) > 12 else "")
    if side == "pass":
        return (amount * 2 if res == "pass" else 0), text + f"\n{'pass line wins' if res == 'pass' else 'seven out / craps'}"
    if res == "bar12":
        return amount, text + "\n12 on the come out - don't pass pushes"
    return (amount * 2 if res == "dont" else 0), text + f"\n{'don’t pass wins' if res == 'dont' else 'shooter made it'}"


def tc_rank(hand):
    ranks = sorted((14 if r == 1 else r) for r, _ in hand)
    flush = len({s for _, s in hand}) == 1
    straight = ranks[2] - ranks[0] == 2 and len(set(ranks)) == 3 or ranks == [2, 3, 14]
    trips = len(set(ranks)) == 1
    pair = len(set(ranks)) == 2
    hi = sorted(ranks, reverse=True) if ranks != [2, 3, 14] else [3, 2, 1]
    if straight and flush:
        return (5, hi), "straight flush"
    if trips:
        return (4, hi), "three of a kind"
    if straight:
        return (3, hi), "straight"
    if flush:
        return (2, hi), "flush"
    if pair:
        p = max(set(ranks), key=ranks.count)
        return (1, [p] + [x for x in hi if x != p]), "pair"
    return (0, hi), "high card"


TC_BONUS = {"straight flush": 6, "three of a kind": 5, "straight": 2.6}


def roll_threecard(amount):
    deck = new_deck()
    you, dealer = [deck.pop() for _ in range(3)], [deck.pop() for _ in range(3)]
    (ys, yn), (ds, dn) = tc_rank(you), tc_rank(dealer)
    text = f"you {' '.join(card_str(c) for c in you)} ({yn})\ndealer {' '.join(card_str(c) for c in dealer)} ({dn})"
    if ys > ds:
        return amount * TC_BONUS.get(yn, 1.86), text + ("\n**bonus hand!**" if yn in TC_BONUS else "")
    if ys == ds:
        return amount, text + "\ntie - push"
    return 0, text


BINGO_DRAWS = 30
BINGO_PAY = {0: 0, 1: 5.2, 2: 20, 3: 60, 4: 200}


def roll_bingo(amount):
    card = [random.sample(range(c * 15 + 1, c * 15 + 16), 5) for c in range(5)]
    drawn = set(random.sample(range(1, 76), BINGO_DRAWS))
    hit = [[(card[c][r] in drawn) or (c == 2 and r == 2) for r in range(5)] for c in range(5)]
    lines = sum(all(hit[c][r] for c in range(5)) for r in range(5)) + sum(all(hit[c]) for c in range(5))
    lines += all(hit[i][i] for i in range(5)) + all(hit[i][4 - i] for i in range(5))
    rows = []
    for r in range(5):
        cells = []
        for c in range(5):
            if c == 2 and r == 2:
                cells.append(" ★ ")
            else:
                n = card[c][r]
                cells.append(f"[{n:>2}]" if n in drawn else f" {n:>2} ")
        rows.append("".join(cells))
    text = "```\n  B   I   N   G   O\n" + "\n".join(rows) + f"\n```{BINGO_DRAWS} balls drawn · **{lines}** line{'s' if lines != 1 else ''}"
    return amount * BINGO_PAY.get(min(lines, 4), 200), text


class PenaltyView(discord.ui.View):
    def __init__(self, kit, space, member, amount):
        super().__init__(timeout=30)
        self.kit, self.space, self.member, self.amount = kit, space, member, amount
        self.done = False
        self.message = None
        self.interaction_check = owner_only_view_check(member.id)
        for side, emo in (("left", "⬅️"), ("middle", "⬆️"), ("right", "➡️")):
            b = discord.ui.Button(label=side, emoji=emo, style=discord.ButtonStyle.primary)
            b.callback = self._shoot(side)
            self.add_item(b)

    def render(self, footer=""):
        e = discord.Embed(title="⚽ Penalty", color=0x51CF66,
                          description="pick a corner. keeper guesses wrong → **1.44x**\n\n🥅\n🧤\n\n⚽" + (f"\n\n{footer}" if footer else ""))
        e.set_footer(text=f"bet {self.amount:,}")
        return e

    def _shoot(self, side):
        async def cb(interaction):
            if self.done:
                return await interaction.response.defer()
            self.done = True
            dive = random.choice(["left", "middle", "right"])
            if self.kit.c.pop_rig(self.space, self.member) == "win" and dive == side:
                dive = next(x for x in ("left", "middle", "right") if x != side)
            goal = dive != side
            net, bal = await self.kit.payout(self.space, self.member, self.amount, int(self.amount * 1.44) if goal else 0, "penalty")
            txt = (f"you went **{side}**, keeper dived **{dive}** - " +
                   (f"⚽ GOAL! +{self.kit.chips(net)}" if goal else "🧤 saved. unlucky") + f" · wallet {self.kit.chips(bal)}")
            await interaction.response.edit_message(embed=self.render(txt), view=None)
        return cb

    async def on_timeout(self):
        if not self.done:
            self.done = True
            await self.kit.payout(self.space, self.member, self.amount, self.amount)
            if self.message:
                try:
                    await self.message.edit(embed=self.render("ran out of time - bet refunded"), view=None)
                except discord.HTTPException:
                    pass


class DoorsView(discord.ui.View):
    def __init__(self, kit, space, member, amount):
        super().__init__(timeout=45)
        self.kit, self.space, self.member, self.amount = kit, space, member, amount
        self.prize = random.randint(1, 3)
        self.pick = None
        self.opened = None
        self.done = False
        self.message = None
        self.interaction_check = owner_only_view_check(member.id)
        self._doors()

    def _doors(self):
        self.clear_items()
        for d in (1, 2, 3):
            b = discord.ui.Button(label=f"door {d}", emoji="🚪", style=discord.ButtonStyle.secondary)
            b.callback = self._choose(d)
            self.add_item(b)

    def render(self, footer=""):
        row = []
        for d in (1, 2, 3):
            if self.done:
                row.append("💰" if d == self.prize else "🐐")
            elif d == self.opened:
                row.append("🐐")
            elif d == self.pick:
                row.append("👉🚪")
            else:
                row.append("🚪")
        e = discord.Embed(title="🚪 Doors", color=0xFFA94D,
                          description="one door has the money. find it → **1.44x**\n\n" + "   ".join(row) + (f"\n\n{footer}" if footer else ""))
        e.set_footer(text=f"bet {self.amount:,}")
        return e

    def _choose(self, d):
        async def cb(interaction):
            if self.done or self.pick:
                return await interaction.response.defer()
            self.pick = d
            if self.kit.c.pop_rig(self.space, self.member) == "win":
                self.prize = d
            self.opened = random.choice([x for x in (1, 2, 3) if x not in (d, self.prize)])
            self.clear_items()
            stay = discord.ui.Button(label=f"stay on {d}", style=discord.ButtonStyle.secondary)
            other = next(x for x in (1, 2, 3) if x not in (d, self.opened))
            swap = discord.ui.Button(label=f"switch to {other}", style=discord.ButtonStyle.success)
            stay.callback = self._final(d)
            swap.callback = self._final(other)
            self.add_item(stay)
            self.add_item(swap)
            await interaction.response.edit_message(embed=self.render(f"door {self.opened} is a goat 🐐. stay or switch?"), view=self)
        return cb

    def _final(self, d):
        async def cb(interaction):
            if self.done:
                return await interaction.response.defer()
            self.done = True
            won = d == self.prize
            net, bal = await self.kit.payout(self.space, self.member, self.amount, int(self.amount * 1.44) if won else 0, "doors")
            await interaction.response.edit_message(
                embed=self.render((f"door {d} - 💰 +{self.kit.chips(net)}" if won else f"door {d} - goat 🐐") + f" · wallet {self.kit.chips(bal)}"),
                view=None)
        return cb

    async def on_timeout(self):
        if not self.done:
            self.done = True
            await self.kit.payout(self.space, self.member, self.amount, self.amount)
            if self.message:
                try:
                    await self.message.edit(embed=self.render("timed out - bet refunded"), view=None)
                except discord.HTTPException:
                    pass


C4_W, C4_H = 7, 6


class C4Challenge(TTTChallenge):
    @discord.ui.button(label="accept", emoji="✅", style=discord.ButtonStyle.success)
    async def accept(self, button, interaction):
        if interaction.user.id != self.p2.id:
            return await interaction.response.send_message("this challenge isn't for you", ephemeral=True)
        if self.answered:
            return await interaction.response.defer()
        self.answered = True
        kit = self.cog.kit
        if not await self.cog.try_deduct(self.space, self.p1, self.amount):
            return await interaction.response.edit_message(content=f"{self.p1.mention} can't cover the bet anymore", view=None)
        if not await self.cog.try_deduct(self.space, self.p2, self.amount):
            await kit.credit(self.space, self.p1, self.amount)
            return await interaction.response.edit_message(content=f"{self.p2.mention} can't cover the bet", view=None)
        game = C4Game(kit, self.space, self.p1, self.p2, self.amount)
        await interaction.response.edit_message(content=game.header(), view=game)
        game.message = self.message
        self.stop()


class C4Game(discord.ui.View):
    def __init__(self, kit, space, p1, p2, amount):
        super().__init__(timeout=240)
        self.kit, self.space, self.p1, self.p2, self.amount = kit, space, p1, p2, amount
        self.grid = [[0] * C4_W for _ in range(C4_H)]
        self.turn = random.choice([p1, p2])
        self.done = False
        self.lock = asyncio.Lock()
        self.message = None
        for c in range(C4_W):
            b = discord.ui.Button(label=str(c + 1), style=discord.ButtonStyle.secondary, row=0 if c < 4 else 1)
            b.callback = self._drop(c)
            self.add_item(b)

    def piece(self, m):
        return 1 if m.id == self.p1.id else 2

    def header(self, extra=""):
        board = "\n".join("".join("⚫🔴🟡"[v] for v in row) for row in self.grid) + "\n1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣"
        return (f"**connect 4** · {self.p1.mention} 🔴 vs 🟡 {self.p2.mention} · pot {self.kit.chips(self.amount * 2)}\n{board}\n"
                + (extra or f"{self.turn.mention}'s turn ({'🔴' if self.piece(self.turn) == 1 else '🟡'})"))

    def won(self, v):
        g = self.grid
        for r in range(C4_H):
            for c in range(C4_W):
                if g[r][c] != v:
                    continue
                for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                    if all(0 <= r + dr * k < C4_H and 0 <= c + dc * k < C4_W and g[r + dr * k][c + dc * k] == v for k in range(4)):
                        return True
        return False

    def _drop(self, col):
        async def cb(interaction):
            async with self.lock:
                if self.done:
                    return await interaction.response.defer()
                if interaction.user.id not in (self.p1.id, self.p2.id):
                    return await interaction.response.send_message("you're not in this game", ephemeral=True)
                if interaction.user.id != self.turn.id:
                    return await interaction.response.send_message("not your turn", ephemeral=True)
                row = next((r for r in range(C4_H - 1, -1, -1) if self.grid[r][col] == 0), None)
                if row is None:
                    return await interaction.response.send_message("that column's full", ephemeral=True)
                v = self.piece(self.turn)
                self.grid[row][col] = v
                if self.won(v):
                    self.done = True
                    win, lose = (self.p1, self.p2) if v == 1 else (self.p2, self.p1)
                    net, _ = await self.kit.payout(self.space, win, self.amount, self.amount * 2, "connect4")
                    await self.kit.payout(self.space, lose, self.amount, 0, "connect4")
                    return await interaction.response.edit_message(content=self.header(f"🏆 {win.mention} connects four and takes {self.kit.chips(net)}!"), view=None)
                if all(self.grid[0][c] for c in range(C4_W)):
                    self.done = True
                    await self.kit.payout(self.space, self.p1, self.amount, self.amount, "connect4")
                    await self.kit.payout(self.space, self.p2, self.amount, self.amount, "connect4")
                    return await interaction.response.edit_message(content=self.header("🤝 board's full - bets refunded"), view=None)
                self.turn = self.p2 if self.turn.id == self.p1.id else self.p1
                await interaction.response.edit_message(content=self.header(), view=self)
        return cb

    async def on_timeout(self):
        async with self.lock:
            if self.done:
                return
            self.done = True
            win = self.p2 if self.turn.id == self.p1.id else self.p1
            net, _ = await self.kit.payout(self.space, win, self.amount, self.amount * 2, "connect4")
            await self.kit.payout(self.space, self.turn, self.amount, 0, "connect4")
            if self.message:
                try:
                    await self.message.edit(content=self.header(f"⏱️ {self.turn.mention} took too long - {win.mention} wins {self.kit.chips(net)}"), view=None)
                except discord.HTTPException:
                    pass


class GamesPlus(commands.Cog):
    play = discord.SlashCommandGroup("play", "the newer casino games")

    def __init__(self, bot):
        self.bot = bot
        self.kit = Kit(bot)
    async def try_deduct(self, space, member, amount):
        ok = {"v": False}
        def fn(a):
            if 0 < amount <= a["bal"]:
                a["bal"] -= amount
                ok['v'] = True
        await self.kit.with_account(space, member, fn)
        return ok['v']

    async def _amount(self, ctx, raw):
        return await self.kit.parse(ctx, raw)
    async def _cups(self, ctx, raw, cup):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        if cup not in (1, 2, 3):
            return await self.kit.reply(ctx, content='pick cup 1, 2, or 3', ephemeral=True)
        await self.kit.instant(ctx, amt, "cups", lambda: roll_cups(amt, cup))
    @play.command(name="cups", description="find the ball under one of 3 cups - 2.88x")
    async def cups(self, ctx, amount: Option(str, "bet (or 'all')"), cup: Option(int, "which cup", choices=[1, 2, 3])):
        await self._cups(ctx, amount, cup)
    @commands.command(name="cups", aliases=["shell"])
    async def cups_cmd(self, ctx, amount: str, cup: int):
        await self._cups(ctx, amount, cup)

    async def _dragontiger(self, ctx, raw, side):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        side = side.lower()
        if side not in ('dragon', 'tiger', 'tie'):
            return await self.kit.reply(ctx, content="pick dragon, tiger, or tie", ephemeral=True)
        await self.kit.instant(ctx, amt, "dragontiger", lambda: roll_dragontiger(amt, side))

    @play.command(name="dragontiger", description="one card each, higher wins - 2x, tie pays 12.5x")
    async def dragontiger(self, ctx, amount: Option(str, "bet (or 'all')"), side: Option(str, "pick one", choices=["dragon", "tiger", "tie"])):
        await self._dragontiger(ctx, amount, side)

    @commands.command(name="dragontiger", aliases=["dt"])
    async def dragontiger_cmd(self, ctx, amount: str, side: str):
        await self._dragontiger(ctx, amount, side)
    async def _sicbo(self, ctx, raw, bet):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        bet = bet.lower()
        if bet not in ("big", "small", "odd", "even", "triple"):
            return await self.kit.reply(ctx, content="bet big, small, odd, even, or triple", ephemeral=True)
        await self.kit.instant(ctx, amt, "sicbo", lambda: roll_sicbo(amt, bet))
    @play.command(name='sicbo', description='three dice - big/small/odd/even pay 2x, any triple pays 35x')
    async def sicbo(self, ctx, amount: Option(str, "bet (or 'all')"),
                    bet: Option(str, 'what to bet on', choices=['big', 'small', 'odd', 'even', 'triple'])):
        await self._sicbo(ctx, amount, bet)
    @commands.command(name='sicbo')
    async def sicbo_cmd(self, ctx, amount: str, bet: str):
        await self._sicbo(ctx, amount, bet)

    async def _sevens(self, ctx, raw, bet):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        bet = bet.lower()
        if bet not in ("under", "over", "seven"):
            return await self.kit.reply(ctx, content="bet under, over, or seven", ephemeral=True)
        await self.kit.instant(ctx, amt, "sevens", lambda: roll_sevens(amt, bet))
    @play.command(name='sevens', description='two dice: under 7 / over 7 pay 2.3x, exactly 7 pays 5.75x')
    async def sevens(self, ctx, amount: Option(str, "bet (or 'all')"), bet: Option(str, "pick one", choices=["under", "over", "seven"])):
        await self._sevens(ctx, amount, bet)

    @commands.command(name="sevens", aliases=["7updown"])
    async def sevens_cmd(self, ctx, amount: str, bet: str):
        await self._sevens(ctx, amount, bet)

    async def _revolver(self, ctx, raw, bullets):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        if not 1 <= bullets <= 5:
            return await self.kit.reply(ctx, content='load 1 to 5 bullets', ephemeral=True)
        await self.kit.instant(ctx, amt, 'revolver', lambda: roll_revolver(amt, bullets))

    @play.command(name='revolver', description='load 1-5 bullets, more bullets = bigger payout if you survive')
    async def revolver(self, ctx, amount: Option(str, "bet (or 'all')"), bullets: Option(int, "1-5", min_value=1, max_value=5)):
        await self._revolver(ctx, amount, bullets)
    @commands.command(name="revolver", aliases=["rr"])
    async def revolver_cmd(self, ctx, amount: str, bullets: int = 1):
        await self._revolver(ctx, amount, bullets)
    async def _chests(self, ctx, raw, pick):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        if not 1 <= pick <= 5:
            return await self.kit.reply(ctx, content='pick a chest from 1 to 5', ephemeral=True)
        await self.kit.instant(ctx, amt, "chests", lambda: roll_chests(amt, pick))
    @play.command(name='chests', description='open 1 of 5 chests - 0x, 0.4x, 1x, 1.5x or 1.9x inside')
    async def chests(self, ctx, amount: Option(str, "bet (or 'all')"), chest: Option(int, "1-5", min_value=1, max_value=5)):
        await self._chests(ctx, amount, chest)
    @commands.command(name="chests", aliases=["chest"])
    async def chests_cmd(self, ctx, amount: str, chest: int):
        await self._chests(ctx, amount, chest)

    async def _diceduel(self, ctx, raw):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        await self.kit.instant(ctx, amt, "diceduel", lambda: roll_diceduel(amt))
    @play.command(name="diceduel", description="2 dice vs the house's 2 dice - higher wins 1.92x, tie pushes")
    async def diceduel(self, ctx, amount: Option(str, "bet (or 'all')")):
        await self._diceduel(ctx, amount)

    @commands.command(name="diceduel", aliases=["dd"])
    async def diceduel_cmd(self, ctx, amount: str):
        await self._diceduel(ctx, amount)
    async def _cardguess(self, ctx, raw, guess):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        kind, value = parse_cardguess(guess)
        if kind is None:
            return await self.kit.reply(ctx, content='guess a color (red/black), a suit (hearts...), or a rank (A, 2-10, J, Q, K)', ephemeral=True)
        await self.kit.instant(ctx, amt, "cardguess", lambda: roll_cardguess(amt, kind, value))
    @play.command(name='cardguess', description='guess the card: color 1.92x, suit 3.84x, exact rank 12.5x')
    async def cardguess(self, ctx, amount: Option(str, "bet (or 'all')"),
                        guess: Option(str, 'red / black / hearts / spades... / A, 2-10, J, Q, K')):
        await self._cardguess(ctx, amount, guess)
    @commands.command(name="cardguess", aliases=["cg"])
    async def cardguess_cmd(self, ctx, amount: str, guess: str):
        await self._cardguess(ctx, amount, guess)
    async def _target(self, ctx, raw, under):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        if not 2 <= under <= 95:
            return await self.kit.reply(ctx, content="target has to be between 2 and 95", ephemeral=True)
        await self.kit.instant(ctx, amt, "target", lambda: roll_target(amt, under))
    @play.command(name='target', description='roll 0-100, win if it lands under your target - lower target, bigger payout')
    async def target(self, ctx, amount: Option(str, "bet (or 'all')"), under: Option(int, "2-95", min_value=2, max_value=95)):
        await self._target(ctx, amount, under)
    @commands.command(name="target", aliases=["under"])
    async def target_cmd(self, ctx, amount: str, under: int = 50):
        await self._target(ctx, amount, under)

    async def _start_view(self, ctx, raw, make_view):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return None
        space = self.kit.c.get_space(ctx)
        if not await self.kit.take_bet(ctx, space, ctx.author, amt):
            return None
        view = make_view(space, amt)
        await self.kit.reply(ctx, embed=view.render(), view=view)
        return view
    async def _towers(self, ctx, raw, mode):
        mode = (mode or "medium").lower()
        if mode not in TOWER_MODES:
            return await self.kit.reply(ctx, content="mode is easy, medium, or hard", ephemeral=True)
        await self._start_view(ctx, raw, lambda s, a: TowersView(self.kit, s, ctx.author, a, mode))
    @play.command(name="towers", description="climb 8 floors picking safe tiles, cash out whenever")
    async def towers(self, ctx, amount: Option(str, "bet (or 'all')"),
                     mode: Option(str, "difficulty", choices=list(TOWER_MODES), required=False) = "medium"):
        await self._towers(ctx, amount, mode)
    @commands.command(name='towers', aliases=['tower'])
    async def towers_cmd(self, ctx, amount: str, mode: str = "medium"):
        await self._towers(ctx, amount, mode)
    @play.command(name="balloon", description="pump the balloon for a bigger multiplier - cash out before it pops")
    async def balloon(self, ctx, amount: Option(str, "bet (or 'all')")):
        await self._start_view(ctx, amount, lambda s, a: BalloonView(self.kit, s, ctx.author, a))
    @commands.command(name='balloon', aliases=['pump'])
    async def balloon_cmd(self, ctx, amount: str):
        await self._start_view(ctx, amount, lambda s, a: BalloonView(self.kit, s, ctx.author, a))

    @play.command(name='videopoker', description='jacks-or-better video poker: hold, draw, get paid')
    async def videopoker(self, ctx, amount: Option(str, "bet (or 'all')")):
        await self._start_view(ctx, amount, lambda s, a: VideoPokerView(self.kit, s, ctx.author, a))

    @commands.command(name='videopoker', aliases=['vp', 'poker'])
    async def videopoker_cmd(self, ctx, amount: str):
        await self._start_view(ctx, amount, lambda s, a: VideoPokerView(self.kit, s, ctx.author, a))
    async def _rocket(self, ctx, raw, auto):
        if auto is not None and auto < 1.01:
            return await self.kit.reply(ctx, content='auto cash-out has to be at least 1.01x', ephemeral=True)
        view = await self._start_view(ctx, raw, lambda s, a: RocketView(self.kit, s, ctx.author, a, auto))
        if view:
            asyncio.create_task(view.fly())

    @play.command(name="rocket", description="live crash - watch the multiplier climb, hit cash out before it blows")
    async def rocket(self, ctx, amount: Option(str, "bet (or 'all')"),
                     auto: Option(float, "optional auto cash-out multiplier", required=False, min_value=1.01) = None):
        await self._rocket(ctx, amount, auto)

    @commands.command(name="rocket")
    async def rocket_cmd(self, ctx, amount: str, auto: float = None):
        await self._rocket(ctx, amount, auto)
    async def _tictactoe(self, ctx, opponent, raw):
        if not ctx.guild:
            return await self.kit.reply(ctx, content="tic-tac-toe needs a server", ephemeral=True)
        if opponent.bot or opponent.id == ctx.author.id:
            return await self.kit.reply(ctx, content='pick a real opponent', ephemeral=True)
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        space = ctx.guild
        for m in (ctx.author, opponent):
            if self.kit.c.is_banned(m, space):
                return await self.kit.reply(ctx, content=f"{m.display_name} is banned from gambling here", ephemeral=True)
        if await self.kit.balance(space, ctx.author) < amt:
            return await self.kit.reply(ctx, content="you don't have that many chips", ephemeral=True)
        view = TTTChallenge(self, space, ctx.author, opponent, amt)
        await self.kit.reply(ctx, content=f"{opponent.mention} - {ctx.author.mention} challenges you to tic-tac-toe for "
                                          f"{self.kit.chips(amt)} each. winner takes the pot.", view=view)

    @play.command(name='tictactoe', description='challenge someone to tic-tac-toe for chips')
    async def tictactoe(self, ctx, opponent: Option(discord.Member, "who to play"), amount: Option(str, "wager each")):
        await self._tictactoe(ctx, opponent, amount)

    @commands.command(name='tictactoe', aliases=['ttt'])
    async def tictactoe_cmd(self, ctx, opponent: discord.Member, amount: str):
        await self._tictactoe(ctx, opponent, amount)

    async def _heist(self, ctx, raw):
        if not ctx.guild:
            return await self.kit.reply(ctx, content="heists need a server full of accomplices", ephemeral=True)
        seconds = 45
        view = await self._start_view(ctx, raw, lambda s, a: HeistLobby(self, s, ctx.author, a, seconds))
        if view:
            asyncio.create_task(view.run(seconds))
    @play.command(name='heist', description='start a heist - others join in 45s, bigger crew = better odds')
    async def heist(self, ctx, entry: Option(str, 'entry fee everyone pays')):
        await self._heist(ctx, entry)

    @commands.command(name="heist")
    async def heist_cmd(self, ctx, entry: str):
        await self._heist(ctx, entry)


    async def _craps(self, ctx, raw, side):
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        side = (side or "pass").lower().replace("'", "").replace(" ", "")
        side = "dont" if side.startswith("dont") else "pass"
        await self.kit.instant(ctx, amt, "craps", lambda: roll_craps(amt, side))

    @play.command(name="craps", description="pass line or don't pass - shooter rolls till they hit or seven out")
    async def craps(self, ctx, amount: Option(str, "bet (or 'all')"), side: Option(str, "which side", choices=["pass", "dont pass"], required=False) = "pass"):
        await self._craps(ctx, amount, side)

    @commands.command(name="craps")
    async def craps_cmd(self, ctx, amount: str, side: str = "pass"):
        await self._craps(ctx, amount, side)

    async def _threecard(self, ctx, raw):
        amt = await self._amount(ctx, raw)
        if amt is not None:
            await self.kit.instant(ctx, amt, "threecard", lambda: roll_threecard(amt))

    @play.command(name="threecard", description="3 cards vs the dealer's 3 - straights and up pay a bonus")
    async def threecard(self, ctx, amount: Option(str, "bet (or 'all')")):
        await self._threecard(ctx, amount)

    @commands.command(name="threecard", aliases=["3card", "tcp"])
    async def threecard_cmd(self, ctx, amount: str):
        await self._threecard(ctx, amount)

    async def _bingo(self, ctx, raw):
        amt = await self._amount(ctx, raw)
        if amt is not None:
            await self.kit.instant(ctx, amt, "bingo", lambda: roll_bingo(amt))

    @play.command(name="bingo", description="30 balls on your card - 1 line 5.2x, 2 lines 20x, 3 lines 60x, 4+ 200x")
    async def bingo(self, ctx, amount: Option(str, "bet (or 'all')")):
        await self._bingo(ctx, amount)

    @commands.command(name="bingo")
    async def bingo_cmd(self, ctx, amount: str):
        await self._bingo(ctx, amount)

    @play.command(name="penalty", description="pick a corner, beat the keeper - 1.44x")
    async def penalty(self, ctx, amount: Option(str, "bet (or 'all')")):
        await self._start_view(ctx, amount, lambda s, a: PenaltyView(self.kit, s, ctx.author, a))

    @commands.command(name="penalty", aliases=["pk"])
    async def penalty_cmd(self, ctx, amount: str):
        await self._start_view(ctx, amount, lambda s, a: PenaltyView(self.kit, s, ctx.author, a))

    @play.command(name="doors", description="3 doors, one has the money - stay or switch? 1.44x")
    async def doors(self, ctx, amount: Option(str, "bet (or 'all')")):
        await self._start_view(ctx, amount, lambda s, a: DoorsView(self.kit, s, ctx.author, a))

    @commands.command(name="doors", aliases=["montyhall"])
    async def doors_cmd(self, ctx, amount: str):
        await self._start_view(ctx, amount, lambda s, a: DoorsView(self.kit, s, ctx.author, a))

    async def _connect4(self, ctx, opponent, raw):
        if not ctx.guild:
            return await self.kit.reply(ctx, content="connect 4 needs a server", ephemeral=True)
        if opponent.bot or opponent.id == ctx.author.id:
            return await self.kit.reply(ctx, content="pick a real opponent", ephemeral=True)
        amt = await self._amount(ctx, raw)
        if amt is None:
            return
        for m in (ctx.author, opponent):
            if self.kit.c.is_banned(m, ctx.guild):
                return await self.kit.reply(ctx, content=f"{m.display_name} is banned from gambling here", ephemeral=True)
        if await self.kit.balance(ctx.guild, ctx.author) < amt:
            return await self.kit.reply(ctx, content="you don't have that many chips", ephemeral=True)
        view = C4Challenge(self, ctx.guild, ctx.author, opponent, amt)
        await self.kit.reply(ctx, content=f"{opponent.mention} - {ctx.author.mention} wants a game of connect 4 for "
                                          f"{self.kit.chips(amt)} each. winner takes it all.", view=view)

    @play.command(name="connect4", description="connect 4 against someone for chips")
    async def connect4(self, ctx, opponent: Option(discord.Member, "who"), amount: Option(str, "wager each")):
        await self._connect4(ctx, opponent, amount)

    @commands.command(name="connect4", aliases=["c4"])
    async def connect4_cmd(self, ctx, opponent: discord.Member, amount: str):
        await self._connect4(ctx, opponent, amount)

    @commands.slash_command(name="games", description="every casino game and what it pays")
    async def games(self, ctx):
        await self.kit.reply(ctx, embed=games_embed())
    @commands.command(name='games')
    async def games_cmd(self, ctx):
        await self.kit.reply(ctx, embed=games_embed())

GAME_GUIDE = {
    '🃏 cards': 'blackjack · baccarat · war · hilo · videopoker · dragontiger · cardguess · threecard',
    "🎰 slots & spins": "slots · jackpot · wheel · chests · scratch · keno",
    '🎲 dice': 'dice · sicbo · sevens · diceduel · target · craps',
    '🚀 risk it': 'crash · rocket · mines · towers · balloon · plinko · ladder',
    "🪙 quick bets": "coinflip · rps · cups · revolver · roulette · allin · horserace · bingo · penalty · doors",
    '⚔️ multiplayer': 'duel · tictactoe · connect4 · heist · lottery',
}


def games_embed():
    e = discord.Embed(title="🎲 the casino floor", color=0xFF6AD5,
                      description="every game takes an amount like `250`, `15k`, `1.5m` or `all`.\n"
                                  'newer games are under `/play` (e.g. `/play towers`) or just `!towers`.')
    for k, v in GAME_GUIDE.items():
        e.add_field(name=k, value=v, inline=False)
    return e


def setup(bot):
    bot.add_cog(GamesPlus(bot))
