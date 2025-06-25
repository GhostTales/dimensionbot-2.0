from .misc import load_json, save_json, InvalidArgument
from typing import Optional


async def search_entry(path: str, discord_id: str) -> bool:
    """Returns True if an entry for the given Discord ID exists in the JSON file."""
    data = await load_json(path)
    return discord_id in data

async def add_entry(path: str, discord_id: str) -> None:
    """Adds a new empty entry for a Discord ID in the JSON file."""
    data = await load_json(path)

    if discord_id in data:
        raise InvalidArgument(f"Entry for {discord_id} already exists.")


    data[discord_id] = {
        "link": None,
        "tablet": None,
        "tablet_area": None,
        "keyboard": None,
        "mouse": None
    }

    await save_json(path, data)
    print(f"Added new entry for {discord_id} in {path}")

async def edit_entry(path: str,
                     discord_id: str,
                     link: Optional[int] = None,
                     tablet: Optional[str] = None,
                     tablet_area: Optional[str] = None,
                     keyboard: Optional[str] = None,
                     mouse: Optional[str] = None) -> None:
    """Edits an existing entry in the JSON file for the given Discord ID."""
    data = await load_json(path)

    if discord_id not in data:
        raise InvalidArgument(f"No entry found for {discord_id}")

    if link is not None:
        data[discord_id]["link"] = link
    if tablet is not None:
        data[discord_id]["tablet"] = tablet
    if tablet_area is not None and isinstance(tablet_area, list) and len(tablet_area) == 2:
        data[discord_id]["tablet_area"] = tablet_area
    if keyboard is not None:
        data[discord_id]["keyboard"] = keyboard
    if mouse is not None:
        data[discord_id]["mouse"] = mouse

    await save_json(path, data)
    print(f"Updated entry for {discord_id} in {path}")

async def get_entry(path: str, discord_id: str) -> Optional[dict]:
    """Returns the entry data for a given Discord ID, or None if it doesn't exist."""
    data = await load_json(path)
    return data.get(discord_id)
