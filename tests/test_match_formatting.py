"""Tests for the labels, names and rosters the match reports are built from."""

import pytest


@pytest.mark.parametrize("riot_id,expected", [
    ("misiektoja#EUNE", ("misiektoja", "EUNE")),
    ("name#with#hashes", ("name", "with#hashes")),
    ("player#1234", ("player", "1234")),
])
# Verifies a Riot ID is split into the name and tag line the API is queried with
def test_riot_id_is_split_into_name_and_tag(lm_module, riot_id, expected):
    assert lm_module.get_user_riot_name_tag(riot_id) == expected


# Verifies a Riot ID without a tag line is refused with an explanation of the expected format
def test_riot_id_without_a_tag_is_refused(lm_module, capsys):
    assert lm_module.get_user_riot_name_tag("misiektoja") == ("", "")
    assert "That is not a complete Riot ID" in capsys.readouterr().out


@pytest.mark.parametrize("game_type,expected", [
    ("MATCHED_GAME", "Matched"),
    ("CUSTOM_GAME", "Custom"),
    ("RANKED_GAME", "Ranked"),
    ("BOT", "Co-op vs AI"),
    ("ARAM_UNRANKED_5x5", "ARAM"),
    (None, "Unknown"),
    ("", "Unknown"),
])
# Verifies the raw game type from Riot is shown as the label a player recognizes
def test_game_types_are_humanized(lm_module, game_type, expected):
    assert lm_module.humanize_game_type(game_type) == expected


# Verifies a game type Riot adds later is still readable instead of being dropped
def test_unknown_game_type_is_made_readable(lm_module):
    assert lm_module.humanize_game_type("SOME_NEW_MODE") == "Some New Mode"


@pytest.mark.parametrize("game_version,expected", [
    ("15.19.700.1234", "15.19 (15.19.700.1234)"),
    ("15.19", "15.19"),
    ("Unknown", "Unknown"),
    (None, "Unknown"),
    ("", "Unknown"),
    ("weird-build", "weird-build"),
])
# Verifies the patch is shown as the short version players talk about, with the full build kept alongside
def test_game_version_labels(lm_module, game_version, expected):
    assert lm_module.format_game_version_label(game_version) == expected


@pytest.mark.parametrize("participant,expected", [
    ({"riotIdGameName": "misiektoja", "summonerName": "old name"}, "misiektoja"),
    ({"riotId": {"gameName": "misiektoja"}}, "misiektoja"),
    ({"riotId": {"riotId": "misiektoja#EUNE"}}, "misiektoja"),
    ({"riotId": "misiektoja#EUNE"}, "misiektoja"),
    ({"summonerName": "legacy name"}, "legacy name"),
    ({}, "unknown"),
])
# Verifies a participant name is found in whichever field this API version populated
def test_participant_names_are_resolved_from_every_known_field(lm_module, participant, expected):
    assert lm_module.get_participant_display_name(participant) == expected


@pytest.mark.parametrize("name,identifier,expected", [
    ("Ahri", 103, "Ahri"),
    (None, 103, "103"),
    ("Unknown", 103, "103"),
    (None, None, "Unknown"),
    (None, 0, "Unknown"),
])
# Verifies a champion, queue or map falls back to its numeric id rather than showing nothing
def test_named_values_fall_back_to_the_identifier(lm_module, name, identifier, expected):
    assert lm_module.format_named_value(name, identifier) == expected


# Verifies the first participant creates the team
def test_first_member_creates_the_team(lm_module):
    teams = []

    lm_module.add_new_team_member(teams, 100, "misiektoja")

    assert teams == [{"id": 100, "members": ["misiektoja"]}]


# Verifies later participants join the team they belong to instead of creating duplicates
def test_members_join_their_own_team(lm_module):
    teams = []

    for team_id, member in ((100, "one"), (200, "two"), (100, "three"), (200, "four")):
        lm_module.add_new_team_member(teams, team_id, member)

    assert teams == [{"id": 100, "members": ["one", "three"]}, {"id": 200, "members": ["two", "four"]}]


# Verifies a roster entry splits into the player and the champion beside them
@pytest.mark.parametrize("entry,expected", [
    ("misiektoja (Ahri)", ("misiektoja", " (Ahri)")),
    ("misiektoja", ("misiektoja", "")),
    ("", ("", "")),
    ("a (b) (c)", ("a", " (b) (c)")),
])
def test_a_roster_entry_splits_into_player_and_champion(lm_module, entry, expected):
    assert lm_module.split_team_member(entry) == expected


# Verifies the Discord roster marks the monitored player and leaves every other line as it was
def test_the_discord_roster_marks_the_monitored_player(lm_module):
    lines = ["Team id 100: ⭐", "- misiektoja (Ahri)", "- teammate (Lux)", "", "Team id 200:", "- rival (Zed)"]

    rendered = lm_module.format_teams_markdown(lines, "misiektoja")

    assert rendered == "Team id 100: ⭐\n- **misiektoja** (Ahri)\n- teammate (Lux)\n\nTeam id 200:\n- rival (Zed)\n"


# Verifies the monitored player is marked even when their champion is unknown
def test_a_monitored_player_without_a_champion_is_marked(lm_module):
    assert lm_module.format_teams_markdown(["- misiektoja"], "misiektoja") == "- **misiektoja**\n"


# Verifies only an exact name is marked, so a player whose name contains the monitored one is left alone
def test_only_an_exact_name_is_marked(lm_module):
    assert lm_module.format_teams_markdown(["- misiektoja2 (Zed)"], "misiektoja") == "- misiektoja2 (Zed)\n"


# Verifies an empty roster produces nothing rather than a blank line
def test_an_empty_discord_roster_renders_as_nothing(lm_module):
    assert lm_module.format_teams_markdown([], "misiektoja") == ""


# Verifies a draft with no bans produces nothing to print
def test_no_bans_produce_no_output(lm_module):
    lines, shared_pool = lm_module.format_banned_champions_output({100: [], 200: []})

    assert lines == []
    assert shared_pool is False


# Verifies bans from both teams are listed per team, in pick order
def test_bans_are_listed_per_team_in_pick_order(lm_module):
    bans_by_team = {200: [(4, "Yasuo"), (2, "Zed")], 100: [(3, "Ahri"), (1, "Lux")]}

    lines, shared_pool = lm_module.format_banned_champions_output(bans_by_team)

    assert shared_pool is False
    assert lines == ["Team id 100:", "- Lux (pick 1)", "- Ahri (pick 3)", "", "Team id 200:", "- Zed (pick 2)", "- Yasuo (pick 4)"]


# Verifies a mode where only one team bans is shown as a single shared pool, without a team header
def test_a_single_banning_team_is_shown_as_a_shared_pool(lm_module):
    lines, shared_pool = lm_module.format_banned_champions_output({100: [(2, "Zed"), (1, "Lux")], 200: []})

    assert shared_pool is True
    assert lines == ["- Lux (pick 1)", "- Zed (pick 2)"]


# Verifies a ban with no pick turn is still listed rather than being dropped or crashing the sort
def test_bans_without_a_pick_turn_are_still_listed(lm_module):
    lines, _shared_pool = lm_module.format_banned_champions_output({100: [(None, "Lux")], 200: [(1, "Zed")]})

    assert "- Lux (pick ?)" in lines


# Verifies a team that banned nothing while the other did is called out explicitly
def test_a_team_with_no_bans_is_called_out(lm_module):
    lines, _shared_pool = lm_module.format_banned_champions_output({100: [(1, "Lux")], 200: [], 300: [(2, "Zed")]})

    assert "- No bans listed" in lines
