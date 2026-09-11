"""Tests for command line handling, startup validation and how settings reach the monitor."""

import pytest

RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"


@pytest.fixture(autouse=True)
# Keeps generated files, the CSV history and the log inside the test directory
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
# Keeps startup offline and away from any config or dotenv file the developer happens to have
def isolated_startup(monkeypatch, lm_module):
    monkeypatch.setattr(lm_module, "DEFAULT_CONFIG_FILENAME", "lol_monitor_test_only.conf")
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "none")
    monkeypatch.setattr(lm_module, "check_internet", lambda *args, **kwargs: True)


@pytest.fixture
# Replaces the monitoring loop with a recorder so main() returns after startup
def monitor_calls(monkeypatch, lm_module):
    recorded = []

    # Records the arguments the monitoring loop was started with
    async def fake_monitor(riotid, region, csv_file_name):
        recorded.append({"riotid": riotid, "region": region, "csv_file_name": csv_file_name})

    monkeypatch.setattr(lm_module, "lol_monitor_user", fake_monitor)
    return recorded


@pytest.fixture
# Replaces the listing mode with a recorder so main() returns without contacting Riot
def listing_calls(monkeypatch, lm_module):
    recorded = []

    # Records how the listing mode was invoked
    async def fake_listing(riotid, region, matches_min, matches_num, csv_file_name):
        recorded.append({"riotid": riotid, "region": region, "matches_min": matches_min, "matches_num": matches_num, "csv_file_name": csv_file_name})

    monkeypatch.setattr(lm_module, "print_save_recent_matches", fake_listing)
    return recorded


# Runs main() with the supplied command line and returns the exit code it raised
def run_main(lm_module, monkeypatch, argv):
    monkeypatch.setattr(lm_module.sys, "argv", ["lol_monitor", *argv])
    with pytest.raises(SystemExit) as raised:
        lm_module.main()
    return raised.value.code


