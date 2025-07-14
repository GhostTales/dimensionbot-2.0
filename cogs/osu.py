import discord
from discord.ext import commands
from discord import app_commands
from .common.osu_data import resolve_osu_user
from .common.misc import ossapi_credentials, delete_file
from ossapi import OssapiAsync
from playwright.async_api import async_playwright


class Osu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        user = await resolve_osu_user(username=username, interaction=interaction, oss_api=oss_api)

        message = await interaction.original_response()

        if mode != "std":
            mode = mode.value


        await render_card(username=user.username, mode=mode, output_path=f"data/assets/cards/card-{user.id}.png")
        file = discord.File(f"data/assets/cards/card-{user.id}.png", filename=f"card-{user.id}.png")

        await message.edit(attachments=[file])
        file.close()
        await delete_file(f"data/assets/cards/card-{user.id}.png")

async def setup(bot):
    await bot.add_cog(Osu(bot))