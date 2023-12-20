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

# Predictor functions:


def avg_points_given_by_position(opp_team_gamelog, stat_name, position):

    filtered_log = gamelog[opponents]


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


def get_past_10_game_usage_rates(player_name):
    # Get player and team IDs
    team_name = utils.get_player_info(player_name)['TEAM_ABBREVIATION'].iloc[0]
    player_id = utils.get_player_id(player_name)
    time.sleep(1)

    team_id = [team['id'] for team in teams.get_teams(
    ) if team['abbreviation'].lower() == team_name.lower()][0]

    # Fetch player's last 10 games
    player_log = playergamelog.PlayerGameLog(
        player_id=player_id, season='2023-24').get_data_frames()[0]
    last_10_games = player_log.head(10)

    if last_10_games.empty:
        return f"No recent games found for {player_name}"

    time.sleep(1)
    usage_rates = []

    for _, game in last_10_games.iterrows():
        # Fetch team's stats for each game
        team_log = teamgamelog.TeamGameLog(
            team_id=team_id, season='2023-24').get_data_frames()[0]
        team_game_stats = team_log[team_log['Game_ID'] == game['Game_ID']]

        if team_game_stats.empty:
            continue  # Skip if no team stats found

        player_stats = game
        team_stats = team_game_stats.iloc[0]

        # Calculate usage rate for each game
        usg_percent = 100 * ((player_stats['FGA'] + 0.44 * player_stats['FTA'] + player_stats['TOV']) * (
            240 / 5)) / (player_stats['MIN'] * (team_stats['FGA'] + 0.44 * team_stats['FTA'] + team_stats['TOV']))
        usage_rates.append(usg_percent)

    return np.mean(usage_rates)


# past 5 games
#
def get_opponent_stats(opponent_name, stat_name, num_games=None):
    opponent_team_id = utils.get_team_id(opponent_name)
    gamefinder = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=opponent_team_id, season_nullable='2023-24')
    time.sleep(5)
    games = gamefinder.get_data_frames()[0]
    num_games = num_games or len(games)
    opp_allowed_stat_list = []
    for i in range(0, num_games):
        iter_game_id = games['GAME_ID'].iloc[i]
        box_score = boxscoretraditionalv2.BoxScoreTraditionalV2(
            game_id=iter_game_id)
        time.sleep(5)
        box_score_data = box_score.team_stats.get_data_frame()
        if box_score_data['TEAM_ID'].iloc[0] == opponent_team_id:
            opp_allowed_stat_list.append(box_score_data[stat_name].iloc[1])
        else:
            opp_allowed_stat_list.append(box_score_data[stat_name].iloc[0])
        print(f'Finished game {i+1}/{num_games}')
    return opp_allowed_stat_list


print(get_opponent_stats('Memphis Grizzlies', 'PTS', num_games=5))


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


class AdaBoost(BettingStrategy):
    def __init__(self, model_path=None):
        self.clf = load(model_path)

    def hit_percentage(self, player_name, stat, pp_line, opponent, game_date=None):
        gamelog = utils.get_games_by_player(
            player_name, game_date)
        thisgame = gamelog[gamelog['GAME_DATE'] == game_date]
        gamelog = gamelog[gamelog['GAME_DATE'] < game_date]
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
        if len(thisgame) == 0:
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
            thisgame = thisgame.iloc[0]
            location = 'away' if '@' in thisgame['MATCHUP'] else 'home'
            away = avg_player_stats_homeaway(
                gamelog, stat_name, pp_line, location)
        b2b = days_since_last_game(gamelog, game_date)
        data_str = 'Past 5: {:.2f}%\nPast 10: {:.2f}%\nPast 15: {:.2f}%\nSeason: {:.2f}%\nAway: {:.2f}%\nVs. Opponent: {:.2f}%\nTotal: {:.2f}%'.format(
            past_5*100, past_10*100, past_15*100, season*100, away*100, vs_opp*100, (past_5 + past_10 + past_15 + season + away + vs_opp) / 6.0 * 100)
        probs = self.clf.predict_proba(
            [[past_5, past_10, past_15, season, vs_opp, away, b2b]])[0]
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


# run these lines to update old hit percentages
# strategy = AdaBoost('models/adaboostmodel.joblib')
# strategy.backtest_strategy(overwrite=True)
