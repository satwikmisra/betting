import numpy as np
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
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playergamelog, leaguegamefinder, teamgamelog, boxscoretraditionalv2

all_predictors = [
    'past_games_over_line',
    'homeaway_over_line',
    'vsopponent_over_line',
    'rest1',
    'rest2',
    'rest3',
    'opp_give_up_ppg',
    'opp_give_up_rpg',
    'opp_give_up_apg',
    'opp_give_up_tovpg',
    # predictor name
]


class Predictor:
    def __init__(self, player_name, stat, opponent, pp_line, game_date):
        self.player_name = player_name
        self.team = utils.get_player_info(player_name)[
            'TEAM_ABBREVIATION'].iloc[0]
        self.stat = stat
        self.opponent = opponent
        self.pp_line = pp_line
        self.game_date = game_date

        self.gamelog = utils.get_games_by_player(player_name, game_date)
        self.team_gamelog = utils.get_games_by_team(self.team, game_date)

        self.thisgame = self.gamelog[self.gamelog['GAME_DATE'] == game_date]
        self.gamelog = self.gamelog[self.gamelog['GAME_DATE'] < game_date]
        if self.thisgame.empty:
            nextgames = playernextngames.PlayerNextNGames(
                utils.get_player_id(player_name), 1).get_data_frames()[0]
            if len(nextgames) == 0:
                raise ValueError("Cannot find player's next game!")
            else:
                self.thisgame = nextgames.iloc[0]
                self.location = 'home' if self.thisgame['VISITOR_TEAM_ABBREVIATION'] == opponent else 'away'
        else:
            self.location = 'home' if 'vs.' in self.thisgame['MATCHUP'].iloc[0] else 'away'

        self.predictors = {pname: None for pname in all_predictors}

    def get_predictors(self):
        for predictor_name in all_predictors:
            self.request_predictor(predictor_name)
        return self.predictors

    def request_predictor(self, predictor_name):
        if self.predictors[predictor_name]:
            return self.predictors[predictor_name]
        if predictor_name == 'past_games_over_line':
            self.past_games_over_line()
        elif predictor_name == 'homeaway_over_line':
            self.homeaway_over_line()
        elif predictor_name == 'vsopponent_over_line':
            self.vsopponent_over_line()
        elif predictor_name == 'usage_rate':
            self.usage_rate()
        elif predictor_name.startswith('opp_give_up'):
            self.defensive_predictors()
        elif predictor_name.startswith('rest'):
            self.days_since_last_game()
        else:
            raise ValueError(
                f"Predictor {predictor_name} not found! Must be one of {all_predictors}")
        return self.predictors[predictor_name]

    def past_games_over_line(self):
        num_games = min(25, len(self.gamelog))
        games_over_line = self.gamelog.head(
            num_games)[self.stat] >= self.pp_line
        discount_rate = 0.99
        self.predictors['past_games_over_line'] = (
            games_over_line * discount_rate ** np.arange(num_games)).sum() / num_games

    def days_since_last_game(self):
        last_game_date = self.gamelog.iloc[0]['GAME_DATE']
        days = (self.game_date - last_game_date).days
        self.predictors['rest1'] = int(days <= 1)
        self.predictors['rest2'] = int(days == 2)
        self.predictors['rest3'] = int(days >= 3)

    def homeaway_over_line(self):
        if self.location == 'home':
            filtered_log = self.gamelog[self.gamelog['MATCHUP'].str.contains(
                'vs.')]
        elif self.location == 'away':
            filtered_log = self.gamelog[self.gamelog['MATCHUP'].str.contains(
                '@')]
        else:
            raise ValueError("Location must be 'home' or 'away'")
        games_over_line = filtered_log[self.stat] >= self.pp_line
        self.predictors['homeaway_over_line'] = np.mean(games_over_line)

    def vsopponent_over_line(self):
        filtered_log = self.gamelog[self.gamelog['MATCHUP'].str.contains(
            self.opponent)]
        games_over_line = filtered_log[self.stat] >= self.pp_line
        self.predictors['vsopponent_over_line'] = np.mean(games_over_line)

    def usage_rate(self):
        usage_rates = []
        for _, game in self.gamelog.iterrows():
            team_game_stats = self.team_log[self.team_log['Game_ID']
                                            == game['Game_ID']]
            if team_game_stats.empty:
                continue  # Skip if no team stats found
            team_game_stats = team_game_stats.iloc[0]
            usg_percent = 100 * ((game['FGA'] + 0.44 * game['FTA'] + game['TOV']) * (
                240 / 5)) / (game['MIN'] * (team_game_stats['FGA'] + 0.44 * team_game_stats['FTA'] + team_game_stats['TOV']))
            usage_rates.append(usg_percent)
        self.predictors['usage_rate'] = np.mean(usage_rates)

    def defensive_predictors(self):
        opponent_gamelog = utils.get_games_by_team(self.opponent)
        opponent_gamelog = opponent_gamelog.head(3)
        opp_allowed_stat_list = []
        for _, game in opponent_gamelog.iterrows():
            game_id = game['Game_ID']
            box_score = boxscoretraditionalv2.BoxScoreTraditionalV2(
                game_id=game_id)
            time.sleep(1)
            box_score_data = box_score.team_stats.get_data_frame()
            if box_score_data['TEAM_ABBREVIATION'].iloc[0] == self.opponent:
                opp_allowed_stat_list.append(box_score_data.iloc[1].to_dict())
            else:
                opp_allowed_stat_list.append(box_score_data.iloc[0].to_dict())
        self.predictors['opp_give_up_ppg'] = np.mean(
            [game['PTS'] for game in opp_allowed_stat_list if game['PTS']])
        self.predictors['opp_give_up_rpg'] = np.mean(
            [game['REB'] for game in opp_allowed_stat_list if game['REB']])
        self.predictors['opp_give_up_apg'] = np.mean(
            [game['AST'] or 0 for game in opp_allowed_stat_list if game['AST']])
        self.predictors['opp_give_up_tovpg'] = np.mean(
            [game['TO'] for game in opp_allowed_stat_list if game['TO']])


def get_predictors(player_name, stat, opponent, pp_line, game_date):
    preds = Predictor(player_name, stat, opponent, pp_line, game_date)
    return np.array([preds.request_predictor(pname) for pname in all_predictors])


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
        return 0

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
        pred_vector = get_predictors(
            player_name, stat, opponent, pp_line, game_date)
        probs = self.clf.predict_proba([pred_vector])[0]
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


class AdaBoost(BettingStrategy):
    def __init__(self, model_path=None):
        self.clf = load(model_path)

    def hit_percentage(self, player_name, stat, pp_line, opponent, game_date=None):
        pred_vector = get_predictors(
            player_name, stat, opponent, pp_line, game_date)
        probs = self.clf.predict_proba([pred_vector])[0]
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


class KNN(BettingStrategy):
    def __init__(self, model_path=None):
        self.clf = load(model_path)

    def hit_percentage(self, player_name, stat, pp_line, opponent, game_date=None):
        pred_vector = get_predictors(
            player_name, stat, opponent, pp_line, game_date)
        probs = self.clf.predict_proba([pred_vector])[0]
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
                    stat=utils.get_stat_name(row['stat']),
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
