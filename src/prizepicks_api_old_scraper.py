import pandas as pd
import cloudscraper
scraper = cloudscraper.create_scraper()
pp_props_url = 'https://api.prizepicks.com/projections?league_id=7&per_page=250&single_stat=true'
headers = {
    'Connection': 'keep-alive',
    'Accept': 'application/json; charset=UTF-8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
    'Access-Control-Allow-Credentials': 'true',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Referer': 'https://app.prizepicks.com/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9'}

response = scraper.get(pp_props_url, headers=headers)
response = response.json()
df_inc = pd.json_normalize(response['included'])
df_inc = df_inc[df_inc['type'] == 'new_player']
df_data = pd.json_normalize(response['data'])
df = df_data.merge(df_inc, left_on='relationships.new_player.data.id',
                   right_on='id', how='left')
selected_columns = ['attributes.name', 'attributes.team', 'attributes.position',
                    'attributes.stat_type', 'attributes.line_score', 'attributes.start_time']
df = df[selected_columns]
df.columns = ['player_name', 'team', 'position',
              'stat_type', 'line_score', 'start_time']
print(df)
