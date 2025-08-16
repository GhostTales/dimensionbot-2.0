import random
import discord
from discord.ext import commands
from discord import app_commands


class Roll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Rolls a number")
    async def roll(self, interaction: discord.Interaction, limit: int = 100):
        await interaction.response.defer()
        message = await interaction.original_response()
        if limit == 0:
            limit = 100

        embed = discord.Embed(
            description=f'{interaction.user.mention} rolled {random.randint(1, abs(limit))}',
            colour=discord.Colour.orange()
        )

        await message.edit(embed=embed)

async def setup(bot):
    await bot.add_cog(Roll(bot))