# Verifies the version is printed without needing an API key or a network connection
def test_version_is_printed_and_exits(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--version"]) == 0
    assert lm_module.VERSION in capsys.readouterr().out


# Verifies running without arguments shows the help text and fails, instead of silently doing nothing
def test_bare_invocation_shows_help(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, []) == 1
    assert "usage: lol_monitor" in capsys.readouterr().err


# Verifies the generated config template is complete and is accepted by the tool's own parser
def test_generated_config_is_written_and_valid(lm_module, monkeypatch, isolated_working_directory):
    target = isolated_working_directory / "lol_monitor.conf"

    assert run_main(lm_module, monkeypatch, ["--generate-config", str(target)]) == 0

    content = target.read_text(encoding="utf-8")
    assert "RIOT_API_KEY" in content
    assert "REGION_TO_CONTINENT" in content
    lm_module.validate_config_content(content, str(target))


# Verifies the template is printed when no output file is given, so it can be redirected
def test_generated_config_is_printed_without_a_filename(lm_module, monkeypatch, capfd):
    assert run_main(lm_module, monkeypatch, ["--generate-config"]) == 0
    assert "RIOT_API_KEY" in capfd.readouterr().out


# Verifies a config file supplied on the command line is applied to the run
def test_config_file_settings_reach_the_monitor(lm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "custom.conf"
    config.write_text('RIOT_API_KEY = "key-from-config"\nLOL_CHECK_INTERVAL = 300\nLOL_ACTIVE_CHECK_INTERVAL = 20\n', encoding="utf-8")

    assert run_main(lm_module, monkeypatch, ["--config-file", str(config), RIOT_ID, REGION]) == 0

    assert lm_module.RIOT_API_KEY == "key-from-config"
    assert lm_module.LOL_CHECK_INTERVAL == 300
    assert lm_module.LOL_ACTIVE_CHECK_INTERVAL == 20
    assert monitor_calls[0] == {"riotid": RIOT_ID, "region": REGION, "csv_file_name": ""}


# Verifies a config path that does not exist is refused instead of being silently ignored
def test_missing_config_file_is_refused(lm_module, monkeypatch, capsys, isolated_working_directory):
    assert run_main(lm_module, monkeypatch, ["--config-file", str(isolated_working_directory / "absent.conf"), RIOT_ID, REGION]) == 1
    assert "does not exist" in capsys.readouterr().out


# Verifies a config file carrying executable content stops startup rather than running it
def test_executable_config_content_stops_startup(lm_module, monkeypatch, capsys, isolated_working_directory):
    hostile = isolated_working_directory / "hostile.conf"
    hostile.write_text("import os\nos.environ['LOL_CLI_EXEC_PROBE'] = 'yes'\n", encoding="utf-8")
    monkeypatch.delenv("LOL_CLI_EXEC_PROBE", raising=False)

    assert run_main(lm_module, monkeypatch, ["--config-file", str(hostile), RIOT_ID, REGION]) == 1

    import os

    assert os.environ.get("LOL_CLI_EXEC_PROBE") is None
    assert "Correct the reported line" in capsys.readouterr().out


# Verifies a setting an older version wrote is ignored with a note rather than stopping startup
def test_retired_settings_are_ignored_with_a_note(lm_module, monkeypatch, monitor_calls, capsys, isolated_working_directory):
    config = isolated_working_directory / "old.conf"
    config.write_text("LOL_HANGED_INGAME_INTERVAL = 900\nLOL_CHECK_INTERVAL = 200\n", encoding="utf-8")

    assert run_main(lm_module, monkeypatch, ["--config-file", str(config), RIOT_ID, REGION]) == 0

    assert lm_module.LOL_CHECK_INTERVAL == 200
    assert "no longer uses" in capsys.readouterr().out


# Verifies the API key is picked up from a dotenv file, so it never has to be typed on the command line
def test_api_key_is_read_from_a_dotenv_file(lm_module, monkeypatch, monitor_calls, isolated_working_directory):
    pytest.importorskip("dotenv")
    env_file = isolated_working_directory / "secrets.env"
    env_file.write_text("RIOT_API_KEY=key-from-dotenv\n", encoding="utf-8")
    monkeypatch.delenv("RIOT_API_KEY", raising=False)

    assert run_main(lm_module, monkeypatch, ["--env-file", str(env_file), RIOT_ID, REGION]) == 0

    assert lm_module.RIOT_API_KEY == "key-from-dotenv"


# Verifies the command line key wins over everything else, which is what makes a one-off run possible
def test_command_line_api_key_wins(lm_module, monkeypatch, monitor_calls):
    assert run_main(lm_module, monkeypatch, ["-r", "key-from-cli", RIOT_ID, REGION]) == 0

    assert lm_module.RIOT_API_KEY == "key-from-cli"


# Verifies startup refuses to run with the placeholder key from the template
def test_placeholder_api_key_is_refused(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "your_riot_api_key")

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 1
    assert "No Riot API key reached the tool" in capsys.readouterr().out


# Verifies a run without both a player and a region is refused with an explanation
def test_missing_player_or_region_is_refused(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, [RIOT_ID]) == 1
    assert "No region was provided" in capsys.readouterr().out


# Verifies a region the tool cannot route is refused before any request is made
def test_an_unroutable_region_is_refused(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, [RIOT_ID, "not-a-region"]) == 1
    assert "is not present in REGION_TO_CONTINENT" in capsys.readouterr().out


# Verifies a Riot ID without a tag line is refused, since it cannot be resolved
def test_a_riot_id_without_a_tag_is_refused(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["misiektoja", REGION]) == 1
    assert "That is not a complete Riot ID" in capsys.readouterr().out


# Verifies a missing internet connection stops startup, since every poll would fail anyway
def test_missing_connectivity_stops_startup(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "check_internet", lambda *args, **kwargs: False)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 1


# Verifies a misspelled separator mode is caught at startup rather than on the first log line
def test_invalid_separator_mode_is_refused(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "ASCII_LOG_SEPARATORS", "yes please")

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 1
    assert "ASCII_LOG_SEPARATORS must be" in capsys.readouterr().out


# Verifies a CSV path that cannot be written is caught before monitoring starts
def test_unwritable_csv_path_is_refused(lm_module, monkeypatch, capsys, isolated_working_directory):
    unreachable = isolated_working_directory / "missing-directory" / "matches.csv"

    assert run_main(lm_module, monkeypatch, ["-b", str(unreachable), RIOT_ID, REGION]) == 1
    assert "cannot be opened for writing" in capsys.readouterr().out


# Verifies the CSV path reaches the monitoring loop
def test_csv_path_reaches_the_monitor(lm_module, monkeypatch, monitor_calls, isolated_working_directory):
    history = isolated_working_directory / "matches.csv"

    assert run_main(lm_module, monkeypatch, ["-b", str(history), RIOT_ID, REGION]) == 0

    assert monitor_calls[0]["csv_file_name"] == str(history)


# Verifies the interval flags override the configured polling intervals
def test_interval_flags_override_the_configuration(lm_module, monkeypatch, monitor_calls):
    assert run_main(lm_module, monkeypatch, ["-c", "600", "-k", "20", RIOT_ID, REGION]) == 0

    assert lm_module.LOL_CHECK_INTERVAL == 600
    assert lm_module.LOL_ACTIVE_CHECK_INTERVAL == 20
    assert lm_module.LIVENESS_CHECK_COUNTER == lm_module.LIVENESS_CHECK_INTERVAL / 600


# Verifies the notification flags switch on exactly the alerts they name
def test_notification_flags_switch_on_the_named_alerts(lm_module, monkeypatch, monitor_calls):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)

    assert run_main(lm_module, monkeypatch, ["-s", RIOT_ID, REGION]) == 0

    assert lm_module.STATUS_NOTIFICATION is True
    assert lm_module.ERROR_NOTIFICATION is True


# Verifies error alerts can be switched off from the command line
def test_error_alerts_can_be_disabled(lm_module, monkeypatch, monitor_calls):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)

    assert run_main(lm_module, monkeypatch, ["-e", RIOT_ID, REGION]) == 0

    assert lm_module.ERROR_NOTIFICATION is False


