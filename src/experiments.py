from datetime import datetime
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
import pandas as pd
import time




def days_since_last_game(gamelog):
    try:
        # Check if gamelog is not empty
        if not gamelog.empty:
            # Get the date of the last game
            last_game_date = gamelog.iloc[0]['GAME_DATE']

            # Ensure last_game_date is a datetime object (in case it's not)
            if not isinstance(last_game_date, datetime):
                last_game_date = pd.to_datetime(last_game_date)

            # Get the current date
            current_date = datetime.now()

            # Calculate the difference in days
            days_diff = (current_date - last_game_date).days

            return days_diff
        else:
            return None
    except Exception as e:
        print(f"Error calculating days since last game: {e}")
        return None


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

# Example usage
player_name = "Pascal Siakam"  # Replace with the actual player name
gamelog = get_games_by_player(player_name)
days_since = days_since_last_game(gamelog)
if days_since is not None:
    print(f"It has been {days_since} days since {player_name}'s last game.")
else:
    print("Could not determine the days since the last game.")
