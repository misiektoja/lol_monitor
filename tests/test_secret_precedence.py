"""Tests for which source supplies each secret and how that choice is reported."""

import os
import signal

import pytest

RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"
EXPORTED = "RGAPI-exported-0000-0000-0000-000000000000"
FROM_FILE = "RGAPI-fromfile-0000-0000-0000-00000000000"
FROM_ARGUMENT = "RGAPI-argument-0000-0000-0000-00000000000"


@pytest.fixture(autouse=True)
# Keeps startup offline, out of the developer's own files and inside the test directory
def isolated_startup(tmp_path, monkeypatch, lm_module):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lm_module, "DEFAULT_CONFIG_FILENAME", "lol_monitor_test_only.conf")
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(lm_module, "CONFIG_DISCOVERY_DISABLED", False)
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "")
    monkeypatch.setattr(lm_module, "EXPORTED_SECRET_KEYS", frozenset())
    monkeypatch.setattr(lm_module, "COMMAND_LINE_SECRET_KEYS", frozenset())
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


# Writes a dotenv file holding one Riot API key and returns its path
def write_dotenv(directory, value=FROM_FILE):
    env_file = directory / ".env-lol_monitor"
    env_file.write_text(f"RIOT_API_KEY={value}\n", encoding="utf-8")
    return env_file


# Verifies a secret exported before the run wins over the same name in a dotenv file
def test_the_environment_beats_the_dotenv_file(lm_module, monkeypatch, monitor_calls, isolated_startup):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)
    monkeypatch.setenv("RIOT_API_KEY", EXPORTED)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--env-file", str(env_file)]) == 0

    assert lm_module.RIOT_API_KEY == EXPORTED


# Verifies an exported secret applies with no dotenv file at all, which is the documented export-only setup
def test_an_exported_secret_applies_without_a_dotenv_file(lm_module, monkeypatch, monitor_calls):
    monkeypatch.setenv("RIOT_API_KEY", EXPORTED)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--env-file", "none"]) == 0

    assert lm_module.RIOT_API_KEY == EXPORTED


# Verifies the dotenv file supplies the secret when nothing was exported
def test_the_dotenv_file_supplies_what_the_environment_does_not(lm_module, monkeypatch, monitor_calls, isolated_startup):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--env-file", str(env_file)]) == 0

    assert lm_module.RIOT_API_KEY == FROM_FILE


# Verifies an argument overrides every other source, since it is the most deliberate thing a user can type
def test_the_command_line_beats_everything(lm_module, monkeypatch, monitor_calls, isolated_startup):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)
    monkeypatch.setenv("RIOT_API_KEY", EXPORTED)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--env-file", str(env_file), "-r", FROM_ARGUMENT]) == 0

    assert lm_module.RIOT_API_KEY == FROM_ARGUMENT
    assert lm_module.COMMAND_LINE_SECRET_KEYS == frozenset({"RIOT_API_KEY"})


# Verifies each source is named in the startup summary, so a run says where its credential came from
@pytest.mark.parametrize("argv,expected", [
    ([], "RIOT_API_KEY (dotenv file)"),
    (["-r", FROM_ARGUMENT], "RIOT_API_KEY (command line)"),
])
def test_the_startup_summary_names_the_source(lm_module, monkeypatch, monitor_calls, isolated_startup, capsys, argv, expected):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--env-file", str(env_file), *argv]) == 0

    assert expected in capsys.readouterr().out


# Verifies an exported secret is reported as coming from the environment even when the file names it too
def test_the_summary_names_the_environment_for_an_exported_secret(lm_module, monkeypatch, monitor_calls, isolated_startup, capsys):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)
    monkeypatch.setenv("RIOT_API_KEY", EXPORTED)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--env-file", str(env_file)]) == 0

    assert "RIOT_API_KEY (environment)" in capsys.readouterr().out


# Verifies a secret left in the configuration file is reported as such rather than as an unnamed source
def test_a_configured_secret_is_reported_as_configuration(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "RGAPI-configured-000-0000-0000-00000000000")
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "")

    assert lm_module.describe_secret_sources(None) == "RIOT_API_KEY (configuration)"


# Verifies a run with no secret at all says so instead of printing an empty line
def test_no_secret_is_reported_as_none(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "")
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "")

    assert lm_module.describe_secret_sources(None) == "None"


# Verifies the four buckets stay separate, since each one means a different place to look when a credential is wrong
def test_the_sources_are_grouped_into_four_buckets(lm_module, monkeypatch, isolated_startup):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)
    monkeypatch.setenv("RIOT_API_KEY", EXPORTED)
    monkeypatch.setenv("SMTP_PASSWORD", "from-the-file")
    monkeypatch.setattr(lm_module, "EXPORTED_SECRET_KEYS", frozenset({"RIOT_API_KEY"}))
    env_file.write_text(f"RIOT_API_KEY={FROM_FILE}\nSMTP_PASSWORD=from-the-file\n", encoding="utf-8")

    from_file, from_environment, from_settings, from_command_line = lm_module.group_secrets_by_source(str(env_file))

    assert from_environment == ["RIOT_API_KEY"]
    assert from_file == ["SMTP_PASSWORD"]
    assert (from_settings, from_command_line) == ([], [])


# Verifies a reload leaves an exported secret alone, so precedence is the same before and after it
def test_a_reload_leaves_an_exported_secret_alone(lm_module, monkeypatch, isolated_startup, capsys):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)
    monkeypatch.setenv("RIOT_API_KEY", EXPORTED)
    monkeypatch.setattr(lm_module, "EXPORTED_SECRET_KEYS", frozenset({"RIOT_API_KEY"}))
    monkeypatch.setattr(lm_module, "DOTENV_FILE", str(env_file))
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", EXPORTED)

    lm_module.reload_secrets_signal_handler(signal.SIGHUP, None)

    assert lm_module.RIOT_API_KEY == EXPORTED
    assert os.environ["RIOT_API_KEY"] == EXPORTED
    assert "Reloaded RIOT_API_KEY" not in capsys.readouterr().out


# Verifies a reload still picks up a rotated secret that was never exported, which is what the signal is for
def test_a_reload_picks_up_a_rotated_secret(lm_module, monkeypatch, isolated_startup, capsys):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)
    monkeypatch.setattr(lm_module, "EXPORTED_SECRET_KEYS", frozenset())
    monkeypatch.setattr(lm_module, "DOTENV_FILE", str(env_file))
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "RGAPI-stale-00000-0000-0000-000000000000")

    lm_module.reload_secrets_signal_handler(signal.SIGHUP, None)

    assert lm_module.RIOT_API_KEY == FROM_FILE
    assert "Reloaded RIOT_API_KEY" in capsys.readouterr().out
