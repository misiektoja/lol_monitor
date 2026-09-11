"""Tests for the --doctor preflight: every check branch, the rendered report and the exit code it returns."""

import ast
import inspect
import os

import pytest


RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"


@pytest.fixture(autouse=True)
# Keeps every destination the report names inside the test directory
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
# Keeps the report offline and away from whatever the developer happens to have configured
def isolated_report(monkeypatch, lm_module):
    # The request is replaced rather than the check, so every test runs the connectivity code a real run runs
    monkeypatch.setattr(lm_module.req, "get", lambda url, timeout=None, verify=True: None)
    monkeypatch.setattr(lm_module, "LOL_LOGFILE", "lol_monitor", raising=False)
    monkeypatch.setattr(lm_module, "VERIFY_SSL", True, raising=False)
    monkeypatch.setattr(lm_module, "CHECK_INTERNET_URL", "https://europe.api.riotgames.test/", raising=False)
    monkeypatch.setattr(lm_module, "CHECK_INTERNET_TIMEOUT", 5, raising=False)
    monkeypatch.setattr(lm_module, "COMMAND_LINE_SECRET_KEYS", frozenset(), raising=False)
    monkeypatch.setattr(lm_module, "EXPORTED_SECRET_KEYS", frozenset(), raising=False)


# Returns every check one section produced
def rows(checks, section):
    return [check for check in checks if check.section == section]


# Returns the single check one section produced, failing when the section produced any other number
def only_row(checks, section):
    section_rows = rows(checks, section)
    assert len(section_rows) == 1, [(row.status, row.label) for row in section_rows]
    return section_rows[0]


# Returns the row whose label starts with the given text
def row_labelled(checks, prefix):
    matched = [check for check in checks if check.label.startswith(prefix)]
    assert len(matched) == 1, [check.label for check in checks]
    return matched[0]


# Verifies a marker outside the shared four is refused, so no tool can invent a fifth status
def test_a_fifth_marker_is_refused(lm_module):
    with pytest.raises(ValueError):
        lm_module.make_doctor_check("Environment", "INFO", "Something happened")


@pytest.mark.parametrize("status", ["PASS", "WARN", "FAIL", "SKIP"])
# Verifies all four shared markers are accepted, since a rejected SKIP is why two tools reported a skipped check as a warning
def test_every_shared_marker_is_accepted(lm_module, status):
    advice = lm_module.make_recovery_advice("config.invalid", "Summary", "Correct the setting", False)

    assert lm_module.make_doctor_check("Environment", status, "Label", advice=advice).status == status


@pytest.mark.parametrize("status", ["WARN", "FAIL"])
# Verifies a row the reader has to act on is refused without an action, rather than printed with nothing to do
def test_an_actionable_row_without_a_fix_is_refused(lm_module, status):
    with pytest.raises(ValueError):
        lm_module.make_doctor_check("Configuration", status, "Something is wrong", "Detail")


# Verifies a detail repeating its label is dropped where the row is built, since printing it twice reads as two problems
def test_a_detail_repeating_its_label_is_dropped(lm_module):
    check = lm_module.make_doctor_check("Environment", "PASS", "Everything is fine", " Everything is fine ")

    assert check.detail == ""


# Verifies a Python below the floor fails against the same constant the startup gate reads
def test_an_unsupported_python_fails_against_the_shared_floor(lm_module):
    checks = lm_module.doctor_check_environment(version_info=(3, 8, 0))

    check = checks[0]
    assert check.status == "FAIL"
    assert lm_module.MINIMUM_PYTHON_VERSION_TEXT in check.detail


# Verifies a missing required dependency fails and names an install command for the interpreter in use
def test_a_missing_required_dependency_names_this_interpreter(lm_module):
    checks = lm_module.doctor_check_environment(spec_finder=lambda name: None)

    check = row_labelled(checks, "Required dependency pulsefire")
    assert check.status == "FAIL"
    assert "Install it with: " in check.advice.fix
    assert os.path.basename(lm_module.sys.executable) in check.advice.fix


# Verifies a missing optional dependency warns and says the rest of the tool keeps working
def test_a_missing_optional_dependency_warns_without_blocking(lm_module):
    checks = lm_module.doctor_check_environment(spec_finder=lambda name: None)

    check = row_labelled(checks, "Optional dependency python-dotenv")
    assert check.status == "WARN"
    assert check.detail.endswith("Every other feature is unaffected")


# Verifies a dependency whose parent cannot be imported is reported as absent rather than raising out of the report
def test_an_unimportable_dependency_counts_as_missing(lm_module):
    def refuse(name):
        raise ImportError(name)

    checks = lm_module.doctor_check_environment(spec_finder=refuse)

    assert row_labelled(checks, "Required dependency requests").status == "FAIL"


# Verifies the file a run was given is reported as loaded, with its path on the detail line
def test_a_loaded_configuration_file_is_reported_with_its_path(lm_module):
    checks = lm_module.doctor_check_configuration(config_path="/tmp/lol_monitor.conf")

    assert row_labelled(checks, "Configuration file loaded").detail == "Path: /tmp/lol_monitor.conf"


