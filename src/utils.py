from basketball_reference_web_scraper import client
from basketball_reference_web_scraper.data import Location, Outcome, PeriodType, Position, Team
import datetime
import requests
from bs4 import BeautifulSoup


team_name_mapping = {
    "ATL": Team.ATLANTA_HAWKS,
    "BOS": Team.BOSTON_CELTICS,
    "BKN": Team.BROOKLYN_NETS,
    "CHA": Team.CHARLOTTE_HORNETS,
    "CHI": Team.CHICAGO_BULLS,
    "CLE": Team.CLEVELAND_CAVALIERS,
    "DAL": Team.DALLAS_MAVERICKS,
    "DEN": Team.DENVER_NUGGETS,
    "DET": Team.DETROIT_PISTONS,
    "GSW": Team.GOLDEN_STATE_WARRIORS,
    "HOU": Team.HOUSTON_ROCKETS,
    "IND": Team.INDIANA_PACERS,
    "LAC": Team.LOS_ANGELES_CLIPPERS,
    "LAL": Team.LOS_ANGELES_LAKERS,
    "MEM": Team.MEMPHIS_GRIZZLIES,
    "MIA": Team.MIAMI_HEAT,
    "MIL": Team.MILWAUKEE_BUCKS,
    "MIN": Team.MINNESOTA_TIMBERWOLVES,
    "NOP": Team.NEW_ORLEANS_PELICANS,
    "NYK": Team.NEW_YORK_KNICKS,
    "OKC": Team.OKLAHOMA_CITY_THUNDER,
    "ORL": Team.ORLANDO_MAGIC,
    "PHI": Team.PHILADELPHIA_76ERS,
    "PHX": Team.PHOENIX_SUNS,
    "POR": Team.PORTLAND_TRAIL_BLAZERS,
    "SAC": Team.SACRAMENTO_KINGS,
    "SAS": Team.SAN_ANTONIO_SPURS,
    "TOR": Team.TORONTO_RAPTORS,
    "UTA": Team.UTAH_JAZZ,
    "WAS": Team.WASHINGTON_WIZARDS,
}


def team_mapping(team_name):
    team_name = team_name.upper()
    return team_name_mapping[team_name]


def get_teams():
    return list(team_name_mapping.keys())


def get_player_id(player_name):
    parts = player_name.lower().split()
    last_name = parts[-1]
    first_name = parts[0]
    first_two_letters = first_name[:2]
    return f'{last_name[:5]}{first_two_letters}01'
