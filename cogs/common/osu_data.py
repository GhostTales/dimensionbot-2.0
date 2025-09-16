import json
import aiosqlite
import discord
from ossapi import OssapiAsync, UserLookupKey
from .misc import InvalidArgument, discord_message_to_str
from typing import Optional, Any
import re
from .osu_mods import mods_list, incompatible_mods

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

        #mods = await extract_full_mods(message_str)
        await set_recent_map(discord_channel_id=str(message.channel.id), beatmap_link=short_url, mods=[])
        return True

async def sanitize_mod_string(input_str: str) -> str:
    s = input_str.upper()
    i = 0
    parsed = []

    # greedy parse: try longest mods first
    while i < len(s):
        match = None
        for length in range(4, 1, -1):  # 4,3,2
            if i + length <= len(s):
                candidate = s[i:i+length]
                if candidate in mods_list:
                    # check for optional speed setting in parentheses e.g. DT(1.2X)
                    if candidate in {"DT","NC","HT","DC"} and i + length < len(s) and s[i+length] == "(":
                        m = re.match(r"\((\d+(\.\d+)?)X\)", s[i+length:], re.IGNORECASE)
                        if m:
                            candidate += m.group(0)  # include the (1.2X)
                            length += len(m.group(0))
                    match = candidate
                    i += length
                    break
        if match:
            parsed.append(match)
        else:
            i += 1  # skip unknown char

    # remove duplicates while preserving order
    seen = set()
    unique_mods = [m for m in parsed if not (m in seen or seen.add(m))]

    # enforce incompatibilities using mod **without settings**
    final_mods = []
    for mod in unique_mods:
        base_mod = re.match(r"^[A-Z0-9]+", mod).group(0)
        if any(re.match(r"^[A-Z0-9]+", f).group(0) in incompatible_mods.get(base_mod, set()) for f in final_mods):
            continue
        final_mods.append(mod)

    return "".join(final_mods)

async def extract_full_mods(s: str) -> list[dict[str, Any]]:

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