# Verifies a run with no configuration file says so rather than leaving the reader to guess
def test_no_configuration_file_is_its_own_row(lm_module):
    checks = lm_module.doctor_check_configuration()

    assert row_labelled(checks, "No configuration file selected").status == "PASS"


# Verifies a dotenv file the user selected and the tool could not find is a warning, never a pass
def test_a_missing_dotenv_file_warns(lm_module, tmp_path):
    checks = lm_module.doctor_check_configuration(env_path=str(tmp_path / "absent.env"))

    check = row_labelled(checks, "The requested dotenv file was not found")
    assert check.status == "WARN"
    assert check.detail.startswith("Path: ")


# Verifies a dotenv file that exists is reported as loaded
def test_an_existing_dotenv_file_is_reported_as_loaded(lm_module, tmp_path):
    env_file = tmp_path / "present.env"
    env_file.write_text("RIOT_API_KEY=value\n", encoding="utf-8")

    checks = lm_module.doctor_check_configuration(env_path=str(env_file))

    assert row_labelled(checks, "Dotenv file loaded").status == "PASS"


# Verifies a run with no secret at all says which sources were read, since an empty report reads as a bug
def test_no_secrets_names_every_source_that_was_read(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "", raising=False)
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "", raising=False)

    check = row_labelled(lm_module.doctor_secret_checks(), "No secrets loaded")

    assert check.detail == "Nothing was read from a dotenv file, the environment, the configuration file or the command line"


# Verifies a secret is filed under the source it actually came from rather than under a single catch-all row
@pytest.mark.parametrize("label", ["Secrets loaded from the environment", "Secrets loaded from the dotenv file", "Secrets loaded from the command line", "Secrets loaded from the configuration file"])
def test_each_secret_source_has_its_own_row(lm_module, monkeypatch, tmp_path, label):
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "", raising=False)
    env_file = tmp_path / "secrets.env"
    env_file.write_text("RIOT_API_KEY=from-the-file\n", encoding="utf-8")
    env_path = None
    if label.endswith("environment"):
        monkeypatch.setenv("RIOT_API_KEY", "from-the-environment")
    elif label.endswith("dotenv file"):
        # A dotenv file supplies its value through the environment, so the source is the file it came from
        monkeypatch.setenv("RIOT_API_KEY", "from-the-file")
        env_path = str(env_file)
    elif label.endswith("command line"):
        monkeypatch.setattr(lm_module, "COMMAND_LINE_SECRET_KEYS", frozenset(("RIOT_API_KEY",)), raising=False)
    if label.endswith("environment"):
        monkeypatch.setattr(lm_module, "EXPORTED_SECRET_KEYS", frozenset(("RIOT_API_KEY",)), raising=False)

    checks = lm_module.doctor_secret_checks(env_path)

    assert row_labelled(checks, label).detail == "RIOT_API_KEY"


# Verifies the routing the region resolves to is stated, since the tool no longer picks a continent on its own
def test_a_known_region_reports_the_continent_it_routes_to(lm_module):
    check = only_row(lm_module.doctor_region_checks("eun1"), "Configuration")

    assert check.status == "PASS"
    assert "europe" in check.detail


# Verifies a region the routing table does not carry fails with the code it was given on the detail line
def test_an_unknown_region_fails_with_the_code_it_was_given(lm_module):
    check = only_row(lm_module.doctor_region_checks("narnia"), "Configuration")

    assert check.status == "FAIL"
    assert check.detail == "Region: narnia"
    assert "short code" in check.advice.fix


# Verifies a run with no region takes no region row, since the target section already reports the gap
def test_no_region_takes_no_row(lm_module):
    assert lm_module.doctor_region_checks(None) == []


# Verifies an active interval short enough to be rate limited warns and names the setting to raise
def test_a_short_active_interval_warns(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "LOL_ACTIVE_CHECK_INTERVAL", 3, raising=False)

    check = row_labelled(lm_module.doctor_check_configuration(), "Check intervals are short")
    assert check.status == "WARN"
    assert "LOL_ACTIVE_CHECK_INTERVAL" in check.advice.fix


# Verifies verification left on is reported as a state rather than left unsaid
def test_tls_verification_on_is_reported(lm_module):
    assert row_labelled(lm_module.doctor_check_configuration(), "TLS certificate verification is on").status == "PASS"


