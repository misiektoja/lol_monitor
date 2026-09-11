"""Tests for the signal-driven runtime controls and the log output filter."""

import signal

import pytest


# Verifies SIGUSR1 flips status change notifications without a restart
def test_status_notifications_toggle_on_sigusr1(lm_module, capsys):
    assert lm_module.STATUS_NOTIFICATION is False

    lm_module.toggle_status_changes_notifications_signal_handler(signal.SIGUSR1, None)
    assert lm_module.STATUS_NOTIFICATION is True

    lm_module.toggle_status_changes_notifications_signal_handler(signal.SIGUSR1, None)
    assert lm_module.STATUS_NOTIFICATION is False
    assert "status changes" in capsys.readouterr().out


# Verifies SIGTRAP raises the in-game polling interval by the configured step
def test_active_interval_increases_on_sigtrap(lm_module):
    lm_module.increase_active_check_signal_handler(signal.SIGTRAP, None)

    assert lm_module.LOL_ACTIVE_CHECK_INTERVAL == 75


# Verifies SIGABRT lowers the in-game polling interval by the configured step
def test_active_interval_decreases_on_sigabrt(lm_module):
    lm_module.decrease_active_check_signal_handler(signal.SIGABRT, None)

    assert lm_module.LOL_ACTIVE_CHECK_INTERVAL == 15


# Verifies the polling interval is never driven to zero or below, which would spin the loop
def test_active_interval_never_drops_to_zero(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "LOL_ACTIVE_CHECK_INTERVAL", 30)

    lm_module.decrease_active_check_signal_handler(signal.SIGABRT, None)

    assert lm_module.LOL_ACTIVE_CHECK_INTERVAL == 30


# Verifies SIGHUP picks up a rotated API key from the dotenv file without a restart
def test_sighup_reloads_rotated_secrets(lm_module, tmp_path, monkeypatch, capsys):
    pytest.importorskip("dotenv")
    env_file = tmp_path / ".env"
    env_file.write_text("RIOT_API_KEY=rotated-api-key\nSMTP_PASSWORD=rotated-smtp-password\n", encoding="utf-8")
    monkeypatch.setattr(lm_module, "DOTENV_FILE", str(env_file))
    monkeypatch.delenv("RIOT_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)

    lm_module.reload_secrets_signal_handler(signal.SIGHUP, None)

    try:
        assert lm_module.RIOT_API_KEY == "rotated-api-key"
        assert lm_module.SMTP_PASSWORD == "rotated-smtp-password"
        assert "Reloaded RIOT_API_KEY" in capsys.readouterr().out
    finally:
        lm_module.RIOT_API_KEY = "riot-api-key-test-value"
        lm_module.SMTP_PASSWORD = "not-a-real-password"


# Verifies a secret is never printed when it is reloaded, only its name and the file it came from
def test_reloaded_secrets_are_not_printed(lm_module, tmp_path, monkeypatch, capsys):
    pytest.importorskip("dotenv")
    env_file = tmp_path / ".env"
    env_file.write_text("RIOT_API_KEY=super-secret-key-value\n", encoding="utf-8")
    monkeypatch.setattr(lm_module, "DOTENV_FILE", str(env_file))
    monkeypatch.delenv("RIOT_API_KEY", raising=False)

    lm_module.reload_secrets_signal_handler(signal.SIGHUP, None)

    try:
        assert "super-secret-key-value" not in capsys.readouterr().out
    finally:
        lm_module.RIOT_API_KEY = "riot-api-key-test-value"


# Verifies the dotenv scan can be turned off entirely, which a container deployment relies on
def test_dotenv_reload_can_be_disabled(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "none")
    monkeypatch.setenv("RIOT_API_KEY", "key-from-the-environment")

    lm_module.reload_secrets_signal_handler(signal.SIGHUP, None)

    assert lm_module.RIOT_API_KEY == "riot-api-key-test-value"


@pytest.mark.parametrize("mode,system,expected", [
    ("Auto", "Windows", True),
    ("Auto", "Linux", False),
    ("Auto", "Darwin", False),
    ("On", "Linux", True),
    ("Off", "Windows", False),
    (" on ", "Linux", True),
])
# Verifies the ASCII separator mode resolves the way the configuration documents it
def test_ascii_separator_mode_resolution(lm_module, monkeypatch, mode, system, expected):
    monkeypatch.setattr(lm_module, "ASCII_LOG_SEPARATORS", mode)
    monkeypatch.setattr(lm_module.platform, "system", lambda: system)

    assert lm_module.ascii_log_separators_enabled() is expected


# Verifies a misspelled mode is rejected by name so startup can explain the mistake
def test_unknown_separator_mode_is_rejected(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "ASCII_LOG_SEPARATORS", "yes please")

    with pytest.raises(ValueError, match="ASCII_LOG_SEPARATORS"):
        lm_module.ascii_log_separators_enabled()


# Verifies separator lines become ASCII when enabled, so a Windows log file stays readable
def test_separator_lines_are_converted_when_enabled(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "ASCII_LOG_SEPARATORS", "On")

    assert lm_module.normalize_log_separators("─────\n") == "-----\n"


# Verifies only separator-only lines are converted, so a champion name containing a dash is left alone
def test_only_separator_lines_are_converted(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "ASCII_LOG_SEPARATORS", "On")

    assert lm_module.normalize_log_separators("Champion: Nunu ─ Willump\n") == "Champion: Nunu ─ Willump\n"


# Verifies the log text is untouched when the conversion is off
def test_separator_lines_are_preserved_when_disabled(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "ASCII_LOG_SEPARATORS", "Off")

    assert lm_module.normalize_log_separators("─────\n") == "─────\n"


# Verifies the logger writes to both the terminal and the log file, applying the separator conversion only to the file
def test_logger_writes_to_the_terminal_and_the_file(lm_module, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "ASCII_LOG_SEPARATORS", "On")
    log_file = tmp_path / "lol_monitor_user.log"

    logger = lm_module.Logger(str(log_file))
    try:
        logger.write("─────\n")
        logger.write("LoL user is in game now\n")
    finally:
        logger.logfile.close()

    assert capsys.readouterr().out == "─────\nLoL user is in game now\n"
    assert log_file.read_text(encoding="utf-8") == "-----\nLoL user is in game now\n"


# Verifies tabs are expanded in the log file so the aligned output survives outside a terminal
def test_logger_expands_tabs_in_the_log_file(lm_module, tmp_path):
    log_file = tmp_path / "lol_monitor_user.log"

    logger = lm_module.Logger(str(log_file))
    try:
        logger.write("Victory:\tYes\n")
    finally:
        logger.logfile.close()

    assert log_file.read_text(encoding="utf-8") == "Victory:        Yes\n"


# Verifies a reachable endpoint reports connectivity and an unreachable one reports the failure
def test_connectivity_check(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module.req, "get", lambda url, timeout=None: object())
    assert lm_module.check_internet("https://riot.example.test", 5) is True

    # Refuses the request the way an offline host would
    def explode(url, timeout=None):
        raise lm_module.req.RequestException("network unreachable")

    monkeypatch.setattr(lm_module.req, "get", explode)
    assert lm_module.check_internet("https://riot.example.test", 5) is False
    assert "The connectivity endpoint could not be reached" in capsys.readouterr().out


# Verifies an executable is found on PATH and a missing one is reported by name
def test_executable_resolution(lm_module):
    assert lm_module.resolve_executable("sh").endswith("sh")

    with pytest.raises(FileNotFoundError, match="not-a-real-executable"):
        lm_module.resolve_executable("not-a-real-executable")
