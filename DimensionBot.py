import contextlib
import datetime
import json
import os
import random
import shutil
import time
import urllib.request
from PIL import Image
import discord
from discord.ext import tasks, commands
import re

from help_list import commands_info
from osu_commands import osu_stats, linking

def run():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)
    bot.remove_command('help')

    @bot.command()
    async def link(ctx, string=''):
        # Write to JSON with guild id and string as value
        try:
            links = linking(string)
            user = links.user
            # Check if the user is already linked to an account
            with open('osu_links.json', 'r') as file:
                data = json.load(file)
            data[ctx.author.id] = user.id if ctx.author.id in data else user.id
            with open('osu_links.json', 'w') as file:
                json.dump(data, file)

            embed = discord.Embed(description=f'succesfully linked {ctx.author.mention} to {string}',
                                  colour=discord.Colour.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error linking account: {e}")
            await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention} Error linking. Please make sure the account exists.',
                                               colour=discord.Colour.red()))

    @bot.command()
    async def rs(ctx, username=''):
        with open('osu_links.json', 'r') as file:
            data = json.load(file)
        member = ''

        if username == '':
            member = str(ctx.author.id)
            if member in data:
                member = data[member]

        if '<' in username:
            member = username.replace('<', '').replace('@', '').replace('>', '')
            if member in data:
                member = data[member]

        if username != '' and '<' not in username:
            member = linking(username).user.id

        stats = ''


        with open('osu_links.json', 'r') as file:
            data = json.load(file)

        try:
            stats = osu_stats(user=member, play_type='recent', mode='osu')
            play = stats.play
        except Exception as e:
            print(f"An error occurred: {e}")
            play = None

        # print(play)
        # print(stats.MapInfo)
        if play is not None and play != "":

            pp = f'{"{:.2f}".format(stats.stat_pp)}PP ({"{:.2f}".format(stats.stat_fc_pp)}PP if fc)'
            acc = f'{"{:.2f}".format(stats.stat_acc)}% ({"{:.2f}".format(stats.stat_fc_acc)}% if fc)\n'

            if stats.stat_fc_acc == stats.stat_acc:
                pp = f'{"{:.2f}".format(stats.stat_pp)}PP'
                acc = f'{"{:.2f}".format(stats.stat_acc)}% '

            hit = f'[{stats.stat_n300}/{stats.stat_n100}/{stats.stat_n50}/{stats.stat_n_miss}]'
            map_stats = (f'**BPM:** {stats.map_bpm} ▸ **AR:** {"{:.1f}".format(stats.map_ar)} ▸ **OD:** {"{:.1f}".format(stats.map_od)}'
                             f' ▸ **HP:** {"{:.1f}".format(stats.map_hp)} ▸ **CS:** {"{:.1f}".format(stats.map_cs)}')

            if float(stats.stat_map_progress) != 100.0:
                    progress = f'▸ ({"{:.1f}".format(stats.stat_map_progress)}%)'
            else: progress = ''


            recent = discord.Embed(description=f'{progress} ▸ {acc}▸ {pp}\n'
                                                   f'▸ {stats.stat_score} ▸ x{stats.stat_achieved_combo}/{stats.map_max_combo} ▸ {hit}\n'
                                                   f'▸ {map_stats}', colour=discord.Colour.orange())


            # base image location to download from osu map
            base_image_pos = "map_image_card/map_card.png"
            # download map card
            urllib.request.urlretrieve(stats.map_image, base_image_pos)

            ranking_grade_set = "website"

            # open all images for editing
            base_image = Image.open(base_image_pos)
            middle_image = Image.open('map_image_card/rectangle.png')
            top_image = Image.open(f'rank_grades/{ranking_grade_set}/{stats.stat_rank_grade}.png')

            # edit all the images together
            base_image.paste(middle_image.resize((100, 100)), (-30, -65), middle_image.resize((100, 100)))
            base_image.paste(top_image.resize((48, 24)), (10, 0), top_image.resize((48, 24)))

            # save the finished image
            base_image.save(base_image_pos, quality=95)

            # make the saved image a discord.file attachment
            map_card = discord.File(base_image_pos, filename='map_card.png')

            recent.set_image(url='attachment://map_card.png')

            recent.set_footer(icon_url=stats.player_avatar, text=f'{stats.player_name}  |  On osu! Bancho ')
            recent.timestamp = stats.map_date_created

            rank_status = discord.File(f'ranking_status/{stats.map_rank_status}.png', filename=f'{stats.map_rank_status}.png')
            recent.set_author(name=f'{stats.map_title} [{stats.map_diff}] +{stats.stat_mods} [{"{:.2f}".format(stats.stat_stars)}★]',
                                  url=f'https://osu.ppy.sh/beatmapsets/{stats.mapset_id}#osu/{stats.map_id}',
                                  icon_url=f'attachment://{stats.map_rank_status}.png')

            await ctx.send(files=[rank_status, map_card], embed=recent)

        elif play is None and '<' not in username:
            await ctx.send(embed=discord.Embed(description=f'{username} has no recent play data available',
                                               colour=discord.Colour.red()))
        elif play is None and username.replace('<', '').replace('@', '').replace('>', '') in data:
            await ctx.send(embed=discord.Embed(description=f'{username} has no recent play data available',
                                               colour=discord.Colour.red()))
        elif play is None and '<' in username:
            await ctx.send(embed=discord.Embed(description=f'{username} is not linked to an osu account',
                                               colour=discord.Colour.red()))
        elif play is None and str(ctx.author.id) not in data:
            await ctx.send(embed=discord.Embed(description=f'{ctx.author.id} is not linked to an osu account',
                                               colour=discord.Colour.red()))

        else:
            await ctx.send(embed=discord.Embed(description="error contact <@341531784418164738>",
                                                   colour=discord.Colour.red()))

    @bot.command()
    async def roll(ctx, number=100):
        embed = discord.Embed(description=f'{ctx.author.mention} rolled {random.randint(1, number)}',
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
            with open('vc_time.json', 'r') as file:
                user_call_times = json.load(file)
        # Sort the users by time spent in a call and get the top 10
        top_users = sorted(user_call_times.items(), key=lambda x: x[1], reverse=True)[:5]
        title = "**Top 5 in vc:**\n"
        description = ""
        for i, (user_id, time_spent) in enumerate(top_users, start=1):
            hours, remainder = divmod(time_spent, 3600)
            minutes, seconds = divmod(remainder, 60)
            # Use a non-pinging format for user mentions
            description += f"**{i}.**  <@!{user_id}> - {hours}h {minutes}m {seconds}s\n"
        age = int(time.time()) - 1679505465
        hours2, remainder2 = divmod(age, 3600)
        minutes2, seconds2 = divmod(remainder2, 60)
        description += f"**Age of leaderboard:** {hours2}h {minutes2}m {seconds2}s"
        embed = discord.Embed(title=title, description=description, colour=discord.Colour.orange())
        await ctx.send(embed=embed)

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

        greetings = {
            r'\bh+e+l+o+\b': 'Hello! <:scymenHey:1071540827928662037>',
            r'\bh+i+\b': 'Wassup! <:virgin:1064263792386637986>',
            r'\bh+a+i+\b': 'Wassup! <:virgin:1064263792386637986>',
            r'\bh+e+y+\b': 'Hey there! <a:petthepainaway:1062736826617561108>',
            r'\bh+e+y+a+\b': 'Hey there! <a:petthepainaway:1062736826617561108>'
        }

        for greet, response in greetings.items():
            if re.search(greet, message.content, re.IGNORECASE):
                await message.channel.send(response)

        simple_responses = {
            'owo': "*owo what's this?*",
            'uwu': 'uwu'
        }

        for msg, response in simple_responses.items():
            if message.content.lower() == msg:
                await message.channel.send(response)

        pet_emotes = {
            ':petthepainaway:': '<a:petthepainaway:1062736826617561108>',
            ':Petkizu:': '<a:Petkizu:1069555999633059840>',
            ':nedpet:': '<a:nedpet:1069621576930164858>',
            ':Petelle:': '<a:Petelle:1069558979216281682>',
            ':KayPet:': '<a:KayPet:880356602803261462>',
            ':Petrainy:': '<a:Petrainy:1062735394132742205>'
        }

        for emote, response in pet_emotes.items():
            if emote in message.content:
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
                    if user_id in vc_time:
                        vc_time[user_id] += time_spent
                    else:
                        vc_time[user_id] = time_spent
        update_vc_time.start()
        backups_date.start()
        if not os.path.exists('osu_links.json'):
            with open('osu_links.json', 'w') as file:
                file.write('{}')

    @tasks.loop(seconds=1)
    async def update_vc_time():
        for guild in bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    user_id = str(member.id)  # Ensure user_id is a string
                    if user_id not in vc_time:
                        vc_time[user_id] = 1
                    else:
                        vc_time[user_id] += 1
                    milestones = {90000: 25, 180000: 50, 360000: 100,
                                  900000: 250, 1800000: 500, 3600000: 1000,
                                  9000000: 2500, 18000000: 5000, 36000000: 10000}
                    for milestone, hours in milestones.items():
                        if vc_time[user_id] == milestone:
                            channel = bot.get_channel(559826045453205568) # replace with the ID of the "general" channel
                            await channel.send(
                                f"Congratulations! <@!{user_id}> has spent {hours} hours in a voice channel!")
        # Save vc_time to a file
        with open("vc_time.json", "w") as file:
            json.dump(vc_time, file)

    @tasks.loop(minutes=5)
    async def backups_date():
        now = datetime.datetime.now()
        backup_file = f"backups/vc_time_backups/vc_time_{now.strftime('%Y_%m_%d')}.json"
        if not os.path.exists(backup_file) or json.load(open("vc_time.json", "r")) != json.load(open(backup_file, "r")):
            shutil.copy("vc_time.json", backup_file)

    bot.run('MTA5MTA5MDE3NjUwMTA5NjUzMA.G4nuJn.Ud1Mvr44LZqkjDpsiwBR6ZCL4z4pic4AXqHDrQ')


if __name__ == '__main__':
    run()
