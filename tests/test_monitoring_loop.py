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

    assert "No match history to start from" in capsys.readouterr().out


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
    # Off, because a banner that only explains itself in verbose is the split this contract exists to prevent
    monkeypatch.setattr(lm_module, "VERBOSE_MODE", False)
    monkeypatch.setattr(lm_module, "DEBUG_MODE", False)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 300)
    script_profile(riot_api)

    run_loop(lm_module, riot_api, [{}, {}, {}])

    output = capsys.readouterr().out
    assert f"* Monitoring healthy for {RIOT_ID}. The user is not in a match with no match change since the last check" in output
    assert "Liveness check, timestamp:" in output


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
    # The first failure takes the one short retry, the second waits the polling interval
    assert "* Error: The Riot API is temporarily unavailable (retrying in 5 seconds)" in output
    assert "* Error: The Riot API is temporarily unavailable (retrying in 2 minutes, 30 seconds)" not in output
    assert output.count("* Error: The Riot API is temporarily unavailable") == 1
    assert fake_clock.slept[:2] == [lm_module.TRANSIENT_RETRY_SECONDS, lm_module.LOL_CHECK_INTERVAL]
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


# ---------------------------------------------------------------------------
# What a long run prints: the liveness banner, the outage reporter and the shared failure line
# ---------------------------------------------------------------------------


# Runs the loop for a fixed number of checks with the in-game answer the caller supplies
def run_checks(lm_module, riot_api, monkeypatch, answer, checks):
    script_profile(riot_api)
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", lambda **kwargs: [])
    remaining = {"n": checks}

    async def counted(puuid, region):
        remaining["n"] -= 1
        if remaining["n"] < 0:
            raise LoopFinished
        return answer(remaining["n"])

    monkeypatch.setattr(lm_module, "is_user_in_match", counted)
    with pytest.raises(LoopFinished):
        asyncio.run(lm_module.lol_monitor_user(RIOT_ID, "eun1", ""))


# Raises the Riot outage every check
def always_failing(_remaining):
    raise RuntimeError("500 Internal Server Error")


# Skips the in-game report, which is covered by its own tests and would need a live match payload here
async def skip_match_report(*args, **kwargs):
    return 0


# Reports no live snapshot, so the custom game capture has nothing to arm
async def no_live_snapshot(*args, **kwargs):
    return None


# Verifies the banner is timed against the setting rather than counted in checks, which is what drifts when
# a failing run retries on a different interval than a healthy one
def test_the_liveness_banner_is_timed_not_counted(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)

    run_checks(lm_module, riot_api, monkeypatch, lambda n: False, 36)

    # Checks land every five minutes over three hours, so the half-hourly reminder fires five times
    assert capsys.readouterr().out.count("Monitoring healthy for") == 5


# Verifies a check interval longer than the liveness interval still yields at most one banner per check,
# which is what the removed counter needed a floor to achieve
def test_a_poll_slower_than_the_banner_does_not_repeat_it(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 60)
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 3600)

    run_checks(lm_module, riot_api, monkeypatch, lambda n: False, 4)

    # The banner is due on every check after the first, and a run cannot print between checks
    assert capsys.readouterr().out.count("Monitoring healthy for") == 3


# Verifies a player who stays in a match still gets the banner, since gating it on the idle state is what
# left a week-long session with no periodic output at all
def test_a_player_in_a_match_still_gets_the_banner(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 300)
    monkeypatch.setattr(lm_module, "LOL_ACTIVE_CHECK_INTERVAL", 60)
    # The in-game report runs on the transition only, so the run starts already in a match
    monkeypatch.setattr(lm_module, "print_current_match", skip_match_report)
    monkeypatch.setattr(lm_module, "get_current_match_details", no_live_snapshot)

    run_checks(lm_module, riot_api, monkeypatch, lambda n: True, 20)

    assert f"* Monitoring healthy for {RIOT_ID}. The user is in a match with no match change since the last check" in capsys.readouterr().out