# Verifies verification switched off warns, since an intercepted connection cannot be told from the real service
def test_tls_verification_off_warns(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", False, raising=False)

    check = row_labelled(lm_module.doctor_check_configuration(), "TLS certificate verification is off")
    assert check.status == "WARN"
    assert "VERIFY_SSL" in check.advice.fix


@pytest.mark.parametrize("name,value", [("LOL_CHECK_INTERVAL", 0), ("LOL_ACTIVE_CHECK_INTERVAL", -1), ("CHECK_INTERNET_TIMEOUT", "soon"), ("LIVENESS_CHECK_INTERVAL", -5), ("LOL_ACTIVE_CHECK_SIGNAL_VALUE", -1), ("SMTP_PORT", 70000)])
# Verifies a setting that would break the run is a failure naming that setting, not a crash further down
def test_an_invalid_numeric_setting_fails_and_names_itself(lm_module, monkeypatch, name, value):
    monkeypatch.setattr(lm_module, name, value, raising=False)

    check = row_labelled(lm_module.doctor_check_configuration(), "One or more numeric settings are invalid")
    assert check.status == "FAIL"
    assert name in check.detail


# Verifies a separator mode the tool cannot read is a row rather than the exit it used to be
def test_an_unreadable_separator_mode_fails(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "ASCII_LOG_SEPARATORS", "Sometimes", raising=False)

    check = row_labelled(lm_module.doctor_check_configuration(), "The log separator mode is not one this tool knows")
    assert check.status == "FAIL"
    assert check.detail == "Mode: Sometimes"


# Verifies the log destination reported is the file monitoring would open for this Riot ID
def test_the_log_destination_names_the_file_a_run_would_open(lm_module, monkeypatch, isolated_working_directory):
    monkeypatch.setattr(lm_module, "DISABLE_LOGGING", False, raising=False)

    check = row_labelled(lm_module.doctor_output_destination_checks(RIOT_ID), "Log destination")
    assert check.status == "PASS"
    assert check.detail.endswith("lol_monitor_misiektoja.log")


# Verifies a run with no target names no log file, since that path is one no run would ever write
def test_the_log_destination_waits_for_a_target(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "DISABLE_LOGGING", False, raising=False)

    check = row_labelled(lm_module.doctor_output_destination_checks(), "Log destination will be finalized")
    assert check.status == "PASS"
    assert check.detail.startswith("Base path: ")


# Verifies a configured log file that already carries its own extension stays checkable without a target
def test_a_complete_log_path_is_checked_without_a_target(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "DISABLE_LOGGING", False, raising=False)
    monkeypatch.setattr(lm_module, "LOL_LOGFILE", "monitor.log", raising=False)

    assert row_labelled(lm_module.doctor_output_destination_checks(), "Log destination appears writable").status == "PASS"


# Verifies logging switched off takes one row and no path, since nothing will be written
def test_disabled_logging_reports_no_path(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "DISABLE_LOGGING", True, raising=False)

    assert row_labelled(lm_module.doctor_output_destination_checks(RIOT_ID), "Output logging is disabled").detail == ""


# Verifies a destination the tool cannot create is a failure before monitoring starts rather than after
def test_an_unwritable_destination_fails(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "CSV_FILE", "/nonexistent-root-for-tests/history.csv", raising=False)

    check = row_labelled(lm_module.doctor_output_destination_checks(RIOT_ID), "CSV destination is not writable")
    assert check.status == "FAIL"
    assert check.advice.fix


# Verifies a writable destination is reported with the path it would use
def test_a_writable_destination_reports_its_path(lm_module, monkeypatch, isolated_working_directory):
    monkeypatch.setattr(lm_module, "CSV_FILE", str(isolated_working_directory / "history.csv"), raising=False)

    check = row_labelled(lm_module.doctor_output_destination_checks(RIOT_ID), "CSV destination appears writable")
    assert check.detail.startswith("Path: ")


# Verifies the connectivity row checks the endpoint startup gates on, not an authenticated service call
def test_the_connectivity_row_names_the_endpoint_startup_uses(lm_module):
    check = only_row(lm_module.doctor_check_connectivity(), "Connectivity")

    assert check.status == "PASS"
    assert check.detail == f"Endpoint: {lm_module.CHECK_INTERNET_URL}"


# Verifies a failed connectivity check explains the failure instead of sending the reader to a debug flag
def test_a_failed_connectivity_check_knows_why(lm_module, monkeypatch):
    def refuse(url=None, timeout=None, verify=True):
        raise lm_module.req.ConnectionError("name resolution failed")

    monkeypatch.setattr(lm_module.req, "get", refuse)

    check = only_row(lm_module.doctor_check_connectivity(), "Connectivity")
    assert check.status == "FAIL"
    assert check.advice.code == "network.unavailable"
    assert "--debug" not in check.advice.fix


# Verifies a run with no API key fails before any request rather than reporting a network problem
def test_a_missing_api_key_fails_before_any_request(lm_module, monkeypatch, riot_api):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "", raising=False)
    report = lm_module.DoctorReport()

    check = only_row(lm_module.doctor_check_authentication(report, REGION), "Authentication")
    assert check.status == "FAIL"
    assert riot_api.calls == []
    assert report.api_key_valid is False


# Verifies a placeholder key is refused the same way an empty one is
def test_a_placeholder_api_key_is_not_a_key(lm_module, monkeypatch, riot_api):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "your_riot_api_key", raising=False)

    assert only_row(lm_module.doctor_check_authentication(lm_module.DoctorReport(), REGION), "Authentication").status == "FAIL"


