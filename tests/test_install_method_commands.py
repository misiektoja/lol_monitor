"""Tests that every printed command matches the detected install method and carries the files this run was given."""

import sys

import pytest

RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"


@pytest.fixture(autouse=True)
# Keeps install detection and path rendering deterministic regardless of how the suite itself was started
def isolated_install_detection(monkeypatch, lm_module):
    monkeypatch.delenv(lm_module.INSTALL_METHOD_ENV_VAR, raising=False)
    monkeypatch.delenv("LOL_MONITOR_IN_CONTAINER", raising=False)
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(lm_module, "CONFIG_DISCOVERY_DISABLED", False)
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "")
    monkeypatch.setattr(lm_module.platform, "system", lambda: "Linux")


@pytest.fixture
# Replaces the monitoring loop with a recorder so main() returns after the startup output is printed
def monitor_calls(monkeypatch, lm_module, tmp_path):
    recorded = []

    # Records the arguments the monitoring loop was started with
    async def fake_monitor(riotid, region, csv_file_name):
        recorded.append({"riotid": riotid, "region": region, "csv_file_name": csv_file_name})

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lm_module, "DEFAULT_CONFIG_FILENAME", "lol_monitor_test_only.conf")
    monkeypatch.setattr(lm_module, "check_internet", lambda *args, **kwargs: True)
    monkeypatch.setattr(lm_module, "lol_monitor_user", fake_monitor)
    return recorded


# Verifies a downloaded script is detected from the invoked file name
def test_a_downloaded_script_is_detected(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/home/user/lol_monitor.py", "--version"])

    assert lm_module.install_method() == lm_module.INSTALL_METHOD_SCRIPT
    assert lm_module.install_method_display_name() == "downloaded script"
    assert lm_module.render_command(["--version"]) == "python3 lol_monitor.py --version"


# Verifies the packaged console script is detected and rendered by its entry point name
def test_a_pypi_install_is_detected(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor", "--version"])

    assert lm_module.install_method() == lm_module.INSTALL_METHOD_PYPI
    assert lm_module.install_method_display_name() == "PyPI install"
    assert lm_module.render_command(["--version"]) == "lol_monitor --version"


# Verifies detection can be pinned explicitly, which containers and packaged builds need
def test_the_install_method_can_be_overridden(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/home/user/lol_monitor.py"])
    monkeypatch.setenv(lm_module.INSTALL_METHOD_ENV_VAR, "pip")

    assert lm_module.install_method() == lm_module.INSTALL_METHOD_PYPI


# Verifies a container is named in the install method, so printed guidance can be tailored to it
def test_a_container_is_reported_in_the_install_method(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])
    monkeypatch.setenv("LOL_MONITOR_IN_CONTAINER", "true")

    assert lm_module.running_in_container() is True
    assert lm_module.install_method_display_name() == "PyPI install in a container"


# Verifies the config and dotenv files this run was given are carried into every printed command
def test_active_paths_are_carried_into_printed_commands(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", "/home/user/my tool.conf")
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "/home/user/secrets.env")

    rendered = lm_module.render_command([RIOT_ID, REGION])

    assert rendered == f"lol_monitor '{RIOT_ID}' {REGION} --config-file '/home/user/my tool.conf' --env-file /home/user/secrets.env"


# Verifies a run with discovery switched off prints commands that switch it off too, so the suggestion reads the setup this run read
def test_disabled_discovery_is_carried_into_printed_commands(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])
    monkeypatch.setattr(lm_module, "CONFIG_DISCOVERY_DISABLED", True)

    assert lm_module.render_command([RIOT_ID, REGION]) == f"lol_monitor '{RIOT_ID}' {REGION} --config-file none"


# Verifies a command that must stay path-free does not inherit the paths this run was given
def test_paths_can_be_left_out(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", "/home/user/tool.conf")

    assert lm_module.render_command(["--generate-config"], include_paths=False) == "lol_monitor --generate-config"


# Verifies an explicitly supplied path is rendered even when the active ones are left out
def test_an_explicit_path_wins_over_the_active_ones(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "/home/user/other.env")

    rendered = lm_module.render_command(["--send-test-email"], include_paths=False, env_path="/home/user/chosen.env")

    assert rendered == "lol_monitor --send-test-email --env-file /home/user/chosen.env"


# Verifies the disabled dotenv search reaches a command that only reads, so the retry checks the setup that failed
def test_a_disabled_dotenv_search_is_carried_into_a_reading_command(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "none")

    assert lm_module.render_command([RIOT_ID, REGION]) == f"lol_monitor '{RIOT_ID}' {REGION} --env-file none"


# Verifies the sentinel stays out of a command that writes the dotenv file, since those refuse it at their own gate
def test_a_disabled_dotenv_search_stays_out_of_a_writing_command(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "none")

    assert lm_module.command_writes_dotenv(["--setup"]) is True
    assert lm_module.command_writes_dotenv(["--set-riot-api-key"]) is True
    assert lm_module.command_writes_dotenv([RIOT_ID, REGION]) is False
    assert lm_module.render_command(["--setup"]) == "lol_monitor --setup"


# Verifies a placeholder stays readable, since quoting it makes it look like a value rather than a blank to fill
def test_a_placeholder_is_never_quoted(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])

    assert lm_module.render_command(["<riot_id>", "<region>"]) == "lol_monitor <riot_id> <region>"


# Verifies arguments containing spaces are quoted for the shell the user pastes into
def test_windows_quoting_uses_double_quotes(lm_module, monkeypatch):
    monkeypatch.setattr("sys.argv", ["C:\\tools\\lol_monitor.exe"])
    monkeypatch.setattr(lm_module.platform, "system", lambda: "Windows")

    assert lm_module.quote_command_argument("C:\\Program Files\\tool.conf") == '"C:\\Program Files\\tool.conf"'
    assert lm_module.quote_command_argument("--version") == "--version"
    assert lm_module.quote_command_argument("<riot_id>") == "<riot_id>"


# Verifies the startup summary names the install method, so a reader knows which form of every command applies
def test_the_startup_summary_names_the_install_method(lm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor", RIOT_ID, REGION])

    with pytest.raises(SystemExit):
        lm_module.main()

    assert "* Install method:\t\tPyPI install" in capsys.readouterr().out


# Verifies the missing-dependency warning names the command that resumes this run rather than saying to re-run it
def test_the_dotenv_warning_names_the_command_to_re_run(lm_module, monkeypatch, monitor_calls, capsys, tmp_path):
    env_file = tmp_path / "secrets.env"
    env_file.write_text("RIOT_API_KEY=value\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "dotenv", None)
    monkeypatch.setattr("sys.argv", ["/home/user/lol_monitor.py", RIOT_ID, REGION, "--env-file", str(env_file)])

    with pytest.raises(SystemExit):
        lm_module.main()

    output = capsys.readouterr().out
    assert f"Once installed, re-run this tool with:\n    python3 lol_monitor.py '{RIOT_ID}' {REGION} --env-file {env_file}" in output
