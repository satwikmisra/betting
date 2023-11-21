from utils import get_games_by_player, get_stat_name
from datetime import datetime
import pandas as pd
import gspread

GOOGLE_SHEET_KEY = '1FEBmMm0lmr5U6qoDi_3NS2yMbMAziKNwFewy5_5GSLI'
WORKSHEET_INDEX = 0


def update_game_results():
    client = gspread.oauth()
    sheet = client.open_by_key(GOOGLE_SHEET_KEY)
    worksheet = sheet.get_worksheet(WORKSHEET_INDEX)
    current_lines = pd.DataFrame(
        worksheet.get_all_records())
    col_pos = current_lines.columns.get_loc('actual_stat')+1
    for i, row in current_lines.iterrows():
        try:
            if not pd.isna(row['actual_stat']) and len(str(row['actual_stat'])) > 0:
                continue
            player = row['name']
            date = row['game_date']
            stat = get_stat_name(row['stat'])
            all_games = get_games_by_player(player)
            date = datetime.strptime(date, '%Y-%m-%d')
            # all_games['GAME_DATE'] = pd.to_datetime(
            #     all_games['GAME_DATE'], format='%b %d, %Y')
            game = all_games[all_games['GAME_DATE'] == date]
            if len(game) == 0:
                print(f'No game found for {player} on {date}')
                continue
            game = game.iloc[0]
            worksheet.update_cell(i+2, col_pos, str(game[stat]))
            print('Updated game results for', player, date, stat, game[stat])
        except Exception as e:
            print(f'Error updating game results for {player} on {date}: {e}')
            continue


update_game_results()
