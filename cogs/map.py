import math
import re
import aiofiles.ospath
import discord
from discord.ext import commands
from discord import app_commands
from .common.osu_data import get_recent_map, set_recent_map, get_beatmap_link_from_message, extract_full_mods, discord_message_to_str, sanitize_mod_string
from .common.misc import ossapi_credentials, InvalidArgument, sanitize_filename
from .common.osu_scores import download_and_extract
from ossapi import OssapiAsync
import rosu_pp_py as rosu


async def map_logic(reply_to: discord.Message | None, interaction: discord.Interaction, user_beatmap_id: int = None, user_mods: str = ""):
    await interaction.response.defer()
    message = await interaction.original_response()

    global calc_fc
    client_id, client_secret = await ossapi_credentials()
    oss_api = OssapiAsync(client_id, client_secret)

    if reply_to:
        if not await get_beatmap_link_from_message(reply_to):
            raise InvalidArgument(message="Could not get beatmap link from selected message")

    recent_map = await get_recent_map(discord_channel_id=str(interaction.channel.id))


    if user_beatmap_id:
        beatmap_link = f"https://osu.ppy.sh/b/{user_beatmap_id}"
    else:
        beatmap_link = recent_map[0]

    mods_str = f"+{user_mods}" if user_mods else ""
    mods = await extract_full_mods(mods_str) if mods_str or user_beatmap_id else recent_map[1]



    beatmap_id = re.search(r"https://osu\.ppy\.sh/b/(\d+)", beatmap_link, re.IGNORECASE).group(1)

    beatmap = await oss_api.beatmap(beatmap_id=beatmap_id)

    if beatmap is None:
        raise InvalidArgument("Could not find beatmap")

    beatmapset = beatmap.beatmapset()



    if reply_to is not None:
        reply_to_str = await discord_message_to_str(reply_to)
        mods = await extract_full_mods(reply_to_str)

    parts = []
    for mod in mods:
        acronym = mod["acronym"]
        settings = mod.get("settings")
        if settings and "speed_change" in settings:
            parts.append(f"{acronym}({settings['speed_change']}x)")
        else:
            parts.append(acronym)

    mods_str = "+" + "".join(parts) if parts else ""

    download_sites = {
        f'https://beatconnect.io/b/{beatmapset.id}',
        f'https://dl.sayobot.cn/beatmaps/download/novideo/{beatmapset.id}',
        f'https://api.nerinyan.moe/d/{beatmapset.id}?nv=1'
    }

    current_map = f'{beatmapset.artist} - {beatmapset.title} ({beatmapset.creator}) [{beatmap.version}]'
    current_map = await sanitize_filename(current_map)
    single_difficulty = f'{beatmapset.artist} - {beatmapset.title} ({beatmapset.creator})'
    single_difficulty = await sanitize_filename(single_difficulty)

    for site in download_sites:
        if await aiofiles.ospath.exists(f"data/osu_maps/{current_map}.osu"):
            break
        if await aiofiles.ospath.exists(f"data/osu_maps/{single_difficulty}.osu"):
            break

        await download_and_extract(url=site, file_to_extract=f"data/osu_maps/{current_map}", message=message)

    if not await aiofiles.ospath.exists(f"data/osu_maps/{current_map}.osu"):
        current_map = single_difficulty

    beatmap_rosu = rosu.Beatmap(path=f"data/osu_maps/{current_map}.osu")

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



    ar = calc_fc.difficulty.ar
    hp = calc_fc.difficulty.hp
    od = -(1 / 6) * calc_fc.difficulty.great_hit_window + (13 + 1 / 3)

    mod_map = {"HR": 1.3, "EZ": 0.5}
    multiplier = next((mod_map[m["acronym"]] for m in mods if m["acronym"] in mod_map), 1)
    cs = beatmap.cs * multiplier

    bpm_map = {"DT": 1.5, "HT": 0.75}
    bpm_multiplier = 1
    for m in mods:
        if m["acronym"] in bpm_map:
            bpm_multiplier = m.get("settings", {}).get("speed_change", bpm_map[m["acronym"]])
            break
    bpm = beatmap.bpm * bpm_multiplier
    beatmap.hit_length = round(beatmap.hit_length / bpm_multiplier)


    map_stats = (
        f'`AR: {int(ar) if ar.is_integer() else round(ar, 1)} '
        f'OD: {int(od) if od.is_integer() else round(od, 1)} '
        f'HP: {int(hp) if hp.is_integer() else round(hp, 1)} '
        f'CS: {int(cs) if cs.is_integer() else round(cs, 1)}`')

    beatmap_obj_count = beatmap.count_circles + beatmap.count_sliders + beatmap.count_spinners

    beatmap_length = f"{math.floor(beatmap.hit_length / 60)}:{beatmap.hit_length % 60:02}"




    embed = discord.Embed(colour=discord.Colour.orange())

    embed.set_author(name=f'{beatmapset.title} by {beatmapset.creator}', url=f"https://osu.ppy.sh/b/{beatmap_id}")

    description = (f'> Difficulty: `{calc_fc.difficulty.stars:.1f}★` | Max Combo: `{beatmap.max_combo}x`\n'
                   f'> <:Length:1406065518946942986> `{beatmap_length}` | <:bpm:1387150781093773312> `{round(bpm)}` | Objects: `{beatmap_obj_count}`\n'
                   f'> {map_stats}\n'
                   f'{pp_per_acc}')

    embed.add_field(name=f"<:osu_std:1406031929014485003>[{beatmap.version}] {mods_str}", value=description)

    downloads = (f'[osu!direct](https://bathbot.de/osudirect/{beatmapset.id})\n'
                 f'[catboy.best](https://catboy.best/d/{beatmapset.id})\n'
                 f'[osu.direct](https://osu.direct/d/{beatmapset.id})\n'
                 f'[nerinyan.moe](https://api.nerinyan.moe/d/{beatmapset.id})')

    embed.add_field(name=f"Download", value=downloads)


    embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{beatmapset.id}/covers/cover@2x.jpg")

    ranked_date = f": {beatmapset.ranked_date.date()} " if beatmapset.ranked_date else ""

    embed.set_footer(text=f'{beatmap.ranked.name.lower()}{ranked_date} | uploaded: {beatmapset.submitted_date.date()}')

    await message.edit(embed=embed)

    await set_recent_map(discord_channel_id=str(interaction.channel.id),
                         beatmap_link=f"https://osu.ppy.sh/b/{beatmap.id}",
                         mods=mods)





async def map_message(interaction: discord.Interaction, reply_to: discord.Message):
    await map_logic(reply_to=reply_to, interaction=interaction)

# Create a context menu command
map_context_menu = app_commands.ContextMenu(name="Show Map Data", callback=map_message)


class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="map", description="show map data")
    async def map(self, interaction: discord.Interaction, beatmap_id: int = None, mods: str = None):
        mods = await sanitize_mod_string(mods or "")

        await map_logic(reply_to=None, interaction=interaction, user_beatmap_id=beatmap_id, user_mods=mods)

async def setup(bot):
    await bot.add_cog(Map(bot))
    bot.tree.add_command(map_context_menu)


