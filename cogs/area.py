import math
import discord
from discord.ext import commands
from discord import app_commands
from .common.misc import InvalidArgument

class Area(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def calc_GCD(self, numerator, denominator):

        r = numerator % denominator
        while r:
            numerator = denominator
            denominator = r
            r = numerator % denominator

        return denominator

    async def calc_fraction(self, ratio: float):
        denominator = 1
        while (int(denominator * ratio)) / denominator != ratio:
            denominator += 1
        numerator = int(denominator * ratio)
        factor = await self.calc_GCD(numerator, denominator)

        return numerator / factor, denominator / factor

    @app_commands.command(name="area", description="Calculates areas for your tablet, based on min/max width and ratio")
    async def area(self, interaction: discord.Interaction, min: int, max: int, ratio: float):
        description = ""

        if min > max:
            min, max = max, min

        if min <= 0:
            raise InvalidArgument("Minimum value cannot be 0 or less.")
        if max > 150:
            raise InvalidArgument("Max value cannot be more then 150 to avoid spam")
        if ratio % 1 == 0:
            raise InvalidArgument("Ratio cannot be a whole number to avoid spam")


        absolute_min = await self.calc_fraction(ratio)

        multiplier = math.ceil(min / absolute_min[0])

        numerator = absolute_min[0] * multiplier
        denominator = absolute_min[1] * multiplier

        if max >= numerator >= min:
            description += f"{int(numerator)} x {int(denominator)}\n"
        else:
            description = "ratio has too many decimal points to find valid areas of whole numbers"

        while max >= numerator >= min:
            if numerator + absolute_min[0] > max:
                break
            numerator += absolute_min[0]
            denominator += absolute_min[1]
            description += f"{int(numerator)} x {int(denominator)}\n"


        embed = discord.Embed(
            description=f"Lowest whole fraction for ratio {ratio} is {int(absolute_min[0])} x {int(absolute_min[1])}\n\n{description}",
            colour=discord.Colour.orange())

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Area(bot))