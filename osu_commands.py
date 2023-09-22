import contextlib
import os
from ossapi import UserLookupKey, Ossapi
import oppadc
import requests
import zipfile
import shutil
import concurrent.futures
from rosu_pp_py import Beatmap, Calculator

client_id = 24667
client_secret = "3u3hoHG5DZ54zWWj4XRuf6a1wzXuIap5uBSqXIPT"


class osu_stats:
    def __init__(self, user, play_type, mode):
        self.api = Ossapi(client_id, client_secret)

        # osu play data
        self.play = self.api.user_scores(user, play_type, include_fails=True, mode=mode, limit=1)
        self.map_id = self.play[0].beatmap.id

        # map data
        self.beatmap = self.api.beatmap(self.map_id)
        self.mapset_id = self.beatmap.beatmapset_id
        self.mapset_artist = self.play[0].beatmapset.artist
        self.mapset_creator = self.play[0].beatmapset.creator
        self.map_diff = self.beatmap.version
        self.map_rank_status = self.beatmap.status
        self.map_image = self.play[0].beatmapset.covers.card
        self.map_title = self.play[0].beatmapset.title
        self.map_date_created = self.play[0].created_at
        self.map_obj_count = self.beatmap.count_circles + self.beatmap.count_sliders + self.beatmap.count_spinners

        # player data
        self.player_name = self.play[0]._user.username
        self.player_avatar = self.play[0]._user.avatar_url

        # play stats
        self.stat_acc = 100 * self.play[0].accuracy
        self.stat_n300 = self.play[0].statistics.count_300
        self.stat_n100 = self.play[0].statistics.count_100
        self.stat_n50 = self.play[0].statistics.count_50
        self.stat_n_miss = self.play[0].statistics.count_miss
        self.stat_mods = self.play[0].mods
        self.stat_score = f'{self.play[0].score:,}'
        self.stat_stars = self.api.beatmap_attributes(self.map_id, mods=self.stat_mods).attributes.star_rating
        self.stat_rank_grade = self.play[0].rank
        self.stat_achieved_combo = self.play[0].max_combo
        self.stat_map_progress = 100 * (self.stat_n300 + self.stat_n100 + self.stat_n50 + self.stat_n_miss) / self.map_obj_count

        # ___________ calc fc_acc ___________ #

        self.max_n300 = self.map_obj_count - self.stat_n100 - self.stat_n50
        top = 300 * self.max_n300 + 100 * self.stat_n100 + 50 * self.stat_n50
        divider = 300 * (self.max_n300 + self.stat_n100 + self.stat_n50)
        self.stat_fc_acc = 100 * (top / divider)
        # ___________ calc fc_acc ___________ #

        # ___________ calc pp ___________ #

        folder_path = 'map_files'
        with contextlib.suppress(FileNotFoundError):
            # Remove the folder and its contents
            shutil.rmtree(folder_path)
        # Create a new folder
        os.mkdir(folder_path)

        response = [
            requests.get(f'https://beatconnect.io/b/{self.mapset_id}'),
            requests.get(f'https://dl.sayobot.cn/beatmaps/download/novideo/{self.mapset_id}'),
            requests.get(f'https://api.nerinyan.moe/d/{self.mapset_id}?nv=1'),
            requests.get(f'https://api.chimu.moe/v1/download/{self.mapset_id}?n=1')
        ]

        mapset_download = f'map_files/{self.mapset_id} {self.mapset_artist} - {self.map_title}'

        def download_and_extract(index, resp):
            try:
                if os.path.exists(f'map_files/{self.mapset_artist} - {self.map_title} ({self.mapset_creator}) [{self.map_diff.rstrip("?")}].osu'):
                    return None

                with open(f'{mapset_download}_{index}.osz', 'wb') as file:
                    file.write(resp.content)
                with zipfile.ZipFile(f'{mapset_download}_{index}.osz', 'r') as zip_ref:
                    osu_files = zip_ref.namelist()
                    for file in osu_files:
                        if self.map_diff is not None and file.endswith(f'[{self.map_diff.rstrip("?")}].osu'):
                            zip_ref.extract(file, 'map_files')
                            return file
            except Exception:
                return None

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = [executor.submit(download_and_extract, index, resp) for index, resp in enumerate(response)]

        map_extract = ''
        for result in results:
            if result.result() is not None:
                map_extract = result.result()
                break

        self.MapInfo = oppadc.OsuMap(file_path=f'map_files/{map_extract}')
        self.map_max_combo = self.MapInfo.maxCombo()


        self.mod_int_value = 0

        mod_values = {
            'NF': pow(2, 0),
            'EZ': pow(2, 1),
            'TD': pow(2, 2),
            'HD': pow(2, 3),
            'HR': pow(2, 4),
            'SD': pow(2, 5),
            'DT': pow(2, 6),
            'RX': pow(2, 7),
            'HT': pow(2, 8),
            'NC': pow(2, 9) + pow(2, 6),  # Only set along with DoubleTime. i.e: NC only gives 576
            'FL': pow(2, 10),
            'AT': pow(2, 11),
            'SO': pow(2, 12),
            'AP': pow(2, 13),
            'PF': pow(2, 14) + pow(2, 5),  # Only set along with SuddenDeath. i.e: PF only gives 16416
            'K4': pow(2, 15),
            'K5': pow(2, 16),
            'K6': pow(2, 17),
            'K7': pow(2, 18),
            'K8': pow(2, 19),
            'FI': pow(2, 20),
            'RD': pow(2, 21),
            'CN': pow(2, 22),
            'TP': pow(2, 23),
            'K9': pow(2, 24),
            'CO': pow(2, 25),
            'K1': pow(2, 26),
            'K3': pow(2, 27),
            'K2': pow(2, 28),
            'V2': pow(2, 29),
            'MR': pow(2, 30),
        }

        for mod in mod_values:
            if mod in str(self.stat_mods):
                self.mod_int_value += mod_values[mod]

        map = Beatmap(path=f'map_files/{map_extract}')
        calc_pp = Calculator(mods=self.mod_int_value)

        calc_pp.set_acc(self.stat_acc)
        calc_pp.set_n50(self.stat_n50)
        calc_pp.set_n100(self.stat_n100)
        calc_pp.set_n300(self.stat_n300)
        calc_pp.set_n_misses(self.stat_n_miss)
        calc_pp.set_combo(self.stat_achieved_combo)

        self.stat_pp = calc_pp.performance(map).pp

        calc_fc_pp = Calculator(mods=self.mod_int_value)

        calc_fc_pp.set_acc(self.stat_fc_acc)
        calc_fc_pp.set_n50(self.stat_n50)
        calc_fc_pp.set_n100(self.stat_n100)
        calc_fc_pp.set_n300(self.max_n300)
        calc_fc_pp.set_n_misses(0)
        calc_fc_pp.set_combo(self.map_max_combo)

        self.stat_fc_pp = calc_fc_pp.performance(map).pp

        # ___________ calc pp ___________ #

        self.map_ar = self.MapInfo.ar
        self.map_od = self.MapInfo.od
        self.map_hp = self.MapInfo.hp
        self.map_cs = self.MapInfo.cs
        self.map_bpm = self.beatmap.bpm

        import math

        if 'HR' in str(self.stat_mods):
            self.map_ar = min(int(self.map_ar) * 1.4, 10)
            self.map_hp = min(int(self.map_hp) * 1.4, 10)
            self.map_cs = min(int(self.map_cs) * 1.3, 10)
            self.map_od = min(int(self.map_od) * 1.4, 10)

        if 'EZ' in str(self.stat_mods):
            self.map_hp = int(self.map_hp) * 0.5
            self.map_cs = int(self.map_cs) * 0.5
            self.map_ar = int(self.map_ar) * 0.5
            self.map_od = int(self.map_od) * 0.5

        if 'DT' in str(self.stat_mods):

            self.map_bpm = int(self.beatmap.bpm) * 1.5
            self.map_ar = min(0.126e-1 * int(self.map_ar) ** 2 + 0.4833e0 * int(self.map_ar) + 5, 11.11)
            self.map_od = min(0.6667 * int(self.map_od) + 4.4427, 11.11)

        if 'HT' in str(self.stat_mods):
            self.map_bpm = int(self.beatmap.bpm) * 0.75
            self.map_ar = min(2.89 + 12.1708 * math.sin(0.1226 * int(self.map_ar) - 0.6973), 9)
            self.map_od = min(1.3333 * int(self.map_od) - 4.4427, 11.11)




        # Round the number to the nearest multiple of 5
        rounded_number = round(float(self.stat_map_progress) / 5) * 5

        # Define the list of emotes
        emotes = [
            "<:progress_0:1154520040884944996>",
            "<:progress_5:1154520042206142596>",
            "<:progress_10:1154520045519642714>",
            "<:progress_15:1154520047784566784>",
            "<:progress_20:1154520048971567157>",
            "<:progress_25:1154520051567833179>",
            "<:progress_30:1154520053274914866>",
            "<:progress_35:1154520054499659826>",
            "<:progress_40:1154520056546476042>",
            "<:progress_45:1154520057725079652>",
            "<:progress_50:1154520058983358584>",
            "<:progress_55:1154520771406860389>",
            "<:progress_60:1154520772631605328>",
            "<:progress_65:1154520775055900822>",
            "<:progress_70:1154520776502943774>",
            "<:progress_75:1154520778893701213>",
            "<:progress_80:1154520780273614968>",
            "<:progress_85:1154520097931677846>",
            "<:progress_90:1154520122157973575>",
            "<:progress_95:1154520172988727347>",
            "<:progress_100:1154520224708706376>"
        ]

        # Ensure the index is within the valid range

        self.chart_map_progress = emotes[rounded_number // 5]

class linking:
    def __init__(self, string):
        self.api = Ossapi(client_id, client_secret)
        self.user = self.api.user(string, key=UserLookupKey.USERNAME)
