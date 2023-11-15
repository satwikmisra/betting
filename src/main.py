import api
import utils
import time
import pandas as pd
from datetime import datetime
from online import scrape_prizepicks
import gspread

GOOGLE_SHEET_KEY = '1FEBmMm0lmr5U6qoDi_3NS2yMbMAziKNwFewy5_5GSLI'
WORKSHEET_INDEX = 0
THRESHOLD = 10


def hit_percentage(player_id, stat_name, pp_line, opponent, quiet=True):
    time.sleep(4)
    past_5 = api.avg_player_stats_pastngames(player_id, stat_name, pp_line, 5)
    time.sleep(4)
    past_10 = api.avg_player_stats_pastngames(
        player_id, stat_name, pp_line, 10)
    time.sleep(4)
    past_15 = api.avg_player_stats_pastngames(
        player_id, stat_name, pp_line, 15)
    time.sleep(4)
    season = api.avg_player_stats_season(player_id, stat_name, pp_line)
    time.sleep(4)
    away = api.avg_player_stats_away(player_id, stat_name, pp_line, "AWAY")
    time.sleep(4)
    vs_opp = api.avg_player_stats_vsteam(
        player_id, stat_name, pp_line, opponent)
    hp = (past_5 + past_10 + past_15 + season + away + vs_opp) / 6.0
    if not quiet:
        print(
            f"Percentage of last 5 games where {player_id} scored more than {pp_line} {stat_name}: {past_5:.2f}%")
        print(
            f"Percentage of last 10 games where {player_id} scored more than {pp_line} {stat_name}: {past_10:.2f}%")
        print(
            f"Percentage of last 15 games where {player_id} scored more than {pp_line} {stat_name}: {past_15:.2f}%")
        print(
            f"Percentage of season where {player_id} scored more than {pp_line} {stat_name}: {season:.2f}%")
        print(
            f"Percentage of away games where {player_id} scored more than {pp_line} {stat_name}: {away:.2f}%")
        print(
            f"Percentage of games vs {opponent} where {player_id} scored more than {pp_line} {stat_name}: {vs_opp:.2f}%")
        print('-'*20)
        print(f"Total Hit Percentage: {hp:.2f}%")
    return hp


output = scrape_prizepicks()
timestamp = datetime.now().isoformat()

client = gspread.oauth()
sheet = client.open_by_key(GOOGLE_SHEET_KEY)
worksheet = sheet.get_worksheet(0)

for i, row in output.iterrows():
    stat = row['stat']
    if stat != 'Points':
        continue
    try:
        player_id = utils.get_player_id(row['name'])
        hp = hit_percentage(
            player_id, 'points_scored', float(row['line']), row['opponent'])
        abs_diff = abs(hp - 50)
        action = 'OVER' if hp > 50 else 'UNDER'
        if abs_diff < THRESHOLD:
            action = 'PASS'
        hp = round(hp, 2)
        abs_diff = round(abs_diff, 2)
        worksheet.append_row([
            timestamp,
            row['date'],
            row['time'],
            row['name'],
            row['team'],
            row['position'],
            row['opponent'],
            row['stat'],
            row['line'],
            hp,
            abs_diff,
            action,
        ])
        print(f'Hit Percentage for {row["name"]}: {hp:.2f}%')
        time.sleep(5)
    except Exception as e:
        print(f'Error {e}, skipping...')
