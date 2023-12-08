import models
import utils
import pandas as pd
import datetime
from prizepicks_selenium import scrape_prizepicks
import gspread


SCRAPE_STATS = utils.stat_mapping.keys()
output = scrape_prizepicks()
timestamp = datetime.datetime.now().isoformat()
worksheet = utils.get_master_sheet()

# get rows from worksheetx
total_rows = worksheet.row_count
start_row = max(1, total_rows - 100)
current_lines = pd.DataFrame(
    worksheet.get_records(f'A{start_row}:L{total_rows}'))
already_scraped = set()
for i, row in current_lines.iterrows():
    already_scraped.add(
        str(row['game_date'])+str(row['name'])+str(row['stat']))  # +str(row['line'])) comment this out to add back bumps

strategy = models.LogisticRegression('./models/lrmodel.joblib')
for i, row in output.iterrows():
    try:
        if row['stat'] not in SCRAPE_STATS:
            continue
        pkey = str(row['date'])+str(row['name']) + str(row['stat'])
        if pkey in already_scraped:
            print(f'{row["name"]} already scraped, skipping...')
            continue
        hp = strategy.hit_percentage(
            player_name=row['name'],
            stat=row['stat'],
            pp_line=float(row['line']),
            opponent=row['opponent'],
            game_date=datetime.datetime.strptime(row['date'], '%Y-%m-%d'))
        hp *= 100
        hp = round(hp, 2)
        worksheet.append_row([
            timestamp,
            row['date'],
            row['time'],
            row['name'],
            row['team'],
            row['position'],
            row['opponent'],
            row['stat'],
            float(row['line']),
            float(hp)
        ], value_input_option='USER_ENTERED')
        print(f'Hit Percentage for {row["name"]}: {hp:.2f}%')
    except Exception as e:
        print(f'Error {e}, skipping...')