# Verifies the banner names the state as a fact rather than being gated on it
def test_the_banner_names_the_state_it_is_not_gated_on(lm_module, capsys):
    lm_module.print_liveness_banner(f"Monitoring healthy for {RIOT_ID}. The user is in a match with no match change since the last check")

    output = capsys.readouterr().out
    assert output.startswith(f"* Monitoring healthy for {RIOT_ID}. The user is in a match with no match change since the last check\n")
    assert "Liveness check, timestamp:" in output


# Verifies the banner is switched off entirely by the setting, which is the state the outage reporter falls back for
def test_the_banner_is_switched_off_by_the_setting(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 0)

    run_checks(lm_module, riot_api, monkeypatch, lambda n: False, 20)

    assert "Liveness check, timestamp:" not in capsys.readouterr().out


# Verifies a lasting failure is reported once and then carried by the liveness banner, rather than printing
# one block per check for as long as it lasts
def test_a_lasting_failure_is_reported_once_then_carried_by_the_banner(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)

    run_checks(lm_module, riot_api, monkeypatch, always_failing, 130)

    output = capsys.readouterr().out
    assert output.count("* Error: The Riot API is temporarily unavailable") == 1
    assert output.count("* Monitoring degraded for") == 21
    assert "The Riot API is temporarily unavailable since " in output


# Verifies the degraded reminder carries the failure and when it started, so it says strictly more than the
# per-check line it replaced
def test_the_degraded_reminder_names_the_failure_and_when_it_started(lm_module, capsys):
    advice = lm_module.classify_recovery_error(RuntimeError("500 Internal Server Error"))

    lm_module.print_outage_liveness(RIOT_ID, advice, TS)

    output = capsys.readouterr().out
    assert f"* Monitoring degraded for {RIOT_ID}. {advice.summary} since {lm_module.get_date_from_ts(TS)}" in output
    assert "Liveness check, timestamp:" in output


# Verifies the summary keeps its per-check cadence when the banner that would carry the reminder is off,
# since going fully silent for anyone who disabled it is a regression rather than a feature
def test_the_summary_keeps_its_cadence_when_the_banner_is_off(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 0)

    run_checks(lm_module, riot_api, monkeypatch, always_failing, 6)

    output = capsys.readouterr().out
    assert output.count("* Error: The Riot API is temporarily unavailable") == 6
    # The advice is still rendered once, so the repeats stay one line each
    assert output.count("To fix:") == 1


# Verifies a failure that clears says so, since a throttled failure no longer stops printing when it is over
def test_a_cleared_failure_is_reported_with_how_long_it_lasted(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)

    def clears_after_ten(remaining):
        if remaining > 20:
            raise RuntimeError("500 Internal Server Error")
        return False

    run_checks(lm_module, riot_api, monkeypatch, clears_after_ten, 30)

    # Nine checks failed: the first waits the short retry, the other eight wait the polling interval
    assert f"* Monitoring recovered for {RIOT_ID} after 40 minutes, 5 seconds" in capsys.readouterr().out


# Verifies the recovery line restarts the quiet period, or the healthy banner lands immediately after it
# because the timer had been running for the whole outage
def test_the_recovery_line_restarts_the_quiet_period(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)

    def clears_near_the_end(remaining):
        if remaining > 3:
            raise RuntimeError("500 Internal Server Error")
        return False

    # Three checks follow the recovery, which is fifteen minutes: less than the half-hour quiet period it restarts
    run_checks(lm_module, riot_api, monkeypatch, clears_near_the_end, 18)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith(("* Monitoring recovered", "* Monitoring healthy"))]
    assert lines and lines[0].startswith("* Monitoring recovered")
    assert not lines[1:], "a healthy banner followed the recovery line without a fresh quiet period"


# Verifies a failure that changes category is a different failure, so it is reported in full again
def test_a_failure_that_changes_category_is_reported_again(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)

    def changing(remaining):
        raise RuntimeError("500 Internal Server Error" if remaining > 4 else "401 Unauthorized")

    run_checks(lm_module, riot_api, monkeypatch, changing, 8)

    output = capsys.readouterr().out
    assert "* Error: The Riot API is temporarily unavailable" in output
    assert "* Error: Riot rejected the configured API key" in output


