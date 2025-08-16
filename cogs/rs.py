import aiofiles.ospath
import discord
from discord.ext import commands
from discord import app_commands
from .common.misc import ossapi_credentials, InvalidArgument, sanitize_filename
from .common.osu_scores import calculate_accuracy, download_and_extract
from .common.osu_data import resolve_osu_user, set_recent_map
from ossapi import OssapiAsync
import rosu_pp_py as rosu


class Rs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rs", description="Shows recent osu score")
    async def rs(self, interaction: discord.Interaction, username: str = ""):
        await interaction.response.defer()
        message = await interaction.original_response()

        client_id, client_secret = await ossapi_credentials()
        oss_api = OssapiAsync(client_id, client_secret)

        user = await resolve_osu_user(username=username, interaction=interaction, oss_api=oss_api)

        user_score = await oss_api.user_scores(user_id=user.id, type='recent', include_fails=True, mode='osu', limit=1)

        try:
            play = user_score[0]
        except:
            raise InvalidArgument(f"No recent plays for user {user.username}")

        #print(play)

        play.accuracy *= 100
        beatmap = play.beatmap
        beatmapset = await beatmap.beatmapset()
        n50 = play.statistics.meh or 0
        n100 = play.statistics.ok or 0
        n300 = play.statistics.great or 0
        nmiss = play.statistics.miss or 0

        stats = {
            'great': n300,
            'ok': n100,
            'meh': n50,
            'miss': nmiss,
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
            passed=play.passed
        )

        calculated_fc_acc = await calculate_accuracy(
            max_stats=play.maximum_statistics,
            stats=stats,
            full_combo=True,
            passed=play.passed
        )

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
                    await download_and_extract(url=site, file_to_extract=f"data/osu_maps/{current_map}", message=message)
                except:
                    pass
            else:
                break

        mods_str = ""
        if play.mods:
            mods_str = " +"
            for mod in reversed(play.mods):
                acronym = mod.acronym
                if mod.settings and "speed_change" in mod.settings:
                    acronym += f"({mod.settings['speed_change']}x)"
                mods_str += acronym

        beatmap_rosu = rosu.Beatmap(path=f"data/osu_maps/{current_map}.osu")

        mods = [
            {"acronym": mod.acronym, "settings": mod.settings} if hasattr(mod, "settings") and mod.settings is not None else {"acronym": mod.acronym}
            for mod in play.mods]

        for m in mods:
            if m["acronym"] == "DA":
                settings = m.get("settings", {})
                beatmap.ar = settings.get("approach_rate", beatmap.ar)
                beatmap.drain = settings.get("drain_rate", beatmap.drain)
                beatmap.accuracy = settings.get("overall_difficulty", beatmap.accuracy)
                beatmap.cs = settings.get("circle_size", beatmap.cs)
                break


        if play.pp is None:
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
                hitresult_priority=rosu.HitResultPriority.WorstCase
            )
            calc = calc.calculate(beatmap_rosu)
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
            hp=beatmap.drain,
            hitresult_priority=rosu.HitResultPriority.WorstCase
        )

        calc_fc = calc_fc.calculate(beatmap_rosu)

        fc_pp = calc_fc.pp
        # star rating with mods
        play.beatmap.difficulty_rating = calc_fc.difficulty.stars
        # max combo is none if not here
        beatmap.max_combo = calc_fc.difficulty.max_combo

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

        if calculated_fc_acc == calculated_acc and (play.statistics.large_tick_miss or 0) <= 0 and play.rank.value != "F":
            pp_acc = f'**{"{:.2f}".format(play.pp)}PP** | {"{:.2f}".format(play.accuracy)}%'
        else:
            pp_acc = f'**{"{:.2f}".format(play.pp)}PP** ({"{:.2f}".format(fc_pp)}PP for {"{:.2f}".format(calculated_fc_acc)}% fc) {"{:.2f}".format(play.accuracy)}%'

        map_stats = (
            f'<:bpm:1387150781093773312> `{round(bpm)}` | '
            f'`AR: {int(ar) if ar.is_integer() else round(ar, 1)} '
            f'OD: {int(od) if od.is_integer() else round(od, 1)} '
            f'HP: {int(hp) if hp.is_integer() else round(hp, 1)} '
            f'CS: {int(cs) if cs.is_integer() else round(cs, 1)}`')

        beatmap_obj_count = beatmap.count_circles + beatmap.count_sliders + beatmap.count_spinners
        map_progress = 100 * (n300 + n100 + n50 + nmiss) / beatmap_obj_count

        progress = ''
        if float(map_progress) != 100.0:
            progress = f'({"{:.1f}".format(map_progress)}%) | '

        rank_grade = {
                "F":"<:GradeF:1387520871576371230>",
                "D":"<:GradeD:1387520868074262782>",
                "C":"<:GradeC:1387520864328749260>",
                "B":"<:GradeB:1387520860021067836>",
                "A":"<:GradeA:1387520854769926277>",
                "S":"<:GradeS:1387520877754716240>",
                "SH":"<:GradeSH:1387520881487642756>",
                "X":"<:GradeSS:1387520883186208778>",
                "XH":"<:GradeSSH:1387520886315421849>"
            }

        hit = f'[{n300}/{n100}/{n50}/{nmiss}]'

        description = (f'> {rank_grade[play.rank.value]} {progress}{pp_acc}\n '
                       f'> -# <:sliders:1387187521175158914> `{play.total_score}` | `{play.max_combo}x`**/**`{beatmap.max_combo}x` | `{hit}`\n'
                       f'> -# {map_stats}')

        embed = discord.Embed(description=description, colour=discord.Colour.orange())
        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{beatmapset.id}/covers/cover@2x.jpg")

        embed.set_footer(icon_url=play.user().avatar_url, text=f'{play.user().username}  |  On osu! Bancho ')

        embed.timestamp = play.ended_at

        rank_status = discord.File(f'data/assets/ranking_status/{beatmap.status}.png', filename=f'{beatmap.status}.png')

        embed.set_author(
            name=f'{beatmapset.title} [{beatmap.version}]{mods_str} [{"{:.2f}".format(beatmap.difficulty_rating)}★]',
            url=f'https://osu.ppy.sh/beatmapsets/{beatmapset.id}#osu/{beatmap.id}',
            icon_url=f'attachment://{beatmap.status}.png')

        await message.edit(embed=embed, attachments=[rank_status])
        await set_recent_map(discord_channel_id=str(interaction.channel.id), beatmap_link=f"https://osu.ppy.sh/b/{beatmapset.id}")

async def setup(bot):
    await bot.add_cog(Rs(bot))
