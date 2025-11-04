# -*- coding: utf-8 -*-
import random
import openai
import os
import logging
from discord.ext import commands

logger = logging.getLogger('cipher_oracle')


class CipherOracle(commands.Cog):
    """Cipher-based divination and mystical readings."""

    def __init__(self, bot):
        self.bot = bot
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.custom_uri = os.getenv("CIPHER_ORACLE_API_URI", None)

        if not openai.api_key:
            logger.warning("OPENAI_API_KEY not set - cipher readings will not work")

        self.descriptions = {
            '00000': 'The Seed: Untapped potential, the beginning of a personal journey.',
            '00001': 'The Shadow: Personal doubts, inner fears, and unresolved issues.',
            '00010': 'The Beacon: Personal clarity, enlightenment, and self-awareness.',
            '00011': 'The Chains: Personal limitations, feeling trapped by one\'s own beliefs or choices.',
            '00100': 'The Mirror: Reflection, self-realization, understanding one\'s true nature.',
            '00101': 'The Maze: Confusion, feeling lost, a need for introspection.',
            '00110': 'The Garden: Growth, prosperity, and harmony with one\'s surroundings.',
            '00111': 'The Storm: External challenges, disruptions, and conflicts.',
            '01000': 'The Clock: Time, cycles, and inevitable change.',
            '01001': 'The Desert: Isolation, barrenness, a need to find resources.',
            '01010': 'The Key: Solutions, answers, and unlocking mysteries.',
            '01011': 'The Dagger: Betrayal, danger, and external threats.',
            '01100': 'The Fountain: Overflowing emotions, rejuvenation, and healing.',
            '01101': 'Death: Endings, transitions, and rebirth.',
            '01110': 'The Star: Hope, guidance, and a bright future.',
            '01111': 'The Void: Emptiness, feeling lost in the vastness, a need for purpose.',
            '10000': 'The Phoenix: Renewal, rebirth, rising from the ashes.',
            '10001': 'The Serpent: Temptation, deceit, and challenges from unseen forces.',
            '10010': 'The Book: Knowledge, secrets, and revelations.',
            '10011': 'The Spider: Manipulation, entanglement, and complex situations.',
            '10100': 'The Crown: Authority, power, and divine favor.',
            '10101': 'The Tower: Sudden upheaval, chaos, and unexpected change.',
            '10110': 'The Harp: Harmony, music, and positive vibrations.',
            '10111': 'The Flames: Destruction, passion, and uncontrollable forces.',
            '11000': 'The Chalice: Emotions, relationships, and connections.',
            '11001': 'The Wolf: Wild instincts, threats, and survival.',
            '11010': 'The Angel: Divine messages, protection, and blessings.',
            '11011': 'The Demon: Inner demons, external temptations, and challenges.',
            '11100': 'The Sun: Success, vitality, and radiant energy.',
            '11101': 'The Moon: Illusions, dreams, and the subconscious.',
            '11110': 'The World: Completion, wholeness, and realization of goals.',
            '11111': 'The Abyss: Deep fears, the unknown, and profound mysteries.'
        }

    def generate_codes(self):
        bins = format(random.randint(0, 32767), '015b')
        return [bins[:5], bins[5:10], bins[10:15]], bins

    def generate_hexagram(self, bins):
        hex_value = hex(int(bins, 2))[2:].upper().zfill(4)
        return hex_value

    async def interpret_reading(self, hexagram: str, past: str, present: str, future: str) -> str:
        """
        Generate AI interpretation of cipher reading.

        Args:
            hexagram: Hexagram code
            past: Past cipher code
            present: Present cipher code
            future: Future cipher code

        Returns:
            Interpretation string
        """
        prompt = (
            "You are a wise being who walks between worlds, offering insight with subtle, symbolic language.\n\n"
            "Provide a contemplative interpretation using metaphor and imagery based on this cipher reading:\n\n"
            f"Hexagram Code: {hexagram}\n"
            f"Past: {self.descriptions.get(past)}\n"
            f"Present: {self.descriptions.get(present)}\n"
            f"Future: {self.descriptions.get(future)}\n\n"
            "Evoke gentle reverence toward unseen forces, mysteries of transformation, and thresholds of change.\n\n"
            "Interpretation:"
        )

        try:
            if self.custom_uri:
                client = openai.OpenAI(base_url=self.custom_uri)
            else:
                client = openai.OpenAI()

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )

            return response.choices[0].message.content.strip()
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return f"An API error occurred: {e}"
        except Exception as e:
            logger.error(f"Unexpected error in cipher reading: {e}")
            return f"An unexpected error occurred: {e}"

    @commands.command(name='cipher')
    async def cipher(self, ctx):
        """Generate a mystical cipher reading with AI interpretation."""
        logger.debug(f"Cipher reading requested by {ctx.author.id}")

        (past, present, future), bins = self.generate_codes()
        hexagram = self.generate_hexagram(bins)
        interpretation = await self.interpret_reading(hexagram, past, present, future)

        initial_message = (
            f"Code: {hexagram}\n"
            f"{past} | Past - {self.descriptions.get(past, 'Undefined')}\n"
            f"{present} | Present - {self.descriptions.get(present, 'Undefined')}\n"
            f"{future} | Future - {self.descriptions.get(future, 'Undefined')}\n"
            f"**Interpretation:**\n{interpretation}"
        )

        await ctx.send(f"```\n{initial_message}\n```")

async def setup(bot):
    await bot.add_cog(CipherOracle(bot))