# Verifies a rate limit that lasts is reminded on the liveness cadence too, rather than only reported once
def test_a_lasting_rate_limit_is_reminded_on_the_same_cadence(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)

    def limited(_remaining):
        raise RuntimeError("429 Too Many Requests")

    run_checks(lm_module, riot_api, monkeypatch, limited, 24)

    output = capsys.readouterr().out
    assert output.count("* Error: Riot is rate limiting requests") == 1
    assert output.count("* Monitoring degraded for") == 3


# Verifies a failure while the player is in a match waits the active interval, since that is what the run
# would have waited had the check succeeded
def test_a_failure_in_a_match_waits_the_active_interval(lm_module, riot_api, fake_clock, monkeypatch):
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)
    monkeypatch.setattr(lm_module, "LOL_ACTIVE_CHECK_INTERVAL", 60)
    monkeypatch.setattr(lm_module, "print_current_match", skip_match_report)
    monkeypatch.setattr(lm_module, "get_current_match_details", no_live_snapshot)
    state = {"ingame": False}

    def in_a_match_then_failing(remaining):
        if state["ingame"]:
            raise RuntimeError("500 Internal Server Error")
        state["ingame"] = True
        return True

    run_checks(lm_module, riot_api, monkeypatch, in_a_match_then_failing, 4)

    # The first check enters the match, the second spends the short retry, the rest wait the active interval
    assert fake_clock.slept == [60, lm_module.TRANSIENT_RETRY_SECONDS, 60, 60]


# Verifies the failure line puts the label first, the failure second and the schedule in parentheses, which
# is the one shape every monitor in this family prints
def test_the_failure_line_puts_the_variable_part_last(lm_module):
    advice = lm_module.classify_recovery_error(RuntimeError("500 Internal Server Error"))

    assert lm_module.render_recovery_advice(advice, retry_note="retrying in 5 minutes", with_fix=False) == "* Error: The Riot API is temporarily unavailable (retrying in 5 minutes)"


# Verifies the raw exception text reaches a debug run, since the summary alone is not enough to file a report
def test_the_failure_line_carries_the_technical_detail_in_debug(lm_module, monkeypatch):
    advice = lm_module.classify_recovery_error(RuntimeError("500 Internal Server Error"))
    quiet = lm_module.render_recovery_advice(advice)
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    loud = lm_module.render_recovery_advice(advice)

    assert "Technical detail:" not in quiet
    assert f"Technical detail: {advice.detail}" in loud


# Verifies a detail that only repeats the summary is dropped, since a line saying nothing costs a line
def test_a_detail_that_repeats_the_summary_is_dropped(lm_module, monkeypatch):
    advice = lm_module.classify_recovery_error(RuntimeError("500 Internal Server Error"))
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)

    assert "Technical detail:" not in lm_module.render_recovery_advice(advice._replace(detail=advice.summary))


# Verifies a sub-operation takes the label slot rather than inventing a second sentence shape
def test_a_label_replaces_the_error_word_rather_than_the_sentence(lm_module):
    advice = lm_module.classify_recovery_error(RuntimeError("500 Internal Server Error"))

    assert lm_module.render_recovery_advice(advice, retry_note="", with_fix=False, label="Warning").startswith("* Warning: ")


# Verifies advice is a To fix line rather than a second starred line, since one failure gets one report
def test_the_failure_report_is_one_starred_line(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)

    run_checks(lm_module, riot_api, monkeypatch, always_failing, 4)

    monitoring = capsys.readouterr().out.split("Timestamp:", 1)[1]
    starred = [line for line in monitoring.splitlines() if line.startswith("* ")]
    assert starred == ["* Error: The Riot API is temporarily unavailable (retrying in 5 seconds)"]


