import contextlib
import os
from ossapi import UserLookupKey, Ossapi
import oppadc
import requests
import zipfile
import shutil

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
        self.stat_acc = "{:.2f}".format(round(100 * self.play[0].accuracy, 2))
        self.stat_n300 = self.play[0].statistics.count_300
        self.stat_n100 = self.play[0].statistics.count_100
        self.stat_n50 = self.play[0].statistics.count_50
        self.stat_n_miss = self.play[0].statistics.count_miss
        self.stat_mods = self.play[0].mods
        self.stat_score = f'{self.play[0].score:,}'
        self.stat_stars = round(self.api.beatmap_attributes(self.map_id, mods=self.stat_mods).attributes.star_rating, 2)
        self.stat_rank_grade = self.play[0].rank
        self.stat_achieved_combo = self.play[0].max_combo
        self.stat_map_progress = "{:.1f}".format(100 * (self.stat_n300 + self.stat_n100 + self.stat_n50 + self.stat_n_miss) / self.map_obj_count)

        # ___________ calc fc_acc ___________ #

        max_n300 = self.map_obj_count - self.stat_n100 - self.stat_n50
        top = 300 * max_n300 + 100 * self.stat_n100 + 50 * self.stat_n50
        divider = 300 * (max_n300 + self.stat_n100 + self.stat_n50)
        self.stat_fc_acc = "{:.2f}".format(round(100 * (top / divider), 2))
        # ___________ calc fc_acc ___________ #

        # ___________ calc pp ___________ #

        folder_path = 'map_files'
        with contextlib.suppress(FileNotFoundError):
            # Remove the folder and its contents
            shutil.rmtree(folder_path)
        # Create a new folder
        os.mkdir(folder_path)

        response = requests.get(f'https://beatconnect.io/b/{self.mapset_id}')

        mapset_download = f'map_files/{self.mapset_id} {self.mapset_artist} - {self.map_title}.osz'

        with open(mapset_download, 'wb') as file:
            file.write(response.content)

        with zipfile.ZipFile(mapset_download, 'r') as zip_ref:
            osu_files = zip_ref.namelist()
            for file in osu_files:
                if file.endswith(f'[{self.map_diff.rstrip("?")}].osu'):
                    zip_ref.extract(file, 'map_files')
                    map_extract = file
                    break


        self.MapInfo = oppadc.OsuMap(file_path=f'map_files/{map_extract}')

        self.stat_pp = round(self.MapInfo.getPP(str(self.stat_mods), recalculate=True, **{'n300': int(self.stat_n300),
                                                                                        'n100': int(self.stat_n100),
                                                                                        'n50': int(self.stat_n50),
                                                                                        'combo': int(self.stat_achieved_combo)}).total_pp, 2)

        self.stat_fc_pp = round(self.MapInfo.getPP(str(self.stat_mods), recalculate=True, **{'n300': int(max_n300),
                                                                                        'n100': int(self.stat_n100),
                                                                                        'n50': int(self.stat_n50)}).total_pp, 2)

        # ___________ calc pp ___________ #

        self.map_ar = round(self.api.beatmap_attributes(self.map_id, mods=self.stat_mods).attributes.approach_rate, 2)
        self.map_od = round(self.api.beatmap_attributes(self.map_id, mods=self.stat_mods).attributes.overall_difficulty,2)
        self.map_hp = self.beatmap.drain
        self.map_cs = self.beatmap.cs
        self.map_bpm = self.beatmap.bpm

        if 'HR' in str(self.stat_mods):
            self.map_hp = min(int(self.beatmap.drain) * 1.4, 10)
            self.map_cs = min(int(self.beatmap.cs) * 1.4, 10)

        if 'EZ' in str(self.stat_mods):
            self.map_hp = int(self.beatmap.drain) * 0.5
            self.map_cs = int(self.beatmap.cs) * 0.5

        if 'DT' in str(self.stat_mods):
            self.map_bpm = int(self.beatmap.bpm) * 1.5

        if 'HT' in str(self.stat_mods):
            self.map_bpm = int(self.beatmap.bpm) * 0.75

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
            'NC': pow(2, 9) + pow(2, 6), # Only set along with DoubleTime. i.e: NC only gives 576
            'FL': pow(2, 10),
            'AT': pow(2, 11),
            'SO': pow(2, 12),
            'AP': pow(2, 13),
            'PF': pow(2, 14) + pow(2, 5), # Only set along with SuddenDeath. i.e: PF only gives 16416
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


class linking:
    def __init__(self, string):
        self.api = Ossapi(client_id, client_secret)
        self.user = self.api.user(string, key=UserLookupKey.USERNAME)
