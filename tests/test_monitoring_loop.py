"""Offline end-to-end tests that drive the monitoring loop with scripted Riot API responses."""

import asyncio
import csv

import pytest

from conftest import LoopFinished

PUUID = "test-puuid-value"
RIOT_ID = "misiektoja#EUNE"
USER = "misiektoja"
TS = 1767226800  # Thu 01 Jan 2026, 00:20:00 UTC


@pytest.fixture(autouse=True)
# Keeps the CSV history and the log inside the test directory
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


# Builds a finished match payload shaped like the one the match endpoint returns
def match_payload(win=True):
    return {"info": {"gameStartTimestamp": TS * 1000, "gameEndTimestamp": (TS + 1800) * 1000, "gameCreation": (TS - 60) * 1000, "gameDuration": 1800, "gameMode": "CLASSIC", "queueId": 420, "mapId": 11, "gameType": "MATCHED_GAME", "gameVersion": "15.19.700.1234", "teams": [], "participants": [
        {"puuid": PUUID, "riotIdGameName": USER, "teamId": 100, "championName": "Ahri", "championId": 103, "win": win, "kills": 7, "deaths": 2, "assists": 11, "champLevel": 15, "role": "SOLO", "lane": "MIDDLE"},
        {"puuid": "puuid-rival", "riotIdGameName": "rival", "teamId": 200, "championName": "Zed", "championId": 238, "win": not win, "kills": 2, "deaths": 7, "assists": 3, "champLevel": 14, "role": "SOLO", "lane": "MIDDLE"},
    ]}}


# Builds a live match payload shaped like the one the spectator endpoint returns
def live_match_payload(game_type="MATCHED_GAME", game_mode="CLASSIC"):
    return {"gameId": 987654321, "gameStartTime": TS * 1000, "gameLength": 300, "gameMode": game_mode, "gameQueueConfigId": 420, "mapId": 11, "gameType": game_type, "gameVersion": "15.19.700.1234", "participants": [
        {"riotId": f"{USER}#EUNE", "teamId": 100, "championId": 103},
        {"riotId": "rival#EUNE", "teamId": 200, "championId": 238},
    ], "bannedChampions": []}


# Scripts the profile endpoints the tool reads once at startup
def script_profile(riot_api, ranked_entries=None, masteries=None):
    riot_api.script("get_account_v1_by_riot_id", {"puuid": PUUID})
    riot_api.script("get_lol_summoner_v4_by_puuid", {"summonerLevel": 421, "revisionDate": TS * 1000})
    riot_api.script("get_lol_league_v4_entries_by_puuid", ranked_entries if ranked_entries is not None else [])
    riot_api.script("get_lol_champion_v4_top_masteries_by_puuid", masteries if masteries is not None else [])


# Runs the monitoring loop through the supplied cycles and stops when they are exhausted
def run_loop(lm_module, riot_api, cycles, csv_file_name="", initial_match_ids=None, match=None):
    state = {"live": None}
    remaining = list(cycles)

    # Serves the startup history once, then one scripted cycle per poll
    def next_match_ids(**kwargs):
        if kwargs["queries"]["count"] == 20:
            return list(initial_match_ids or [])
        if not remaining:
            raise LoopFinished
        cycle = remaining.pop(0)
        state["live"] = cycle.get("live")
        return list(cycle.get("match_ids", []))

    riot_api.script("get_lol_match_v5_match_ids_by_puuid", next_match_ids)
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", lambda **kwargs: state["live"] or {})
    riot_api.script("get_lol_match_v5_match", match if match is not None else match_payload())

    with pytest.raises(LoopFinished):
        asyncio.run(lm_module.lol_monitor_user(RIOT_ID, "eun1", csv_file_name))


# Verifies the run starts by reporting who is being monitored and their account details
def test_startup_reports_the_account(lm_module, riot_api, fake_clock, capsys):
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [])

    output = capsys.readouterr().out
    assert f"Riot ID (name#tag):\t\t{RIOT_ID}" in output
    assert f"Riot PUUID:\t\t\t{PUUID}" in output
    assert "Summoner level:\t\t\t421" in output
    assert "Last modified:\t\t\tThu 01 Jan 2026, 00:20:00" in output


