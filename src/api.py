from basketball_reference_web_scraper import client
from basketball_reference_web_scraper.data import Location, Outcome, PeriodType, Position, Team
import datetime
import requests
from bs4 import BeautifulSoup
from utils import get_player_id, get_stat_name, get_games_by_player
from nba_api.stats.endpoints import playercareerstats
import re


def calculate_hit_percentage(player_name, stat, pp_line, opponent, before_date=None):
    gamelog = get_games_by_player(player_name, before_date)
    stat_name = get_stat_name(stat)
    past_5 = avg_player_stats_pastngames(gamelog, stat_name, pp_line, 5)
    past_10 = avg_player_stats_pastngames(gamelog, stat_name, pp_line, 10)
    past_15 = avg_player_stats_pastngames(gamelog, stat_name, pp_line, 15)
    season = avg_player_stats_season(gamelog, stat_name, pp_line)
    # away = avg_player_stats_homeaway(gamelog, stat_name, pp_line, location)
    vs_opp = avg_player_stats_vsteam(gamelog, stat_name, pp_line, opponent)
    return (past_5 + past_10 + past_15 + season + vs_opp) / 5.0


def avg_player_stats_homeaway(gamelog, stat_name, pp_line, location):
    if location.lower() == 'home':
        filtered_log = gamelog[gamelog['MATCHUP'].str.contains('vs.')]
    elif location.lower() == 'away':
        filtered_log = gamelog[gamelog['MATCHUP'].str.contains('@')]
    else:
        raise ValueError("Location must be 'home' or 'away'")

    games_over_line = filtered_log[filtered_log[stat_name] > pp_line]

    if len(filtered_log) > 0:
        percentage_over_line = len(games_over_line) / len(filtered_log)
    else:
        percentage_over_line = 0

    return percentage_over_line


def avg_player_stats_vsteam(gamelog, stat_name, pp_line, opponent):
    pattern = re.compile(r' vs\. | @ ')
    opponents = [re.split(pattern, mu)[1] ==
                 opponent for mu in gamelog['MATCHUP']]
    filtered_log = gamelog[opponents]
    games_over_line = filtered_log[filtered_log[stat_name] > pp_line]
    if len(filtered_log) > 0:
        percentage_over_line = len(games_over_line) / len(filtered_log)
    else:
        percentage_over_line = 0
    return percentage_over_line


def avg_player_stats_pastngames(gamelog, stat_name, pp_line, num_games):
    return (gamelog.head(num_games)[stat_name] >= pp_line).sum()/num_games


def avg_player_stats_season(gamelog, stat_name, pp_line):
    cur_season_id = gamelog['SEASON_ID'].iloc[0]
    cur_season_gamelog = gamelog[gamelog['SEASON_ID'] == cur_season_id]
    return (cur_season_gamelog[stat_name] >= pp_line).sum()/len(cur_season_gamelog)
