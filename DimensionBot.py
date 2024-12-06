import contextlib
import datetime
import asyncio
import glob
import rosu_pp_py as rosu
import aiofiles
import json
import oppadc
import os
import random
import shutil
import time
import urllib.request
from PIL import Image
import discord
from discord.ext import tasks, commands
import re
from ossapi import OssapiAsync, UserLookupKey

from osu_commands import calculate_accuracy, mod_values, download_and_extract, mod_math
from help_list import commands_info
from capture_svg_frames import capture_svg_frames
from create_gif import create_gif



intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

#osu api credentials
with open("Credentials.json") as json_file:
    json_data = json.load(json_file)
    client_id = json_data["ossapi"][0]["Client_id"]
    client_secret = json_data["ossapi"][0]["Client_secret"]
    oss_api = OssapiAsync(client_id, client_secret)

@bot.command()
async def link(ctx, string=''):
    # Write to JSON with guild id and string as value
    if string == '':
        await ctx.send(
            embed=discord.Embed(description=f'{ctx.author.mention} Error linking. Please make sure to insert a username.',
                                colour=discord.Colour.red()))
    else:
        try:
            user = await oss_api.user(string, key=UserLookupKey.USERNAME)

            async with aiofiles.open('osu_links.json', mode='r+') as file:
                # Read the file content
                content = await file.read()
                data = json.loads(content)

                # Update the data
                data[str(ctx.author.id)] = user.id

                # Move to the beginning of the file and write updated content
                await file.seek(0)
                await file.write(json.dumps(data, indent=4))
                await file.truncate()  # Ensure the file is truncated if the new data is shorter


            embed = discord.Embed(description=f'succesfully linked {ctx.author.mention} to {string}',
                                  colour=discord.Colour.orange())
            await ctx.send(embed=embed)


        except Exception as e:
            print(f"Error linking account: {e}")
            await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention} Error linking. Please make sure the account exists.',
                                               colour=discord.Colour.red()))


async def get_member(ctx, username, data_file='osu_links.json'):
    async with aiofiles.open(data_file, 'r') as file:
        content = await file.read()
        data = json.loads(content)

    member = ''

    if username == '':
        member = str(ctx.author.id)
        if member in data:
            member = data[member]

    elif '<' in username:
        member = username.replace('<@', '').replace('>', '')
        if member in data:
            member = data[member]

    elif username != '' and '<' not in username:
        user = await oss_api.user(username, key=UserLookupKey.USERNAME)
        member = user.id

    return member

@bot.command()
async def osu(ctx, username=''):
    member = await get_member(ctx=ctx, username=username)
    user = await oss_api.user(member, key=UserLookupKey.ID)
    username = user.username

    user_directory = f"downloaded_svgs/{user.id}"
    os.makedirs(user_directory, exist_ok=True)

    message = await ctx.send(
        embed=discord.Embed(
            description=f'generating profile for {username}',
            colour=discord.Colour.red()
        )
    )


    ## https://osu-sig.vercel.app/card?user={username}&mode=std&lang=en&blur=5&round_avatar=true&animation=true&hue=218&w=1100&h=640

    card_url = f'https://osu-sig.vercel.app/card?user={username}&mode=std&lang=en&blur=1&round_avatar=true&animation=true&hue=218&w=1100&h=640'
    await capture_svg_frames(card_url, output_dir=f"{user_directory}/frames")

    png_folder = f"{user_directory}/frames/"
    output_gif = f"{user_directory}/outputGif/"

    create_gif(png_folder, output_gif, fps=24, num_interpolated_frames=0)

    gif = discord.File(f"{output_gif}/output.gif", filename="output.gif")


    await message.edit(embed=None, attachments=[gif])


    await asyncio.sleep(1.9)
    image = discord.File(f"{user_directory}/frames/frame_30.png", filename="frame_30.png")


    await message.edit(attachments=[image])

    shutil.rmtree(user_directory)


