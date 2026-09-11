"""Offline tests for the finished-match report, the in-game report and match history listing."""

import asyncio
import csv

import pytest

from conftest import Replies

PUUID = "test-puuid-value"
USER = "misiektoja"
TS = 1767226800  # Thu 01 Jan 2026, 00:20:00 UTC


# Raised the way the Riot client reports a match whose details need an RSO token
class ForbiddenMatch(Exception):
    status = 403


# Builds one participant of a finished match
def participant(name, team_id=100, champion="Ahri", champion_id=103, win=True, puuid=None, **overrides):
    entry = {"puuid": puuid or f"puuid-{name}", "riotIdGameName": name, "teamId": team_id, "championName": champion, "championId": champion_id, "win": win, "kills": 7, "deaths": 2, "assists": 11, "champLevel": 15, "role": "SOLO", "lane": "MIDDLE"}
    entry.update(overrides)
    return entry


# Builds a finished match payload shaped like the one the match endpoint returns
def match_payload(participants=None, teams=None, **info_overrides):
    info = {"gameStartTimestamp": TS * 1000, "gameEndTimestamp": (TS + 1800) * 1000, "gameCreation": (TS - 60) * 1000, "gameDuration": 1800, "gameMode": "CLASSIC", "queueId": 420, "mapId": 11, "gameType": "MATCHED_GAME", "gameVersion": "15.19.700.1234"}
    info.update(info_overrides)
    info["participants"] = participants if participants is not None else [participant(USER, puuid=PUUID), participant("teammate", champion="Lux", champion_id=99), participant("rival", team_id=200, champion="Zed", champion_id=238, win=False)]
    info["teams"] = teams if teams is not None else []
    return {"info": info}


# Runs the single match report against a payload the caller supplies
def report_match(lm_module, match, csv_file_name=None, notify=False, match_id="EUN1_1"):
    return asyncio.run(lm_module.process_and_print_single_match(match_id, PUUID, USER, "eun1", notify, csv_file_name, cached_match_data=match))


# Verifies the match header names the mode, queue, map, type and patch a player would look for
def test_match_header_identifies_the_game(lm_module, fake_clock, capsys):
    report_match(lm_module, match_payload())

    output = capsys.readouterr().out
    assert "Match ID:\t\t\tEUN1_1" in output
    assert "Game mode:\t\t\tSummoner's Rift" in output
    assert "Queue:\t\t\t\tRanked Solo/Duo" in output
    assert "Map:\t\t\t\tSummoner's Rift" in output
    assert "Game type:\t\t\tMatched" in output
    assert "Game version:\t\t\t15.19 (15.19.700.1234)" in output


# Verifies the timeline reports when the match ran, when it was created and how long it lasted
def test_match_timeline_is_reported(lm_module, fake_clock, capsys):
    report_match(lm_module, match_payload())

    output = capsys.readouterr().out
    assert "Match start-end date:\t\tThu 01 Jan 2026, 00:20:00 - 00:50:00" in output
    assert "Match creation:\t\t\tThu 01 Jan 2026, 00:19:00" in output
    assert "Match duration:\t\t\t30 minutes" in output
    assert "Match finished:" in output


# Verifies the report returns the start and stop timestamps the monitoring loop tracks
def test_the_match_timestamps_are_returned(lm_module, fake_clock):
    assert report_match(lm_module, match_payload()) == (TS, TS + 1800)


# Verifies the monitored player's own result is reported, not another participant's
def test_the_monitored_player_result_is_reported(lm_module, fake_clock, capsys):
    report_match(lm_module, match_payload())

    output = capsys.readouterr().out
    assert "Victory:\t\t\tYes" in output
    assert "Kills/Deaths/Assists:\t\t7/2/11" in output
    assert "Champion:\t\t\tAhri" in output
    assert "Level:\t\t\t\t15" in output
    assert "Role:\t\t\t\tSOLO" in output
    assert "Lane:\t\t\t\tMIDDLE" in output


