import math
import re
import aiofiles
import discord
from discord.ext import commands
from discord import app_commands
from .common.osu_data import get_recent_map, get_beatmap_link_from_message
from .common.misc import ossapi_credentials, InvalidArgument, sanitize_filename
from .common.osu_scores import download_and_extract
from ossapi import OssapiAsync
import rosu_pp_py as rosu


async def map_logic(reply_to: discord.Message | None, interaction: discord.Interaction):
    client_id, client_secret = await ossapi_credentials()
    oss_api = OssapiAsync(client_id, client_secret)

    if reply_to:
        if not await get_beatmap_link_from_message(reply_to):
            raise InvalidArgument(message="Could not get beatmap link from selected message")

    beatmap_link = await get_recent_map(discord_channel_id=str(interaction.channel.id))


    beatmap_id = re.search(r"https://osu\.ppy\.sh/b/(\d+)", beatmap_link, re.IGNORECASE).group(1)

    beatmap = await oss_api.beatmap(beatmap_id=beatmap_id)

    beatmapset = beatmap.beatmapset()

    current_map = f'{beatmapset.artist} - {beatmapset.title} ({beatmapset.creator}) [{beatmap.version}]'
    current_map = await sanitize_filename(current_map)

    download_sites = {
        f'https://beatconnect.io/b/{beatmapset.id}',
        f'https://dl.sayobot.cn/beatmaps/download/novideo/{beatmapset.id}',
        f'https://api.nerinyan.moe/d/{beatmapset.id}?nv=1'
    }

    for site in download_sites:
        if not await aiofiles.ospath.exists(f"data/osu_maps/{current_map}.osu"):
            try:
                await download_and_extract(url=site, file_to_extract=f"data/osu_maps/{current_map}", message= await interaction.original_response())
            except:
                pass
        else:
            break

    beatmap_rosu = rosu.Beatmap(path=f"data/osu_maps/{current_map}.osu")
    mods = None

    acc_increments = [95, 97, 99, 100]
    pp_per_increment = []
    for acc in acc_increments:
        calc_fc = rosu.Performance(
            mods=mods,
            accuracy=acc,
            misses=0,
            combo=beatmap.max_combo,
            ar=beatmap.ar,
            cs=beatmap.cs,
            od=beatmap.accuracy,
            hp=beatmap.drain,
            hitresult_priority=rosu.HitResultPriority.WorstCase
        )

        calc_fc = calc_fc.calculate(beatmap_rosu)

        fc_pp = calc_fc.pp
        pp_per_increment.append(fc_pp)

    pp_per_acc = "\n".join(
        "> " + " | ".join(f"`{acc}% {pp:.2f}pp`" for acc, pp in zip(acc_increments[i:i + 2], pp_per_increment[i:i + 2]))
        for i in range(0, len(acc_increments), 2)
    )

    map_stats = (
        f'`AR: {int(beatmap.ar) if beatmap.ar.is_integer() else round(beatmap.ar, 1)} '
        f'OD: {int(beatmap.accuracy) if beatmap.accuracy.is_integer() else round(beatmap.accuracy, 1)} '
        f'HP: {int(beatmap.drain) if beatmap.drain.is_integer() else round(beatmap.drain, 1)} '
        f'CS: {int(beatmap.cs) if beatmap.cs.is_integer() else round(beatmap.cs, 1)}`')

    beatmap_obj_count = beatmap.count_circles + beatmap.count_sliders + beatmap.count_spinners

    beatmap_length = f"{math.floor(beatmap.total_length / 60)}:{beatmap.total_length % 60}"

    embed = discord.Embed(colour=discord.Colour.orange())

    embed.set_author(name=f'{beatmapset.title} by {beatmapset.creator}', url=beatmap_link)

    description = (f'> Difficulty: `{beatmap.difficulty_rating}★` | Max Combo: `{beatmap.max_combo}x`\n'
                   f'> <:Length:1406065518946942986> `{beatmap_length}` | <:bpm:1387150781093773312> `{round(beatmap.bpm)}` | Objects: `{beatmap_obj_count}`\n'
                   f'> {map_stats}\n'
                   f'{pp_per_acc}')

    embed.add_field(name=f"<:osu_std:1406031929014485003>[{beatmap.version}]", value=description)

    downloads = (f'[osu!direct](https://bathbot.de/osudirect/{beatmapset.id})\n'
                 f'[catboy.best](https://catboy.best/d/{beatmapset.id})\n'
                 f'[osu.direct](https://osu.direct/d/{beatmapset.id})\n'
                 f'[nerinyan.moe](https://api.nerinyan.moe/d/{beatmapset.id})')

    embed.add_field(name=f"Download", value=downloads)


    embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{beatmapset.id}/covers/cover@2x.jpg")

    ranked_date = f": {beatmapset.ranked_date.date()} " if beatmapset.ranked_date else ""

    embed.set_footer(text=f'{beatmap.ranked.name.lower()}{ranked_date} | uploaded: {beatmapset.submitted_date.date()}')


    return embed





async def map_message(interaction: discord.Interaction, reply_to: discord.Message):
    # This works: message is the one you right-clicked / replied to
    await interaction.response.defer()
    message = await interaction.original_response()

    embed = await map_logic(reply_to=reply_to, interaction=interaction)

    await message.edit(embed=embed)


# Create a context menu command
map_context_menu = app_commands.ContextMenu(name="Show Map Data",callback=map_message)




class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="map", description="show map data")
    async def map(self, interaction: discord.Interaction):
        await interaction.response.defer()
        message = await interaction.original_response()

        embed = await map_logic(reply_to=None, interaction=interaction)

        await message.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(Map(bot))
    bot.tree.add_command(map_context_menu)