@bot.command()
async def rs(ctx, username=''):
    member = await get_member(ctx=ctx, username=username)

    with open('osu_links.json', 'r') as file:
        data = json.load(file)

    try:
        user_scores = await oss_api.user_scores(user_id=member, type='recent', include_fails=True, mode='osu', limit=1)
        if user_scores:
            play = user_scores[0]
        else:
            play = None

        print(play)


    except Exception as e:
        print(f"An error occurred: {e}")
        play = None

        if '<' not in username or str(ctx.author.id) in data:
            await ctx.send(embed=discord.Embed(description=f'{username} has no recent play data available', colour=discord.Colour.red()))

        elif '<' in username and str(ctx.author.id) not in data:
            await ctx.send(embed=discord.Embed(description=f'{username} is not linked to an osu account', colour=discord.Colour.red()))

        else:
            await ctx.send(
                embed=discord.Embed(description="error contact <@341531784418164738>", colour=discord.Colour.red()))

    if play is not None and play != "":

        play.accuracy *= 100
        beatmap = play.beatmap
        beatmapset = await beatmap.beatmapset()
        n50 = play.statistics.meh or 0
        n100 = play.statistics.ok or 0
        n300 = play.statistics.great or 0
        nmiss = play.statistics.miss or 0

        stats = {
            'great': play.statistics.great,
            'ok': play.statistics.ok,
            'meh': play.statistics.meh,
            'miss': play.statistics.miss,
            'slider_tail_hit': play.statistics.slider_tail_hit,
            'large_tick_hit': play.statistics.large_tick_hit,
            'large_tick_miss': play.statistics.large_tick_miss
        }
        try:
            stats.update({'slider_tail_miss': play.maximum_statistics['slider_tail_hit'] - play.statistics.slider_tail_hit})
        except:
            print("stable_score")

        calculated_acc = await calculate_accuracy(
            max_stats=play.maximum_statistics,
            stats=stats,
            full_combo=False,
            passed=play.passed
        )

        calculated_fc_acc = await calculate_accuracy(
            max_stats=play.maximum_statistics,
            stats=stats,
            full_combo=True,
            passed=play.passed
        )

        os.makedirs('map_files', exist_ok=True)
        # Remove only files ending in .osz instead of the entire folder
        osu_files = glob.glob('map_files/*.osz')
        for file in osu_files:
            os.remove(file)

        async def sanitize_filename(filename: str) -> str:
            # Remove any character that is not a letter, number, or underscore
            sanitized = re.sub(r"[^a-zA-Z0-9 ()\[\]\-.]", '', filename)
            return sanitized



        current_map = f'{beatmapset.artist} - {beatmapset.title} ({beatmapset.creator}) [{beatmap.version}].osu'
        current_map = await sanitize_filename(current_map)


        async def async_exists(path):
            return await asyncio.to_thread(os.path.exists, path)

        download_sites = {
            f'https://beatconnect.io/b/{beatmapset.id}',
            f'https://dl.sayobot.cn/beatmaps/download/novideo/{beatmapset.id}',
            f'https://api.nerinyan.moe/d/{beatmapset.id}?nv=1'
        }

        map_extract = ''

        if await async_exists(f"map_files/{current_map}"):
            map_extract = current_map

        if not await async_exists(f"map_files/{current_map}"):
            downloading = await ctx.send(embed=discord.Embed(description=f'Downloading map', colour=discord.Colour.red()))
            for site in download_sites:
                try:
                    map_extract = await asyncio.to_thread(download_and_extract, site, current_map)
                except Exception as e:
                    print(f"An error occurred: {e}")
                if await async_exists(f"map_files/{current_map}"):
                    break
            await downloading.delete()


        settings = {}
        mods_str = "No Mod"

        if play.mods != []:
            mods_str = ""
            for i in range(len(play.mods)):
                mods_str += play.mods[len(play.mods) - i - 1].acronym
                if play.mods[0].settings is not None:
                    settings.update(play.mods[len(play.mods) - i - 1].settings)
            if settings.get("speed_change"):
                mods_str += f" ({settings.get('speed_change')}x)"


        beatmap = mod_math(mods_str, beatmap, settings)

        map = rosu.Beatmap(path=f'map_files/{map_extract}')

        mods = [{"acronym": mod.acronym, "settings": mod.settings} if hasattr(mod, "settings") else {"acronym": mod.acronym} for mod in play.mods]

        if play.pp == None:
            calc = rosu.Performance(
                mods=mods,
                accuracy=play.accuracy,
                n300=n300,
                n100=n100,
                n50=n50,
                misses=nmiss,
                combo=play.max_combo,
                ar=beatmap.ar,
                cs=beatmap.cs,
                od=beatmap.accuracy,
                hp=beatmap.drain,
            )

            calc = calc.calculate(map)
            play.pp = calc.pp

        calc_fc = rosu.Performance(
            mods=mods,
            accuracy=play.accuracy,
            n300=(play.maximum_statistics['great'] - n100 - n50),
            n100=n100,
            n50=n50,
            misses=0,
            combo=beatmap.max_combo,
            ar=beatmap.ar,
            cs=beatmap.cs,
            od=beatmap.accuracy,
            hp=beatmap.drain
            )

        calc_fc = calc_fc.calculate(map)

        fc_pp = calc_fc.pp
        play.beatmap.difficulty_rating = calc_fc.difficulty.stars
        beatmap.max_combo = calc_fc.difficulty.max_combo


        if calculated_fc_acc == calculated_acc and (play.statistics.large_tick_miss or 0) <= 0:
            pp = f'**{"{:.2f}".format(play.pp)}PP**'
            acc = f'{"{:.2f}".format(play.accuracy)}% '
        else:
            pp = f'**{"{:.2f}".format(play.pp)}PP** ({"{:.2f}".format(fc_pp)}PP if fc)'
            acc = f'{"{:.2f}".format(play.accuracy)}% ({"{:.2f}".format(calculated_fc_acc)}% if fc)\n'

        hit = f'[{n300}/{n100}/{n50}/{nmiss}]'
        map_stats = (f'**BPM:** {round(beatmap.bpm)} ▸ **AR:** {"{:.1f}".format(beatmap.ar)} ▸ **OD:** {"{:.1f}".format(beatmap.accuracy)}'
                             f' ▸ **HP:** {"{:.1f}".format(beatmap.drain)} ▸ **CS:** {"{:.1f}".format(beatmap.cs)}')

        beatmap_obj_count = beatmap.count_circles + beatmap.count_sliders + beatmap.count_spinners
        map_progress = 100 * (n300 + n100 + n50 + nmiss) / beatmap_obj_count
        if float(map_progress) != 100.0:
                progress = f'▸ ({"{:.1f}".format(map_progress)}%)'
        else: progress = ''



        recent = discord.Embed(description=f'{progress} ▸ {acc}▸ {pp}\n'
                            f'▸ {play.total_score} ▸ x{play.max_combo}/{beatmap.max_combo} ▸ {hit}\n'
                            f'▸ {map_stats}', colour=discord.Colour.orange())


        # base image location to download from osu map
        base_image_pos = f"map_image_card/map_{beatmap.id}_card.png"
        # download map card
        urllib.request.urlretrieve(beatmapset.covers.card, base_image_pos)

        ranking_grade_set = "website"

        # open all images for editing
        base_image = Image.open(base_image_pos)
        middle_image = Image.open('map_image_card/rectangle.png')
        top_image = Image.open(f'rank_grades/{ranking_grade_set}/{play.rank}.png')

        # edit all the images together
        base_image.paste(middle_image.resize((100, 100)), (-30, -65), middle_image.resize((100, 100)))
        base_image.paste(top_image.resize((48, 24)), (10, 0), top_image.resize((48, 24)))

        # save the finished image
        base_image.save(base_image_pos, quality=95)

        # make the saved image a discord.file attachment
        map_card = discord.File(base_image_pos, filename=f'map_{beatmap.id}_card.png')

        recent.set_image(url=f'attachment://map_{beatmap.id}_card.png')

        recent.set_footer(icon_url=play._user.avatar_url, text=f'{play._user.username}  |  On osu! Bancho ')
        recent.timestamp = play.ended_at

        rank_status = discord.File(f'ranking_status/{beatmap.status}.png', filename=f'{beatmap.status}.png')

        recent.set_author(name=f'{beatmapset.title} [{beatmap.version}] +{mods_str} [{"{:.2f}".format(beatmap.difficulty_rating)}★]',
                                  url=f'https://osu.ppy.sh/beatmapsets/{beatmapset.id}#osu/{beatmap.id}',
                                  icon_url=f'attachment://{beatmap.status}.png')

        await ctx.send(files=[rank_status, map_card], embed=recent)
        os.remove(base_image_pos)