# Verifies a defeat is reported as such rather than defaulting to a win
def test_a_defeat_is_reported(lm_module, fake_clock, capsys):
    match = match_payload(participants=[participant(USER, puuid=PUUID, win=False)])

    report_match(lm_module, match)

    assert "Victory:\t\t\tNo" in capsys.readouterr().out


# Verifies a mode with no role or lane leaves those lines out instead of printing a placeholder
def test_modes_without_a_role_or_lane_omit_those_lines(lm_module, fake_clock, capsys):
    match = match_payload(participants=[participant(USER, puuid=PUUID, role="NONE", lane="NONE")])

    report_match(lm_module, match)

    output = capsys.readouterr().out
    assert "Role:" not in output
    assert "Lane:" not in output


# Verifies both team rosters are listed with the champion each player used
def test_both_team_rosters_are_listed(lm_module, fake_clock, capsys):
    report_match(lm_module, match_payload())

    output = capsys.readouterr().out
    assert "Teams:\t\t\t\t2" in output
    assert "- misiektoja (Ahri)" in output
    assert "- teammate (Lux)" in output
    assert "- rival (Zed)" in output


# Verifies the monitored player's own team is marked so it can be spotted at a glance
def test_the_monitored_players_team_is_marked(lm_module, fake_clock, capsys):
    report_match(lm_module, match_payload())

    output = capsys.readouterr().out
    assert "Team id 100: ⭐" in output
    assert "Team id 200:\n" in output


# Verifies bans are listed per team in pick order
def test_bans_are_reported(lm_module, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", {64: "LeeSin", 55: "Katarina"})
    teams = [{"teamId": 100, "bans": [{"championId": 64, "pickTurn": 1}]}, {"teamId": 200, "bans": [{"championId": 55, "pickTurn": 2}, {"championId": -1, "pickTurn": 3}]}]

    report_match(lm_module, match_payload(teams=teams))

    output = capsys.readouterr().out
    assert "Banned champions:" in output
    assert "- LeeSin (pick 1)" in output
    assert "- Katarina (pick 2)" in output
    assert "- No ban (pick 3)" in output


# Verifies the match is appended to the CSV history with the player's own result
def test_the_match_is_appended_to_the_csv_history(lm_module, fake_clock, tmp_path):
    history = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(history))

    report_match(lm_module, match_payload(), csv_file_name=str(history))

    row = list(csv.DictReader(history.open(encoding="utf-8")))[0]
    assert row["Match Start"] == "2026-01-01 00:20:00"
    assert row["Match Stop"] == "2026-01-01 00:50:00"
    assert row["Duration"] == "30 minutes"
    assert row["Game Mode"] == "Summoner's Rift"
    assert row["Victory"] == "Yes"
    assert row["Champion"] == "Ahri"
    assert row["Team 1"] == "'misiektoja' 'teammate'"
    assert row["Team 2"] == "'rival'"


# Verifies a match with no role or lane records those columns as unavailable instead of NONE
def test_missing_role_and_lane_are_recorded_as_unavailable(lm_module, fake_clock, tmp_path):
    history = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(history))
    match = match_payload(participants=[participant(USER, puuid=PUUID, role="NONE", lane="NONE", champLevel=None)])

    report_match(lm_module, match, csv_file_name=str(history))

    row = list(csv.DictReader(history.open(encoding="utf-8")))[0]
    assert (row["Role"], row["Lane"], row["Level"]) == ("N/A", "N/A", "N/A")


# Verifies the match summary email carries the result in the subject and the full report in both bodies
def test_the_match_summary_email_carries_the_result(lm_module, fake_clock, sent_emails):
    report_match(lm_module, match_payload(), notify=True)

    assert len(sent_emails) == 1
    message = sent_emails[0]
    assert message["subject"] == "LoL user misiektoja match summary (Thu 01 Jan 00:20 - 00:50, 30 minutes, Yes)"
    assert "Champion: Ahri" in message["body"]
    assert "Kills/deaths/assists: 7/2/11" in message["body"]
    assert "<b>misiektoja</b> (Ahri)" in message["body_html"]