# Verifies both ranked queues are reported with the record and the win rate
def test_startup_reports_ranked_standing(lm_module, riot_api, fake_clock, capsys):
    script_profile(riot_api, ranked_entries=[
        {"queueType": "RANKED_SOLO_5x5", "tier": "PLATINUM", "rank": "II", "leaguePoints": 64, "wins": 60, "losses": 40},
        {"queueType": "RANKED_FLEX_SR", "tier": "GOLD", "rank": "IV", "leaguePoints": 12, "wins": 5, "losses": 5},
    ])

    run_loop(lm_module, riot_api, [])

    output = capsys.readouterr().out
    assert "Solo/Duo:\t\t\tPLATINUM II (64 LP) - Wins: 60 / Losses: 40 (Winrate: 60.0%)" in output
    assert "Flex:\t\t\t\tGOLD IV (12 LP) - Wins: 5 / Losses: 5 (Winrate: 50.0%)" in output


# Verifies a player with no rank is shown as unranked instead of a blank line
def test_startup_reports_an_unranked_player(lm_module, riot_api, fake_clock, capsys):
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [])

    output = capsys.readouterr().out
    assert "Solo/Duo:\t\t\tUnranked" in output
    assert "Flex:\t\t\t\tUnranked" in output


# Verifies the most played champions are listed with their level and point total
def test_startup_reports_champion_mastery(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", {103: "Ahri"})
    script_profile(riot_api, masteries=[{"championId": 103, "championLevel": 10, "championPoints": 300000}])

    run_loop(lm_module, riot_api, [])

    assert "1. Ahri:             Level 10 (300,000 points)" in capsys.readouterr().out


# Verifies the last known match is shown at startup so the run begins with context
def test_startup_shows_the_last_known_match(lm_module, riot_api, fake_clock, capsys):
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [], initial_match_ids=["EUN1_1"])

    output = capsys.readouterr().out
    assert "User last played match:" in output
    assert "Match ID:\t\t\tEUN1_1" in output


# Verifies a player with no history is called out rather than treated as an error
def test_startup_without_history_is_called_out(lm_module, riot_api, fake_clock, capsys):
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [])

    assert "Could not fetch initial match history" in capsys.readouterr().out


# Verifies a Riot ID that cannot be resolved stops the run instead of monitoring nothing
def test_an_unresolvable_riot_id_stops_the_run(lm_module, riot_api, fake_clock):
    riot_api.script("get_account_v1_by_riot_id", RuntimeError("404 Not Found"))

    with pytest.raises(SystemExit) as raised:
        asyncio.run(lm_module.lol_monitor_user(RIOT_ID, "eun1", ""))

    assert raised.value.code == 2


# Verifies a newly finished match is announced, reported and emailed once
def test_a_finished_match_is_reported_and_emailed(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True)
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"match_ids": ["EUN1_2"]}], initial_match_ids=["EUN1_1"])

    output = capsys.readouterr().out
    assert "*** Found 1 new completed match(es)" in output
    assert "Match ID:\t\t\tEUN1_2" in output
    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"].startswith(f"LoL user {USER} match summary")


# Verifies a match already seen is not reported again on the next poll
def test_a_match_is_reported_only_once(lm_module, riot_api, fake_clock, capsys):
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"match_ids": ["EUN1_2"]}, {"match_ids": ["EUN1_2"]}], initial_match_ids=["EUN1_1"])

    assert capsys.readouterr().out.count("*** Found") == 1


# Verifies matches known at startup are not reported as new
def test_startup_history_is_not_reported_as_new(lm_module, riot_api, fake_clock, capsys):
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"match_ids": ["EUN1_1"]}], initial_match_ids=["EUN1_1"])

    assert "*** Found" not in capsys.readouterr().out


# Verifies every finished match reaches the CSV history
def test_finished_matches_reach_the_csv_history(lm_module, riot_api, fake_clock, isolated_working_directory):
    history = isolated_working_directory / "matches.csv"
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"match_ids": ["EUN1_2"]}], initial_match_ids=["EUN1_1"], csv_file_name=str(history))

    rows = list(csv.DictReader(history.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["Champion"] == "Ahri"


# Verifies starting a match is announced while the player is still in it
def test_a_started_match_is_announced(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", {103: "Ahri", 238: "Zed"})
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"live": live_match_payload()}])

    output = capsys.readouterr().out
    assert f"*** LoL user {USER} is in game now" in output
    assert "Match ID:\t\t\t987654321" in output


# Verifies leaving a match is announced and emailed once the start was announced
def test_stopping_a_match_is_announced_and_emailed(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True)
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"live": live_match_payload()}, {"live": None}])

    assert f"*** LoL user {USER} stopped playing !" in capsys.readouterr().out
    subjects = [message["subject"] for message in sent_emails]
    assert len(subjects) == 2
    assert subjects[0].startswith(f"LoL user {USER} is in game now")
    assert subjects[1] == f"LoL user {USER} stopped playing"