# Verifies one short retry absorbs a blip, and only one, so a lasting outage still waits the polling interval
def test_only_one_short_retry_is_spent_per_outage(lm_module, riot_api, fake_clock, monkeypatch):
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)

    run_checks(lm_module, riot_api, monkeypatch, always_failing, 4)

    assert fake_clock.slept == [lm_module.TRANSIENT_RETRY_SECONDS, 300, 300, 300]


# Verifies a rejected credential is not retried quickly, since nothing about it resolves in five seconds
def test_a_rejected_credential_skips_the_short_retry(lm_module, riot_api, fake_clock, monkeypatch):
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)

    def rejected(_remaining):
        raise RuntimeError("401 Unauthorized")

    run_checks(lm_module, riot_api, monkeypatch, rejected, 3)

    assert fake_clock.slept == [300, 300, 300]


# Verifies a fresh short retry is available after the run recovers, so the next blip is absorbed too
def test_the_short_retry_is_available_again_after_a_recovery(lm_module, riot_api, fake_clock, monkeypatch):
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 0)

    def blip(remaining):
        if remaining in (3, 1):
            raise RuntimeError("500 Internal Server Error")
        return False

    run_checks(lm_module, riot_api, monkeypatch, blip, 5)

    assert fake_clock.slept.count(lm_module.TRANSIENT_RETRY_SECONDS) == 2


# Verifies a rate limit waits the period Riot named rather than burning the short retry on it
def test_a_rate_limit_waits_the_period_riot_named(lm_module, riot_api, fake_clock, monkeypatch):
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)

    class RateLimited(RuntimeError):
        response = type("Response", (), {"headers": {"Retry-After": "42"}})()

    def limited(_remaining):
        raise RateLimited("429 Too Many Requests")

    run_checks(lm_module, riot_api, monkeypatch, limited, 3)

    assert fake_clock.slept == [42, 42, 42]


# Verifies a rate limit with no period named falls back to the polling interval rather than to zero
def test_a_rate_limit_without_a_period_waits_the_polling_interval(lm_module, riot_api, fake_clock, monkeypatch):
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 300)

    def limited(_remaining):
        raise RuntimeError("429 Too Many Requests")

    run_checks(lm_module, riot_api, monkeypatch, limited, 2)

    assert fake_clock.slept == [300, 300]


# Verifies a period the service asked for is capped, so a header the tool cannot vouch for cannot stall a run
def test_a_hostile_rate_limit_period_is_capped(lm_module):
    hostile = type("Error", (), {"response": type("Response", (), {"headers": {"Retry-After": "999999"}})()})()

    assert lm_module.riot_retry_after_seconds(hostile, 300) == lm_module.RIOT_MAX_RETRY_AFTER_SECONDS


# Verifies the cap bounds only what the service asked for, since clamping the tool's own polling interval
# would make a rate-limited run poll faster than it was configured to
def test_the_cap_does_not_shorten_the_tools_own_interval(lm_module):
    beyond_the_cap = int(lm_module.RIOT_MAX_RETRY_AFTER_SECONDS) + 600

    assert lm_module.riot_retry_after_seconds(RuntimeError("429 Too Many Requests"), beyond_the_cap) == beyond_the_cap


# Verifies a failure the tool can retry away is alerted only once the outage has lasted the alert delay, so a
# blip of a few checks reaches nobody while a real outage still does
@pytest.mark.parametrize("checks,expected", [(3, 0), (4, 1)])
def test_a_retryable_failure_is_alerted_once_the_outage_has_lasted(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys, checks, expected):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)

    # The short retry and then two full intervals put the fourth failing check past the five minute delay
    run_checks(lm_module, riot_api, monkeypatch, always_failing, checks)

    assert len(sent_emails) == expected


# Verifies a failure nothing here can retry away is alerted on the first check, since waiting would change nothing
def test_a_failure_that_cannot_clear_itself_is_alerted_at_once(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)

    def rejected(_remaining):
        raise RuntimeError("401 Unauthorized")

    run_checks(lm_module, riot_api, monkeypatch, rejected, 1)

    assert [email["subject"] for email in sent_emails] == [f"lol_monitor: API key error! (user: {USER})"]


