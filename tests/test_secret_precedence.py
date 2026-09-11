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


# The doctor reads the dotenv file keys before answering, so a trace that names a different source contradicts it
@pytest.mark.parametrize("argv, environment, expected", [
    (["--env-file", "DOTENV"], {}, "dotenv file"),
    (["--env-file", "none"], {"RIOT_API_KEY": EXPORTED}, "environment"),
    (["--env-file", "none", "--riot-api-key", FROM_ARGUMENT], {}, "command line"),
])
def test_the_secret_trace_names_the_source_the_doctor_names(lm_module, monkeypatch, monitor_calls, capsys, isolated_startup, argv, environment, expected):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)
    for name in lm_module.SECRET_KEYS:
        monkeypatch.setattr(lm_module, name, "", raising=False)
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    argv = [str(env_file) if part == "DOTENV" else part for part in argv]

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--debug", *argv]) == 0

    output = capsys.readouterr().out
    # The length belongs to its own field, so a reader can split the line on ", " and get pairs
    trace = [line for line in output.splitlines() if "Secret resolution: name=RIOT_API_KEY" in line][-1].split("Secret resolution: ", 1)[1]
    assert dict(field.split("=", 1) for field in trace.split(", ")) == {"name": "RIOT_API_KEY", "source": expected, "value": "set", "chars": str(len(lm_module.RIOT_API_KEY))}
    for value in (EXPORTED, FROM_FILE, FROM_ARGUMENT):
        assert value not in output


# The command line is the last layer to supply a secret, so a run with none says so only after it has had its say
def test_a_run_with_no_secret_anywhere_says_so(lm_module, monkeypatch, monitor_calls, capsys, isolated_startup):
    for name in lm_module.SECRET_KEYS:
        monkeypatch.setattr(lm_module, name, "", raising=False)
        monkeypatch.delenv(name, raising=False)

    run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--debug", "--env-file", "none"])

    output = capsys.readouterr().out
    assert "Secret resolution:" not in output
    assert "No private settings were resolved from config, dotenv, environment or the command line" in output


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
    ([], "Secrets from dotenv"),
    (["-r", FROM_ARGUMENT], "Secrets from command line"),
])
def test_the_startup_summary_names_the_source(lm_module, monkeypatch, monitor_calls, isolated_startup, capsys, argv, expected):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--env-file", str(env_file), "--verbose", *argv]) == 0

    assert summary_row(capsys.readouterr().out, expected) == "RIOT_API_KEY"


# Verifies an exported secret is reported as coming from the environment even when the file names it too
def test_the_summary_names_the_environment_for_an_exported_secret(lm_module, monkeypatch, monitor_calls, isolated_startup, capsys):
    pytest.importorskip("dotenv")
    env_file = write_dotenv(isolated_startup)
    monkeypatch.setenv("RIOT_API_KEY", EXPORTED)

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--env-file", str(env_file), "--verbose"]) == 0

    output = capsys.readouterr().out
    assert summary_row(output, "Secrets from environment") == "RIOT_API_KEY"
    assert summary_row(output, "Secrets from dotenv") == "None"


# Returns the value one startup summary row carries, so a test names the row rather than its column width
def summary_row(output, label):
    line = next((line for line in output.splitlines() if line.startswith(f"* {label}:")), None)
    assert line is not None, f"the summary has no '{label}' row"
    return line.split(":", 1)[1].strip()


# Verifies a secret left in the configuration file is reported as such rather than as an unnamed source
def test_a_configured_secret_is_reported_as_configuration(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "RGAPI-configured-000-0000-0000-00000000000")
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "")

    rows = {row.label: row.value for row in lm_module.build_startup_summary()}

    assert rows["Secrets from config file"] == "RIOT_API_KEY"
    assert rows["Secrets from dotenv"] == "None"


# Verifies a run with no secret at all says so in every bucket instead of printing an empty line
def test_no_secret_is_reported_as_none(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "")
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "")

    rows = {row.label: row.value for row in lm_module.build_startup_summary()}

    assert [rows[f"Secrets from {source}"] for source in ("dotenv", "environment", "config file", "command line")] == ["None"] * 4


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
