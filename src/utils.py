from nba_api.stats.endpoints import commonplayerinfo, teamgamelog
from datetime import datetime
from nba_api.stats.endpoints import teamgamelog
from nba_api.stats.static import players, teams
import pandas as pd
from nba_api.stats.endpoints import playergamelog
from basketball_reference_web_scraper import client
from basketball_reference_web_scraper.data import Location, Outcome, PeriodType, Position, Team
from bs4 import BeautifulSoup
from nba_api.stats.static import players
from nba_api.stats.static import teams
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.endpoints import leaguegamelog
from nba_api.stats.library.parameters import *
import time

stat_mapping = {
    'Points': 'PTS',
    'Rebounds': 'REB',
    'Offensive Rebounds': 'OREB',
    'Defensive Rebounds': 'DREB',
    'Assists': 'AST',
    'Steals': 'STL',
    'Blocked Shots': 'BLK',
    'Turnovers': 'TOV',
    '3-PT Made': 'FG3M',
    '3-PT Attempted': 'FG3A',
    'FG Made': 'FGM',
    'FG Attempted': 'FGA',
    'Free Throws Made': 'FTM',
    'Free Throws Attempted': 'FTA',
}


def get_stat_name(stat):
    return stat_mapping[stat]


def get_teams():
    return teams.get_teams()


def get_player_id(player_name):
    all_players = players.get_players()
    player = [p for p in all_players if p['full_name'].lower() ==
              player_name.lower()]
    if player:
        return player[0]['id']
    else:
        raise Exception("Player not found")


def get_player_name(player_id):
    return players.find_player_by_id(player_id)['full_name']


def get_team_id(team_name):
    all_teams = teams.get_teams()
    team = [t for t in all_teams if t['full_name']
            == team_name or t['nickname'] == team_name]
    if team:
        return team[0]['id']
    else:
        raise Exception("Team not found")


def get_team_name(team_id):
    return teams.find_team_name_by_id(team_id)


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
        all_games = all_games[all_games['GAME_DATE'] < before_date]
    time.sleep(1)
    return all_games
