from .Utils import *

import discord
from discord.ext import commands
from dice_roller.DiceThrower import DiceThrower

from card_picker.Deck import Deck
from card_picker.Card import *

from flipper.Tosser import Tosser
from flipper.Casts import *

class Games(commands.Cog):
    """Game tools! Custom RNG tools for whatever."""

    def __init__(self, bot):
        self.bot = bot

    async def setup(bot):
        print('I am being loaded!')

    async def teardown(bot):
        print('I am being unloaded!')

    @commands.command(pass_context=True)
    async def dice(self, ctx, roll='1d1'):
        """Roll some dice! Great for RPG and such.
        See here for the roll syntax: https://github.com/pknull/rpg-dice"""
        msg = DiceThrower().throw(roll)
        print(msg)
        if type(msg) is dict:
            msg['roller'] = ctx.message.author
            if msg['natural'] == msg['modified']:
                msg.pop('modified', None)
            title = '🎲 Dice Roll'
            embed = make_embed(title, msg)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing dice.")

    @commands.command(pass_context=True)
    async def card(self, ctx, card: str, count=1):
        """Deal a hand of cards. Doesn't currently support games.
        cards: [standard,shadow,tarot,uno]"""
        card_conv = {
            'standard' : StandardCard,
            'shadow' : ShadowCard,
            'tarot' : TarotCard,
            'uno' : UnoCard
        }

        if len(card) > 0:
            card_type = card
        else:
            card_type = 'standard'

        cards = card_conv[card_type]
        deck = Deck(cards)
        deck.create()
        deck.shuffle()
        hand = deck.deal(count)
        if type(hand) is list:
            title = '🎴 Card Hand ' + card_type[0].upper() + card_type[1:]
            embed = make_embed(title, hand)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing cards.")

    @commands.command(pass_context=True)
    async def coin(self, ctx, count=1):
        """Flip a coin. Add a number for multiples."""
        tosser = Tosser(Coin)
        result = tosser.toss(count)
        if type(result) is list:
            title = '⭕ Coin Flip'
            embed = make_embed(title, result)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing coin.")

    @commands.command(pass_context=True)
    async def eightball(self, ctx, count=1):
        """Rolls an eightball!"""
        tosser = Tosser(EightBall)
        result = tosser.toss(count)
        if type(result) is list:
            title = '🎱 Eightball'
            embed = make_embed(title, result)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing eightball.")

    @commands.command(pass_context=True)
    async def toss(self, ctx, items, count=1, unique='t'):
        """Pick an amount from a list"""
        words = items.split(',')

        user_list = lambda: None
        setattr(user_list, 'SIDES', words)

        tosser = Tosser(user_list)
        result = tosser.toss(count, bool(unique == 't'))

        if type(result) is list:
            title = '⁉ Lists!'
            embed = make_embed(title, result)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing list.")

async def setup(bot):
    await bot.add_cog(Games(bot))
