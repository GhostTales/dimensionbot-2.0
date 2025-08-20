import json
import aiosqlite
import discord
from ossapi import OssapiAsync, UserLookupKey
from .misc import InvalidArgument, discord_message_to_str
from typing import Optional, Any
import re

async def get_osu_id(discord_id: str) -> int | None:
    async with aiosqlite.connect("data/osu_data/profiles.db") as db:
        async with db.execute("SELECT osu_id FROM profiles WHERE discord_id = ?", (discord_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def save_profile(discord_id: str, osu_id: int) -> None:
    async with aiosqlite.connect("data/osu_data/profiles.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO profiles (discord_id, osu_id) VALUES (?, ?)",
            (discord_id, osu_id)
        )
        await db.commit()

async def set_recent_map(discord_channel_id: str, beatmap_link: str, mods: list[dict[str, Any]]) -> None:
    async with aiosqlite.connect("data/osu_data/recent_map.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO recent_map (discord_channel_id, beatmap_link, mods) VALUES (?, ?, ?)",
            (discord_channel_id, beatmap_link, json.dumps(mods))
        )
        await db.commit()

async def get_recent_map(discord_channel_id: str) -> tuple[str, list[dict[str, Any]]] | None:
    async with aiosqlite.connect("data/osu_data/recent_map.db") as db:
        async with db.execute("SELECT beatmap_link, mods FROM recent_map WHERE discord_channel_id = ?", (discord_channel_id,)) as cursor:
            row = await cursor.fetchone()
            return (row[0], json.loads(row[1])) if row else None

async def resolve_osu_user(username: Optional[str], interaction: discord.Interaction, oss_api: OssapiAsync):
    discord_id = None
    osu_id = None

    # 1. Handle mention input
    if username and "<@" in username:
        discord_id = username.strip("<@!>")

    # 2. No username — default to command user
    elif not username:
        discord_id = str(interaction.user.id)

    # 3. If discord_id was extracted or inferred, try DB lookup
    if discord_id:
        osu_id = await get_osu_id(discord_id)
        if not osu_id:
            raise InvalidArgument(f"User <@{discord_id}> has not been linked to an osu account")

    # 4. Fetch osu! user via ID or username
    try:
        if osu_id:
            return await oss_api.user(osu_id, key=UserLookupKey.ID)
        else:
            return await oss_api.user(username, key=UserLookupKey.USERNAME)
    except Exception:
        raise InvalidArgument(f'It seems the osu account "{username or discord_id}" does not exist')

async def get_beatmap_link_from_message(message: discord.message) -> False:
    message_str = await discord_message_to_str(message)

    beatmapset_pattern = r"https://osu\.ppy\.sh/beatmapsets/\d+#\w+/(\d+)|https://osu\.ppy\.sh/b/(\d+)|/\d+-(\d+)-\d+\.png"
    match = re.search(beatmapset_pattern, message_str, re.IGNORECASE)
    if match:
        beatmap_id = match.group(1) or match.group(2) or match.group(3) or match.group(4)
        short_url = f"https://osu.ppy.sh/b/{beatmap_id}"
        #print(message.channel.id, short_url)

        mods = await extract_full_mods(message_str)
        await set_recent_map(discord_channel_id=str(message.channel.id), beatmap_link=short_url, mods=mods)
        return True


import re
from typing import Any

async def extract_full_mods(s: str) -> list[dict[str, Any]]:
    mods_list = [
        "EZ","NF","HT","DC","NR",
        "HR","SD","PF","DT","NC","FI","HD","CO","FL","BL","ST","AC",
        "AT","CN","RX","AP","SO",
        "TP","DA","CL","RD","MR","AL","SW","SG","IN","CS","HO","1K","2K","3K","4K","5K","6K","7K","8K","9K","10K",
        "TR","WG","SI","GR","DF","WU","WD","TC","BR","AD","FF","MU","NS","MG","RP","AS","FR","BU","SY","DP","BM",
        "SV2","TD"
    ]

    mods_sorted = sorted(mods_list, key=len, reverse=True)
    mods_pattern = "|".join(mods_sorted)

    # Match individual mods optionally followed by (x), all starting with +
    # Example: +DT(2x)HR -> matches DT(2x) and HR separately
    regex = re.compile(rf"\+(({mods_pattern})(?:\(([\d.]+)X\))?)+")
    matches = regex.finditer(s.upper())

    mods_data: list[dict[str, Any]] = []

    for match in matches:
        # Extract each individual mod with optional speed
        inner_text = match.group(0)[1:]  # remove leading '+'
        i = 0
        while i < len(inner_text):
            for m in mods_sorted:
                if inner_text.startswith(m, i):
                    mod = m
                    i += len(m)
                    # Check if there's a (x) right after this mod
                    speed_match = re.match(r"\(([\d.]+)X\)", inner_text[i:])
                    if speed_match and mod in {"DT", "NC", "HT", "DC"}:
                        mods_data.append({
                            "acronym": mod,
                            "settings": {"speed_change": float(speed_match.group(1))}
                        })
                        i += len(speed_match.group(0))
                    else:
                        mods_data.append({"acronym": mod})
                    break
            else:
                i += 1  # fallback

    return mods_data