# Verifies notifications are switched off when SMTP was never configured, so nothing fails on every change
def test_unconfigured_smtp_disables_every_notification(lm_module, monkeypatch, monitor_calls):
    monkeypatch.setattr(lm_module, "SMTP_HOST", "your_smtp_server_ssl")
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)

    assert run_main(lm_module, monkeypatch, ["-s", RIOT_ID, REGION]) == 0

    assert lm_module.STATUS_NOTIFICATION is False
    assert lm_module.ERROR_NOTIFICATION is False


# Verifies matches needing an RSO token can be included from the command line
def test_forbidden_matches_can_be_included(lm_module, monkeypatch, monitor_calls):
    assert run_main(lm_module, monkeypatch, ["-f", RIOT_ID, REGION]) == 0

    assert lm_module.INCLUDE_FORBIDDEN_MATCHES is True


# Verifies the startup banner reports the settings the run will actually use
def test_startup_banner_reports_the_effective_settings(lm_module, monkeypatch, monitor_calls, capsys):
    assert run_main(lm_module, monkeypatch, ["-c", "600", "-k", "20", RIOT_ID, REGION]) == 0

    output = capsys.readouterr().out
    assert "* LoL polling intervals:\t[NOT in game: 10 minutes] [in game: 20 seconds]" in output
    assert "* Include forbidden matches:\tFalse" in output
    assert f"Monitoring user {RIOT_ID}" in output


# Verifies the log file is created in the working directory and named after the monitored player
def test_log_file_is_named_after_the_player(lm_module, monkeypatch, monitor_calls, isolated_working_directory):
    monkeypatch.setattr(lm_module, "DISABLE_LOGGING", False)
    monkeypatch.setattr(lm_module, "LOL_LOGFILE", "lol_monitor")

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 0

    log_file = isolated_working_directory / "lol_monitor_misiektoja.log"
    assert log_file.is_file()
    assert "Monitoring user" in log_file.read_text(encoding="utf-8")


# Verifies logging can be switched off, which a container or systemd deployment relies on
def test_logging_can_be_disabled(lm_module, monkeypatch, monitor_calls, isolated_working_directory):
    monkeypatch.setattr(lm_module, "DISABLE_LOGGING", False)
    monkeypatch.setattr(lm_module, "LOL_LOGFILE", "lol_monitor")

    assert run_main(lm_module, monkeypatch, ["-d", RIOT_ID, REGION]) == 0

    assert not (isolated_working_directory / "lol_monitor_misiektoja.log").exists()


