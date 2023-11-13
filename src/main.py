import api
import utils


def hit_percentage(player_id, stat_name, pp_line, opponent, quiet=True):
    past_5 = api.avg_player_stats_pastngames(player_id, stat_name, pp_line, 5)
    past_10 = api.avg_player_stats_pastngames(
        player_id, stat_name, pp_line, 10)
    past_15 = api.avg_player_stats_pastngames(
        player_id, stat_name, pp_line, 15)
    season = api.avg_player_stats_season(player_id, stat_name, pp_line)
    away = api.avg_player_stats_away(player_id, stat_name, pp_line, "AWAY")
    vs_opp = api.avg_player_stats_vsteam(
        player_id, stat_name, pp_line, opponent)
    hp = (past_5 + past_10 + past_15 + season + away + vs_opp) / 6.0
    if not quiet:
        print(
            f"Percentage of last 5 games where {player_id} scored more than {pp_line} {stat_name}: {past_5:.2f}%")
        print(
            f"Percentage of last 10 games where {player_id} scored more than {pp_line} {stat_name}: {past_10:.2f}%")
        print(
            f"Percentage of last 15 games where {player_id} scored more than {pp_line} {stat_name}: {past_15:.2f}%")
        print(
            f"Percentage of season where {player_id} scored more than {pp_line} {stat_name}: {season:.2f}%")
        print(
            f"Percentage of away games where {player_id} scored more than {pp_line} {stat_name}: {away:.2f}%")
        print(
            f"Percentage of games vs {opponent} where {player_id} scored more than {pp_line} {stat_name}: {vs_opp:.2f}%")
        print('-'*20)
        print(f"Total Hit Percentage: {hp:.2f}%")
    return hp


hit_percentage('antetgi01', 'points_scored', 27.5, "NYK", quiet=False)