@bot.command()
async def roll(ctx, number=100):
    if number == 0:
        number = 100
    embed = discord.Embed(description=f'{ctx.author.mention} rolled {random.randint(1, abs(number))}',
                              colour=discord.Colour.orange())
    await ctx.send(embed=embed)

@roll.error
async def roll_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        embed = discord.Embed(description=f'{ctx.author.mention} rolled {random.randint(1, 100)}',
                                  colour=discord.Colour.orange())
        await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    # Load user call times from the JSON file
    with contextlib.suppress(FileNotFoundError):
        async with aiofiles.open('vc_time.json', 'r') as file:
            content = await file.read()
            user_call_times = json.loads(content)

    # Sort the users by time spent in a call and get the top 10
    top_users = sorted(user_call_times.items(), key=lambda x: x[1], reverse=True)[:5]

    title = "**Top 5 in vc:**\n"
    description = ""
    for i, (user_id, time_spent) in enumerate(top_users, start=1):
        hours, remainder = divmod(time_spent, 3600)
        minutes, seconds = divmod(remainder, 60)
        # Use a non-pinging format for user mentions
        description += f"**{i}.**  <@!{user_id}> - {hours}h {minutes}m\n"

    age = int(time.time()) - 1679505465
    hours2, remainder2 = divmod(age, 3600)
    minutes2, seconds2 = divmod(remainder2, 60)
    description += f"**Age of leaderboard:** {hours2}h {minutes2}m"

    await ctx.send(embed=discord.Embed(title=title, description=description, colour=discord.Colour.orange()))