# Verifies the test email uses the configured SMTP settings and reports the outcome
def test_test_email_reports_success(lm_module, monkeypatch, sent_emails, capsys):
    assert run_main(lm_module, monkeypatch, ["--send-test-email"]) == 0

    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"] == "lol_monitor: test email"
    assert "Email sent successfully" in capsys.readouterr().out


# Verifies a failing test email exits with an error, so a broken relay is noticed immediately
def test_failing_test_email_exits_with_an_error(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "send_email", lambda *args, **kwargs: 1)

    assert run_main(lm_module, monkeypatch, ["--send-test-email"]) == 1


# Verifies listing recent matches defaults to the two most recent ones and never starts monitoring
def test_listing_defaults_to_the_two_most_recent_matches(lm_module, monkeypatch, listing_calls, monitor_calls):
    assert run_main(lm_module, monkeypatch, ["-l", RIOT_ID, REGION]) == 0

    assert listing_calls[0]["matches_min"] == 1
    assert listing_calls[0]["matches_num"] == 2
    assert monitor_calls == []


# Verifies a listing range is passed through as given
def test_listing_range_is_passed_through(lm_module, monkeypatch, listing_calls):
    assert run_main(lm_module, monkeypatch, ["-l", "-m", "5", "-n", "20", RIOT_ID, REGION]) == 0

    assert listing_calls[0]["matches_min"] == 5
    assert listing_calls[0]["matches_num"] == 20


# Verifies an inverted listing range is refused with both bounds named
def test_an_inverted_listing_range_is_refused(lm_module, monkeypatch, listing_calls, capsys):
    assert run_main(lm_module, monkeypatch, ["-l", "-m", "20", "-n", "5", RIOT_ID, REGION]) == 1

    assert "cannot be greater than max matches" in capsys.readouterr().out
    assert listing_calls == []


# Verifies listing the whole history first determines how many matches there are
def test_listing_everything_measures_the_history_first(lm_module, monkeypatch, listing_calls, capsys):
    async def fake_puuid(riotid, region):
        return "test-puuid-value"

    async def fake_total(puuid, region):
        return 137

    monkeypatch.setattr(lm_module, "get_user_puuid", fake_puuid)
    monkeypatch.setattr(lm_module, "get_total_match_count", fake_total)

    assert run_main(lm_module, monkeypatch, ["-l", "-a", RIOT_ID, REGION]) == 0

    assert listing_calls[0]["matches_min"] == 1
    assert listing_calls[0]["matches_num"] == 137
    assert "Found 137 total matches available" in capsys.readouterr().out


# Verifies listing everything stops when the player cannot be resolved
def test_listing_everything_stops_without_a_player(lm_module, monkeypatch, listing_calls, capsys):
    async def no_puuid(riotid, region):
        return None

    monkeypatch.setattr(lm_module, "get_user_puuid", no_puuid)

    assert run_main(lm_module, monkeypatch, ["-l", "-a", RIOT_ID, REGION]) == 1
    assert "Could not get PUUID for user" in capsys.readouterr().out
    assert listing_calls == []


# Verifies listing says where the matches are saved when a CSV file is configured
def test_listing_reports_where_matches_are_saved(lm_module, monkeypatch, listing_calls, capsys, isolated_working_directory):
    history = isolated_working_directory / "matches.csv"

    assert run_main(lm_module, monkeypatch, ["-l", "-b", str(history), RIOT_ID, REGION]) == 0

    assert f"* Listing & saving recent matches from 1 to 2 for '{RIOT_ID}' to '{history}'" in capsys.readouterr().out
    assert listing_calls[0]["csv_file_name"] == str(history)


# Verifies an optional config file in the working directory is picked up without a flag
def test_config_file_in_the_working_directory_is_used(lm_module, monkeypatch, monitor_calls, isolated_working_directory, capsys):
    config = isolated_working_directory / "lol_monitor_test_only.conf"
    config.write_text("LOL_CHECK_INTERVAL = 900\n", encoding="utf-8")

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 0

    assert lm_module.LOL_CHECK_INTERVAL == 900
    assert f"* Configuration file:\t\t{config}" in capsys.readouterr().out
