from .Utils import *

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

    @commands.command(pass_context=True)
    async def dice(self, ctx, roll='1d1'):
        """Roll some dice! Great for RPG and such.
        See here for the roll syntax: https://github.com/pknull/rpg-dice"""
        msg = DiceThrower().throw(roll)
        print(msg)
        if type(msg) is dict:
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
    async def killer(self, ctx, count=1):
        """Pick a Dead By Daylight Killer!"""
        class Killer:
            SIDES = ['Trapper', 'Wraith', 'Hillbilly', 'Nurse', 'Shape', 'Hag', 'Doctor', 'Huntress', 'Cannibal',
                     'Nightmare', 'Pig', 'Clown', 'Spirit', 'Legion', 'Plague', 'Ghost Face']
        tosser = Tosser(Killer)
        result = tosser.toss(count, True)
        if type(result) is list:
            title = '🗡 Killers'
            embed = make_embed(title, result)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing killer.")

    @commands.command(pass_context=True)
    async def sperks(self, ctx, count=4):
        """Pick a Dead By Daylight Survivor Perk!"""
        class SPerks:
            SIDES = ['Ace in the Hole', 'Adrenaline', 'Aftercare', 'Alert',
                     'Autodidact', 'Balanced Landing', 'Boil Over', 'Bond',
                     'Borrowed Time', 'Botany Knowledge', 'Breakdown',
                     'Buckle Up', 'Calm Spirit', 'Dance With Me',
                     'Dark Sense', 'Dead Hard', 'Decisive Strike', 'Déjà Vu',
                     'Deliverance', 'Detective\'s Hunch', 'Distortion',
                     'Diversion', 'Empathy', 'Flip-Flop', 'Head On', 'Hope', 'Iron Will',
                     'Kindred', 'Leader', 'Left Behind', 'Lightweight',
                     'Lithe',
                     'Mettle of Man', 'No Mither', 'No One Left Behind',
                     'Object of Obsession', 'Open-Handed', 'Pharmacy',
                     'Plunderer\'s Instinct',
                     'Poised', 'Premonition', 'Prove Thyself',
                     'Quick & Quiet', 'Resilience', 'Saboteur', 'Self-Care',
                     'Slippery Meat',
                     'Small Game', 'Sole Survivor', 'Solidarity',
                     'Spine Chill', 'Sprint Burst', 'Stake Out',
                     'Streetwise', 'This Is Not Happening',
                     'Technician', 'Tenacity', 'Up the Ante', 'Unbreakable',
                     'Urban Evasion', 'Vigil', 'Wake Up!', 'We\'ll Make It',
                     'We\'re Gonna Live Forever',
                     'Windows of Opportunity']
        tosser = Tosser(SPerks)
        result = tosser.toss(count, True)
        if type(result) is list:
            title = '🔣 Survivor Perks'
            embed = make_embed(title, result)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing survivor perks.")

    @commands.command(pass_context=True)
    async def kperks(self, ctx, count=4):
        """Pick a Dead By Daylight Killer Perk!"""
        class KPerks:
            SIDES = ['A Nurse\'s Calling', 'Agitation', 'Bamboozle', 'Barbecue & Chill',
                     'Beast of Prey', 'Bitter Murmur', 'Bloodhound', 'Blood Warden',
                     'Brutal Strength', 'Corrupt Intervention', 'Coulrophobia',
                     'Dark Devotion', 'Deerstalker', 'Discordance', 'Distressing',
                     'Dying Light', 'Enduring', 'Fire Up', 'Franklin\'s Demise',
                     'Furtive Chase', 'Hangman\'s Trick', 'Hex: Devour Hope',
                     'Hex: Haunted Ground', 'Hex: Huntress Lullaby', 'Hex: No One Escapes Death',
                     'Hex: Ruin', 'Hex: The Third Seal', 'Hex: Thrill of the Hunt', 'I\'m All Ears',
                     'Infectious Fright', 'Insidious', 'Iron Grasp', 'Iron Maiden',
                     'Knock Out', 'Lightborn', 'Mad Grit', 'Make Your Choice', 'Monitor & Abuse',
                     'Monstrous Shrine', 'Overcharge', 'Overwhelming Presence',
                     'Play with Your Food', 'Pop Goes the Weasel', 'Predator', 'Rancor',
                     'Remember Me', 'Save the Best for Last', 'Shadowborn', 'Sloppy Butcher',
                     'Spies from the Shadows', 'Spirit Fury', 'Stridor', 'Surveillance',
                     'Territorial Imperative', 'Tinkerer', 'Thanatophobia', 'Thrilling Tremors',
                     'Unnerving Presence', 'Unrelenting', 'Whispers']
        tosser = Tosser(KPerks)
        result = tosser.toss(count, True)
        if type(result) is list:
            title = '🔣 Killer Perks'
            embed = make_embed(title, result)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing killer perks.")


    @commands.command(pass_context=True)
    async def defender(self, ctx, count=1):
        """Pick a Rainbow Six DEFENDER"""
        class Defender:
            SIDES = ["Alibi", "Bandit", "Castle", "Caveira", "Clash", "Doc", "Echo", "Ela", "Frost", "Jäger", "Kaid",
                     "Kapkan", "Lesion", "Maestro", "Mira", "Mozzie", "Mute", "Pulse", "Recruit", "Rook", "Smoke",
                     "Tachanka", "Valkyrie", "Vigil", "Warden"]
        tosser = Tosser(Defender)
        result = tosser.toss(count, True)
        if type(result) is list:
            title = '🛡️ Defenders'
            embed = make_embed(title, result)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing defender.")

    @commands.command(pass_context=True)
    async def attacker(self, ctx, count=1):
        """Pick a Rainbow Six ATTACKER"""
        class Attacker:
            SIDES = ["Ash", "Blackbeard", "Blitz", "Buck", "Capitão", "Dokkaebi", "Finka", "Fuze", "Glaz", "Gridlock",
                     "Hibana", "IQ", "Jackal", "Lion", "Maverick", "Montagne", "Nomad", "Nøkk", "Recruit", "Sledge",
                     "Thatcher", "Thermite", "Twitch", "Ying", "Zofia"]
        tosser = Tosser(Attacker)
        result = tosser.toss(count, True)
        if type(result) is list:
            title = '🔫 Attackers'
            embed = make_embed(title, result)
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.channel.send("Error parsing attacker.")

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

def setup(bot):
    bot.add_cog(Games(bot))