@pytest.mark.parametrize("region,cause", [(None, "No region was given"), ("narnia", "The region is not one this tool knows")])
# Verifies the key is not checked without a routing host, and the row says which one was missing
def test_the_key_is_not_checked_without_a_routable_region(lm_module, riot_api, region, cause):
    report = lm_module.DoctorReport()

    check = only_row(lm_module.doctor_check_authentication(report, region), "Authentication")
    assert check.status == "SKIP"
    assert check.detail == f"{cause}, so no request was attempted"
    assert check.advice is None
    assert riot_api.calls == []
    assert report.target_skip_reason == cause


# Verifies a key Riot rejects fails with the advice a rejected key deserves and never prints the key
def test_a_rejected_key_fails_without_showing_it(lm_module, monkeypatch, riot_api):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "RGAPI-secret-value-that-must-not-leak", raising=False)
    riot_api.script("get_lol_status_v4_platform_data", RuntimeError("401 Unauthorized"))
    report = lm_module.DoctorReport()

    check = only_row(lm_module.doctor_check_authentication(report, REGION), "Authentication")
    assert check.status == "FAIL"
    assert check.advice.code == "auth.api_key_invalid"
    assert "RGAPI-secret-value-that-must-not-leak" not in f"{check.label}{check.detail}{check.advice.fix}"


# Verifies an accepted key passes against the region the run would use and records that for the target lookup
def test_an_accepted_key_passes_against_the_configured_region(lm_module, riot_api):
    riot_api.script("get_lol_status_v4_platform_data", {"id": "EUN1"})
    report = lm_module.DoctorReport()

    check = only_row(lm_module.doctor_check_authentication(report, REGION), "Authentication")
    assert check.status == "PASS"
    assert report.api_key_valid is True
    assert riot_api.requests_to("get_lol_status_v4_platform_data")[0]["region"] == REGION


# Verifies a Riot ID the tool rejected is reported as a row instead of exiting before the report is printed
def test_a_rejected_riot_id_is_a_target_row(lm_module):
    check = only_row(lm_module.doctor_check_target(lm_module.DoctorReport(), "Faker", REGION, target_error=lm_module.RIOT_ID_INPUT_ERROR), "Target")

    assert check.status == "FAIL"
    assert check.advice.code == "target.invalid"


@pytest.mark.parametrize("riot_id,region,detail", [(None, None, "No Riot ID and no region were provided"), (RIOT_ID, None, "No region was provided"), (None, REGION, "No Riot ID was provided")])
# Verifies a half-given target warns naming the missing half, at the severity every sibling monitor uses so
# one preflight does not exit 1 where the same state exits 0 in the next tool
def test_a_missing_target_warns_naming_what_is_missing(lm_module, riot_id, region, detail):
    check = only_row(lm_module.doctor_check_target(lm_module.DoctorReport(), riot_id, region), "Target")

    assert check.status == "WARN"
    assert check.label == detail
    assert check.detail.startswith("Nothing will be monitored until ")


# Verifies a lookup that could not run is skipped with the cause the authentication check recorded
def test_an_unchecked_target_is_skipped_with_its_cause(lm_module, riot_api):
    report = lm_module.DoctorReport()
    report.target_skip_reason = "The Riot API key did not validate"

    check = only_row(lm_module.doctor_check_target(report, RIOT_ID, REGION), "Target")
    assert check.status == "SKIP"
    assert check.detail == "The Riot API key did not validate, so no lookup was attempted"
    assert riot_api.calls == []


# Verifies a lookup skipped for a reason other than the key says so, rather than blaming the key for every skip
def test_a_skipped_target_names_the_reason_it_was_skipped(lm_module, riot_api):
    report = lm_module.DoctorReport()
    lm_module.doctor_check_authentication(report, "narnia")

    check = only_row(lm_module.doctor_check_target(report, RIOT_ID, "narnia"), "Target")
    assert check.status == "SKIP"
    assert check.detail == "The region is not one this tool knows, so no lookup was attempted"


# Verifies a lookup Riot answers with nothing fails with advice about the Riot ID rather than about the key
def test_a_target_riot_cannot_find_fails(lm_module, riot_api):
    riot_api.script("get_account_v1_by_riot_id", RuntimeError("404 not found"))
    report = lm_module.DoctorReport()
    report.api_key_valid = True

    check = only_row(lm_module.doctor_check_target(report, RIOT_ID, REGION), "Target")
    assert check.status == "FAIL"
    assert check.advice.code == "target.not_found"


# Verifies a resolved account passes and reports the Riot ID Riot itself returned
def test_a_resolved_account_reports_what_riot_returned(lm_module, riot_api):
    riot_api.script("get_account_v1_by_riot_id", {"puuid": "p" * 78, "gameName": "misiektoja", "tagLine": "EUNE"})
    report = lm_module.DoctorReport()
    report.api_key_valid = True

    check = only_row(lm_module.doctor_check_target(report, RIOT_ID, REGION), "Target")
    assert check.status == "PASS"
    assert check.detail == "Riot ID: misiektoja#EUNE"
    assert riot_api.requests_to("get_account_v1_by_riot_id")[0]["region"] == "europe"


