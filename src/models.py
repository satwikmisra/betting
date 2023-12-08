from basketball_reference_web_scraper import client
from basketball_reference_web_scraper.data import Location, Outcome, PeriodType, Position, Team
import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
import utils
from nba_api.stats.endpoints import playercareerstats, playernextngames
import re
from abc import ABC, abstractmethod
from sklearn.linear_model import LogisticRegression
from joblib import dump, load
import time

# Predictor functions:


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


class BettingStrategy(ABC):
    @abstractmethod
    def hit_percentage(self, player_name, stat, pp_line, opponent, game_date=None):
        pass

    @abstractmethod
    def backtest_strategy(self, overwrite=False):
        pass


class DiscordStrategy(BettingStrategy):
    def __init__(self):
        pass

    def hit_percentage(self, player_name, stat, pp_line, opponent, game_date=None):
        gamelog = utils.get_games_by_player(
            player_name, game_date)
        stat_name = utils.get_stat_name(stat)
        past_5 = avg_player_stats_pastngames(
            gamelog, stat_name, pp_line, 5)
        past_10 = avg_player_stats_pastngames(
            gamelog, stat_name, pp_line, 10)
        past_15 = avg_player_stats_pastngames(
            gamelog, stat_name, pp_line, 15)
        season = avg_player_stats_season(gamelog, stat_name, pp_line)
        vs_opp = avg_player_stats_vsteam(
            gamelog, stat_name, pp_line, opponent)
        if gamelog.iloc[0]['GAME_DATE'] < game_date:
            nextgame = playernextngames.PlayerNextNGames(
                utils.get_player_id(player_name), 1).get_data_frames()[0]
            if len(nextgame) == 0:
                away = 0.5
            else:
                nextgame = nextgame.iloc[0]
                location = 'home' if nextgame['VISITOR_TEAM_ABBREVIATION'] == opponent else 'away'
                away = avg_player_stats_homeaway(
                    gamelog, stat_name, pp_line, location)
        else:
            thisgame = gamelog[gamelog['GAME_DATE'] == game_date]
            if len(thisgame) == 0:
                away = 0.5
            else:
                thisgame = thisgame.iloc[0]
                location = 'away' if '@' in thisgame['MATCHUP'] else 'home'
                away = avg_player_stats_homeaway(
                    gamelog, stat_name, pp_line, location)
        data_str = 'Past 5: {:.2f}%\nPast 10: {:.2f}%\nPast 15: {:.2f}%\nSeason: {:.2f}%\nAway: {:.2f}%\nVs. Opponent: {:.2f}%\nTotal: {:.2f}%'.format(
            past_5*100, past_10*100, past_15*100, season*100, away*100, vs_opp*100, (past_5 + past_10 + past_15 + season + away + vs_opp) / 6.0 * 100)
        # print(data_str)
        return (past_5 + past_10 + past_15 + season + away + vs_opp) / 6.0

    def backtest_strategy(self, overwrite=False):
        worksheet = utils.get_master_sheet()
        all_lines = pd.DataFrame(worksheet.get_all_records())
        confusion_matrix = {
            'pred_OVER': {
                'true_OVER': 0,
                'true_UNDER': 0,
                'true_PUSH': 0,
            },
            'pred_UNDER': {
                'true_OVER': 0,
                'true_UNDER': 0,
                'true_PUSH': 0,
            },
        }
        for i, row in all_lines.iterrows():
            if pd.isna(row['true_action']) or row['true_action'] == '':
                continue
            try:
                hp = self.hit_percentage(
                    player_name=row['name'],
                    stat=row['stat'],
                    pp_line=float(row['line']),
                    opponent=row['opponent'],
                    game_date=datetime.datetime.strptime(row['game_date'], '%Y-%m-%d'))
                action = 'OVER' if hp >= 0.5 else 'UNDER'
                true_action = row['true_action']
                if overwrite:
                    hp *= 100
                    abs_diff = abs(hp - 50)
                    hp = round(hp, 2)
                    abs_diff = round(abs_diff, 2)
                    worksheet.update_cell(i+2, 10, hp)
                    worksheet.update_cell(i+2, 11, abs_diff)
                    worksheet.update_cell(i+2, 12, action)
                confusion_matrix[f'pred_{action}'][f'true_{true_action}'] += 1
                print(f'Finished line {i+1}/{len(all_lines)}')
            except Exception as e:
                print(f'Error on row {i}: {e}, skipping...')
                continue
        return confusion_matrix


