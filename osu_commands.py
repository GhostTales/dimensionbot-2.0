import os
from ossapi import UserLookupKey, Ossapi
import oppadc
import requests
import zipfile
import glob
from rosu_pp_py import Beatmap, Calculator

client_id = 24667
client_secret = "3u3hoHG5DZ54zWWj4XRuf6a1wzXuIap5uBSqXIPT"


class osu_stats:
    def __init__(self, ctx, user, play_type, mode):
        self.api = Ossapi(client_id, client_secret)

        # osu play data
        self.play = self.api.user_scores(user, play_type, include_fails=True, mode=mode, limit=1)[0]
        self.beatmap = self.play.beatmap
        self.beatmapset = self.play.beatmapset
        self.map_obj_count = self.beatmap.count_circles + self.beatmap.count_sliders + self.beatmap.count_spinners
        self.n50 = self.play.statistics.meh or 0
        self.n100 = self.play.statistics.ok or 0
        self.n300 = self.play.statistics.great or 0
        self.nmiss = self.play.statistics.miss or 0
        self.pp = self.play.pp


        # ___________ calc fc_acc ___________ #
        self.play.accuracy = self.play.accuracy * 100
        self.max_n300 = self.map_obj_count - self.n100 - self.n50
        top = 300 * self.max_n300 + 100 * self.n100 + 50 * self.n50
        divider = 300 * (self.max_n300 + self.n100 + self.n50)
        self.stat_fc_acc = 100 * (top / divider)
        # ___________ calc fc_acc ___________ #

        # ___________ calc pp ___________ #

        os.makedirs('map_files', exist_ok=True)
        # Remove only files ending in .osu instead of the entire folder
        osu_files = glob.glob('map_files/*.osz')
        for file in osu_files:
            os.remove(file)

        mapset_download = 'map_files/' + f'{self.beatmapset.id} {self.beatmapset.artist} - {self.beatmapset.title}'.translate(
            str.maketrans("", "", '*"/\\<>:|?'))
        current_map = f'{self.beatmapset.artist} - {self.beatmapset.title} ({self.beatmapset.creator}) [{self.beatmap.version}].osu'.translate(
            str.maketrans("", "", '*"/\\<>:|?'))

        def download_and_extract(url, file_to_extract):
            # Step 1: Download the file
            response = requests.get(url)
            if response.status_code == 200:
                temp_zip_path = 'temp.osz'
                with open(temp_zip_path, 'wb') as f:
                    f.write(response.content)
            else:
                raise Exception(f"Failed to download file from {url}")

            # Step 2: Extract all .osu files
            extracted_files = []
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    if file_name.endswith('.osu'):
                        zip_ref.extract(file_name, "map_files/")
                        extracted_files.append(os.path.join("map_files/", file_name))

            # Step 3: Cleanup the temporary file
            os.remove(temp_zip_path)

            # Step 4: Return the file path
            return file_to_extract

        map_extract = ''
        if os.path.exists(f"map_files/{current_map}"):
            map_extract = current_map

        download_sites = {
            f'https://beatconnect.io/b/{self.beatmapset.id}',
            f'https://dl.sayobot.cn/beatmaps/download/novideo/{self.beatmapset.id}',
            f'https://api.nerinyan.moe/d/{self.beatmapset.id}?nv=1'
        }

        if not os.path.exists(f"map_files/{current_map}"):
            print("Downloading map")
            for site in download_sites:
                try:
                    map_extract = download_and_extract(site, current_map)
                except Exception as e:
                    print(f"An error occurred: {e}")
                if os.path.exists(f"map_files/{current_map}"):
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
            if mod in str(self.play.mods):
                self.mod_int_value += mod_values[mod]

        map = Beatmap(path=f'map_files/{map_extract}')

        calc_fc_pp = Calculator(mods=self.mod_int_value)

        calc_fc_pp.set_acc(self.stat_fc_acc)
        calc_fc_pp.set_n50(self.n50)
        calc_fc_pp.set_n100(self.n100)
        calc_fc_pp.set_n300(self.max_n300)
        calc_fc_pp.set_n_misses(0)
        calc_fc_pp.set_combo(self.map_max_combo)

        self.fc_pp = calc_fc_pp.performance(map).pp
        # ___________ calc pp ___________ #

        self.beatmap.difficulty_rating = self.api.beatmap_attributes(self.beatmap.id, mods=self.mod_int_value).attributes.star_rating
        import math

        if 'HR' in str(self.play.mods):
            self.beatmap.ar = min(self.beatmap.ar * 1.4, 10)
            self.beatmap.accuracy = min(self.beatmap.accuracy * 1.4, 10)
            self.beatmap.drain = min(self.beatmap.drain * 1.4, 10)
            self.beatmap.cs = min(self.beatmap.cs * 1.3, 10)

        if 'EZ' in str(self.play.mods):
            self.beatmap.ar *= 0.5
            self.beatmap.accuracy *= 0.5
            self.beatmap.drain *= 0.5
            self.beatmap.cs *= 0.5

        if 'DT' in str(self.play.mods):
            print('DT')
            self.beatmap.bpm *= 1.5
            self.beatmap.ar = min(0.126e-1 * self.beatmap.ar ** 2 + 0.4833e0 * self.beatmap.ar + 5, 11.11)
            self.beatmap.accuracy = min(0.6667 * self.beatmap.accuracy + 4.4427, 11.11)

        if 'HT' in str(self.play.mods):
            self.beatmap.bpm = self.beatmap.bpm * 0.75
            self.beatmap.ar = min(2.89 + 12.1708 * math.sin(0.1226 * self.beatmap.ar - 0.6973), 9)
            self.beatmap.accuracy = min(1.3333 * self.beatmap.accuracy - 4.4427, 11.11)


class linking:
    def __init__(self, name):
        self.api = Ossapi(client_id, client_secret)
        self.user = self.api.user(name, key=UserLookupKey.USERNAME)

class User:
    def __init__(self, id):
        self.api = Ossapi(client_id, client_secret)
        self.user = self.api.user(id, key=UserLookupKey.ID)