# Verifies a display name Riot returns is sanitized before it reaches the report, since Riot data is untrusted
def test_a_returned_name_is_sanitized(lm_module, riot_api):
    riot_api.script("get_account_v1_by_riot_id", {"puuid": "p" * 78, "gameName": "esc\x1b[31mape", "tagLine": "EUNE"})
    report = lm_module.DoctorReport()
    report.api_key_valid = True

    assert "\x1b" not in only_row(lm_module.doctor_check_target(report, RIOT_ID, REGION), "Target").detail


# Verifies a run that asked for no email alert and configured nothing says so without contacting a server
def test_email_that_was_never_set_up_is_reported_as_disabled(lm_module, monkeypatch, smtp_double):
    for name in lm_module.EMAIL_DELIVERY_SETTINGS:
        monkeypatch.setattr(lm_module, name, "", raising=False)

    check = only_row(lm_module.doctor_check_email_notifications(lm_module.DoctorReport()), "Notifications")
    assert check.status == "PASS"
    assert check.label == "Email notifications are disabled"
    assert smtp_double.last is None


# Verifies a channel switched on that cannot deliver is one warning naming the same settings twice over
def test_an_unusable_email_channel_is_one_warning(lm_module, monkeypatch, smtp_double):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True, raising=False)
    monkeypatch.setattr(lm_module, "SMTP_USER", "", raising=False)
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "your_smtp_password", raising=False)

    check = only_row(lm_module.doctor_check_email_notifications(lm_module.DoctorReport()), "Notifications")
    assert check.status == "WARN"
    assert check.label == lm_module.EMAIL_UNUSABLE_CHECK_LABEL
    assert check.detail == "SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder"
    assert "Set SMTP_USER and SMTP_PASSWORD" in check.advice.fix
    assert smtp_double.last is None


# Verifies email that is fully configured with every alert switched off warns that nothing would arrive
def test_configured_email_with_no_alerts_warns(lm_module, monkeypatch, smtp_double):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", False, raising=False)

    check = only_row(lm_module.doctor_check_email_notifications(lm_module.DoctorReport()), "Notifications")
    assert check.status == "WARN"
    assert check.detail == "Nothing would ever be emailed"
    assert smtp_double.last is None


# Verifies the passive check signs in rather than only opening a socket, so a rotated password fails here
def test_the_passive_email_check_signs_in(lm_module, monkeypatch, smtp_double):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True, raising=False)
    report = lm_module.DoctorReport()

    check = only_row(lm_module.doctor_check_email_notifications(report), "Notifications")
    assert check.status == "PASS"
    assert check.label == lm_module.SMTP_READY_CHECK_LABEL
    assert smtp_double.last.login_args == (lm_module.SMTP_USER, lm_module.SMTP_PASSWORD)
    assert smtp_double.last.sent is None
    assert smtp_double.last.quit_called is True
    assert report.email_ready is True


# Verifies the passive check waits far less than a real delivery, so an unreachable host cannot stall the report
def test_the_passive_email_check_uses_the_shorter_timeout(lm_module, monkeypatch, smtp_double):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True, raising=False)

    lm_module.doctor_check_email_notifications(lm_module.DoctorReport())

    assert smtp_double.last.timeout == lm_module.DOCTOR_PASSIVE_TIMEOUT


# Verifies the passing row says which alerts would be delivered and that nothing was sent to find out
def test_the_ready_email_row_says_what_would_be_delivered(lm_module, monkeypatch, smtp_double):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True, raising=False)
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True, raising=False)

    check = only_row(lm_module.doctor_check_email_notifications(lm_module.DoctorReport()), "Notifications")
    assert check.detail == "Alerts: status changes, errors. No email was sent during this passive check"


# Verifies a sign-in the server refuses fails the row and leaves the channel out of the delivery offer
def test_a_refused_sign_in_fails_the_email_row(lm_module, monkeypatch, smtp_double):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True, raising=False)

    def refuse(self, user, password):
        raise RuntimeError("535 authentication failed")

    monkeypatch.setattr(smtp_double, "login", refuse)
    report = lm_module.DoctorReport()

    check = only_row(lm_module.doctor_check_email_notifications(report), "Notifications")
    assert check.status == "FAIL"
    assert check.advice.code == "smtp.authentication"
    assert report.email_ready is False


# Verifies every row of a rendered report sits in one block, with the detail and action lines indented under it
def test_one_row_renders_as_one_indented_block(lm_module):
    report = lm_module.DoctorReport()
    advice = lm_module.make_recovery_advice("config.invalid", "Something is wrong", lm_module.recovery_fix_with_guide("Correct the setting", lm_module.CONFIG_FILE_GUIDE_URL), False)
    report.checks = [
        lm_module.make_doctor_check("Configuration", "WARN", "Something is wrong", "Setting: value", advice),
        lm_module.make_doctor_check("Configuration", "PASS", "Everything else is fine"),
    ]

    lines = lm_module.render_doctor_sections(report).splitlines()
    start = lines.index("[WARN] Something is wrong")
    assert lines[start + 1] == "  Setting: value"
    assert lines[start + 2] == f"  To fix: Correct the setting"
    assert lines[start + 3] == f"  Guide: {lm_module.CONFIG_FILE_GUIDE_URL}"
    assert lines[start + 4] == "[PASS] Everything else is fine"


