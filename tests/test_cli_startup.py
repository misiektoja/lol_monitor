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
    monkeypatch.setattr(lm_module, "CONFIG_DISCOVERY_DISABLED", False)
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


# Verifies running without arguments offers the commands worth knowing instead of dumping the whole option list
def test_bare_invocation_shows_the_welcome_screen(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, []) == 1

    output = capsys.readouterr().out
    assert "Easiest start (guided setup wizard):" in output
    assert "usage: lol_monitor" not in output


# Verifies a run that carries other options is past the welcome screen, so it still names the missing target
def test_an_incomplete_run_names_the_missing_target(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--verbose"]) == 1

    output = capsys.readouterr().out
    assert "* Error: No Riot ID was provided" in output
    assert "To fix: " in output
    assert "usage: lol_monitor" not in output
    assert "Easiest start (guided setup wizard):" not in output


# Verifies a Riot ID given without a region reports the half that is missing rather than a welcome
def test_a_riot_id_without_a_region_names_the_missing_region(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, [RIOT_ID]) == 1

    output = capsys.readouterr().out
    assert "* Error: No region was provided" in output
    assert "Easiest start (guided setup wizard):" not in output


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


# Verifies a saved liveness interval reaches the loop as the number of seconds it names, since a cadence
# counted in checks would drift whenever a check waits something other than the polling interval
def test_the_saved_liveness_interval_reaches_the_loop_in_seconds(lm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "custom.conf"
    config.write_text("LOL_CHECK_INTERVAL = 300\nLIVENESS_CHECK_INTERVAL = 21600\n", encoding="utf-8")

    assert run_main(lm_module, monkeypatch, ["--config-file", str(config), RIOT_ID, REGION]) == 0

    assert lm_module.LIVENESS_REMINDER_SECONDS == 21600


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
    assert lm_module.LIVENESS_REMINDER_SECONDS == lm_module.LIVENESS_CHECK_INTERVAL


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


# Verifies a run that asked for email is told which setting switched it off, rather than being left to guess
def test_a_requested_notification_names_the_setting_that_disabled_it(lm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr(lm_module, "SENDER_EMAIL", "your_sender_email")

    assert run_main(lm_module, monkeypatch, ["--verbose", "-s", RIOT_ID, REGION]) == 0

    assert "* Email notifications are off because SENDER_EMAIL is not set" in capsys.readouterr().out


# Verifies a half-configured SMTP block names every setting that is missing rather than only the first
def test_partly_configured_email_always_names_what_is_missing(lm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr(lm_module, "SENDER_EMAIL", "your_sender_email")
    monkeypatch.setattr(lm_module, "RECEIVER_EMAIL", "")

    assert run_main(lm_module, monkeypatch, ["--verbose", RIOT_ID, REGION]) == 0

    assert "* Email notifications are off because SENDER_EMAIL, RECEIVER_EMAIL are not set" in capsys.readouterr().out


# Verifies the reason is a verbose notice rather than default output, matching where the siblings print it
def test_the_email_gate_reason_is_verbose_only(lm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr(lm_module, "SENDER_EMAIL", "your_sender_email")

    assert run_main(lm_module, monkeypatch, ["-s", RIOT_ID, REGION]) == 0

    assert "Email notifications are off" not in capsys.readouterr().out
    assert lm_module.STATUS_NOTIFICATION is False


# Verifies webhooks with no usable destination are switched off at startup, so nothing tries to deliver to nowhere
def test_a_webhook_with_no_usable_url_is_switched_off(lm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_URL", "not-a-url")

    assert run_main(lm_module, monkeypatch, ["--verbose", RIOT_ID, REGION]) == 0

    assert "Webhook notifications are off because WEBHOOK_URL is not a complete HTTPS link" in capsys.readouterr().out
    assert lm_module.WEBHOOK_ENABLED is False


# Verifies a usable webhook URL is left alone, so the gate did not switch the channel off wholesale
def test_a_usable_webhook_url_stays_enabled(lm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_URL", "https://discord.com/api/webhooks/123456789/tokenvalue")

    assert run_main(lm_module, monkeypatch, ["--verbose", RIOT_ID, REGION]) == 0

    assert "Webhook notifications are off" not in capsys.readouterr().out
    assert lm_module.WEBHOOK_ENABLED is True


# Verifies a run that never asked for email and never configured it stays quiet, since untouched placeholders are not a mistake
def test_untouched_email_settings_stay_quiet(lm_module, monkeypatch, monitor_calls, capsys):
    for name, placeholder in (("SMTP_HOST", "your_smtp_server_ssl"), ("SMTP_USER", "your_smtp_user"), ("SMTP_PASSWORD", "your_smtp_password"), ("SENDER_EMAIL", "your_sender_email"), ("RECEIVER_EMAIL", "your_receiver_email")):
        monkeypatch.setattr(lm_module, name, placeholder)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 0

    assert "Email notifications are off" not in capsys.readouterr().out
    assert lm_module.ERROR_NOTIFICATION is False


# Verifies a fully configured SMTP block leaves the notifications the run asked for switched on
def test_configured_email_keeps_the_notifications_on(lm_module, monkeypatch, monitor_calls, capsys):
    assert run_main(lm_module, monkeypatch, ["-s", RIOT_ID, REGION]) == 0

    assert lm_module.STATUS_NOTIFICATION is True
    assert "Email notifications are off" not in capsys.readouterr().out


# Verifies matches needing an RSO token can be included from the command line
def test_forbidden_matches_can_be_included(lm_module, monkeypatch, monitor_calls):
    assert run_main(lm_module, monkeypatch, ["-f", RIOT_ID, REGION]) == 0

    assert lm_module.INCLUDE_FORBIDDEN_MATCHES is True


# Verifies the startup banner reports the settings the run will actually use
def test_startup_banner_reports_the_effective_settings(lm_module, monkeypatch, monitor_calls, capsys):
    assert run_main(lm_module, monkeypatch, ["-c", "600", "-k", "20", RIOT_ID, REGION, "--verbose"]) == 0

    output = capsys.readouterr().out
    assert "* Polling intervals:            [NOT in game: 10 minutes] [in game: 20 seconds]" in output
    assert "* Forbidden matches:            False" in output
    assert "* TLS verification:             On" in output
    assert f"Monitoring user {RIOT_ID}" in output


# Verifies startup applies the TLS setting before the first connection, so the summary cannot report a choice that never took effect
def test_startup_applies_the_tls_setting(lm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", False)
    silenced = []

    monkeypatch.setattr(lm_module.urllib3, "disable_warnings", lambda category: silenced.append(category))

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 0

    assert silenced, "startup never applied the TLS setting"
    assert "* TLS verification:             Off, server certificates are not checked" in capsys.readouterr().out


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
    assert sent_emails[0]["subject"] == "LoL Monitor test email"
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

    printed = capsys.readouterr().out
    assert "* Error: The lowest match number (20) is above the highest (5)" in printed
    assert "To fix: Raise -n / --recent-matches-count or lower -m / --min-recent-matches" in printed
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
    printed = capsys.readouterr().out
    assert f"* Error: Riot has no account for {RIOT_ID}" in printed
    assert "To fix: Check the game name and the tag line" in printed
    assert listing_calls == []


# Verifies listing says where the matches are saved when a CSV file is configured
def test_listing_reports_where_matches_are_saved(lm_module, monkeypatch, listing_calls, capsys, isolated_working_directory):
    history = isolated_working_directory / "matches.csv"

    assert run_main(lm_module, monkeypatch, ["-l", "-b", str(history), RIOT_ID, REGION]) == 0

    assert f"* Listing & saving recent matches from 1 to 2 for '{RIOT_ID}' to '{history}'" in capsys.readouterr().out
    assert listing_calls[0]["csv_file_name"] == str(history)


# Verifies both file flags advertise the sentinel, since a switch nobody is told about is one nobody uses
@pytest.mark.parametrize("flag", ["--config-file", "--env-file"])
def test_both_file_flags_advertise_the_none_sentinel(lm_module, monkeypatch, capsys, flag):
    assert run_main(lm_module, monkeypatch, ["--help"]) == 0

    segments = (" " + " ".join(capsys.readouterr().out.split())).split(" --")
    described = [segment for segment in segments if segment.startswith(f"{flag.lstrip('-')} PATH")]

    assert described, f"{flag} is missing from the help output"
    assert "disable with 'none'" in described[0]


# Verifies 'none' switches the search off instead of naming a file, so a run cannot pick up a config left in the working directory
@pytest.mark.parametrize("sentinel", ["none", "NONE"])
def test_config_discovery_can_be_disabled(lm_module, monkeypatch, monitor_calls, isolated_working_directory, capsys, sentinel):
    config = isolated_working_directory / "lol_monitor_test_only.conf"
    config.write_text("LOL_CHECK_INTERVAL = 900\n", encoding="utf-8")

    assert run_main(lm_module, monkeypatch, ["--config-file", sentinel, RIOT_ID, REGION]) == 0

    assert lm_module.LOL_CHECK_INTERVAL == 150
    assert lm_module.CONFIG_DISCOVERY_DISABLED is True
    assert "* Config:                       Discovery disabled" in capsys.readouterr().out


# Verifies switching the search off is not read as a missing file, since 'none' is an answer rather than a path
def test_disabled_discovery_is_not_a_missing_file(lm_module, monkeypatch, monitor_calls, capsys):
    assert run_main(lm_module, monkeypatch, ["--config-file", "none", RIOT_ID, REGION]) == 0

    assert "does not exist" not in capsys.readouterr().out


# Verifies a target saved in the config file starts a run with no positional arguments at all
def test_a_saved_target_needs_no_positionals(lm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "lol_monitor_test_only.conf"
    config.write_text(f'RIOT_ID = "{RIOT_ID}"\nREGION = "{REGION}"\n', encoding="utf-8")

    assert run_main(lm_module, monkeypatch, []) == 0

    assert monitor_calls[0]["riotid"] == RIOT_ID
    assert monitor_calls[0]["region"] == REGION


# Verifies a positional overrides the saved pair, so watching somebody else for one run needs no file edit
def test_a_positional_overrides_the_saved_target(lm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "lol_monitor_test_only.conf"
    config.write_text(f'RIOT_ID = "{RIOT_ID}"\nREGION = "{REGION}"\n', encoding="utf-8")

    assert run_main(lm_module, monkeypatch, ["other_name#TAG", "euw1"]) == 0

    assert monitor_calls[0]["riotid"] == "other_name#TAG"
    assert monitor_calls[0]["region"] == "euw1"


# Verifies one saved half still combines with one passed half, since the two positionals resolve independently
def test_a_saved_region_completes_a_passed_riot_id(lm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "lol_monitor_test_only.conf"
    config.write_text(f'REGION = "{REGION}"\n', encoding="utf-8")

    assert run_main(lm_module, monkeypatch, ["other_name#TAG"]) == 0

    assert monitor_calls[0]["riotid"] == "other_name#TAG"
    assert monitor_calls[0]["region"] == REGION


# Verifies the missing-target error is decided after the config file is read, so a saved pair is never called missing
def test_the_missing_target_error_waits_for_the_config_file(lm_module, monkeypatch, monitor_calls, isolated_working_directory, capsys):
    config = isolated_working_directory / "lol_monitor_test_only.conf"
    config.write_text(f'RIOT_ID = "{RIOT_ID}"\nREGION = "{REGION}"\n', encoding="utf-8")

    assert run_main(lm_module, monkeypatch, ["--config-file", str(config)]) == 0

    assert "No Riot ID was provided" not in capsys.readouterr().out


# Verifies an optional config file in the working directory is picked up without a flag
def test_config_file_in_the_working_directory_is_used(lm_module, monkeypatch, monitor_calls, isolated_working_directory, capsys):
    config = isolated_working_directory / "lol_monitor_test_only.conf"
    config.write_text("LOL_CHECK_INTERVAL = 900\n", encoding="utf-8")

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 0

    assert lm_module.LOL_CHECK_INTERVAL == 900
    assert f"* Config:                       {config}" in capsys.readouterr().out


# Verifies the preflight runs without a target, since a first run is the one that most needs the report
def test_doctor_runs_without_a_target(lm_module, monkeypatch, capsys):
    # A preflight that was simply not told what to watch has nothing broken in it, so the exit code stays clean
    assert run_main(lm_module, monkeypatch, ["--doctor", "--config-file", "none"]) == 0

    output = capsys.readouterr().out
    assert "No Riot ID and no region were provided" in output
    assert "Summary" in output


# Verifies the preflight runs ahead of the connectivity gate, so an offline machine still gets a report
def test_doctor_runs_before_the_connectivity_gate(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "check_internet", lambda *args, **kwargs: False)

    assert run_main(lm_module, monkeypatch, ["--doctor", "--config-file", "none", RIOT_ID, REGION]) == 1

    output = capsys.readouterr().out
    assert "The connectivity endpoint could not be reached" in output
    assert "Next steps" in output


# Verifies the preflight runs ahead of the credential gate rather than exiting before it can report on it
def test_doctor_runs_before_the_credential_gate(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "", raising=False)

    assert run_main(lm_module, monkeypatch, ["--doctor", "--config-file", "none", RIOT_ID, REGION]) == 1

    assert "No Riot API key is configured" in capsys.readouterr().out


# Verifies a Riot ID the tool rejects reaches the report as a row rather than exiting before it is printed
def test_doctor_reports_a_rejected_riot_id(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--doctor", "--config-file", "none", "misiektoja", REGION]) == 1

    output = capsys.readouterr().out
    assert lm_module.RIOT_ID_INPUT_ERROR in output
    assert "Summary" in output


# Verifies a rejected Riot ID still stops a normal run, so the report is the only place it is tolerated
def test_a_rejected_riot_id_still_stops_a_normal_run(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--config-file", "none", "misiektoja", REGION]) == 1

    assert lm_module.RIOT_ID_INPUT_ERROR in capsys.readouterr().out


# Verifies a region the routing table does not carry reaches the report before the gate that exits on it
def test_doctor_reports_an_unknown_region(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--doctor", "--config-file", "none", RIOT_ID, "narnia"]) == 1

    assert "Region: narnia" in capsys.readouterr().out


# Verifies the settings a command line changes reach the report, so it describes the run that was asked for
def test_doctor_reports_the_settings_this_command_line_set(lm_module, monkeypatch, capsys, smtp_double, isolated_working_directory):
    csv_file = isolated_working_directory / "history.csv"

    assert run_main(lm_module, monkeypatch, ["--doctor", "--config-file", "none", "-s", "-k", "3", "-b", str(csv_file), RIOT_ID, REGION]) == 1

    output = capsys.readouterr().out
    assert "Check intervals are short" in output
    assert "CSV destination appears writable" in output
    assert "Alerts: status changes" in output


# Verifies the command the report prints carries the files this run was given, so a retry reads the same setup
def test_the_doctor_command_carries_the_files_this_run_used(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--doctor", "--config-file", "none", "--env-file", "none", RIOT_ID, REGION]) == 1

    output = capsys.readouterr().out
    assert "--config-file none" in output
    assert "--env-file none" in output


# Verifies a preflight with nothing wrong exits zero, which is what a script gating on the report reads
def test_a_clean_preflight_exits_zero(lm_module, monkeypatch, riot_api, smtp_double, capsys):
    riot_api.script("get_lol_status_v4_platform_data", {"id": "EUN1"})
    riot_api.script("get_account_v1_by_riot_id", {"puuid": "p" * 78, "gameName": "misiektoja", "tagLine": "EUNE"})

    assert run_main(lm_module, monkeypatch, ["--doctor", "--config-file", "none", "-s", RIOT_ID, REGION]) == 0

    assert "All checks passed" in capsys.readouterr().out


# Verifies the preflight is advertised in the help, so a reader can find it without the documentation
def test_the_help_advertises_the_preflight(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--help"]) == 0

    assert "--doctor" in capsys.readouterr().out


# Verifies every webhook flag is advertised, since a switch nobody is told about is one nobody uses
@pytest.mark.parametrize("flag", ["--webhook", "--no-webhook", "--webhook-url", "--webhook-provider", "--webhook-status", "--webhook-errors", "--no-webhook-error-notify", "--set-webhook-url", "--send-test-webhook", "--set-riot-api-key", "--set-smtp-password"])
def test_every_webhook_and_secret_flag_is_advertised(lm_module, monkeypatch, capsys, flag):
    assert run_main(lm_module, monkeypatch, ["--help"]) == 0

    assert flag in capsys.readouterr().out


# Verifies two secret commands together are refused rather than one silently winning
def test_two_secret_commands_together_are_refused(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--set-riot-api-key", "--set-webhook-url"]) == 2

    assert "--set-riot-api-key cannot be combined with --set-webhook-url" in capsys.readouterr().err


# Verifies the two test messages cannot be asked for at once, since each one reports on its own channel
def test_the_two_test_messages_cannot_be_asked_for_at_once(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--send-test-email", "--send-test-webhook"]) == 2

    assert "--send-test-email cannot be combined with --send-test-webhook" in capsys.readouterr().err


# Verifies a secret command refuses an unrelated flag, so nobody expects a monitoring option to apply to it
def test_a_secret_command_refuses_an_unrelated_flag(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--set-webhook-url", "--verbose"]) == 2

    assert "--set-webhook-url cannot be combined with --verbose" in capsys.readouterr().err


# Verifies a secret command accepts the flag that names where the value goes
def test_a_secret_command_accepts_the_destination_flag(lm_module, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(lm_module.sys.stdin, "isatty", lambda: False)

    assert run_main(lm_module, monkeypatch, ["--set-webhook-url", "--env-file", str(tmp_path / ".env")]) == 1

    assert "requires an interactive terminal" in capsys.readouterr().out


# Verifies a test webhook with nothing configured names the command that sets a destination
def test_a_test_webhook_with_no_destination_names_the_command_that_sets_one(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--send-test-webhook", "--config-file", "none"]) == 1

    output = capsys.readouterr().out
    assert "* Error: No webhook destination is configured" in output
    assert "--set-webhook-url again" in output


# Verifies a configured test webhook is delivered and reported as sent
def test_a_configured_test_webhook_is_delivered(lm_module, monkeypatch, capsys, webhook_session):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(lm_module, "WEBHOOK_PROVIDER", "ntfy")
    webhook_session.responses.append(FakeWebhookResponse(200))

    assert run_main(lm_module, monkeypatch, ["--send-test-webhook", "--config-file", "none", "--webhook-url", "https://ntfy.sh/my-private-topic"]) == 0

    assert "* Webhook sent successfully !" in capsys.readouterr().out
    assert webhook_session.posts[0]["params"]["title"] == lm_module.TEST_WEBHOOK_TITLE


# Verifies a test webhook the service refuses exits non-zero, so a script gating on it reads the failure
def test_a_refused_test_webhook_exits_non_zero(lm_module, monkeypatch, capsys, webhook_session):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(lm_module, "WEBHOOK_PROVIDER", "ntfy")
    webhook_session.responses.append(FakeWebhookResponse(404))

    assert run_main(lm_module, monkeypatch, ["--send-test-webhook", "--config-file", "none", "--webhook-url", "https://ntfy.sh/my-private-topic"]) == 1

    output = capsys.readouterr().out
    assert "* Error: The webhook service returned HTTP 404" in output
    assert "To fix: " in output


# Verifies a test email with no mail server configured names the settings to fill in rather than failing at the server
def test_a_test_email_with_no_mail_server_names_the_settings(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "SMTP_HOST", "")

    assert run_main(lm_module, monkeypatch, ["--send-test-email", "--config-file", "none"]) == 1

    output = capsys.readouterr().out
    assert "* Error: The mail server settings are incomplete, SMTP_HOST is not set" in output
    assert "Set SMTP_HOST, SMTP_USER, SENDER_EMAIL and RECEIVER_EMAIL first" in output


# Verifies a run without a target still reaches the modes that legitimately finish without one. The delivery
# tests end on their own missing settings, while the preflight finds nothing broken and exits clean
@pytest.mark.parametrize("argv,expected", [(["--send-test-webhook"], 1), (["--send-test-email"], 1), (["--doctor"], 0)])
def test_the_modes_that_need_no_target_are_not_stopped_by_the_missing_one(lm_module, monkeypatch, capsys, argv, expected):
    assert run_main(lm_module, monkeypatch, [*argv, "--config-file", "none"]) == expected

    assert "No Riot ID was provided" not in capsys.readouterr().out


# Verifies two secret commands are named in a fixed order, so the message does not depend on which one would run first
def test_two_secret_commands_are_named_in_a_fixed_order(lm_module, monkeypatch, capsys):
    assert run_main(lm_module, monkeypatch, ["--set-webhook-url", "--set-smtp-password"]) == 2

    assert "--set-smtp-password cannot be combined with --set-webhook-url" in capsys.readouterr().err


# Verifies a command that is about to create the dotenv file is not warned that it does not exist
def test_a_command_that_writes_the_dotenv_file_is_not_warned_that_it_is_missing(lm_module, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(lm_module.sys.stdin, "isatty", lambda: False)

    assert run_main(lm_module, monkeypatch, ["--set-smtp-password", "--env-file", str(tmp_path / "absent.env")]) == 1

    output = capsys.readouterr().out
    assert "does not exist" not in output
    assert "requires an interactive terminal" in output


# Verifies a run that only reads the dotenv file is still warned when the named file is not there
def test_a_run_that_only_reads_the_dotenv_file_is_still_warned(lm_module, monkeypatch, capsys, tmp_path):
    assert run_main(lm_module, monkeypatch, ["--send-test-webhook", "--config-file", "none", "--env-file", str(tmp_path / "absent.env")]) == 1

    assert "does not exist" in capsys.readouterr().out
