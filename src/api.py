from basketball_reference_web_scraper import client
from basketball_reference_web_scraper.data import Location, Outcome, PeriodType, Position, Team
import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
from utils import get_player_id, get_stat_name, get_games_by_player
from nba_api.stats.endpoints import playercareerstats, playernextngames
import re
from abc import ABC, abstractmethod


class BettingStrategy(ABC):
    @abstractmethod
    def hit_percentage(self, player_name, stat, pp_line, opponent, before_date=None):
        pass

    @abstractmethod
    def backtest_strategy(self, player_name, stat, pp_line, opponent, before_date=None):
        pass


class DiscordStrategy(BettingStrategy):
    def __init__(self):
        pass

    def hit_percentage(self, player_name, stat, pp_line, opponent, before_date=None):
        gamelog = get_games_by_player(player_name, before_date)
        stat_name = get_stat_name(stat)
        past_5 = self.avg_player_stats_pastngames(
            gamelog, stat_name, pp_line, 5)
        past_10 = self.avg_player_stats_pastngames(
            gamelog, stat_name, pp_line, 10)
        past_15 = self.avg_player_stats_pastngames(
            gamelog, stat_name, pp_line, 15)
        season = self.avg_player_stats_season(gamelog, stat_name, pp_line)
        nextgame = playernextngames.PlayerNextNGames(
            get_player_id(player_name), 1).get_data_frames()[0]
        vs_opp = self.avg_player_stats_vsteam(
            gamelog, stat_name, pp_line, opponent)
        pd.to_datetime(nextgame['GAME_DATE'], format='%b %d, %Y')
        if len(nextgame) == 0:
            away = 0.5
        else:
            nextgame = nextgame.iloc[0]
            if nextgame['GAME_DATE'] != before_date:
                away = 0.5
            else:
                location = 'home' if nextgame['VISITOR_TEAM_ABBREVIATION'] == opponent else 'away'
                away = self.avg_player_stats_homeaway(
                    gamelog, stat_name, pp_line, location)
        return (past_5 + past_10 + past_15 + season + away + vs_opp) / 6.0

    def backtest_strategy(self, player_name, stat, pp_line, opponent, before_date=None):
        raise NotImplementedError()

    def avg_player_stats_homeaway(self, gamelog, stat_name, pp_line, location):
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

    def avg_player_stats_vsteam(self, gamelog, stat_name, pp_line, opponent):
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

    def avg_player_stats_pastngames(self, gamelog, stat_name, pp_line, num_games):
        return (gamelog.head(num_games)[stat_name] >= pp_line).sum()/num_games

    def avg_player_stats_season(self, gamelog, stat_name, pp_line):
        cur_season_id = gamelog['SEASON_ID'].iloc[0]
        cur_season_gamelog = gamelog[gamelog['SEASON_ID'] == cur_season_id]
        return (cur_season_gamelog[stat_name] >= pp_line).sum()/len(cur_season_gamelog)


dataset = playernextngames.PlayerNextNGames(
    get_player_id('LeBron James'), 1).get_data_frames()[0].iloc[0]
print(dataset)