# Verifies nothing is emailed while status notifications are off
def test_no_email_without_status_notifications(lm_module, fake_clock, sent_emails):
    report_match(lm_module, match_payload())

    assert sent_emails == []


# Verifies a match whose details need an RSO token is skipped quietly by default
def test_a_forbidden_match_is_skipped_by_default(lm_module, riot_api, fake_clock, sent_emails, capsys):
    riot_api.script("get_lol_match_v5_match", ForbiddenMatch("403 Forbidden"))

    result = asyncio.run(lm_module.process_and_print_single_match("EUN1_1", PUUID, USER, "eun1", True, None))

    assert result == (0, 0)
    assert capsys.readouterr().out == ""
    assert sent_emails == []


# Verifies a forbidden match can be surfaced instead, for players who want to know it happened
def test_a_forbidden_match_can_be_reported(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(lm_module, "INCLUDE_FORBIDDEN_MATCHES", True)
    riot_api.script("get_lol_match_v5_match", ForbiddenMatch("403 Forbidden"))

    result = asyncio.run(lm_module.process_and_print_single_match("EUN1_1", PUUID, USER, "eun1", True, None))

    assert result == (0, 0)
    assert "Match details require RSO token" in capsys.readouterr().out
    assert sent_emails[0]["subject"] == "LoL user misiektoja new forbidden match detected"


# Verifies any other failure while fetching a match is reported with the match it happened on
def test_other_match_failures_are_reported(lm_module, riot_api, fake_clock, capsys):
    riot_api.script("get_lol_match_v5_match", RuntimeError("500 Internal Server Error"))

    result = asyncio.run(lm_module.process_and_print_single_match("EUN1_1", PUUID, USER, "eun1", False, None))

    assert result == (0, 0)
    assert "unexpected error occurred while processing match EUN1_1" in capsys.readouterr().out


# Verifies a match is fetched from the API when the caller has nothing cached
def test_a_match_is_fetched_when_it_is_not_cached(lm_module, riot_api, fake_clock):
    riot_api.script("get_lol_match_v5_match", match_payload())

    result = asyncio.run(lm_module.process_and_print_single_match("EUN1_1", PUUID, USER, "eun1", False, None))

    assert result == (TS, TS + 1800)
    request = riot_api.requests_to("get_lol_match_v5_match")[0]
    assert request["region"] == "europe"
    assert request["id"] == "EUN1_1"


# Builds a live match payload shaped like the one the spectator endpoint returns
def live_match_payload(**overrides):
    payload = {"gameId": 987654321, "gameStartTime": TS * 1000, "gameLength": 600, "gameMode": "CLASSIC", "gameQueueConfigId": 420, "mapId": 11, "gameType": "MATCHED_GAME", "gameVersion": "15.19.700.1234", "participants": [
        {"riotId": f"{USER}#EUNE", "teamId": 100, "championId": 103},
        {"riotId": "teammate#EUNE", "teamId": 100, "championId": 99},
        {"riotId": "rival#EUNE", "teamId": 200, "championId": 238},
    ], "bannedChampions": [{"championId": 64, "pickTurn": 1, "teamId": 100}, {"championId": 55, "pickTurn": 2, "teamId": 200}]}
    payload.update(overrides)
    return payload


@pytest.fixture
# Names the champions the live match reports so the output does not depend on Data Dragon
def known_champions(monkeypatch, lm_module):
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", {103: "Ahri", 99: "Lux", 238: "Zed", 64: "LeeSin", 55: "Katarina"})


# Verifies a live match is announced with the game details, the rosters and the bans
def test_a_live_match_is_announced(lm_module, riot_api, fake_clock, known_champions, capsys):
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", live_match_payload())

    start_ts = asyncio.run(lm_module.print_current_match(PUUID, USER, "eun1", TS - 7200, TS - 3600, False))

    output = capsys.readouterr().out
    assert start_ts == TS
    assert f"*** LoL user {USER} is in game now" in output
    assert "Match ID:\t\t\t987654321" in output
    assert "Game mode:\t\t\tSummoner's Rift" in output
    assert "Match duration:\t\t\t10 minutes" in output
    assert "Champion:\t\t\tAhri" in output
    assert "Team id 100: ⭐" in output
    assert "- misiektoja (Ahri)" in output
    assert "- LeeSin (pick 1)" in output


# Verifies a roster name Riot supplies cannot repaint the terminal the live match is printed to
def test_a_live_roster_name_is_sanitized(lm_module, riot_api, fake_clock, known_champions, capsys):
    hostile = chr(27) + "[2J" + chr(27) + "[31mrival" + chr(27) + "[0m"
    payload = live_match_payload()
    payload["participants"][2] = {"riotId": f"{hostile}#EUNE", "teamId": 200, "championId": 238}
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", payload)

    asyncio.run(lm_module.print_current_match(PUUID, USER, "eun1", TS - 7200, TS - 3600, False))

    output = capsys.readouterr().out
    assert chr(27) not in output
    assert "- rival (Zed)" in output


# Verifies the live snapshot saved for a custom game carries the sanitized name, not the one Riot sent
def test_a_live_snapshot_name_is_sanitized(lm_module, riot_api, fake_clock, known_champions):
    hostile = chr(27) + "[31mrival" + chr(27) + "[0m"
    payload = live_match_payload()
    payload["participants"][2] = {"riotIdGameName": hostile, "teamId": 200, "championId": 238}
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", payload)

    snapshot = asyncio.run(lm_module.get_current_match_details(PUUID, "eun1"))

    names = [entry["riotIdName"] for entry in snapshot["participants"]]
    assert "rival" in names
    assert not any(chr(27) in name for name in names)


# Verifies a match that has only just started reports that rather than a zero duration
def test_a_match_that_just_started_is_labeled(lm_module, riot_api, fake_clock, known_champions, capsys):
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", live_match_payload(gameLength=0))

    asyncio.run(lm_module.print_current_match(PUUID, USER, "eun1", TS - 7200, TS - 3600, False))

    assert "Match duration:\t\t\tjust starting ..." in capsys.readouterr().out


# Verifies a live match with no usable start time falls back to now instead of reporting 1970
def test_a_missing_start_time_falls_back_to_now(lm_module, riot_api, fake_clock, known_champions):
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", live_match_payload(gameStartTime=0))

    assert asyncio.run(lm_module.print_current_match(PUUID, USER, "eun1", TS - 7200, TS - 3600, False)) == int(fake_clock.time())


# Verifies the in-game email names the player and carries the rosters in both bodies
def test_the_in_game_email_carries_the_rosters(lm_module, riot_api, fake_clock, known_champions, sent_emails):
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", live_match_payload())

    asyncio.run(lm_module.print_current_match(PUUID, USER, "eun1", TS - 7200, TS - 3600, True))

    message = sent_emails[0]
    assert message["subject"].startswith(f"LoL user {USER} is in game now")
    assert "- misiektoja (Ahri)" in message["body"]
    assert "<b>misiektoja</b> (Ahri)" in message["body_html"]
    assert "Banned champions" in message["body"]


# Verifies a player who is not in a match is reported as such, with nothing emailed
def test_no_live_match_is_reported_plainly(lm_module, riot_api, fake_clock, sent_emails, capsys):
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", {})

    assert asyncio.run(lm_module.print_current_match(PUUID, USER, "eun1", TS - 7200, TS - 3600, True)) == 0
    assert "User is not in game currently" in capsys.readouterr().out
    assert sent_emails == []


# Verifies the live snapshot keeps the mode, the start time and every participant for a later CSV row
def test_the_live_snapshot_keeps_what_a_custom_game_needs(lm_module, riot_api, fake_clock):
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", live_match_payload(gameType="CUSTOM_GAME"))

    snapshot = asyncio.run(lm_module.get_current_match_details(PUUID, "eun1"))

    assert snapshot["mode"] == "Summoner's Rift"
    assert snapshot["game_type"] == "CUSTOM_GAME"
    assert snapshot["start_ts"] == TS
    assert snapshot["participants"][0] == {"riotIdName": USER, "teamId": 100, "championId": 103}


# Verifies no snapshot is produced when the player is not in a match
def test_no_snapshot_without_a_live_match(lm_module, riot_api, fake_clock):
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", {})

    assert asyncio.run(lm_module.get_current_match_details(PUUID, "eun1")) == {}


# Verifies the requested range of matches is listed oldest first, each with its position in the history
def test_match_history_is_listed_oldest_first(lm_module, riot_api, fake_clock, capsys):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", ["EUN1_3", "EUN1_2", "EUN1_1"])
    riot_api.script("get_lol_match_v5_match", match_payload())

    asyncio.run(lm_module.print_match_history(PUUID, USER, "eun1", 1, 3, None))

    output = capsys.readouterr().out
    assert output.index("Match number:\t\t\t3") < output.index("Match number:\t\t\t1")
    assert [request["id"] for request in riot_api.requests_to("get_lol_match_v5_match")] == ["EUN1_1", "EUN1_2", "EUN1_3"]


# Verifies listing a range asks for exactly that slice of the history
def test_listing_a_range_requests_that_slice(lm_module, riot_api, fake_clock):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", ["EUN1_5", "EUN1_4", "EUN1_3"])
    riot_api.script("get_lol_match_v5_match", match_payload())

    asyncio.run(lm_module.print_match_history(PUUID, USER, "eun1", 3, 5, None))

    assert riot_api.requests_to("get_lol_match_v5_match_ids_by_puuid")[0]["queries"] == {"start": 2, "count": 3}


# Verifies every listed match reaches the CSV history
def test_listed_matches_are_saved_to_the_csv_history(lm_module, riot_api, fake_clock, tmp_path):
    history = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(history))
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", ["EUN1_2", "EUN1_1"])
    riot_api.script("get_lol_match_v5_match", match_payload())

    asyncio.run(lm_module.print_match_history(PUUID, USER, "eun1", 1, 2, str(history)))

    assert len(list(csv.DictReader(history.open(encoding="utf-8")))) == 2