class LogisticRegression(BettingStrategy):
    def __init__(self, model_path=None):
        self.clf = load(model_path)

    def hit_percentage(self, player_name, stat, pp_line, opponent, game_date=None):
        gamelog = utils.get_games_by_player(
            player_name, game_date)
        stat_name = utils.get_stat_name(stat)
        past_5 = avg_player_stats_pastngames(
            gamelog, stat_name, pp_line, 5)
        past_10 = avg_player_stats_pastngames(
            gamelog, stat_name, pp_line, 10)
        past_15 = avg_player_stats_pastngames(
            gamelog, stat_name, pp_line, 15)
        season = avg_player_stats_season(gamelog, stat_name, pp_line)
        vs_opp = avg_player_stats_vsteam(
            gamelog, stat_name, pp_line, opponent)
        if gamelog.iloc[0]['GAME_DATE'] < game_date:
            nextgame = playernextngames.PlayerNextNGames(
                utils.get_player_id(player_name), 1).get_data_frames()[0]
            if len(nextgame) == 0:
                away = 0.5
            else:
                nextgame = nextgame.iloc[0]
                location = 'home' if nextgame['VISITOR_TEAM_ABBREVIATION'] == opponent else 'away'
                away = avg_player_stats_homeaway(
                    gamelog, stat_name, pp_line, location)
        else:
            thisgame = gamelog[gamelog['GAME_DATE'] == game_date]
            if len(thisgame) == 0:
                away = 0.5
            else:
                thisgame = thisgame.iloc[0]
                location = 'away' if '@' in thisgame['MATCHUP'] else 'home'
                away = avg_player_stats_homeaway(
                    gamelog, stat_name, pp_line, location)
        data_str = 'Past 5: {:.2f}%\nPast 10: {:.2f}%\nPast 15: {:.2f}%\nSeason: {:.2f}%\nAway: {:.2f}%\nVs. Opponent: {:.2f}%\nTotal: {:.2f}%'.format(
            past_5*100, past_10*100, past_15*100, season*100, away*100, vs_opp*100, (past_5 + past_10 + past_15 + season + away + vs_opp) / 6.0 * 100)
        probs = self.clf.predict_proba(
            [[past_5, past_10, past_15, season, vs_opp, away]])[0]
        return probs[1]

    def backtest_strategy(self, overwrite=False):
        worksheet = utils.get_master_sheet()
        all_lines = pd.DataFrame(worksheet.get_all_records())
        confusion_matrix = {
            'pred_OVER': {
                'true_OVER': 0,
                'true_UNDER': 0,
                'true_PUSH': 0,
            },
            'pred_UNDER': {
                'true_OVER': 0,
                'true_UNDER': 0,
                'true_PUSH': 0,
            },
        }
        for i, row in all_lines.iterrows():
            if pd.isna(row['true_action']) or row['true_action'] == '':
                continue
            try:
                hp = self.hit_percentage(
                    player_name=row['name'],
                    stat=row['stat'],
                    pp_line=float(row['line']),
                    opponent=row['opponent'],
                    game_date=datetime.datetime.strptime(row['game_date'], '%Y-%m-%d'))
                action = 'OVER' if hp >= 0.5 else 'UNDER'
                true_action = row['true_action']
                if overwrite:
                    hp *= 100
                    abs_diff = abs(hp - 50)
                    hp = round(hp, 2)
                    abs_diff = round(abs_diff, 2)
                    worksheet.update_cell(i+2, 10, hp)
                    # worksheet.update_cell(i+2, 11, abs_diff)
                    # worksheet.update_cell(i+2, 12, action)
                confusion_matrix[f'pred_{action}'][f'true_{true_action}'] += 1
                print(f'Finished line {i+1}/{len(all_lines)}')
                time.sleep(0.5)
            except Exception as e:
                print(f'Error on row {i}: {e}, skipping...')
                continue
        return confusion_matrix