# Verifies a passing row prints no action, since a row with nothing to fix has nothing to say about fixing it
def test_a_passing_row_prints_no_action(lm_module):
    report = lm_module.DoctorReport()
    report.checks = [lm_module.make_doctor_check("Environment", "PASS", "All good", "Detail: value")]

    assert "To fix:" not in lm_module.render_doctor_sections(report)


# Verifies sections render in the fixed family order rather than in the order the checks happened to run
def test_sections_render_in_the_fixed_order(lm_module):
    report = lm_module.DoctorReport()
    report.checks = [lm_module.make_doctor_check(section, "PASS", f"{section} row") for section in reversed(lm_module.DOCTOR_SECTIONS)]

    rendered = lm_module.render_doctor_sections(report)
    positions = [rendered.index(f"\n{section}\n") for section in lm_module.DOCTOR_SECTIONS]
    assert positions == sorted(positions)


# Verifies a section with no checks is left out entirely rather than printed as an empty heading
def test_an_empty_section_is_not_rendered(lm_module):
    report = lm_module.DoctorReport()
    report.checks = [lm_module.make_doctor_check("Environment", "PASS", "Only row")]

    assert "Notifications" not in lm_module.render_doctor_sections(report)


# Verifies the delivery rows are filed outside the section list, so they are printed once and still counted
def test_the_delivery_section_is_outside_the_section_list(lm_module):
    assert lm_module.DOCTOR_DELIVERY_SECTION not in lm_module.DOCTOR_SECTIONS


@pytest.mark.parametrize("statuses,expected", [(["PASS"], "All checks passed"), (["PASS", "WARN"], "1 warning(s)"), (["FAIL", "WARN"], "1 check(s) failed, 1 warning(s)")])
# Verifies the verdict sentence counts the rows it was rendered from rather than a separate tally
def test_the_summary_counts_the_rows_it_was_given(lm_module, statuses, expected):
    advice = lm_module.make_recovery_advice("config.invalid", "Summary", "Correct the setting", False)
    checks = [lm_module.make_doctor_check("Environment", status, f"Row {index}", advice=advice) for index, status in enumerate(statuses)]

    assert expected in lm_module.render_doctor_summary(checks)


# Verifies the report closes on the doctor page rather than leaving the reader to search for it
def test_the_summary_ends_on_the_doctor_guide(lm_module):
    assert lm_module.render_doctor_summary([]).splitlines()[-1] == f"Guide: {lm_module.DOCTOR_GUIDE_URL}"


# Verifies an approved delivery test that fails is counted by the verdict the same run prints
def test_a_failed_delivery_test_reaches_the_summary(lm_module, monkeypatch, capsys):
    report = lm_module.DoctorReport()
    report.email_ready = True
    monkeypatch.setattr(lm_module, "send_email", lambda *args, **kwargs: 1)

    lm_module.doctor_offer_notification_tests(report, input_func=lambda _: "y", interactive=True)

    capsys.readouterr()
    assert [check.status for check in report.checks] == ["FAIL"]
    assert "1 check(s) failed" in lm_module.render_doctor_summary(report.checks)


# Verifies an approved delivery test that succeeds sends exactly one message and records the pass
def test_an_approved_delivery_test_sends_one_message(lm_module, monkeypatch, capsys, sent_emails):
    report = lm_module.DoctorReport()
    report.email_ready = True

    lm_module.doctor_offer_notification_tests(report, input_func=lambda _: "y", interactive=True)

    capsys.readouterr()
    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"] == "lol_monitor: doctor test email"
    assert [check.status for check in report.checks] == ["PASS"]


# Verifies a declined delivery test reaches the report rather than being printed and forgotten
def test_a_declined_delivery_test_is_recorded(lm_module, monkeypatch, capsys, sent_emails):
    report = lm_module.DoctorReport()
    report.email_ready = True

    lm_module.doctor_offer_notification_tests(report, input_func=lambda _: "n", interactive=True)

    capsys.readouterr()
    assert sent_emails == []
    assert [check.status for check in report.checks] == ["SKIP"]


# Verifies nothing is offered without a terminal, so a scripted run can never be asked to approve a delivery
def test_no_delivery_is_offered_without_a_terminal(lm_module, sent_emails):
    report = lm_module.DoctorReport()
    report.email_ready = True

    def refuse(_):
        raise AssertionError("a non-interactive run must not be asked")

    assert lm_module.doctor_offer_notification_tests(report, input_func=refuse, interactive=False) == []
    assert report.checks == []


# Verifies a channel that never became ready is not offered, since there is nothing it could deliver
def test_an_unready_channel_is_not_offered(lm_module, sent_emails):
    def refuse(_):
        raise AssertionError("an unready channel must not be offered")

    assert lm_module.doctor_offer_notification_tests(lm_module.DoctorReport(), input_func=refuse, interactive=True) == []