# Verifies any monitoring failure alerts both channels, and once per category rather than once per check
def test_a_monitoring_failure_alerts_both_channels_once(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)

    run_checks(lm_module, riot_api, monkeypatch, always_failing, 8)

    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"] == f"lol_monitor: monitoring error (user: {USER})"
    assert "The Riot API is temporarily unavailable" in sent_emails[0]["body"]
    assert "To fix:" in sent_emails[0]["body"]


# The guide link sits under the fix in the HTML body too, since HTML renders the newline the fix carries as a space
def test_the_guide_link_keeps_its_own_line_in_the_html_body(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)

    run_checks(lm_module, riot_api, monkeypatch, always_failing, 8)

    parts = sent_emails[0]["body_html"].split("<br>")
    fix_index = next(index for index, part in enumerate(parts) if part.startswith("To fix: "))
    assert parts[fix_index + 1].startswith("Guide: https://")
    assert "\n" not in parts[fix_index]


# Verifies a failure that changes category earns each channel a new alert, since it is a different failure
def test_a_changed_failure_category_earns_a_new_alert(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)

    def changing(remaining):
        raise RuntimeError("500 Internal Server Error" if remaining > 4 else "401 Unauthorized")

    # The first category has to last past the alert delay before the second one takes over
    run_checks(lm_module, riot_api, monkeypatch, changing, 12)

    assert [email["subject"] for email in sent_emails] == [f"lol_monitor: monitoring error (user: {USER})", f"lol_monitor: API key error! (user: {USER})"]


# Verifies each channel is tracked on its own, so a channel that failed is retried on the next check while
# the one that succeeded is not sent the same alert twice
def test_a_failed_channel_is_retried_and_a_delivered_one_is_not(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)
    webhook_attempts = {"count": 0}

    # Fails the first webhook and delivers every later one, the way an outage at the webhook service looks
    def flaky_webhook(*args, **kwargs):
        webhook_attempts["count"] += 1
        return 1 if webhook_attempts["count"] == 1 else 0

    monkeypatch.setattr(lm_module, "send_webhook", flaky_webhook)

    run_checks(lm_module, riot_api, monkeypatch, always_failing, 8)

    # The email landed once and was never resent, while the webhook was retried until it landed
    assert len(sent_emails) == 1
    assert webhook_attempts["count"] == 2


# Verifies a delivery on a check the reporter keeps quiet still closes its block, so the line is not left
# looking like a run that stopped there
@pytest.mark.parametrize("alerts,expected_blocks", [(False, 1), (True, 2)])
def test_an_alert_on_a_quiet_check_still_closes_its_block(lm_module, riot_api, fake_clock, monkeypatch, sent_emails, capsys, alerts, expected_blocks):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", alerts)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)

    # The first failure spends the short retry and reaches no alert, so the delivery lands on the second
    # check, where the reporter has already gone quiet about the same category and prints nothing itself
    run_checks(lm_module, riot_api, monkeypatch, always_failing, 4)

    blocks = capsys.readouterr().out.split("Timestamp:", 1)[1].count("Timestamp:")
    assert len(sent_emails) == (1 if alerts else 0)
    assert blocks == expected_blocks, "the alert was delivered on a check that printed no trailer"


# Verifies every suppressed report is still traced, so a support transcript loses nothing to the throttling
def test_a_suppressed_failure_is_still_traced_in_debug(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)

    run_checks(lm_module, riot_api, monkeypatch, always_failing, 6)

    output = capsys.readouterr().out
    assert output.count("outcome=failed, code=riot.unavailable") == 6
    assert output.count("* Error: The Riot API is temporarily unavailable") == 1


# Verifies the monitoring loop prints no verbose line of its own, so nothing it prints can float without a trailer
def test_the_loop_prints_no_standalone_verbose_line(lm_module, riot_api, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1800)

    run_checks(lm_module, riot_api, monkeypatch, lambda n: False, 5)

    assert capsys.readouterr().out.split("Timestamp:", 1)[1].split("\n", 2)[2].strip() == ""
