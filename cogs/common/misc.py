import os
import asyncio
import aiofiles.os
import discord
from aiofiles import open as aio_open
import json
from typing import Dict
from discord import app_commands
import re
import aiosqlite


class InvalidArgument(app_commands.AppCommandError):
    def __init__(self, message):
        self.message = message
        super().__init__(message)

async def create_folder(folder_name):
    try:
        await asyncio.to_thread(os.makedirs, folder_name, exist_ok=True)
        #print(f"Folder '{folder_name}' created (or already exists).")
    except Exception as e:
        print(f"Error creating folder: {e}")

async def create_file(filename: str, content: str = ""):
    if not os.path.exists(filename):
        async with aio_open(filename, mode='w') as f:
            await f.write(content)
        print(f"File '{filename}' created.")

async def load_json(path: str) -> Dict:
    #Loads the JSON data from file, or returns an empty dict if the file doesn't exist.
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def save_json(path: str, data: Dict) -> None:
    #Saves the JSON data to file.
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


async def ossapi_credentials():
    json_data = await load_json("Credentials.json")
    client_id = json_data["ossapi"][0]["Client_id"]
    client_secret = json_data["ossapi"][0]["Client_secret"]
    return client_id, client_secret

def color_string(string: str, color: str):
    colors = {
        "grey": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "pink": "35",
        "cyan": "36",
        "white": "37"
              }

    color_start = f"\u001b[0;{colors[color]}m"
    color_end = "\u001b[0;0m"
    return f"{color_start}{string}{color_end}"

async def insure_folders_exist() -> None:

    await create_folder('data')
    await create_folder('data/osu_data')
    await create_folder("data/osu_maps")
    await create_folder('data/assets')

async def insure_files_exist() -> None:
    async with aiosqlite.connect("data/osu_data/profiles.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                discord_id TEXT PRIMARY KEY,
                osu_id INTEGER NOT NULL
            )
        """)
        await db.commit()
    async with aiosqlite.connect("data/osu_data/recent_map.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS recent_map (
                discord_channel_id TEXT PRIMARY KEY,
                beatmap_link TEXT NOT NULL,
                mods TEXT Not NULL
            )
        """)
        await db.commit()


async def delete_file(filename: str):
    try:
        await aiofiles.os.remove(filename)
    except Exception as e:
        print(f"Error deleting file {filename}: {e}")


async def sanitize_filename(filename: str) -> str:
    # Remove any character that is not a letter, number, or underscore
    sanitized = re.sub(r"[^a-zA-Z0-9 ()\[\]\-.]", '', filename)
    return sanitized




async def rename_file(current_path: str, new_name: str):
    # Get the directory of the current file
    directory = os.path.dirname(current_path)

    # Await the async sanitization of the new filename
    sanitized_name = await sanitize_filename(new_name)

    # Construct the new file path
    new_path = os.path.join(directory, sanitized_name)

    # Rename the file asynchronously using a thread
    await asyncio.to_thread(os.rename, current_path, new_path)


async def discord_message_to_str(message: discord.message) -> str | None:
    if message is None:
        return

    message_str = message.content

    for embed in message.embeds:
        for value in embed.to_dict().values():
            message_str += str(value)

    if message.attachments:
        for attachment in message.attachments:
            message_str += attachment.url

    return message_str