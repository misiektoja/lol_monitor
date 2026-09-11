"""Tests for the CSV match history the tool writes alongside the log."""

import asyncio
import csv

import pytest

TS = 1767226800  # Thu 01 Jan 2026, 00:20:00 UTC


# Writes one complete match row with sensible defaults
def write_match(lm_module, target, **overrides):
    row = {"start_date_ts": "2026-01-01 00:20:00", "stop_date_ts": "2026-01-01 00:50:00", "duration_ts": "30 minutes", "game_mode": "Summoner's Rift", "victory": "Yes", "kills": 7, "deaths": 2, "assists": 11, "champion": "Ahri", "level": 15, "role": "SOLO", "lane": "MIDDLE", "team1": "'misiektoja' 'teammate'", "team2": "'rival' 'other'"}
    row.update(overrides)
    lm_module.write_csv_entry(str(target), **row)
    return row


# Verifies a new file gets the documented header row
def test_new_file_starts_with_the_header(lm_module, tmp_path):
    target = tmp_path / "matches.csv"

    lm_module.init_csv_file(str(target))

    assert list(csv.reader(target.open(encoding="utf-8")))[0] == lm_module.csvfieldnames
    assert lm_module.csvfieldnames[:5] == ["Match Start", "Match Stop", "Duration", "Game Mode", "Victory"]


# Verifies an existing history keeps its rows instead of being re-headered on restart
def test_existing_history_is_not_rewritten(lm_module, tmp_path):
    target = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(target))
    write_match(lm_module, target)

    lm_module.init_csv_file(str(target))

    assert len(list(csv.DictReader(target.open(encoding="utf-8")))) == 1


# Verifies an empty leftover file is given a header rather than left unusable
def test_empty_file_is_given_a_header(lm_module, tmp_path):
    target = tmp_path / "matches.csv"
    target.write_text("", encoding="utf-8")

    lm_module.init_csv_file(str(target))

    assert list(csv.reader(target.open(encoding="utf-8")))[0] == lm_module.csvfieldnames


# Verifies every column of a finished match round trips through the file
def test_a_match_row_round_trips(lm_module, tmp_path):
    target = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(target))

    write_match(lm_module, target)

    row = list(csv.DictReader(target.open(encoding="utf-8")))[0]
    assert row["Game Mode"] == "Summoner's Rift"
    assert row["Victory"] == "Yes"
    assert (row["Kills"], row["Deaths"], row["Assists"]) == ("7", "2", "11")
    assert row["Champion"] == "Ahri"
    assert row["Team 1"] == "'misiektoja' 'teammate'"
    assert row["Team 2"] == "'rival' 'other'"


# Verifies a Riot name containing a comma or a quote keeps the file parsable
def test_names_with_separators_stay_parsable(lm_module, tmp_path):
    target = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(target))

    write_match(lm_module, target, team1="'name, with comma' 'name \"quoted\"'")

    row = list(csv.DictReader(target.open(encoding="utf-8")))[0]
    assert row["Team 1"] == "'name, with comma' 'name \"quoted\"'"


# Verifies an unwritable path is reported with the file name instead of surfacing a bare OS error
def test_unwritable_path_is_reported_with_the_file_name(lm_module, tmp_path):
    unreachable = tmp_path / "missing-directory" / "matches.csv"

    with pytest.raises(RuntimeError, match="Could not initialize CSV file"):
        lm_module.init_csv_file(str(unreachable))

    with pytest.raises(RuntimeError, match="Failed to write to CSV file"):
        write_match(lm_module, unreachable)


# Builds a live match snapshot of a custom game
def custom_game_snapshot():
    return {"mode": "Summoner's Rift", "mode_raw": "CLASSIC", "game_type": "CUSTOM_GAME", "start_ts": TS, "participants": [
        {"riotIdName": "misiektoja", "teamId": 100, "championId": 103},
        {"riotIdName": "teammate", "teamId": 100, "championId": 99},
        {"riotIdName": "rival", "teamId": 200, "championId": 238},
    ]}


# Verifies a custom game, which never reaches match history, is still recorded from the live snapshot
def test_custom_game_is_recorded_from_the_live_snapshot(lm_module, tmp_path):
    target = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(target))

    asyncio.run(lm_module.save_custom_match_to_csv(custom_game_snapshot(), "misiektoja", TS, TS + 1800, str(target)))

    row = list(csv.DictReader(target.open(encoding="utf-8")))[0]
    assert row["Match Start"] == "2026-01-01 00:20:00"
    assert row["Match Stop"] == "2026-01-01 00:50:00"
    assert row["Duration"] == "30 minutes"
    assert row["Game Mode"] == "Summoner's Rift"
    assert row["Team 1"] == "'misiektoja' 'teammate'"
    assert row["Team 2"] == "'rival'"
    assert row["Champion"] == "103"


# Verifies the values a live snapshot cannot know are recorded as unavailable rather than guessed
def test_unknown_custom_game_values_are_recorded_as_unavailable(lm_module, tmp_path):
    target = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(target))

    asyncio.run(lm_module.save_custom_match_to_csv(custom_game_snapshot(), "misiektoja", TS, TS + 1800, str(target)))

    row = list(csv.DictReader(target.open(encoding="utf-8")))[0]
    assert [row[column] for column in ("Victory", "Kills", "Deaths", "Assists", "Level", "Role", "Lane")] == ["N/A"] * 7


# Verifies the snapshot's own start time wins over the one the caller passed
def test_the_snapshot_start_time_wins(lm_module, tmp_path):
    target = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(target))

    asyncio.run(lm_module.save_custom_match_to_csv(custom_game_snapshot(), "misiektoja", TS + 99999, TS + 1800, str(target)))

    assert list(csv.DictReader(target.open(encoding="utf-8")))[0]["Match Start"] == "2026-01-01 00:20:00"


# Verifies nothing is written when there is no snapshot or no CSV file configured
def test_nothing_is_written_without_a_snapshot_or_a_file(lm_module, tmp_path):
    target = tmp_path / "matches.csv"
    lm_module.init_csv_file(str(target))

    asyncio.run(lm_module.save_custom_match_to_csv({}, "misiektoja", TS, TS + 1800, str(target)))
    asyncio.run(lm_module.save_custom_match_to_csv(custom_game_snapshot(), "misiektoja", TS, TS + 1800, ""))

    assert list(csv.DictReader(target.open(encoding="utf-8"))) == []
