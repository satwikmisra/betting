from basketball_reference_web_scraper import client
from basketball_reference_web_scraper.data import Location, Outcome, PeriodType, Position, Team
import datetime
import requests
from bs4 import BeautifulSoup
from utils import team_mapping, get_player_id


def avg_player_stats_away(player_id, stat_name, pp_line, location, year=2024):
    game_list = client.regular_season_player_box_scores(
        player_identifier=player_id, season_end_year=year)

    if location == "AWAY":
        games_locationfilter = [
            game for game in game_list if game['location'] == Location.AWAY]
    elif location == "HOME":
        games_locationfilter = [
            game for game in game_list if game['location'] == Location.HOME]

    above_threshold_games = [
        game for game in games_locationfilter if game[stat_name] > pp_line]
    percentage_above_threshold = (len(above_threshold_games) / len(
        games_locationfilter)) * 100 if len(games_locationfilter) > 0 else 0

    return percentage_above_threshold


def avg_player_stats_vsteam(player_id, stat_name, pp_line, opponent, year=2024):
    opponent_enum = team_mapping(opponent)
    game_list = client.regular_season_player_box_scores(
        player_identifier=player_id, season_end_year=year)
    games_opponentfilter = [
        game for game in game_list if game['opponent'] == opponent_enum]
    above_threshold_games = [
        game for game in games_opponentfilter if game[stat_name] > pp_line]
    percentage_above_threshold = (len(above_threshold_games) / len(
        games_opponentfilter)) * 100 if len(games_opponentfilter) > 0 else 0

    return percentage_above_threshold


def avg_player_stats_pastngames(player_id, stat_name, pp_line, num_games, year=2024):
    game_list = []
    while len(game_list) < num_games:
        aux_game_list = client.regular_season_player_box_scores(
            player_identifier=player_id, season_end_year=year)
        aux_game_list.reverse()
        game_list.extend(aux_game_list)
        year = year - 1
    game_list = game_list[:num_games]

    above_threshold_games = [
        game for game in game_list if game[stat_name] > pp_line]
    percentage_above_threshold = (
        len(above_threshold_games) / len(game_list)) * 100 if len(game_list) > 0 else 0

    return percentage_above_threshold


def avg_player_stats_season(player_id, stat_name, pp_line, year=2024):
    game_list = client.regular_season_player_box_scores(
        player_identifier=player_id, season_end_year=year)
    above_threshold_games = [
        game for game in game_list if game[stat_name] > pp_line]
    percentage_above_threshold = (
        len(above_threshold_games) / len(game_list)) * 100 if len(game_list) > 0 else 0
    return percentage_above_threshold
