import discord
from discord.ext import commands
from discord import app_commands
from .common.osu_data import get_entry, search_entry
from .common.misc import ossapi_credentials, InvalidArgument, delete_file
from ossapi import OssapiAsync, UserLookupKey
from playwright.async_api import async_playwright
import random


class Osu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ##pip install playwright
    ##playwright install

    GAMEMODE_CHOICES = [
        app_commands.Choice(name="standard", value="std"),
        app_commands.Choice(name="taiko", value="taiko"),
        app_commands.Choice(name="catch", value="catch"),
        app_commands.Choice(name="mania", value="mania")
    ]

    @app_commands.command(name="osu", description="Shows your osu profile, or of specified user")
    @app_commands.describe(
        mode="Select a game mode"
    )
    @app_commands.choices(mode=GAMEMODE_CHOICES)
    async def osu(self, interaction: discord.Interaction, mode: app_commands.Choice[str] = "std", username: str = ""):
        ##pip install playwright
        ##playwright install
        await interaction.response.defer()
        client_id, client_secret = await ossapi_credentials()
        oss_api = OssapiAsync(client_id, client_secret)


        async def render_card(username: str, output_path: str = "card.png", mode: str = "std"):
            svg_url = f"https://osu-sig.vercel.app/card?user={username}&mode={mode}&lang=en&w=1600&h=931"

            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page(viewport={"width": 1600, "height": 931})
                await page.goto(svg_url)

                await page.screenshot(path=output_path, omit_background=True)
                await browser.close()



        path = "data/osu_data/profiles.json"

        if "<@" in username:
            username = username.strip("<@").strip(">")

            if await search_entry(path=path, discord_id=username):
                osu_id = (await get_entry(path=path, discord_id=username))["link"]
                osu_user = await oss_api.user(osu_id, key=UserLookupKey.ID)
                osu_name = osu_user.username

            else:
                raise InvalidArgument(f"User <@{username}> has not been linked to an osu account")

        elif username == '':
            discord_id = str(interaction.user.id)
            osu_id = (await get_entry(path=path, discord_id=discord_id))["link"]
            osu_user = await oss_api.user(osu_id, key=UserLookupKey.ID)
            osu_name = osu_user.username

        else:
            try:
                await oss_api.user(username, key=UserLookupKey.USERNAME)
                osu_name = username

            except:
                raise InvalidArgument(f"""It seems the osu account "{username}" does not exist""")

        message = await interaction.original_response()

        if mode != "std":
            mode = mode.value


        file_id = random.random()

        await render_card(username=osu_name, mode=mode, output_path=f"data/assets/cards/card-{file_id}.png")
        file = discord.File(f"data/assets/cards/card-{file_id}.png", filename=f"card-{file_id}.png")

        await message.edit(attachments=[file])
        file.close()
        await delete_file(f"data/assets/cards/card-{file_id}.png")

async def setup(bot):
    await bot.add_cog(Osu(bot))