# Verifies the delivery tests are offered before the verdict is rendered, so the two describe the same run
def test_the_delivery_offer_runs_before_the_summary(lm_module):
    tree = ast.parse(inspect.getsource(lm_module))
    matched = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        offers = [call.lineno for call in ast.walk(node) if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "doctor_offer_notification_tests"]
        summaries = [call.lineno for call in ast.walk(node) if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "render_doctor_summary"]
        if offers and summaries:
            matched += 1
            assert max(offers) < min(summaries), node.name

    assert matched == 1, "no function was found that both offers the delivery tests and renders the summary"


# Verifies a clean report exits zero, which is what a script checking the preflight reads
def test_a_clean_report_exits_zero(lm_module, monkeypatch, riot_api, smtp_double, capsys):
    riot_api.script("get_lol_status_v4_platform_data", {"id": "EUN1"})
    riot_api.script("get_account_v1_by_riot_id", {"puuid": "p" * 78, "gameName": "misiektoja", "tagLine": "EUNE"})
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True, raising=False)

    assert lm_module.run_doctor(riot_id=RIOT_ID, region=REGION) == 0
    assert "All checks passed" in capsys.readouterr().out


# Verifies one failing check is enough to exit non-zero, whatever else passed
def test_a_failing_check_exits_one(lm_module, monkeypatch, riot_api, smtp_double, capsys):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "", raising=False)

    assert lm_module.run_doctor(riot_id=RIOT_ID, region=REGION) == 1
    assert "check(s) failed" in capsys.readouterr().out


# Verifies a warning alone leaves the exit code at zero, so a working install does not fail its own preflight
def test_a_warning_alone_exits_zero(lm_module, monkeypatch, riot_api, smtp_double, capsys):
    riot_api.script("get_lol_status_v4_platform_data", {"id": "EUN1"})
    riot_api.script("get_account_v1_by_riot_id", {"puuid": "p" * 78, "gameName": "misiektoja", "tagLine": "EUNE"})
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True, raising=False)
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "your_smtp_password", raising=False)

    assert lm_module.run_doctor(riot_id=RIOT_ID, region=REGION) == 0
    assert lm_module.EMAIL_UNUSABLE_CHECK_LABEL in capsys.readouterr().out


# Verifies the report states what it will and will not do before the first slow check rather than after
def test_the_notice_is_printed_before_the_first_check(lm_module, riot_api, smtp_double, capsys):
    lm_module.run_doctor()

    output = capsys.readouterr().out
    assert output.index("No files will be written") < output.index("Environment")


# Verifies the notice says all three things the family promises: no writes, no email and no webhook without approval
def test_the_notice_states_what_the_run_will_not_do(lm_module, riot_api, smtp_double, capsys):
    lm_module.run_doctor()

    assert capsys.readouterr().out.startswith("Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval.\n")


# Verifies an optional dependency row says what the tool uses it for, so a reader can judge whether to install it
def test_an_optional_dependency_row_says_what_it_is_used_for(lm_module, riot_api, smtp_double, capsys):
    pytest.importorskip("wcwidth")
    lm_module.run_doctor()

    assert "Used only to measure display width for screen truncation" in capsys.readouterr().out


# Verifies the checks run connectivity before authentication, so an offline machine is told it is offline first
def test_connectivity_is_checked_before_authentication(lm_module):
    source = inspect.getsource(lm_module.run_doctor)

    assert source.index("doctor_check_connectivity") < source.index("doctor_check_authentication")


# Verifies the doctor run prints no Next steps block of its own, so the caller decides which one belongs there
@pytest.mark.parametrize("clean", [True, False])
def test_the_doctor_run_leaves_the_next_steps_block_to_its_caller(lm_module, monkeypatch, riot_api, smtp_double, capsys, clean):
    riot_api.script("get_lol_status_v4_platform_data", {"id": "EUN1"})
    riot_api.script("get_account_v1_by_riot_id", {"puuid": "p" * 78, "gameName": "misiektoja", "tagLine": "EUNE"})
    if not clean:
        monkeypatch.setattr(lm_module, "RIOT_API_KEY", "", raising=False)

    lm_module.run_doctor(riot_id=RIOT_ID, region=REGION)

    assert "Next steps" not in capsys.readouterr().out


# Verifies the report ends with the command that starts monitoring rather than leaving it to be assembled
def test_the_next_steps_block_names_the_monitoring_command(lm_module, capsys):
    lm_module.print_doctor_next_steps(RIOT_ID, REGION)

    output = capsys.readouterr().out
    assert "Start monitoring:" in output
    assert RIOT_ID in output
    assert output.rstrip("\n").endswith(f"Guide: {lm_module.QUICK_START_GUIDE_URL}")


# Verifies a failed report labels the command as the step after the failures, not as the next thing to do
def test_a_failed_report_defers_the_monitoring_command(lm_module, capsys):
    lm_module.print_doctor_next_steps(RIOT_ID, REGION, doctor_exit=1)

    assert "After Doctor passes, start monitoring:" in capsys.readouterr().out


