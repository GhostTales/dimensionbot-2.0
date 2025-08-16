import discord
from discord.ext import commands
import os
import sys
from .common.misc import color_string
import asyncio
from discord import app_commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx):
        #Reload all cogs in the 'cogs' folder.
        loads_str = "```ansi\n"
        cogs_dir = os.path.join(os.path.dirname(__file__), "..", "cogs")
        cogs_dir = os.path.abspath(cogs_dir)

        for file in os.listdir(cogs_dir):
            if file.endswith(".py") and file != "__init__.py":
                module_name = file[:-3]  # Strip '.py'
                full_module = f"cogs.{module_name}"

                try:
                    await self.bot.unload_extension(full_module)
                except commands.ExtensionNotLoaded:
                    pass  # It's fine if it wasn't loaded yet

                try:
                    await self.bot.load_extension(full_module)
                    loads_str += f"{color_string("Loaded extension:", "green")} {color_string(f"{full_module}", "yellow")}:\n"
                except Exception as e:
                    loads_str += f"{color_string("Failed to load extension", "red")} {color_string(f"{full_module}", "yellow")}: {color_string(f"{e}", "red")}\n"

        await self.bot.tree.sync()
        await ctx.send(loads_str + "```")

    @reload.error
    async def reload_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("You are not the owner of this bot.")
        else:
            await ctx.send(f"An error occurred: {error}")


async def setup(bot):
    await bot.add_cog(Admin(bot))