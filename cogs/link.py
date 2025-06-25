from ossapi import OssapiAsync, UserLookupKey
import discord
from discord.ext import commands
from .common.osu_data import add_entry, edit_entry, search_entry
from .common.misc import ossapi_credentials, InvalidArgument, create_file
from discord import app_commands


class OsuAccountLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="link", description="Links your osu account to your discord")
    async def link(self, interaction: discord.Interaction, string: str = ""):
        client_id, client_secret = await ossapi_credentials()
        oss_api = OssapiAsync(client_id, client_secret)

        # Write to JSON with guild id and string as value
        if string == '':
            raise InvalidArgument(f'{interaction.user.mention} Error linking. Please make sure to insert a osu username.')

        else:

            try:
                user = await oss_api.user(string, key=UserLookupKey.USERNAME)
                path = "data/osu_data/profiles.json"

                await create_file(path)

                discord_id = str(interaction.user.id)

                if await search_entry(discord_id=discord_id, path=path):
                    await edit_entry(path=path, discord_id=discord_id, link=user.id)

                else:
                    await add_entry(path=path, discord_id=discord_id)
                    await edit_entry(path=path, discord_id=discord_id, link=user.id)


                embed = discord.Embed(
                    description=f'succesfully linked {interaction.user.mention} to {string}',
                    colour=discord.Colour.orange()
                )

                await interaction.response.send_message(embed=embed)


            except:
                raise InvalidArgument(f'{interaction.user.mention} Error linking. Please make sure the account exists.')

async def setup(bot):
    await bot.add_cog(OsuAccountLink(bot))