"""Tests for the Riot API wrappers, using a scripted client instead of the network."""

import asyncio

import pytest

from conftest import Replies

PUUID = "test-puuid-value"


# Verifies a Riot ID is resolved to a PUUID through the account endpoint for the right continent
def test_riot_id_is_resolved_to_a_puuid(lm_module, riot_api):
    riot_api.script("get_account_v1_by_riot_id", {"puuid": PUUID})

    assert asyncio.run(lm_module.get_user_puuid("misiektoja#EUNE", "eun1")) == PUUID

    request = riot_api.requests_to("get_account_v1_by_riot_id")[0]
    assert request["region"] == "europe"
    assert request["game_name"] == "misiektoja"
    assert request["tag_line"] == "EUNE"


# Verifies a region the tool does not know is refused rather than silently answered from a European shard
def test_an_unknown_region_is_not_answered_from_a_default_continent(lm_module, riot_api, capsys):
    riot_api.script("get_account_v1_by_riot_id", {"puuid": PUUID})

    assert asyncio.run(lm_module.get_user_puuid("misiektoja#EUNE", "not-a-region")) is None

    assert riot_api.requests_to("get_account_v1_by_riot_id") == []
    output = capsys.readouterr().out
    assert "not-a-region" in output
    assert "which is the short code and not the display name" in output


# Verifies the API key is sent as the Riot token header and never as a query parameter
def test_the_api_key_travels_in_the_token_header(lm_module, riot_api):
    riot_api.script("get_account_v1_by_riot_id", {"puuid": PUUID})

    asyncio.run(lm_module.get_user_puuid("misiektoja#EUNE", "eun1"))

    session = riot_api.requests_to("__init__")[0]
    assert session["headers"] == {"X-Riot-Token": "riot-api-key-test-value"}


# Verifies a rejected API key is reported with the hint that it may have expired
def test_a_rejected_api_key_is_reported(lm_module, riot_api, capsys):
    riot_api.script("get_account_v1_by_riot_id", RuntimeError("401 Unauthorized"))

    assert asyncio.run(lm_module.get_user_puuid("misiektoja#EUNE", "eun1")) is None

    output = capsys.readouterr().out
    assert "Riot rejected the configured API key" in output
    assert "developer.riotgames.com" in output


# Verifies summoner details are reported with the level and the last profile change
def test_summoner_details_are_reported(lm_module, riot_api):
    riot_api.script("get_lol_summoner_v4_by_puuid", {"summonerLevel": 421, "revisionDate": 1767226800000})

    details = asyncio.run(lm_module.get_summoner_details(PUUID, "eun1"))

    assert details == {"summoner_level": "421", "revision_date": "Thu 01 Jan 2026, 00:20:00"}


# Verifies a failed summoner lookup degrades to unavailable values instead of stopping the run
def test_failed_summoner_lookup_reports_unavailable_values(lm_module, riot_api, capsys):
    riot_api.script("get_lol_summoner_v4_by_puuid", RuntimeError("503 Service Unavailable"))

    details = asyncio.run(lm_module.get_summoner_details(PUUID, "eun1"))

    printed = capsys.readouterr().out
    assert details == {"summoner_level": "N/A", "revision_date": "N/A"}
    assert "* Error: The Riot API is temporarily unavailable" in printed
    assert "To fix: " in printed


# Verifies both ranked queues are reported with tier, division, points and the win record
def test_both_ranked_queues_are_reported(lm_module, riot_api):
    riot_api.script("get_lol_league_v4_entries_by_puuid", [
        {"queueType": "RANKED_SOLO_5x5", "tier": "PLATINUM", "rank": "II", "leaguePoints": 64, "wins": 120, "losses": 100},
        {"queueType": "RANKED_FLEX_SR", "tier": "GOLD", "rank": "IV", "leaguePoints": 12, "wins": 5, "losses": 7},
    ])

    ranked = asyncio.run(lm_module.get_ranked_info(PUUID, "eun1"))

    assert ranked["solo_duo"] == {"tier": "PLATINUM", "rank": "II", "lp": "64", "wins": 120, "losses": 100}
    assert ranked["flex"] == {"tier": "GOLD", "rank": "IV", "lp": "12", "wins": 5, "losses": 7}


# Verifies a queue the player has not played is reported as unavailable rather than as a rank
def test_unplayed_ranked_queues_stay_unavailable(lm_module, riot_api):
    riot_api.script("get_lol_league_v4_entries_by_puuid", [{"queueType": "RANKED_SOLO_5x5", "tier": "IRON", "rank": "I", "leaguePoints": 0, "wins": 1, "losses": 2}])

    ranked = asyncio.run(lm_module.get_ranked_info(PUUID, "eun1"))

    assert ranked["flex"]["tier"] == "N/A"


# Verifies an unranked player is not treated as an error, since having no rank is normal
def test_an_unranked_player_is_not_an_error(lm_module, riot_api, capsys):
    riot_api.script("get_lol_league_v4_entries_by_puuid", [])

    ranked = asyncio.run(lm_module.get_ranked_info(PUUID, "eun1"))

    assert ranked["solo_duo"]["tier"] == "N/A"
    assert capsys.readouterr().out == ""


