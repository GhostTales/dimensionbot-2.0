import discord
from discord.ext import commands
from discord import app_commands
from .common.osu_data import get_entry


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test", description="test command")
    async def test(self, interaction: discord.Interaction):


        discord_id = str(interaction.user.id)
        profile = await get_entry(path="data/osu_data/profiles.json", discord_id=discord_id)
        print(profile)


        await interaction.response.send_message(f"Hello, {interaction.user.mention}!")

async def setup(bot):
    await bot.add_cog(Test(bot))