# Verifies a target the configuration file supplies is left out, so the printed command stays as short as a saved run
def test_a_saved_target_is_left_out_of_the_printed_command(lm_module):
    assert lm_module.command_target_arguments(RIOT_ID, REGION, riot_id_saved=True, region_saved=True) == []


# Verifies a target from the command line is carried into the printed command, since nothing else supplies it
def test_a_passed_target_is_carried_into_the_printed_command(lm_module):
    assert lm_module.command_target_arguments(RIOT_ID, REGION) == [RIOT_ID, REGION]


# Verifies a half-saved target keeps both values, since a positional cannot be passed on its own
def test_a_half_saved_target_keeps_both_values(lm_module):
    assert lm_module.command_target_arguments(RIOT_ID, REGION, riot_id_saved=False, region_saved=True) == [RIOT_ID, REGION]


# Verifies a missing target keeps the placeholders, so the printed command still shows what to type
def test_a_missing_target_keeps_the_placeholders(lm_module):
    assert lm_module.command_target_arguments() == [lm_module.RIOT_ID_PLACEHOLDER, lm_module.REGION_PLACEHOLDER]


# Verifies no detail line repeats its label, carries an instruction, joins two values with a pipe or ends in a stop
def test_every_detail_line_keeps_the_shared_shape(lm_module):
    tree = ast.parse(inspect.getsource(lm_module))
    checked = 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "make_doctor_check"):
            continue
        arguments = {"label": node.args[2] if len(node.args) > 2 else None, "detail": node.args[3] if len(node.args) > 3 else None}
        for keyword in node.keywords:
            if keyword.arg in arguments:
                arguments[keyword.arg] = keyword.value
        detail = arguments["detail"]
        if detail is None:
            continue
        rendered = _render_literal(detail)
        if rendered is None:
            continue
        checked += 1
        assert not rendered.endswith("."), f"detail ends in a full stop: {rendered}"
        assert " | " not in rendered, f"detail joins two values with a pipe: {rendered}"
        assert not rendered.startswith(("Use ", "Set ", "Run ")), f"detail carries an instruction: {rendered}"
        label = _render_literal(arguments["label"])
        assert label is None or label != rendered, f"detail repeats its label: {rendered}"

    assert checked > 20, f"the sweep only rendered {checked} detail lines"


# Renders one literal or f-string argument, using a marker for the parts only known at runtime
def _render_literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("{}")
        return "".join(parts)
    return None


# One row shape and one advice shape across the family: the advice rides on the row and its fix carries the
# guide, so a row or an advice copied from a sibling means the same thing here
def test_the_doctor_row_and_its_advice_share_one_contract(lm_module):
    row_parameters = list(inspect.signature(lm_module.make_doctor_check).parameters.values())
    advice_parameters = list(inspect.signature(lm_module.make_recovery_advice).parameters.values())

    assert [parameter.name for parameter in row_parameters] == ["section", "status", "label", "detail", "advice"]
    assert [parameter.default for parameter in row_parameters[3:]] == ["", None]
    assert [parameter.name for parameter in advice_parameters] == ["code", "summary", "fix", "retryable", "detail"]
    assert lm_module.recovery_fix_with_guide("do the thing", "https://example.invalid/page") == "do the thing\nGuide: https://example.invalid/page"


# A non-pass row is refused without advice and keeps the advice it was given, which is where its fix and guide live
def test_a_row_carries_its_advice_and_refuses_to_go_without(lm_module):
    advice = lm_module.make_recovery_advice("config.invalid", "a warning row", lm_module.recovery_fix_with_guide("do the thing", lm_module.DOCTOR_GUIDE_URL), False)

    row = lm_module.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice)

    assert row.advice is advice
    assert not hasattr(advice, "guide_url")
    with pytest.raises(ValueError):
        lm_module.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping")


# A string such as "false" counts as on, so an on/off setting holding anything but True or False is named in one row
def test_invalid_boolean_settings_are_reported_in_one_row(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", "false", raising=False)
    monkeypatch.setattr(lm_module, "SMTP_SSL", 1, raising=False)

    check = row_labelled(lm_module.doctor_check_configuration(), "One or more on/off settings are invalid")

    assert check.status == "FAIL"
    assert "ERROR_NOTIFICATION must be True or False, not 'false'" in check.detail
    assert "SMTP_SSL must be True or False, not 1" in check.detail
    assert check.advice.fix.startswith("Set the reported settings to True or False")


# An on/off setting written as 0 or 1 was accepted before the values were checked, so it still reads as off and on
def test_a_numeric_on_off_setting_is_read_as_a_boolean(lm_module):
    parsed = lm_module.parse_config_content("VERIFY_SSL = 0\nDISABLE_LOGGING = 1\n")

    assert parsed == {"VERIFY_SSL": False, "DISABLE_LOGGING": True}
    assert all(isinstance(value, bool) for value in parsed.values())


# The shipped defaults are all real booleans, so a run with nothing overridden never sees the on/off row
def test_the_shipped_defaults_pass_the_boolean_check(lm_module):
    assert lm_module.runtime_boolean_errors() == []