# Verifies no request is made when there is no player to look up
def test_no_ranked_request_without_a_player(lm_module, riot_api):
    assert asyncio.run(lm_module.get_ranked_info("", "eun1"))["solo_duo"]["tier"] == "N/A"
    assert asyncio.run(lm_module.get_ranked_info("N/A", "eun1"))["flex"]["tier"] == "N/A"
    assert riot_api.requests_to("get_lol_league_v4_entries_by_puuid") == []


# Verifies a champion name is sanitized as Data Dragon is read, so every report reuses the clean cached one
def test_a_champion_name_is_sanitized_when_it_is_cached(lm_module, monkeypatch):
    hostile = chr(27) + "[31mAhri" + chr(27) + "[0m"

    # Answers the two Data Dragon requests the lookup makes, in the order it makes them
    class FakeResponse:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload

        def json(self):
            return self._payload

    answers = [FakeResponse(["15.19.1"]), FakeResponse({"data": {hostile: {"key": "103"}}})]
    monkeypatch.setattr(lm_module.req, "get", lambda *args, **kwargs: answers.pop(0))
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", None)

    assert lm_module.get_champion_name(103) == "Ahri"


# Verifies the release the champion names came from is recorded, since the champion icon URL has to point at
# the same release rather than guess one
def test_the_data_dragon_release_is_recorded_for_the_asset_urls(lm_module, monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload

        def json(self):
            return self._payload

    answers = [FakeResponse(["15.19.1", "15.18.1"]), FakeResponse({"data": {"Ahri": {"key": "103"}}})]
    monkeypatch.setattr(lm_module.req, "get", lambda *args, **kwargs: answers.pop(0))
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", None)
    monkeypatch.setattr(lm_module, "_ddragon_version_cache", "")

    lm_module.get_champion_name(103)

    assert lm_module._ddragon_version_cache == "15.19.1"
    assert lm_module.champion_image_url("Ahri") == "https://ddragon.leagueoflegends.com/cdn/15.19.1/img/champion/Ahri.png"


# Verifies champion mastery is reported for the highest scoring champions, named rather than numbered
def test_top_champion_mastery_is_reported(lm_module, riot_api, monkeypatch):
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", {103: "Ahri", 99: "Lux", 238: "Zed", 64: "LeeSin"})
    riot_api.script("get_lol_champion_v4_top_masteries_by_puuid", [
        {"championId": 99, "championLevel": 7, "championPoints": 120000},
        {"championId": 103, "championLevel": 10, "championPoints": 300000},
        {"championId": 238, "championLevel": 5, "championPoints": 50000},
        {"championId": 64, "championLevel": 4, "championPoints": 10000},
    ])

    mastery = asyncio.run(lm_module.get_champion_mastery(PUUID, "eun1", top_n=3))

    assert [entry["champion_name"] for entry in mastery] == ["Ahri", "Lux", "Zed"]
    assert mastery[0] == {"champion_id": 103, "champion_name": "Ahri", "level": 10, "points": 300000}


# Verifies a champion the tool cannot name is reported by its id instead of being dropped
def test_unnamed_mastery_champion_falls_back_to_its_id(lm_module, riot_api):
    riot_api.script("get_lol_champion_v4_top_masteries_by_puuid", [{"championId": 9999, "championLevel": 3, "championPoints": 1000}])

    mastery = asyncio.run(lm_module.get_champion_mastery(PUUID, "eun1"))

    assert mastery[0]["champion_name"] == "9999"


# Verifies a hidden or failing mastery lookup is not treated as an error
def test_unavailable_mastery_is_not_an_error(lm_module, riot_api, capsys):
    riot_api.script("get_lol_champion_v4_top_masteries_by_puuid", RuntimeError("403 Forbidden"))

    assert asyncio.run(lm_module.get_champion_mastery(PUUID, "eun1")) == []
    assert capsys.readouterr().out == ""


# Verifies an active game means the player is in a match, and that every other answer reports False rather than nothing
def test_in_game_detection(lm_module, riot_api):
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", Replies([{"gameId": 1}, {}, RuntimeError("404 Not Found")]))

    assert asyncio.run(lm_module.is_user_in_match(PUUID, "eun1")) is True
    assert asyncio.run(lm_module.is_user_in_match(PUUID, "eun1")) is False
    assert asyncio.run(lm_module.is_user_in_match(PUUID, "eun1")) is False


# Verifies a request for at most one page asks the API once, for exactly what was requested
def test_a_single_page_of_match_ids_is_one_request(lm_module, riot_api):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", ["EUN1_1", "EUN1_2"])

    assert asyncio.run(lm_module.get_latest_match_ids(PUUID, "eun1", count=10)) == ["EUN1_1", "EUN1_2"]

    requests = riot_api.requests_to("get_lol_match_v5_match_ids_by_puuid")
    assert len(requests) == 1
    assert requests[0]["queries"] == {"start": 0, "count": 10}


# Verifies a request for more than one page is paginated and returns exactly what was asked for
def test_more_than_one_page_is_paginated(lm_module, riot_api):
    first_page = [f"EUN1_{index}" for index in range(100)]
    second_page = [f"EUN1_{index}" for index in range(100, 200)]
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", Replies([first_page, second_page]))

    match_ids = asyncio.run(lm_module.get_latest_match_ids(PUUID, "eun1", count=150))

    assert len(match_ids) == 150
    assert match_ids[0] == "EUN1_0"
    assert match_ids[-1] == "EUN1_149"
    queries = [request["queries"] for request in riot_api.requests_to("get_lol_match_v5_match_ids_by_puuid")]
    assert queries == [{"start": 0, "count": 100}, {"start": 100, "count": 50}]


# Verifies pagination stops at the end of the player's history instead of requesting forever
def test_pagination_stops_at_the_end_of_the_history(lm_module, riot_api):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", Replies([[f"EUN1_{index}" for index in range(100)], [f"EUN1_{index}" for index in range(100, 130)]]))

    match_ids = asyncio.run(lm_module.get_latest_match_ids(PUUID, "eun1", count=500))

    assert len(match_ids) == 130


# Verifies a starting offset is passed through, which is what listing older matches relies on
def test_the_starting_offset_is_passed_through(lm_module, riot_api):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", ["EUN1_50"])

    asyncio.run(lm_module.get_latest_match_ids(PUUID, "eun1", count=1, start=49))

    assert riot_api.requests_to("get_lol_match_v5_match_ids_by_puuid")[0]["queries"] == {"start": 49, "count": 1}


# Verifies a failing match id lookup reports the error and returns nothing to process
def test_failing_match_id_lookup_returns_nothing(lm_module, riot_api, capsys):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", RuntimeError("429 Rate limit exceeded"))

    assert asyncio.run(lm_module.get_latest_match_ids(PUUID, "eun1", count=10)) == []
    printed = capsys.readouterr().out
    assert "* Error: Riot is rate limiting requests" in printed
    assert "To fix: The tool will wait and retry" in printed


# Verifies the total match count walks the whole history one page at a time
def test_total_match_count_walks_the_whole_history(lm_module, riot_api):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", Replies([[f"EUN1_{index}" for index in range(100)], [f"EUN1_{index}" for index in range(100, 142)]]))

    assert asyncio.run(lm_module.get_total_match_count(PUUID, "eun1")) == 142


# Verifies a player with no match history counts as zero rather than failing
def test_total_match_count_of_an_empty_history_is_zero(lm_module, riot_api):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", [])

    assert asyncio.run(lm_module.get_total_match_count(PUUID, "eun1")) == 0


# Verifies a failing count is reported as zero with the reason printed
def test_failing_total_match_count_is_reported(lm_module, riot_api, capsys):
    riot_api.script("get_lol_match_v5_match_ids_by_puuid", RuntimeError("429 Rate limit exceeded"))

    assert asyncio.run(lm_module.get_total_match_count(PUUID, "eun1")) == 0
    printed = capsys.readouterr().out
    assert "* Error: Riot is rate limiting requests" in printed
    assert "To fix: The tool will wait and retry" in printed


# Builds a Data Dragon response double
class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    # Returns the canned JSON body
    def json(self):
        return self.payload


# Verifies champion names are looked up once from Data Dragon and then served from the cache
def test_champion_names_are_fetched_once_and_cached(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", None)
    requested = []

    # Serves the version list and then the champion list
    def fake_get(url, timeout=None, verify=True):
        requested.append(url)
        if url.endswith("versions.json"):
            return FakeResponse(["15.19.1"])
        return FakeResponse({"data": {"Ahri": {"key": "103"}, "Lux": {"key": "99"}}})

    monkeypatch.setattr(lm_module.req, "get", fake_get)

    assert lm_module.get_champion_name(103) == "Ahri"
    assert lm_module.get_champion_name(99) == "Lux"

    assert len(requested) == 2
    assert "15.19.1" in requested[1]


# Verifies an unreachable Data Dragon leaves the champion unnamed instead of raising during a match report
def test_unreachable_champion_data_leaves_the_champion_unnamed(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", None)

    # Refuses the request the way an offline host would
    def explode(url, timeout=None, verify=True):
        raise RuntimeError("ddragon unreachable")

    monkeypatch.setattr(lm_module.req, "get", explode)

    assert lm_module.get_champion_name(103) is None


# Verifies a champion id that is missing or zero resolves to nothing
def test_missing_champion_id_resolves_to_nothing(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", {103: "Ahri"})

    assert lm_module.get_champion_name(0) is None
    assert lm_module.get_champion_name(404) is None


@pytest.mark.parametrize("region,continent", [("eun1", "europe"), ("na1", "americas"), ("kr", "asia"), ("oc1", "sea")])
# Verifies each supported region is routed to the continent that serves its match history
def test_regions_route_to_their_continent(lm_module, region, continent):
    assert lm_module.REGION_TO_CONTINENT[region] == continent