@bot.command()
async def area(ctx, min, max, ratio):
    ratio = re.sub(r",", ".", ratio)
    description = ""
    perfect = False

    for i in range(int(min), int(max) + 1):
        if i / float(ratio) == int(i / float(ratio)) and float(ratio) != 1.0:
            description += f"{i} x {i / float(ratio)}\n"
            perfect = True

    if not perfect:
        description = "no perfect values"
        if float(ratio) == 1:
            description = "ratio cannot be 1 to avoid spam"

    embed = discord.Embed(
        description=f"{ctx.author.mention} \nyour width values are: \nmin={min} | max={max} | ratio={ratio} \n\n{description}",
        colour=discord.Colour.orange())
    await ctx.send(embed=embed)

@area.error
async def area_error(ctx, min, max, ratio):
    global embed
    if isinstance(min, commands.BadArgument):
        embed = discord.Embed(description="Please input valid min value", colour=discord.Colour.orange())
    elif isinstance(max, commands.BadArgument):
        embed = discord.Embed(description="Please input valid max value", colour=discord.Colour.orange())
    elif isinstance(ratio, commands.BadArgument):
        embed = discord.Embed(description="Please input valid ratio value", colour=discord.Colour.orange())
        await ctx.send(embed=embed)


@bot.command()
async def help(ctx, command=None):
    embed = discord.Embed(title='Help list', colour=discord.Colour.orange())

    if command is None:
        for cmd_info in commands_info:
            embed.add_field(name=cmd_info["name"], value=cmd_info["description"], inline=False)
    elif command.lower() == "commands":
        # Display a list of all available commands
        for cmd_info in commands_info:
            embed.add_field(name=cmd_info["name"], value="", inline=False)
    else:
        cmd_info = next((info for info in commands_info if info["name"].replace('!','').lower() == command), None)
        if cmd_info:
            embed.add_field(name=cmd_info["name"], value=cmd_info["description"], inline=False)
        else:
            embed.add_field(name="Command not found", value="The specified command is not recognized.",
                                inline=False)

    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    print(f'{message.author}: {message.content} | {message.channel}')
    if message.author.id == bot.user.id:
        return

    greetings = [
            r'\bh+e+l+o+\b',
            r'\bh+i+\b',
            r'\bh+a+i+\b',
            r'\bh+e+y+\b',
            r'\bh+e+y+a+\b',
            r'\bw+a+s+u+p+\b'
    ]

    responses = [
            'Hello! <:scymenHey:1071540827928662037>',
            'Wassup! <:virgin:1064263792386637986>',
            'Hey there! <a:petthepainaway:1062736826617561108>',
            'Hai! <:scymenQt:1243537644932042832>',
            'Heya! <:scymenFloosh:1260070773243248732>'

    ]

    for greet in greetings:
        if re.search(greet, message.content, re.IGNORECASE):
            await message.channel.send(responses[random.randint(0, len(responses) - 1)])

    simple_responses = {
            'owo': "*owo what's this?*",
            'uwu': 'uwu'
    }

    for msg, response in simple_responses.items():
        if msg in message.content.lower():
            await message.channel.send(response)

    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload):
    message_id = payload.message_id
    if message_id == 1080112222249943130:  # message id
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g: g.id == guild_id, bot.guilds)

        # roles and emote names from gt test server
        if payload.emoji.name == '💜':  # reaction emote name
            role = discord.utils.get(
                guild.roles, name='stream ping')  # role name
        elif payload.emoji.name == '🧒':
            role = discord.utils.get(guild.roles, name='Child')
        elif payload.emoji.name == '👴':
            role = discord.utils.get(guild.roles, name='18+')
        else:
            role = discord.utils.get(guild.roles, name=payload.emoji.name)

        if role is not None:
            member = await guild.fetch_member(payload.user_id)
            if member is not None:
                await member.add_roles(role)
                print(f'{member} got role: {role}')
            else:
                print('member not found')
        else:
            print(f'role: {role} not found')
            print(payload.emoji.name)
