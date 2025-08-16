import tempfile
import aiofiles.ospath
import discord
from discord.ext import commands
from discord import app_commands
from .common.misc import ossapi_credentials, InvalidArgument, delete_file, sanitize_filename
from .common.osu_scores import calculate_accuracy, download_and_extract
from .common.osu_data import resolve_osu_user, set_recent_map
from ossapi import OssapiAsync
import rosu_pp_py as rosu
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
import aiofiles
from pathlib import Path

class Rs_fancy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rs-fancy", description="Shows recent osu score")
    async def rs_fancy(self, interaction: discord.Interaction, username: str = ""):
        await interaction.response.defer()
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

        message = await interaction.original_response()

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

        if calculated_fc_acc != calculated_acc or (play.statistics.large_tick_miss or 0) > 0 or play.rank.value == "F":
            nonFC = (f'<div class="stat">'
                     f'<span class="value">{"{:.2f}".format(fc_pp)}</span>'
                     f'<span class="label">PP for</span>'
                     f'<span class="value">{"{:.2f}".format(calculated_fc_acc)}%</span>'
                     f'<span class="label">fc</span>'
                     f'</div>')
        else:
            nonFC = ""

        beatmap_obj_count = beatmap.count_circles + beatmap.count_sliders + beatmap.count_spinners
        map_progress = 100 * (n300 + n100 + n50 + nmiss) / beatmap_obj_count

        progress = ''
        if float(map_progress) != 100.0:
            progress = f'({"{:.1f}".format(map_progress)}%)'


        ranks = {
            0: ["GRAVEYARD", "55, 55, 55, 1"],
            1: ["WIP", "255, 163, 100, 1"],
            2: ["PENDING", "255, 223, 83, 1"],
            3 : ["RANKED", "159, 255, 77, 1"],
            4: ["APPROVED", "159, 255, 77, 1"],
            5: ["QUALIFIED", "59, 213, 255, 1"],
            6: ["LOVED", "255, 98, 191, 1"]
        }

        data = {
            "banner": f'https://assets.ppy.sh/beatmaps/{beatmapset.id}/covers/cover.jpg',
            "rankGradeColor": ranks[beatmap.status.value +2][1],
            "rankGrade": ranks[beatmap.status.value +2][0],
            "rank": Path(f"data/assets/rank_grades/custom/Grade{play.rank.value}.png").resolve().as_uri(),
            "title": f'{beatmapset.title} [{beatmap.version}]{mods_str} [{"{:.2f}".format(beatmap.difficulty_rating)}★]',
            "PP": f'{"{:.2f}".format(play.pp)}',
            "nonFC": nonFC,
            "progress": progress,
            "acc": f'{"{:.2f}".format(play.accuracy)}',
            "score": play.total_score,
            "combo": play.max_combo,
            "max_combo": beatmap.max_combo,
            "hit300": n300,
            "hit100": n100,
            "hit50": n50,
            "miss": nmiss,
            "bpm": f'{round(bpm)}',
            "ar": f'{int(ar) if ar.is_integer() else round(ar, 1)}',
            "od": f'{int(od) if od.is_integer() else round(od, 1)}',
            "hp": f'{int(hp) if hp.is_integer() else round(hp, 1)}',
            "cs": f'{int(cs) if cs.is_integer() else round(cs, 1)}',
            "pfp": play.user().avatar_url,
            "username": play.user().username,
            "server": "Bancho",
            "time": play.ended_at.strftime('%Y-%m-%d %H:%M:%S %Z')
        }

        # Step 1: Render the HTML using Jinja2
        async def render_template(context: dict, template_path: str) -> str:
            env = Environment(loader=FileSystemLoader(Path(template_path).parent))
            template = env.get_template(Path(template_path).name)
            return template.render(context)

        # Step 2: Write rendered HTML to temp file
        async def write_temp_html(html: str) -> Path:
            fd, path = tempfile.mkstemp(suffix='.html')
            file_path = Path(path)

            # Close the file descriptor immediately, aiofiles will reopen it.
            import os
            os.close(fd)

            async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
                await f.write(html)
            return file_path

        # Step 3: Render HTML to PNG using Playwright
        async def html_to_png(html_file: Path, output_file: Path):
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page(
                    viewport={"width": 620, "height": 340},
                    device_scale_factor=4  # or 3, 4, etc.
                )

                await page.goto(f"file://{html_file.resolve()}")

                await page.screenshot(path=str(output_file), omit_background=True)
                await browser.close()

        # Step 4: Main function
        async def generate_card(context: dict, template_path: str, output_png: Path):
            html = await render_template(context, template_path)
            html_file = await write_temp_html(html)
            await html_to_png(html_file, output_png)
            html_file.unlink()  # Clean up

        png_name = f"{beatmapset.id}-{beatmap.id}-{play.id}"

        await generate_card(data, "data/assets/genericCardTemplate.html", Path(f"data/osu_data/{png_name}.png"))

        card = discord.File(f'data/osu_data/{png_name}.png', filename=f'{png_name}.png')

        await message.edit(attachments=[card], embed=None)
        await set_recent_map(discord_channel_id=str(interaction.channel.id),
                             beatmap_link=f"https://osu.ppy.sh/b/{beatmapset.id}")

        card.close()

        await delete_file(f"data/osu_data/{png_name}.png")

async def setup(bot):
    await bot.add_cog(Rs_fancy(bot))
