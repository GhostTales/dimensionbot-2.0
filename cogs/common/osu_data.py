import aiosqlite
import discord
from ossapi import OssapiAsync, UserLookupKey
from .misc import InvalidArgument
from typing import Optional

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