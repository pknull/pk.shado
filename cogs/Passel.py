import discord
from discord.ext import commands
from random import randrange

class Passel(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='pins', pass_context=True)
    async def pins(self, ctx):
        numPins = await ctx.message.channel.pins()
        await ctx.send(ctx.message.channel.mention + " has " + str(len(numPins)) + " pins.")

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        global data
        try:
            # discord embed colors
            EMBED_COLORS = [
                discord.Colour.magenta(),
                discord.Colour.blurple(),
                discord.Colour.dark_teal(),
                discord.Colour.blue(),
                discord.Colour.dark_blue(),
                discord.Colour.dark_gold(),
                discord.Colour.dark_green(),
                discord.Colour.dark_grey(),
                discord.Colour.dark_magenta(),
                discord.Colour.dark_orange(),
                discord.Colour.dark_purple(),
                discord.Colour.dark_red(),
                discord.Colour.darker_grey(),
                discord.Colour.gold(),
                discord.Colour.green(),
                discord.Colour.greyple(),
                discord.Colour.orange(),
                discord.Colour.purple(),
                discord.Colour.magenta(),
            ]
            pins_channel = "826669073081171978"
            randomColor = randrange(len(EMBED_COLORS))
            numPins = await channel.pins()
            blacklisted_channels = ["826669073081171978"]

            # checks to see if message is in the blacklist
            # message is only sent if there is a blacklisted server with 50 messages pinned, informs them
            # that passel is in the server and they can un-blacklist the channel to have passel work
            if str(channel.id) in blacklisted_channels:
                return

            isChannelThere = False
            # checks to see if pins channel exists in the server
            channnelList = channel.guild.channels
            for channel in channnelList:
                if int(pins_channel) == int(channel.id):
                    isChannelThere = True

            # checks to see if pins channel exists or has been deleted
            if not isChannelThere:
                print("Can't find the pins channel!")
                await channel.send("Check to see if the pins archive channel during setup has been deleted")
                return

            last_pinned = numPins[0]
            if len(numPins) == 50:
                last_pinned = numPins[len(numPins) - 1]
                pinEmbed = discord.Embed(
                    # title="Sent by " + last_pinned.author.name,
                    description="\"" + last_pinned.content + "\"",
                    colour=EMBED_COLORS[randomColor]
                )
                # checks to see if pinned message has attachments
                attachments = last_pinned.attachments
                if len(attachments) >= 1:
                    pinEmbed.set_image(url=attachments[0].url)
                pinEmbed.add_field(
                    name="Jump", value=last_pinned.jump_url, inline=False)
                pinEmbed.set_footer(
                    text="sent in: " + last_pinned.channel.name + " - at: " + str(last_pinned.created_at))
                pinEmbed.set_author(name='Sent by ' + last_pinned.author.name)
                await last_pinned.guild.get_channel(int(pins_channel)).send(embed=pinEmbed)

                # remove this message if you do not want the bot to send a message when you pin a message
                await last_pinned.channel.send(
                    "See oldest pinned message in " + channel.guild.get_channel(int(pins_channel)).mention)
                await last_pinned.unpin()
        except:
            print(traceback.format_exc())
            quit()

async def setup(bot):
    await bot.add_cog(Passel(bot))
    