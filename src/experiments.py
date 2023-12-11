from datetime import datetime
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playergamelog, leaguegamefinder, teamgamelog
import pandas as pd
import time


pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)


def get_player_id(player_name):
    all_players = players.get_players()
    player = [p for p in all_players if p['full_name'].lower() ==
              player_name.lower()]
    if player:
        return player[0]['id']
    else:
        raise Exception("Player not found")


def get_games_by_player(player_name, before_date=None):
    player_id = get_player_id(player_name)
    if player_id is None:
        return f"No player found with the name '{player_name}'"

    # Fetch the player's game log
    gamelog_cur = playergamelog.PlayerGameLog(
        player_id=player_id, season="2023-24")
    gamelog_last = playergamelog.PlayerGameLog(
        player_id=player_id, season="2022-23")
    # Convert the game log data to a DataFrame
    games_cur_df = gamelog_cur.get_data_frames()[0]
    games_last_df = gamelog_last.get_data_frames()[0]
    games_cur_df['GAME_DATE'] = pd.to_datetime(
        games_cur_df['GAME_DATE'], format='%b %d, %Y')
    games_last_df['GAME_DATE'] = pd.to_datetime(
        games_last_df['GAME_DATE'], format='%b %d, %Y')
    all_games = pd.concat([games_cur_df, games_last_df])
    if before_date is not None:
        all_games = all_games[all_games['GAME_DATE'] <= before_date]
    time.sleep(1)
    return all_games



def days_since_last_game(gamelog, game_date):
    try:
        # Check if gamelog is not empty
        if not gamelog.empty:
            last_game_date = gamelog.iloc[0]['GAME_DATE']
            days_diff = (game_date - last_game_date).days
            return days_diff
        else:
            return None
    except Exception as e:
        print(f"Error calculating days since last game: {e}")
        return None




def get_past_10_game_usage_rates(player_name, team_name):
    # Get player and team IDs
    player_id = get_player_id(player_name)
    team_id = [team['id'] for team in teams.get_teams() if team['full_name'].lower() == team_name.lower()][0]

    # Fetch player's last 10 games
    player_log = playergamelog.PlayerGameLog(player_id=player_id, season='2023-24').get_data_frames()[0]
    last_10_games = player_log.head(10)

    if last_10_games.empty:
        return f"No recent games found for {player_name}"

    usage_rates = []

    for index, game in last_10_games.iterrows():
        # Fetch team's stats for each game
        team_log = teamgamelog.TeamGameLog(team_id=team_id, season='2023-24').get_data_frames()[0]
        team_game_stats = team_log[team_log['Game_ID'] == game['Game_ID']]

        if team_game_stats.empty:
            continue  # Skip if no team stats found

        player_stats = game
        team_stats = team_game_stats.iloc[0]

        # Calculate usage rate for each game
        usg_percent = 100 * ((player_stats['FGA'] + 0.44 * player_stats['FTA'] + player_stats['TOV']) * (240 / 5)) / (player_stats['MIN'] * (team_stats['FGA'] + 0.44 * team_stats['FTA'] + team_stats['TOV']))
        usage_rates.append(usg_percent)

    return usage_rates

# Example usage
player_name = "Austin Reaves"
team_name = "Los Angeles Lakers"
usage_rates = get_past_10_game_usage_rates(player_name, team_name)
print(sum(usage_rates) / 10)
print()
print(f"{player_name}'s Usage Rates for the past 10 games: {usage_rates}")



#IGNORE

# def calculate_usage_rate(player_name):
#     # Fetch player ID
#     player_dict = players.get_players()
#     player_id = [player['id'] for player in player_dict if player['full_name'] == player_name][0]

#     # Fetch player's last 5 games
#     gamelog = playergamelog.PlayerGameLog(player_id=player_id, season='2023-24')
#     last_5_games = gamelog.get_data_frames()[0].head(1)
#     print(last_5_games)

#     # Calculate usage rate for each game
#     # usage_rates = []
#     # for index, game in last_5_games.iterrows():
#     #     # Fetch team stats for the game (for Team FGA, FTA, TO, Pace)
#     #     # ...

#     #     # Calculate USG% using the formula
#     #     usg_percent = 100 * ((game['FGA'] + 0.44 * game['FTA'] + game['TO']) * team_pace) / (game['MIN'] * (team_fga + 0.44 * team_fta + team_to))
#     # #     usage_rates.append(usg_percent)

#     # # Calculate average usage rate
#     # average_usage_rate = sum(usage_rates) / len(usage_rates)
#     # return average_usage_rate

# # Usage
# # player_usage_rate = calculate_usage_rate('LeBron James')
# #print(f"Average Usage Rate: {player_usage_rate}%")



# def get_recent_games_for_team(team_name, num_games=5):
#     # Get all teams
#     nba_teams = teams.get_teams()

#     # Find team ID based on team name
#     team_id = [team['id'] for team in nba_teams if team['full_name'].lower() == team_name.lower()]
#     if not team_id:
#         return f"No team found with the name {team_name}"
#     team_id = team_id[0]

#     # Fetch game log for the team
#     gamelog = teamgamelog.TeamGameLog(team_id=team_id, season='2023-24')
#     team_games = gamelog.get_data_frames()[0]

#     # Get the most recent 'num_games' games
#     return team_games.head(1)

# # Example usage:
# # team_name = "Los Angeles Lakers"  # Replace with the team of your choice
# # recent_games = get_recent_games_for_team(team_name)
# # #print(recent_games)
# # # print(recent_games.columns)
