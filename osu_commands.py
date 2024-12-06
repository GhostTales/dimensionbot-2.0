import os
import requests
import zipfile
import re

def sanitize_filename(filename: str) -> str:
    # Remove any character that is not a letter, number, or underscore
    sanitized = re.sub(r"[^a-zA-Z0-9 ()\[\]\-.]", '', filename)
    return sanitized


def rename_file(current_path: str, new_name: str):
    # Get the directory of the current file
    directory = os.path.dirname(current_path)

    # Sanitize the new name and append the original file extension
    sanitized_name = sanitize_filename(new_name)

    # Construct the new file path
    new_path = os.path.join(directory, sanitized_name)

    # Rename the file
    os.rename(current_path, new_path)

async def calculate_accuracy(max_stats, stats, full_combo=False, passed=False):
    # Define base scores for each HitResult
    base_scores = {
        'great': 300, #300
        'ok': 100, #100
        'meh': 50, #50
        'miss': 0, #0
        'slider_tail_hit': 150, #150
        'slider_tail_miss': 0, #0
        'large_tick_hit': 30, #30
        'large_tick_miss': 0, #0
    }


    # Add missing keys from base_scores to max_stats and stats with a value of 0
    for key in base_scores:
        if key not in max_stats:
            max_stats[key] = 0
        if key not in stats:
            stats[key] = 0

    # Replace None values with 0 in all three dictionaries
    for key in base_scores:
        if base_scores[key] is None:
            base_scores[key] = 0
        if max_stats[key] is None:
            max_stats[key] = 0
        if stats[key] is None:
            stats[key] = 0

    # adjust to full combo
    if full_combo:
        base_scores['miss'] = base_scores['great']
        base_scores['large_tick_miss'] = base_scores['large_tick_hit']
        base_scores['slider_tail_miss'] = base_scores['slider_tail_hit']
    # calculate if player quit out before finish map
    if not passed:
        stats['great'] = max_stats['great'] - ((stats['ok']) + (stats['meh']) + (stats['miss']))
        stats['large_tick_hit'] = max_stats['large_tick_hit']

    # Function to safely handle None values
    def get_value_or_zero(stat, stats_dict):
        return stats_dict.get(stat, 0) or 0  # Return 0 if value is None

    # Calculate maximum possible base score
    current_maximum_base_score = sum(
        get_value_or_zero(key, max_stats) * base_scores.get(key, 0) for key in base_scores)

    # Calculate player's achieved base score
    current_base_score = sum(get_value_or_zero(key, stats) * base_scores.get(key, 0) for key in base_scores)

    # Calculate accuracy
    accuracy = (current_base_score / current_maximum_base_score) * 100 if current_maximum_base_score > 0 else 0
    print(max_stats)
    print(stats)
    print(current_base_score, current_maximum_base_score, accuracy)
    return accuracy


def download_and_extract(url, file_to_extract):
    # Step 1: Download the file
    response = requests.get(url)
    if response.status_code == 200:
        temp_zip_path = 'map_files/temp.osz'
        with open(temp_zip_path, 'wb') as f:
            f.write(response.content)
    else:
        raise Exception(f"Failed to download file from {url}")

    # Step 2: Extract all .osu files
    extracted_files = []
    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.endswith('.osu'):
                extracted_path = zip_ref.extract(file_name, "map_files/")
                new_path = rename_file(extracted_path, file_name)
                extracted_files.append(new_path)

    # Step 3: Cleanup the temporary file
    os.remove(temp_zip_path)

    # Step 4: Return the file path
    return file_to_extract

def mod_values(mods):
    mod_int_value = 0
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
        if mod in str(mods):
            mod_int_value += mod_values[mod]
    return mod_int_value

def mod_math(mods, beatmap, settings):
    import math

    mods = re.sub(r"[^A-Z]", '', mods)

    if 'DA' in str(mods):
        beatmap.ar = settings.get("approach_rate", beatmap.ar)
        beatmap.accuracy = settings.get("overall_difficulty", beatmap.accuracy)
        beatmap.drain = settings.get("drain_rate", beatmap.drain)
        beatmap.cs = settings.get("circle_size", beatmap.cs)



    if 'HR' in str(mods):
        beatmap.ar = min(beatmap.ar * 1.4, 10)
        beatmap.accuracy = min(beatmap.accuracy * 1.4, 10)
        beatmap.drain = min(beatmap.drain * 1.4, 10)
        beatmap.cs = min(beatmap.cs * 1.3, 10)

    if 'EZ' in str(mods):
        beatmap.ar *= 0.5
        beatmap.accuracy *= 0.5
        beatmap.drain *= 0.5
        beatmap.cs *= 0.5


    def CalculateOD(OD, multiplier):
        ms = (-6 * OD + 79.5) / multiplier
        new_od = (79.5 - ms) / 6
        new_od = round(new_od * 10) / 10
        return new_od

    if 'DT' in str(mods):

        speed = settings.get("speed_change", 1.5)

        beatmap.bpm *= speed

        if beatmap.ar >= 5:
            timings = (1950 - (150 * beatmap.ar)) / speed
        else:
            timings = (1800 - (120 * beatmap.ar)) / speed

        beatmap.ar = -((2 / 3) / 100) * timings + 13

        beatmap.accuracy = CalculateOD(beatmap.accuracy, speed)


    if 'HT' in str(mods):

        speed = settings.get("speed_change", 0.75)

        beatmap.bpm *= speed

        beatmap.ar = min(2.89 + 12.1708 * math.sin(0.1226 * beatmap.ar - 0.6973), 9)

        if beatmap.ar >= 5:
            timings = (1300 - (100 * beatmap.ar)) / speed
        else:
            timings = (1200 - (80 * beatmap.ar)) / speed

        if timings > 1000:
            beatmap.ar = -((5 / 6) / 100) * timings + 15
        else:
            beatmap.ar = -((2 / 3) / 100) * timings + 13

        beatmap.accuracy = CalculateOD(beatmap.accuracy, speed)


    return beatmap
