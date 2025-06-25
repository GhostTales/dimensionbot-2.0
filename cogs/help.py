import discord
from discord.ext import commands
from discord import app_commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    HELP_CHOICES = [
        app_commands.Choice(name="help", value="/help"),
        app_commands.Choice(name="roll", value="/roll"),
        app_commands.Choice(name="area", value="/area"),
        app_commands.Choice(name="rs", value="/rs"),
        app_commands.Choice(name="osu", value="/osu"),
        app_commands.Choice(name="link", value="/link")
    ]


    @app_commands.command(name="help", description="Shows a list of all bot functions")
    @app_commands.describe(
        command="Select a command"
    )
    @app_commands.choices(command=HELP_CHOICES)
    async def help(self, interaction: discord.Interaction, command: app_commands.Choice[str] = None):
        commands_info = {
            "/help": "Displays a message with information about the bot's commands and functionality.",
            "/roll": "Rolls a random number between 1 and the specified number (default is 100).\nExample: /roll 1000",
            "/area": "Calculates the perfect osu tablet area from the given width from the minimum width, maximum width, and ratio values.\nExample: /area 80 120 1.4",
            "/rs": "Displays your most recent score in osu or of the user specified after the command.\nExample: /rs Ghost-Tales",
            "/osu": "Displays your osu profile stats or of the user specified after the command.\nExample: /osu Ghost-Tales",
            "/link": "Allows you to link your discord to your osu profile, so the osu related commands can work properly.\nExample: /link Ghost-Tales",
        }

        embed = discord.Embed(title='Help list', colour=discord.Colour.orange())

        if command:
            # Show help for a specific command
            description = commands_info.get(command.value, "No help available for that command.")
            embed.add_field(name=command.value, value=description, inline=False)
        else:
            # Show help for all commands
            for cmd_name, desc in commands_info.items():
                embed.add_field(name=cmd_name, value=desc, inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))