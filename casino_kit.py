import random

import discord

import store


def bar(done, total, width=10):
    total = max(total, 1)
    filled = min(width, int(width * done / total))
    return '▰' * filled + '▱' * (width - filled)

class Kit:
    def __init__(self, bot):
        self.bot = bot
        self.c = bot.casino
    def chips(self, n):
        return self.c.chips(n)
    async def reply(self, ctx, **kw):
        return await self.c.reply(ctx, **kw)
    async def parse(self, ctx, raw):
        return await self.c.parse_slash_amount(ctx, raw)

    def space_of(self, ctx_or_guild):
        guild = getattr(ctx_or_guild, 'guild', ctx_or_guild)
        return guild if guild is not None else self.c.get_space(ctx_or_guild)

    async def with_account(self, space, member, fn):
        f = self.c.econ_file_for(space)
        async with store.locked(f):
            econ = self.c.loadEcon(f)
            a = self.c.acct(econ, space, member)
            result = fn(a)
            self.c.save(econ, f)
        return result

    async def credit(self, space, member, amount, reason=None):
        def fn(a):
            a["bal"] += int(amount)
            return a["bal"]
        bal = await self.with_account(space, member, fn)
        if reason:
            self.c.log_event(space.name, f"{member.display_name} {reason} ({self.chips(int(amount))})")
        return bal
    async def balance(self, space, member):
        f = self.c.econ_file_for(space)
        econ = self.c.loadEcon(f)
        return self.c.acct(econ, space, member)["bal"]
    async def take_bet(self, ctx, space, member, amount):
        if self.c.is_banned(member, space):
            await self.reply(ctx, content="you're banned from gambling here", ephemeral=True)
            return False
        ok = {"v": False}
        def fn(a):
            if 0 < amount <= a['bal']:
                a["bal"] -= amount
                ok["v"] = True
        await self.with_account(space, member, fn)
        if not ok["v"]:
            await self.reply(ctx, content="bad bet amount - you don't have that many chips in your wallet", ephemeral=True)
        return ok["v"]

    async def payout(self, space, member, amount, gross, game=None):
        net = gross - amount
        if net > 0:
            net = await self.c.take_tax(space, net)
        back = amount + net if gross > 0 else 0
        def fn(a):
            bal_before = a["bal"] + amount
            a["bal"] += back
            self.c.check_bet_badges(a, space.name, amount, bal_before, net)
            return a["bal"]
        bal = await self.with_account(space, member, fn)
        try:
            self.c.record_game(space, member, net)
        except Exception:
            pass
        if game:
            self.bot.dispatch("casino_game", member, space, game, amount, net)
        return net, bal

    async def instant(self, ctx, amount, game, resolve):
        space = self.c.get_space(ctx)
        member = ctx.author
        if self.c.is_banned(member, space):
            await self.reply(ctx, content="you're banned from gambling here", ephemeral=True)
            return
        f = self.c.econ_file_for(space)
        async with store.locked(f):
            econ = self.c.loadEcon(f)
            a = self.c.acct(econ, space, member)
            if amount <= 0 or amount > a['bal']:
                await self.reply(ctx, content='bad bet amount', ephemeral=True)
                return
            gross, text = resolve()
            if self.c.pop_rig(space, member) == "win":
                for _ in range(500):
                    if gross > amount:
                        break
                    gross, text = resolve()
            gross = int(gross)
            net = gross - amount
            if net > 0:
                net = await self.c.take_tax(space, net)
            bal_before = a["bal"]
            a["bal"] += net
            self.c.check_bet_badges(a, space.name, amount, bal_before, net)
            bal = a['bal']
            self.c.save(econ, f)
        try:
            self.c.record_game(space, member, net)
        except Exception:
            pass
        self.bot.dispatch("casino_game", member, space, game, amount, net)
        await self.reply(ctx, embed=result_embed(game, text, amount, net, bal, self.chips))

GAME_TITLES = {}

def result_embed(game, text, amount, net, bal, chips_fn):
    if net > 0:
        color, head = 0x3BD671, f"won {chips_fn(net)}"
    elif net == 0:
        color, head = 0xF5C542, 'push - bet returned'
    else:
        color, head = 0xED4245, f"lost {chips_fn(-net)}"
    e = discord.Embed(title=GAME_TITLES.get(game, game), description=text, color=color)
    e.add_field(name="result", value=head, inline=True)
    e.add_field(name='wallet', value=chips_fn(bal), inline=True)
    return e


SUITS = {'hearts': '♥️', 'diamonds': '♦️', 'clubs': '♣️', 'spades': '♠️'}
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def new_deck():
    deck = [(r, s) for r in range(1, 14) for s in SUITS]
    random.shuffle(deck)
    return deck


def card_str(card):
    r, s = card
    return f"`{RANKS[r - 1]}{SUITS[s]}`"
