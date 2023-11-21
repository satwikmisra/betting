import api
import utils
import pandas as pd
import datetime
from prizepicks_selenium import scrape_prizepicks
import gspread

GOOGLE_SHEET_KEY = '1FEBmMm0lmr5U6qoDi_3NS2yMbMAziKNwFewy5_5GSLI'
WORKSHEET_INDEX = 0
SCRAPE_STATS = utils.stat_mapping.keys()
output = scrape_prizepicks()
timestamp = datetime.datetime.now().isoformat()

client = gspread.oauth()
sheet = client.open_by_key(GOOGLE_SHEET_KEY)
worksheet = sheet.get_worksheet(WORKSHEET_INDEX)

# get rows from worksheet
total_rows = worksheet.row_count
start_row = max(1, total_rows - 100)
current_lines = pd.DataFrame(
    worksheet.get_records(f'A{start_row}:L{total_rows}'))
already_scraped = set()
for i, row in current_lines.iterrows():
    already_scraped.add(
        str(row['game_date'])+str(row['name'])+str(row['stat'])+str(row['line']))

strategy = api.DiscordStrategy()
for i, row in output.iterrows():
    try:
        if row['stat'] not in SCRAPE_STATS:
            continue
        pkey = str(row['date'])+str(row['name']) + \
            str(row['stat'])+str(row['line'])
        if pkey in already_scraped:
            print(f'{row["name"]} already scraped, skipping...')
            continue
        hp = strategy.hit_percentage(
            player_name=row['name'],
            stat=row['stat'],
            pp_line=float(row['line']),
            opponent=row['opponent'],
            before_date=datetime.datetime.strptime(row['date'], '%Y-%m-%d')-datetime.timedelta(days=1))
        hp *= 100
        abs_diff = abs(hp - 50)
        action = 'OVER' if hp >= 50 else 'UNDER'
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
            float(row['line']),
            float(hp),
            float(abs_diff),
            action,
        ], value_input_option='USER_ENTERED')
        print(f'Hit Percentage for {row["name"]}: {hp:.2f}%')
    except Exception as e:
        print(f'Error {e}, skipping...')