@bot.event
async def on_raw_reaction_remove(payload):
    message_id = payload.message_id
    if message_id == 1080112222249943130:  # message id
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g: g.id == guild_id, bot.guilds)

        # roles and emote names from gt test server
        if payload.emoji.name == '💜':  # reaction emote name
            role = discord.utils.get(
                guild.roles, name='stream ping')  # role name
        elif payload.emoji.name == '🧒':
            role = discord.utils.get(guild.roles, name='Child')
        elif payload.emoji.name == '👴':
            role = discord.utils.get(guild.roles, name='18+')
        else:
            role = discord.utils.get(guild.roles, name=payload.emoji.name)

        if role is not None:
            member = await guild.fetch_member(payload.user_id)
            if member is not None:
                await member.remove_roles(role)
                print(f'{member} lost role: {role}')
            else:
                print('member not found')
        else:
            print(f'role: {role} not found')

# Dictionary to store user_id as key and time spent in vc as value
vc_time = {}
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await bot.change_presence(status=discord.Status.do_not_disturb , activity=discord.Game('!help'))
    # Load vc_time from the file if it exists
    with contextlib.suppress(FileNotFoundError):
        with open("vc_time.json", "r") as file:
            loaded_data = json.load(file)
            for user_id, time_spent in loaded_data.items():
                user_id = str(user_id)  # Ensure user_id is a string
                vc_time[user_id] = time_spent

    update_vc_time.start()
    backups_date.start()
    if not os.path.exists('osu_links.json'):
        with open('osu_links.json', 'w') as file:
            file.write('{}')

@tasks.loop(minutes=1)
async def update_vc_time():
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            for member in vc.members:
                if member.bot:
                    continue
                user_id = str(member.id)  # Ensure user_id is a string
                if user_id not in vc_time:
                    vc_time[user_id] = 60
                else:
                    vc_time[user_id] += 60
                milestones = {90000: 25, 180000: 50, 360000: 100,
                                  900000: 250, 1800000: 500, 3600000: 1000,
                                  9000000: 2500, 18000000: 5000, 36000000: 10000}
                for milestone, hours in milestones.items():
                    if vc_time[user_id] == milestone:
                        channel_id = 931084168098623492 # default to test server

                        for guild in bot.guilds:
                            for channel in guild.channels:
                                if channel.name.lower() == "general" and channel.type.name == "text":
                                    if channel.guild.name == guild.name:
                                        for vc in guild.voice_channels:
                                            for member in vc.members:
                                                if member.id == user_id:
                                                    #print(channel.id, channel.name, channel.guild.name)
                                                    channel_id = channel.id

                        await bot.get_channel(channel_id).send(f"Congratulations! <@!{user_id}> has spent {hours} hours in a voice channel!")


    # Save vc_time to a file
    async with aiofiles.open("vc_time.json", "w") as file:
        await file.write(json.dumps(vc_time, indent=4))


@tasks.loop(minutes=5)
async def backups_date():
    now = datetime.datetime.now()
    backup_file = f"backups/vc_time_backups/vc_time_{now.strftime('%Y_%m_%d')}.json"

    # Use a thread pool for blocking operations like os.path.exists
    loop = asyncio.get_event_loop()
    backup_exists = await loop.run_in_executor(None, os.path.exists, backup_file)

    if not backup_exists:
        should_backup = True
    else:
        async with aiofiles.open("vc_time.json", "r") as vc_file, aiofiles.open(backup_file, "r") as backup_file_obj:
            vc_data = json.loads(await vc_file.read())
            backup_data = json.loads(await backup_file_obj.read())
            should_backup = vc_data != backup_data

    if should_backup:
        # Use a thread pool for shutil.copy since it's a blocking operation
        await loop.run_in_executor(None, shutil.copy, "vc_time.json", backup_file)


with open("Credentials.json") as json_file:
    json_data = json.load(json_file)
    token = json_data["Credentials"][0]["Token"]


bot.run(token)
