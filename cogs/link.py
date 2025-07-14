from ossapi import OssapiAsync, UserLookupKey
import discord
from discord.ext import commands
from .common.osu_data import save_profile
from .common.misc import ossapi_credentials, InvalidArgument
from discord import app_commands


class OsuAccountLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="link", description="Links your osu account to your discord")
    async def link(self, interaction: discord.Interaction, username: str = ""):
        client_id, client_secret = await ossapi_credentials()
        oss_api = OssapiAsync(client_id, client_secret)

        if username == '':
            raise InvalidArgument(f'{interaction.user.mention} Error linking. Please make sure to insert a osu username.')

        else:

            try:
                user = await oss_api.user(username, key=UserLookupKey.USERNAME)
                discord_id = str(interaction.user.id)

                await save_profile(discord_id=discord_id, osu_id=user.id)


                embed = discord.Embed(
                    description=f'succesfully linked {interaction.user.mention} to {username}',
                    colour=discord.Colour.orange()
                )

                await interaction.response.send_message(embed=embed)


            except:
                raise InvalidArgument(f'{interaction.user.mention} Error linking. Please make sure the account exists.')

async def setup(bot):
    await bot.add_cog(OsuAccountLink(bot))