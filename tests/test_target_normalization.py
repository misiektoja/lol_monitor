"""Tests that the Riot ID and the region are stored in one canonical form."""

import pytest

RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"


@pytest.fixture(autouse=True)
# Keeps startup offline, out of the developer's own files and inside the test directory
def isolated_startup(tmp_path, monkeypatch, lm_module):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lm_module, "DEFAULT_CONFIG_FILENAME", "lol_monitor_test_only.conf")
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(lm_module, "CONFIG_DISCOVERY_DISABLED", False)
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "none")
    monkeypatch.setattr(lm_module, "check_internet", lambda *args, **kwargs: True)
    return tmp_path


@pytest.fixture
# Replaces the monitoring loop with a recorder so main() returns after startup
def monitor_calls(monkeypatch, lm_module):
    recorded = []

    # Records the arguments the monitoring loop was started with
    async def fake_monitor(riotid, region, csv_file_name):
        recorded.append({"riotid": riotid, "region": region, "csv_file_name": csv_file_name})

    monkeypatch.setattr(lm_module, "lol_monitor_user", fake_monitor)
    return recorded


# Runs main() with the supplied command line and returns the exit code it raised
def run_main(lm_module, monkeypatch, argv):
    monkeypatch.setattr(lm_module.sys, "argv", ["lol_monitor", *argv])
    with pytest.raises(SystemExit) as raised:
        lm_module.main()
    return raised.value.code


@pytest.mark.parametrize("value,expected", [
    ("misiektoja#EUNE", "misiektoja#EUNE"),
    ("  misiektoja#EUNE  ", "misiektoja#EUNE"),
    ("misiektoja # EUNE", "misiektoja#EUNE"),
    ("Hide on bush#KR1", "Hide on bush#KR1"),
    ("MiSiEkToJa#eune", "MiSiEkToJa#eune"),
])
# Verifies a pasted Riot ID is stored without the spacing it arrived with, and with the case Riot shows
def test_a_riot_id_is_stored_canonically(lm_module, value, expected):
    assert lm_module.normalize_riot_id(value) == expected


@pytest.mark.parametrize("value", ["misiektoja", "", "   ", "#EUNE", "misiektoja#", "  #  ", "name#with#hashes", None, True])
# Verifies anything that is not a name and a tag line is refused at the boundary instead of reaching Riot
def test_an_incomplete_riot_id_is_refused(lm_module, value):
    with pytest.raises(ValueError, match="complete Riot ID"):
        lm_module.normalize_riot_id(value)


@pytest.mark.parametrize("value,expected", [
    ("eun1", "eun1"),
    ("EUN1", "eun1"),
    ("  Euw1 ", "euw1"),
])
# Verifies a region is stored in the case the routing table is keyed by, so EUN1 and eun1 are one region
def test_a_region_is_stored_lower_case(lm_module, value, expected):
    assert lm_module.normalize_region(value) == expected


@pytest.mark.parametrize("value", ["", "   ", None, True])
# Verifies an empty region is refused rather than stored as a blank that fails later
def test_an_empty_region_is_refused(lm_module, value):
    with pytest.raises(ValueError, match="region code"):
        lm_module.normalize_region(value)


# Verifies the routing continent comes from the table rather than a default, so a wrong region cannot answer from Europe
def test_an_unknown_region_has_no_continent(lm_module):
    assert lm_module.region_continent("eun1") == "europe"

    with pytest.raises(ValueError, match="REGION_TO_CONTINENT"):
        lm_module.region_continent("not-a-region")


# Verifies the region is normalized before the known-region check, so an upper-case code is not rejected as unknown
def test_an_upper_case_region_starts_a_run(lm_module, monkeypatch, monitor_calls):
    assert run_main(lm_module, monkeypatch, [RIOT_ID, "EUN1"]) == 0

    assert monitor_calls[0]["region"] == REGION


# Verifies the canonical Riot ID is what the run carries, so the log file and every message agree on one spelling
def test_the_canonical_riot_id_is_what_the_run_carries(lm_module, monkeypatch, monitor_calls, capsys):
    assert run_main(lm_module, monkeypatch, ["  misiektoja # EUNE ", REGION]) == 0

    assert monitor_calls[0]["riotid"] == RIOT_ID
    assert f"Monitoring user {RIOT_ID}" in capsys.readouterr().out


# Verifies a saved target is normalized too, since a config file is edited by hand and picks up the same spacing
def test_a_saved_target_is_normalized(lm_module, monkeypatch, monitor_calls, isolated_startup):
    config = isolated_startup / "lol_monitor_test_only.conf"
    config.write_text('RIOT_ID = " misiektoja # EUNE "\nREGION = "EUN1"\n', encoding="utf-8")

    assert run_main(lm_module, monkeypatch, []) == 0

    assert monitor_calls[0]["riotid"] == RIOT_ID
    assert monitor_calls[0]["region"] == REGION


# Verifies a malformed Riot ID is reported before the API key is checked, so the first problem named is the real one
def test_a_malformed_riot_id_is_reported_before_the_api_key(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "your_riot_api_key")

    assert run_main(lm_module, monkeypatch, ["misiektoja", REGION]) == 1

    output = capsys.readouterr().out
    assert "That is not a complete Riot ID" in output
    assert "No Riot API key reached the tool" not in output