# Verifies listing never emails, since it reports history the player asked for on purpose
def test_listing_never_emails(lm_module, riot_api, fake_clock, monkeypatch, sent_emails):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True)
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", ["EUN1_1"])
    riot_api.script("get_lol_match_v5_match", match_payload())

    asyncio.run(lm_module.print_match_history(PUUID, USER, "eun1", 1, 1, None))

    assert sent_emails == []


# Verifies an empty history is reported instead of printing an empty listing
def test_an_empty_history_is_reported(lm_module, riot_api, fake_clock, capsys):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", [])

    assert asyncio.run(lm_module.print_match_history(PUUID, USER, "eun1", 1, 5, None)) == (0, 0)
    assert "No match history found" in capsys.readouterr().out


# Verifies a request whose lower bound is above its upper bound lists nothing
def test_an_inverted_range_lists_nothing(lm_module, riot_api, fake_clock):
    assert asyncio.run(lm_module.print_match_history(PUUID, USER, "eun1", 5, 1, None)) == (0, 0)
    assert riot_api.requests_to("get_lol_match_v5_match_ids_by_puuid") == []


# Verifies a shortfall of displayable matches is called out rather than passing unnoticed
def test_a_shortfall_of_displayable_matches_is_reported(lm_module, riot_api, fake_clock, capsys):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", ["EUN1_2", "EUN1_1"])
    riot_api.script("get_lol_match_v5_match", Replies([match_payload(), ForbiddenMatch("403 Forbidden")]))

    asyncio.run(lm_module.print_match_history(PUUID, USER, "eun1", 1, 2, None))

    assert "Not enough displayable matches found" in capsys.readouterr().out