# Verifies a player who never appeared in a match is not reported as having stopped
def test_a_player_who_never_started_is_not_reported_as_stopped(lm_module, riot_api, fake_clock, sent_emails, capsys):
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"live": None}, {"live": None}])

    assert "stopped playing" not in capsys.readouterr().out
    assert sent_emails == []


# Verifies a custom game, which never reaches match history, is saved once no completion arrives
def test_a_custom_game_is_saved_after_the_grace_period(lm_module, riot_api, fake_clock, isolated_working_directory, capsys):
    history = isolated_working_directory / "matches.csv"
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"live": live_match_payload(game_type="CUSTOM_GAME")}, {"live": None}, {}, {}], csv_file_name=str(history))

    assert "Saved custom game match to CSV" in capsys.readouterr().out
    rows = list(csv.DictReader(history.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["Team 1"] == f"'{USER}'"
    assert rows[0]["Victory"] == "N/A"


# Verifies a match that does reach match history is not also saved from the live snapshot
def test_a_completed_match_cancels_the_custom_game_save(lm_module, riot_api, fake_clock, isolated_working_directory, capsys):
    history = isolated_working_directory / "matches.csv"
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"live": live_match_payload(game_type="CUSTOM_GAME")}, {"live": None}, {"match_ids": ["EUN1_2"]}, {}, {}], csv_file_name=str(history))

    output = capsys.readouterr().out
    assert "Saved custom game match to CSV" not in output
    rows = list(csv.DictReader(history.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["Victory"] == "Yes"


# Verifies a normal match is never saved from the live snapshot, since it arrives through match history
def test_a_normal_match_is_not_saved_from_the_snapshot(lm_module, riot_api, fake_clock, isolated_working_directory):
    history = isolated_working_directory / "matches.csv"
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"live": live_match_payload()}, {"live": None}, {}, {}], csv_file_name=str(history))

    assert list(csv.DictReader(history.open(encoding="utf-8"))) == []


# Verifies polling speeds up while the player is in a match and slows down once they are idle again
def test_the_polling_interval_follows_the_player(lm_module, riot_api, fake_clock, monkeypatch):
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 150)
    monkeypatch.setattr(lm_module, "LOL_ACTIVE_CHECK_INTERVAL", 45)
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{"live": None}, {"live": live_match_payload()}, {"live": None}, {}, {}, {}, {}])

    # Idle, then in game, then the grace period that keeps polling fast right after a match
    assert fake_clock.slept[:6] == [150, 45, 45, 45, 45, 45]
    assert fake_clock.slept[6] == 150


# Verifies the liveness line is printed while an idle player produces no other output
def test_liveness_check_reports_the_loop_is_alive(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_CHECK_COUNTER", 2)
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{}, {}, {}])

    assert "Liveness check, timestamp:" in capsys.readouterr().out


# Verifies an unexpected failure is retried instead of ending the run
def test_an_unexpected_failure_is_retried(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    script_profile(riot_api)
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", [])
    attempts = {"count": 0}

    # Fails the in-game check twice and then ends the run
    async def failing_check(puuid, region):
        attempts["count"] += 1
        if attempts["count"] > 2:
            raise LoopFinished
        raise RuntimeError("500 Internal Server Error")

    monkeypatch.setattr(lm_module, "is_user_in_match", failing_check)

    with pytest.raises(LoopFinished):
        asyncio.run(lm_module.lol_monitor_user(RIOT_ID, "eun1", ""))

    output = capsys.readouterr().out
    assert output.count("* Retrying in 2 minutes, 30 seconds") == 2
    # The same category twice renders its hint once, so a lasting outage does not repeat the advice every cycle
    assert output.count("To fix:") == 1


# Verifies a rejected API key is called out and alerted on once, since only a new key can fix it
def test_a_rejected_api_key_is_alerted_once(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)
    script_profile(riot_api)
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", [])
    attempts = {"count": 0}

    # Reports an expired key and then ends the run
    async def rejected_key(puuid, region):
        attempts["count"] += 1
        if attempts["count"] > 2:
            raise LoopFinished
        raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr(lm_module, "is_user_in_match", rejected_key)

    with pytest.raises(LoopFinished):
        asyncio.run(lm_module.lol_monitor_user(RIOT_ID, "eun1", ""))

    assert "Riot rejected the configured API key" in capsys.readouterr().out
    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"] == f"lol_monitor: API key error! (user: {USER})"
