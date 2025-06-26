import asyncio
import json
import discord
from discord.ext import commands
from discord.app_commands import AppCommandError
from cogs.common.misc import insure_folders_exist, insure_files_exist, InvalidArgument, color_string
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

with open("Credentials.json") as json_file:
    json_data = json.load(json_file)
    token = json_data["Credentials"][0]["Token"]

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return
    print(f'{message.author}: {message.content} | {message.channel}')
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(status=discord.Status.do_not_disturb, activity=discord.Game('osu! lazer'))


async def load_cogs(bot):
    for file in os.listdir("cogs"):
            if file.endswith(".py") and file != "__init__.py":
                module_name = file[:-3]  # Strip '.py'
                full_module = f"cogs.{module_name}"
                try:
                    await bot.load_extension(full_module)  # Await here
                    print(f"{color_string("Loaded extension:", "green")} {color_string(f"{full_module}", "yellow")}:")
                except Exception as e:
                    print(f"{color_string("Failed to load extension", "red")} {color_string(f"{full_module}", "yellow")}: {color_string(f"{e}", "red")}")

@bot.event
async def setup_hook():
    await load_cogs(bot)
    await bot.tree.sync()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: AppCommandError):
    # Custom error handling see cogs/common/misc
    if isinstance(error, InvalidArgument):
        embed = discord.Embed(description=error.message, colour=discord.Colour.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        # Fallback for unknown errors
        embed = discord.Embed(description="An unexpected error occurred.", colour=discord.Colour.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        raise error

async def main():
    async with bot:
        await insure_folders_exist()
        await insure_files_exist()
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())

#https://discordpy.readthedocs.io/en/stable/interactions/api.html?highlight=send_message#discord.InteractionResponse.send_message