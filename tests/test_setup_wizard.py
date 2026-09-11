"""Tests the guided setup wizard and the input normalizers it asks its questions through."""

import os
import pty
import re
import select
import signal
import sys
import time
from pathlib import Path

import pytest

import lol_monitor as monitor


REPO_ROOT = Path(__file__).resolve().parents[1]
RIOT_ID = "Faker#KR1"
REGION = "kr"
API_KEY = "RGAPI-00000000-1111-2222-3333-444444444444"
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/verysecrettokenvalue"


@pytest.fixture
# Restores every module-level setting the wizard reads or writes back, plus the secrets it exports on save
def wizard_globals(monkeypatch):
    snapshot = {name: value for name, value in vars(monitor).items() if name.isupper()}
    environment_snapshot = {name: os.environ.get(name) for name in monitor.SECRET_KEYS}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    # Every wizard test starts from the shipped template, which is what a first run has in effect
    for name, value in monitor._config_template_defaults().items():
        monkeypatch.setattr(monitor, name, value, raising=False)
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)
    for name, value in environment_snapshot.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@pytest.fixture(autouse=True)
# Keeps the wizard's mail server sign-in check offline, so a scripted run never opens a connection
def accepted_smtp_sign_in(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: None)


# The real Riot and mail server checks, kept before the fixtures below replace them for every other test
verify_target = monitor._wizard_verify_target
verify_smtp = monitor._wizard_verify_smtp


@pytest.fixture(autouse=True)
# Keeps the wizard's Riot ID check offline, so a scripted run never contacts Riot
def accepted_target_check(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_verify_target", lambda _state: True)


# Returns an input function that replays scripted answers and records the prompts it was asked
def scripted_input(answers, transcript=None):
    remaining = list(answers)

    def respond(prompt):
        if transcript is not None:
            transcript.append(prompt)
        if not remaining:
            raise EOFError("the script ran out of answers")
        return remaining.pop(0)

    return respond


# Runs the whole wizard offline with a scripted operator and no real Riot call
def run_wizard(tmp_path, monkeypatch, answers, secrets=None, transcript=None, initial_riot_id=None, initial_region=None, validator=None, input_func=None):
    monkeypatch.setattr(monitor, "validate_riot_api_key", validator or (lambda _key: True))
    monkeypatch.setattr(monitor, "run_doctor", lambda **_kwargs: 0)
    secret_answers = list(secrets or [API_KEY])

    def fake_getpass(prompt):
        if transcript is not None:
            transcript.append(prompt)
        return secret_answers.pop(0) if secret_answers else ""

    return monitor.run_setup_wizard(
        initial_riot_id=initial_riot_id,
        initial_region=initial_region,
        config_file=str(tmp_path / "lol_monitor.conf"),
        env_file=str(tmp_path / ".env"),
        input_func=input_func or scripted_input(answers, transcript),
        getpass_func=fake_getpass,
        interactive=True,
    )


# The shortest answer script that reaches Save: target, two intervals, no email, no webhook, save, no doctor
def minimal_answers(riot_id=RIOT_ID, region=REGION):
    return [riot_id, region, "y", "5m", "45s", "n", "n", "y", "", "1", "n"]


# Reads the written configuration back as a name to value mapping
def written_config(tmp_path, name="lol_monitor.conf"):
    return monitor.parse_config_content((tmp_path / name).read_text(encoding="utf-8"))


@pytest.fixture
# Switches colour on with the shipped theme, the way a run on a real terminal has it
def colored(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    styles = {name: monitor._build_ansi_sequence(style) for name, style in monitor.DEFAULT_COLOR_THEME.items()}
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: sequence for name, sequence in styles.items() if sequence})
    return styles


# Verifies explicit setup keeps the shared startup screen-clearing behavior
def test_setup_cli_clears_screen_before_wizard(tmp_path, monkeypatch, wizard_globals):
    clear_calls = []
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled: clear_calls.append(enabled))
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor.signal, "signal", lambda *args: None)
    monkeypatch.setattr(monitor, "find_config_file", lambda _path=None: None)
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: 0)
    monkeypatch.setattr(monitor.sys, "argv", ["lol_monitor", "--setup", "--config-file", str(tmp_path / "lol_monitor.conf"), "--env-file", "none"])

    with pytest.raises(SystemExit) as exit_error:
        monitor.main()

    assert exit_error.value.code == 0
    assert clear_calls == [True]


# Verifies setup runs before the connectivity check, so an offline machine can still be configured
def test_setup_runs_before_the_internet_check(tmp_path, monkeypatch, wizard_globals):
    reached = []
    monkeypatch.setattr(monitor, "clear_screen", lambda _enabled: None)
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor.signal, "signal", lambda *args: None)
    monkeypatch.setattr(monitor, "find_config_file", lambda _path=None: None)
    monkeypatch.setattr(monitor, "check_internet", lambda *args, **kwargs: reached.append("internet") or True)
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: reached.append("setup") or 0)
    monkeypatch.setattr(monitor.sys, "argv", ["lol_monitor", "--setup", "--config-file", str(tmp_path / "lol_monitor.conf"), "--env-file", "none"])

    with pytest.raises(SystemExit):
        monitor.main()

    assert reached == ["setup"]


# Verifies setup accepts a config path that does not exist yet, since creating it is the point
def test_setup_accepts_a_config_path_that_does_not_exist(tmp_path, monkeypatch, wizard_globals):
    monkeypatch.setattr(monitor, "clear_screen", lambda _enabled: None)
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor.signal, "signal", lambda *args: None)
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: 0)
    monkeypatch.setattr(monitor.sys, "argv", ["lol_monitor", "--setup", "--config-file", str(tmp_path / "missing.conf"), "--env-file", "none"])

    with pytest.raises(SystemExit) as exit_error:
        monitor.main()

    assert exit_error.value.code == 0


# Verifies a duration is accepted in the formats people actually type
@pytest.mark.parametrize("value,expected", [
    ("30s", 30), ("2m", 120), ("1.5h", 5400), ("1h 30m", 5400), ("1h30m", 5400),
    ("1d", 86400), ("90", 90), ("2 minutes", 120), ("45 sec", 45), ("  3h  ", 10800),
])
def test_durations_accept_human_formats(value, expected):
    assert monitor.parse_duration_input(value) == expected


# Verifies anything that is not a duration is refused rather than silently read as seconds
@pytest.mark.parametrize("value", ["", "   ", "abc", "5x", "-10", "0", "m", None, True, "1h abc"])
def test_non_durations_are_refused(value):
    assert monitor.parse_duration_input(value) is None


# Verifies a wizard duration is rendered as raw seconds plus a readable form, the way the siblings render it
@pytest.mark.parametrize("seconds,expected", [
    (45, "45s"), (60, "60s - 1m"), (150, "150s - 2m 30s"), (3600, "3600s - 1h"), (90000, "90000s - 1d 1h"),
])
def test_wizard_durations_show_seconds_and_a_readable_form(seconds, expected):
    assert monitor._wizard_format_duration(seconds) == expected


# Verifies the wizard writes nothing at all until Save is chosen
def test_nothing_is_written_before_save(tmp_path, monkeypatch, wizard_globals):
    answers = minimal_answers()
    answers[9] = "3"
    code = run_wizard(tmp_path, monkeypatch, answers + ["y"])

    assert code == 1
    assert sorted(path.name for path in tmp_path.iterdir()) == []


# Verifies declining the discard keeps every answer rather than restarting
def test_declining_the_discard_keeps_the_answers(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = minimal_answers()
    answers[9:10] = ["3", "n", "1"]
    code = run_wizard(tmp_path, monkeypatch, answers)

    assert code == 0
    assert "Setup answers retained." in capsys.readouterr().out
    assert (tmp_path / "lol_monitor.conf").is_file()


# Verifies saving writes both files with the answers given
def test_saving_writes_both_files(tmp_path, monkeypatch, wizard_globals):
    code = run_wizard(tmp_path, monkeypatch, minimal_answers())

    assert code == 0
    values = written_config(tmp_path)
    assert values["RIOT_ID"] == RIOT_ID
    assert values["REGION"] == REGION
    assert values["LOL_CHECK_INTERVAL"] == 300
    assert values["LOL_ACTIVE_CHECK_INTERVAL"] == 45
    assert (tmp_path / ".env").read_text(encoding="utf-8").strip() == f'RIOT_API_KEY="{API_KEY}"'


# Verifies the generated configuration survives the tool's own parser, so the next run can read it
def test_the_generated_configuration_round_trips(tmp_path, monkeypatch, wizard_globals):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    values = monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))

    assert values["RIOT_ID"] == RIOT_ID
    assert values["LOL_CHECK_INTERVAL"] == 300


# Verifies the secret goes only to the dotenv file and never into the configuration
def test_the_secret_never_reaches_the_configuration(tmp_path, monkeypatch, wizard_globals):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    config_text = (tmp_path / "lol_monitor.conf").read_text(encoding="utf-8")

    assert API_KEY not in config_text
    assert 'RIOT_API_KEY = "your_riot_api_key"' in config_text


# Verifies the configuration renderer keeps the template placeholder for every secret whatever the values hold
def test_the_configuration_renderer_never_writes_a_secret():
    values = {name: "leaked-secret-value" for name in monitor.SECRET_KEYS}
    rendered = monitor.generate_config_with_current_values(values)

    assert "leaked-secret-value" not in rendered


# Verifies a setting still holding the shipped default keeps the template's own lines rather than a collapsed repr
def test_an_unchanged_setting_keeps_the_template_formatting():
    rendered = monitor.generate_config_with_current_values(dict(monitor._config_template_defaults()))

    assert rendered.count("\nWEBHOOK_TEMPLATE = {\n") == 1
    assert "WEBHOOK_TEMPLATE = {'" not in rendered


# Verifies a changed setting is rewritten in place, replacing every line of the value it stood for
def test_a_changed_setting_replaces_the_whole_template_value():
    values = dict(monitor._config_template_defaults())
    values["WEBHOOK_TEMPLATE"] = {"content": "one line"}
    rendered = monitor.generate_config_with_current_values(values)

    assert "WEBHOOK_TEMPLATE = {'content': 'one line'}\n" in rendered
    assert monitor.parse_config_content(rendered)["WEBHOOK_TEMPLATE"] == {"content": "one line"}


# Verifies editing one section reverts only that section and leaves the other answers standing
def test_editing_one_section_keeps_the_others(tmp_path, monkeypatch, wizard_globals):
    answers = minimal_answers()
    answers[9:10] = ["2", "2", "10m", "30s", "1"]
    run_wizard(tmp_path, monkeypatch, answers)

    values = written_config(tmp_path)

    assert values["LOL_CHECK_INTERVAL"] == 600
    assert values["LOL_ACTIVE_CHECK_INTERVAL"] == 30
    assert values["RIOT_ID"] == RIOT_ID


# Verifies editing the target section asks for it again rather than keeping the previous answer
def test_editing_the_target_section_asks_again(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    answers = minimal_answers()
    answers[9:10] = ["2", "1", "Uzi#EUW", "euw1", "y", "1"]
    run_wizard(tmp_path, monkeypatch, answers, transcript=transcript)

    values = written_config(tmp_path)

    assert values["RIOT_ID"] == "Uzi#EUW"
    assert values["REGION"] == "euw1"
    assert sum(1 for prompt in transcript if prompt.startswith("Riot ID to monitor")) == 2


# Verifies the edit menu offers every section the wizard collects, so no answer is unreachable from the summary
def test_every_collected_section_can_be_edited():
    collected = {"Target", "Polling", "Authentication", "Email", "Webhook", "Output", "Destinations"}

    assert {name for name, *_rest in monitor.WIZARD_SECTIONS} == collected


# Verifies every styled summary label names a real summary row, so a rename cannot silently drop its colour
def test_every_styled_summary_label_is_a_real_summary_row(tmp_path, monkeypatch, wizard_globals, capsys):
    run_wizard(tmp_path, monkeypatch, minimal_answers())
    printed = capsys.readouterr().out

    for label in monitor.WIZARD_SUMMARY_VALUE_STYLES:
        assert f"\n  {label}:" in printed


# Verifies every summary value starts in the same column, so the block reads as one aligned table
def test_the_summary_rows_are_aligned(tmp_path, monkeypatch, wizard_globals, capsys):
    run_wizard(tmp_path, monkeypatch, minimal_answers())
    printed = capsys.readouterr().out
    block = printed.split("Setup summary\n\n", 1)[1].split("\n\n", 1)[0]
    columns = {len(line) - len(line.split(":", 1)[1].lstrip()) for line in block.splitlines()}

    assert len(block.splitlines()) == 14
    assert columns == {38}


# Verifies the summary paints the values whose kind is known, so the block is not plain text
def test_the_summary_paints_the_values_with_a_known_kind(tmp_path, monkeypatch, wizard_globals, colored, capsys):
    run_wizard(tmp_path, monkeypatch, minimal_answers())
    printed = capsys.readouterr().out

    assert f"{monitor.colorize('username', f'{RIOT_ID} (kr)')}" in printed
    assert f"{monitor.colorize('duration', '300s - 5m')}" in printed


# Verifies declining email turns every email alert off, so the summary cannot promise alerts that never fire
def test_declining_email_turns_every_email_alert_off(tmp_path, monkeypatch, wizard_globals):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    values = monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))

    assert values["STATUS_NOTIFICATION"] is False
    assert values["ERROR_NOTIFICATION"] is False


# Verifies a declined email section clears the mail server, so the written config cannot contradict the summary
def test_a_declined_email_section_clears_the_mail_server(tmp_path, monkeypatch, wizard_globals):
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitoring@example.test")
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    values = monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))

    assert values["SMTP_HOST"] == monitor._config_template_defaults()["SMTP_HOST"]
    assert values["SMTP_USER"] == monitor._config_template_defaults()["SMTP_USER"]


# Verifies the email question defaults to the saved alerts, so a rerun over configured email proposes keeping it
def test_the_email_question_defaults_to_the_saved_alerts(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(monitor, "STATUS_NOTIFICATION", True)
    run_wizard(tmp_path, monkeypatch, minimal_answers(), transcript=transcript)

    assert any(prompt.startswith("Configure email notifications? [Y/n]") for prompt in transcript)


# Verifies the error alert alone does not count as configured email, since it ships switched on
def test_the_error_alert_alone_does_not_count_as_configured_email():
    assert monitor._wizard_email_enabled({"ERROR_NOTIFICATION": True, "SMTP_HOST": "your_smtp_server_ssl"}) is False
    assert monitor._wizard_email_enabled({"ERROR_NOTIFICATION": True, "SMTP_HOST": "smtp.gmail.com"}) is True


# Verifies declining email clears only the alerts the wizard offers, so alerts enabled by hand survive
def test_declining_email_keeps_the_alerts_the_wizard_never_offers(tmp_path, wizard_globals):
    state = monitor.WizardSetupState(tmp_path / "lol_monitor.conf", tmp_path / ".env", {"SMTP_HOST": "smtp.gmail.com"})
    state.config_values["INCLUDE_FORBIDDEN_MATCHES"] = True
    monitor._wizard_disable_email(state)

    assert state.config_values["INCLUDE_FORBIDDEN_MATCHES"] is True
    assert state.config_values["ERROR_NOTIFICATION"] is False


# Verifies the recommended alert preset enables every alert the channel owns
@pytest.mark.parametrize("keys", [monitor.WIZARD_EMAIL_NOTIFICATION_KEYS, monitor.WIZARD_WEBHOOK_NOTIFICATION_KEYS])
def test_the_recommended_alert_preset_enables_every_alert(keys):
    chosen = monitor._wizard_collect_alert_preset("Which?", "Everything.", "Pick each.", keys, [(name, name) for name in keys], input_func=scripted_input(["1"]))

    assert chosen == {name: True for name in keys}


# Verifies the recommended entry names the alerts it turns on, so the choice is readable without the description
def test_the_recommended_preset_entry_names_what_it_enables(capsys):
    keys = monitor.WIZARD_EMAIL_NOTIFICATION_KEYS
    monitor._wizard_collect_alert_preset("Which?", "Everything.", "Pick each.", keys, [(name, name) for name in keys], input_func=scripted_input(["1"]))

    assert "1. Status and errors, recommended" in capsys.readouterr().out


# Verifies each channel describes its own custom preset, so the menu never offers to pick email alerts for a webhook
@pytest.mark.parametrize("section,answers,expected", [
    ("_wizard_collect_email_section", ["y", "smtp.example.com", "", "", "user", "a@example.com", "b@example.com", "2", "n", "n"], "Choose each notification type separately."),
    ("_wizard_collect_webhook_section", ["y", "1", "2", "n", "n"], "Choose each webhook alert separately."),
])
def test_each_channel_names_its_own_custom_preset(tmp_path, monkeypatch, wizard_globals, capsys, section, answers, expected):
    monkeypatch.setattr(monitor, "_wizard_smtp_sign_in_accepted", lambda *args, **kwargs: True)
    state = monitor.WizardSetupState(tmp_path / "lol_monitor.conf", tmp_path / ".env", {})
    getattr(monitor, section)(state, input_func=scripted_input(answers), getpass_func=lambda _prompt: WEBHOOK_URL)

    assert expected in capsys.readouterr().out


# Verifies the custom alert preset asks about each alert separately
def test_the_custom_alert_preset_asks_about_each_alert():
    keys = monitor.WIZARD_EMAIL_NOTIFICATION_KEYS
    chosen = monitor._wizard_collect_alert_preset("Which?", "Everything.", "Pick each.", keys, [(name, name) for name in keys], input_func=scripted_input(["2", "y", "n"]))

    assert chosen == {"STATUS_NOTIFICATION": True, "ERROR_NOTIFICATION": False}


# Verifies a blank key is offered the way out rather than only being asked for again
def test_an_empty_api_key_answer_is_asked_again(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    answers = minimal_answers()
    answers[5:5] = ["n"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=["", API_KEY], transcript=transcript)

    assert sum(1 for prompt in transcript if prompt.startswith("Riot API key:")) == 2
    assert any("Continue without the Riot API key?" in prompt for prompt in transcript)


# Verifies a key Riot refuses is offered again, since a mistyped key is the common case
def test_a_rejected_api_key_is_asked_again(tmp_path, monkeypatch, wizard_globals, capsys):
    transcript = []
    accepted = [False, True]
    answers = minimal_answers()
    answers[5:5] = ["y"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=["wrong-key", API_KEY], transcript=transcript, validator=lambda _key: accepted.pop(0))

    assert "A development key expires 24 hours after it is issued." in capsys.readouterr().out
    assert sum(1 for prompt in transcript if prompt.startswith("Riot API key:")) == 2


# Verifies a key Riot keeps refusing can be given up on, since it cannot be corrected from inside the loop
def test_a_rejected_api_key_can_be_abandoned(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = minimal_answers()
    answers[5:5] = ["n"]
    code = run_wizard(tmp_path, monkeypatch, answers, secrets=["wrong-key"], validator=lambda _key: False)

    assert code == 0
    assert "Authentication status:              incomplete" in capsys.readouterr().out
    assert not (tmp_path / ".env").exists()


# Verifies the wizard says it is contacting Riot, since the key check blocks the prompt with no output
def test_the_wizard_announces_the_key_check(tmp_path, monkeypatch, wizard_globals, capsys):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    assert "Checking the key with Riot ..." in capsys.readouterr().out


# Verifies the wizard checks the collected Riot ID once a key is available, so a typo is caught before the save
def test_the_target_is_checked_with_riot_after_the_key(tmp_path, monkeypatch, wizard_globals, capsys):
    checked = []
    monkeypatch.setattr(monitor, "_wizard_verify_target", lambda state: checked.append((state.riot_id, state.region)) or True)
    run_wizard(tmp_path, monkeypatch, minimal_answers())
    printed = capsys.readouterr().out

    assert checked == [(RIOT_ID, REGION)]
    assert "Checking the Riot ID with Riot ..." in printed
    assert f"Riot found {RIOT_ID} on {REGION}." in printed


# Verifies the Riot ID check uses the key just entered rather than the one the process started with
def test_the_target_check_uses_the_key_the_wizard_accepted(tmp_path, monkeypatch, wizard_globals):
    seen = []
    monkeypatch.setattr(monitor, "riot_account_probe", lambda riot_id, region: seen.append((monitor.RIOT_API_KEY, riot_id, region)))
    monkeypatch.setattr(monitor.asyncio, "run", lambda awaitable: awaitable)
    state = monitor.WizardSetupState(tmp_path / "lol_monitor.conf", tmp_path / ".env", {})
    state.riot_id, state.region = RIOT_ID, REGION
    state.secret_updates["RIOT_API_KEY"] = API_KEY

    assert verify_target(state) is True
    assert seen == [(API_KEY, RIOT_ID, REGION)]
    assert monitor.RIOT_API_KEY == "your_riot_api_key"


# Verifies a Riot ID Riot does not know is offered again with the guidance the reader needs
def test_a_target_riot_does_not_know_is_asked_again(tmp_path, monkeypatch, wizard_globals, capsys):
    found = [False, True]
    monkeypatch.setattr(monitor, "_wizard_verify_target", lambda _state: found.pop(0))
    answers = minimal_answers()
    answers[5:5] = ["n", "Uzi#EUW", "euw1", "y"]
    code = run_wizard(tmp_path, monkeypatch, answers)
    printed = capsys.readouterr().out

    assert code == 0
    assert f"Riot has no account for '{RIOT_ID}' on '{REGION}'." in printed
    assert written_config(tmp_path)["RIOT_ID"] == "Uzi#EUW"


# Verifies giving up on a target Riot does not know leaves it out rather than saving one that cannot be monitored
def test_a_target_riot_does_not_know_can_be_abandoned(tmp_path, monkeypatch, wizard_globals, capsys):
    monkeypatch.setattr(monitor, "_wizard_verify_target", lambda _state: False)
    answers = minimal_answers()
    answers[5:5] = ["y"]
    code = run_wizard(tmp_path, monkeypatch, answers)

    assert code == 0
    assert "Target:                             not set" in capsys.readouterr().out
    assert written_config(tmp_path)["RIOT_ID"] == ""


# Verifies a target that could not be checked says so rather than claiming Riot confirmed it
def test_a_target_is_not_claimed_checked_without_a_key(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = minimal_answers()
    answers[5:5] = ["n"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=["wrong-key"], validator=lambda _key: False)
    printed = capsys.readouterr().out

    assert f"'{RIOT_ID}' was not checked with Riot, which needs an API key. Run --doctor once one is set." in printed
    assert "Riot found" not in printed


# Verifies a Riot ID the tool cannot read is asked again with the guidance the reader needs
def test_a_rejected_riot_id_is_asked_again(tmp_path, monkeypatch, wizard_globals, capsys):
    transcript = []
    answers = minimal_answers()
    answers[0:1] = ["no-tag-line", "y", RIOT_ID]
    run_wizard(tmp_path, monkeypatch, answers, transcript=transcript)

    assert "That is not a complete Riot ID" in capsys.readouterr().out
    assert sum(1 for prompt in transcript if prompt.startswith("Riot ID to monitor")) == 2


# Verifies a region the tool does not know is asked again rather than saved for the doctor to reject
def test_a_rejected_region_is_asked_again(tmp_path, monkeypatch, wizard_globals, capsys):
    transcript = []
    answers = minimal_answers()
    answers[1:2] = ["Korea", "y", REGION]
    run_wizard(tmp_path, monkeypatch, answers, transcript=transcript)

    assert "'Korea' is not a region this tool knows." in capsys.readouterr().out
    assert sum(1 for prompt in transcript if prompt.startswith("Region (")) == 2


# Verifies declining the Riot ID retry ends the section instead of asking the same question forever
def test_declining_the_riot_id_retry_ends_the_section(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = ["no-tag-line", "n", "5m", "45s", "n", "n", "y", "", "1"]
    code = run_wizard(tmp_path, monkeypatch, answers)
    printed = capsys.readouterr().out

    assert code == 0
    assert "No target selected." in printed
    assert "Run doctor now?" not in printed


# Verifies declining the region retry clears the Riot ID too, so half a target is never saved
def test_declining_the_region_retry_clears_the_riot_id(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = [RIOT_ID, "Korea", "n", "5m", "45s", "n", "n", "y", "", "1"]
    code = run_wizard(tmp_path, monkeypatch, answers)

    assert code == 0
    assert "No region selected." in capsys.readouterr().out
    assert written_config(tmp_path)["RIOT_ID"] == ""


# Verifies the persist answer puts the target in the config file, so the tool runs without arguments
def test_a_persisted_target_reaches_the_config_file(tmp_path, monkeypatch, wizard_globals):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    values = written_config(tmp_path)

    assert values["RIOT_ID"] == RIOT_ID
    assert values["REGION"] == REGION


# Verifies declining the persist question leaves the target out of the written config and in the printed command
def test_a_declined_persist_leaves_the_target_out_of_the_config(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = minimal_answers()
    answers[2] = "n"
    run_wizard(tmp_path, monkeypatch, answers)

    assert written_config(tmp_path)["RIOT_ID"] == ""
    assert f"{monitor.shlex.quote(RIOT_ID)} {REGION}" in capsys.readouterr().out


# The mail server answers the wizard asks for before the hidden password prompt
EMAIL_ANSWERS_BEFORE = {
    "SMTP_HOST": [],
    "SMTP_USER": ["smtp.gmail.com", "587", "y"],
    "SENDER_EMAIL": ["smtp.gmail.com", "587", "y", "monitoring@example.test"],
    "RECEIVER_EMAIL": ["smtp.gmail.com", "587", "y", "monitoring@example.test", "monitoring@example.test"],
}


@pytest.mark.parametrize("abandoned", sorted(EMAIL_ANSWERS_BEFORE))
# Verifies an abandoned mail server answer switches email off rather than writing half a configuration
def test_an_abandoned_mail_server_answer_turns_email_off(tmp_path, monkeypatch, wizard_globals, capsys, abandoned):
    answers = minimal_answers()
    answers[5:6] = ["y"] + EMAIL_ANSWERS_BEFORE[abandoned] + ["", "n"]
    code = run_wizard(tmp_path, monkeypatch, answers)
    printed = capsys.readouterr().out

    assert code == 0
    assert "Email notifications stay off until every mail server setting is answered." in printed
    values = monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))
    assert values["SMTP_HOST"] == monitor._config_template_defaults()["SMTP_HOST"]
    assert values["ERROR_NOTIFICATION"] is False


# Verifies the wizard signs in with exactly the answers just given, so a wrong password is caught during setup
def test_the_wizard_signs_in_with_the_collected_mail_server(tmp_path, monkeypatch, wizard_globals, capsys):
    attempts = []
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: attempts.append((dict(values), password)))
    answers = minimal_answers()
    answers[5:6] = ["y", "smtp.gmail.com", "587", "y", "monitoring@example.test", "monitoring@example.test", "alerts@example.test", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "mail-password"])

    assert attempts[0][0]["SMTP_HOST"] == "smtp.gmail.com"
    assert attempts[0][0]["SMTP_PORT"] == 587
    assert attempts[0][1] == "mail-password"
    assert "The mail server accepted the sign-in. No email was sent." in capsys.readouterr().out


# Verifies a refused sign-in offers the mail server questions again rather than saving settings that cannot work
def test_a_refused_mail_server_sign_in_offers_another_attempt(tmp_path, monkeypatch, wizard_globals, capsys):
    outcomes = [monitor.classify_recovery_error(monitor.smtplib.SMTPAuthenticationError(535, b"denied"), "email"), None]
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: outcomes.pop(0))
    mail = ["smtp.gmail.com", "587", "y", "monitoring@example.test", "monitoring@example.test", "alerts@example.test"]
    answers = minimal_answers()
    answers[5:6] = ["y"] + mail + ["y"] + mail + ["1"]
    code = run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "wrong", "right"])

    assert code == 0
    assert "The mail server accepted the sign-in." in capsys.readouterr().out


# Verifies declining the retry keeps the answers, since being offline is the usual reason a correct setup fails here
def test_declining_the_sign_in_retry_keeps_the_mail_server_settings(tmp_path, monkeypatch, wizard_globals, capsys):
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: monitor.classify_recovery_error(OSError("network is unreachable"), "email"))
    mail = ["smtp.gmail.com", "587", "y", "monitoring@example.test", "monitoring@example.test", "alerts@example.test"]
    answers = minimal_answers()
    answers[5:6] = ["y"] + mail + ["n", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "mail-password"])

    assert "The settings were kept without being checked. Run --doctor to check the sign-in again." in capsys.readouterr().out
    assert monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))["SMTP_HOST"] == "smtp.gmail.com"


# Verifies giving up on a refused sign-in switches every email alert off rather than saving settings that cannot work
def test_abandoning_a_refused_sign_in_switches_email_off(tmp_path, monkeypatch, wizard_globals, capsys):
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: monitor.classify_recovery_error(monitor.smtplib.SMTPAuthenticationError(535, b"denied"), "email"))
    mail = ["smtp.gmail.com", "587", "y", "monitoring@example.test", "monitoring@example.test", "alerts@example.test"]
    answers = minimal_answers()
    answers[5:6] = ["y"] + mail + ["n", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "mail-password"])

    assert "Email notifications stay off until the mail server accepts the settings." in capsys.readouterr().out
    assert monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))["ERROR_NOTIFICATION"] is False


# Verifies the port question rejects a number no TCP port can be, instead of saving it for the doctor to reject
def test_the_smtp_port_question_rejects_a_number_above_the_port_range(capsys):
    chosen = monitor._wizard_ask_positive_int("SMTP port", 587, maximum=65535, input_func=scripted_input(["70000", "y", "465"]))

    assert chosen == 465
    assert "Enter a whole number from 1 through 65535." in capsys.readouterr().out


# Verifies declining the retry offer keeps the saved value rather than asking the same question forever
def test_declining_the_retry_offer_keeps_the_saved_number(capsys):
    chosen = monitor._wizard_ask_positive_int("SMTP port", 587, maximum=65535, input_func=scripted_input(["0", "n"]))

    assert chosen == 587
    assert "Keeping 587." in capsys.readouterr().out


# Verifies a rejected duration is asked again instead of being stored as something else
def test_a_rejected_duration_is_asked_again(capsys):
    chosen = monitor._wizard_ask_duration("Interval", 150, input_func=scripted_input(["soon", "y", "2m"]))

    assert chosen == 120
    assert "Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d." in capsys.readouterr().out


# Verifies declining the retry offer after a duration the wizard cannot use keeps the default rather than asking again
def test_a_rejected_duration_keeps_the_default(capsys):
    chosen = monitor._wizard_ask_duration("Interval", 150, input_func=scripted_input(["soon", "n"]))

    assert chosen == 150
    assert "Keeping 150s - 2m 30s." in capsys.readouterr().out


# Verifies duration prompts name the accepted units and show the stored seconds beside a readable form
def test_duration_prompts_show_the_units_and_the_stored_seconds(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    run_wizard(tmp_path, monkeypatch, minimal_answers(), transcript=transcript)
    polling = [prompt for prompt in transcript if prompt.startswith("Riot polling interval")]

    assert polling[0] == "Riot polling interval while not in game (seconds or use s/m/h/d) [150s - 2m 30s]: "
    assert polling[1] == "Riot polling interval while in game (seconds or use s/m/h/d) [45s]: "


# Verifies the webhook service is chosen before the URL is pasted, the shared order across these tools
def test_the_webhook_service_is_chosen_before_the_url(tmp_path, monkeypatch, wizard_globals, capsys):
    transcript = []
    answers = minimal_answers()
    answers[6:7] = ["y", "1", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, WEBHOOK_URL], transcript=transcript)
    printed = capsys.readouterr().out

    assert printed.index("Which webhook service should receive alerts?") < printed.index("Copy Webhook URL")
    assert any(prompt.startswith("Paste the Discord webhook URL") for prompt in transcript)


# Verifies the chosen webhook service and its URL reach the written files
def test_the_webhook_choice_reaches_both_files(tmp_path, monkeypatch, wizard_globals):
    answers = minimal_answers()
    answers[6:7] = ["y", "1", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, WEBHOOK_URL])

    values = monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))

    assert values["WEBHOOK_ENABLED"] is True
    assert values["WEBHOOK_PROVIDER"] == "discord"
    assert values["WEBHOOK_STATUS_NOTIFICATION"] is True
    assert f'WEBHOOK_URL="{WEBHOOK_URL}"' in (tmp_path / ".env").read_text(encoding="utf-8")
    assert WEBHOOK_URL not in (tmp_path / "lol_monitor.conf").read_text(encoding="utf-8")


# Verifies a blank destination is told apart from a malformed one and that skipping it leaves the channel off
def test_a_blank_webhook_url_is_worded_as_a_blank_one(tmp_path, monkeypatch, wizard_globals, capsys):
    transcript = []
    answers = minimal_answers()
    answers[6:7] = ["y", "1", "y"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "", ""], transcript=transcript)

    assert any("Continue without the webhook URL? Webhook alerts stay off until one is set" in prompt for prompt in transcript)
    assert "That does not look like a complete HTTPS webhook URL." not in capsys.readouterr().out
    assert monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))["WEBHOOK_ENABLED"] is False


# Verifies a URL the wizard cannot use can be given up on, which leaves the channel and its alerts off
def test_a_malformed_webhook_url_can_be_abandoned(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = minimal_answers()
    answers[6:7] = ["y", "1", "n"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "not-a-url"])
    printed = capsys.readouterr().out

    assert "That does not look like a complete HTTPS webhook URL." in printed
    values = monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))
    assert values["WEBHOOK_ENABLED"] is False
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False


# Verifies a bare ntfy topic name typed into the wizard is saved as a complete URL
def test_a_bare_ntfy_topic_name_is_saved_as_a_url(tmp_path, monkeypatch, wizard_globals):
    answers = minimal_answers()
    answers[6:7] = ["y", "2", "n", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "lol-monitor-alerts"])

    assert 'WEBHOOK_URL="https://ntfy.sh/lol-monitor-alerts"' in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies an ntfy topic the wizard cannot use is explained rather than reported as nothing entered
def test_a_rejected_ntfy_topic_is_explained(tmp_path, monkeypatch, wizard_globals, capsys):
    transcript = []
    answers = minimal_answers()
    answers[6:7] = ["y", "2", "n"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "not a topic"], transcript=transcript)

    assert "Enter a complete HTTPS ntfy topic URL or a topic name containing up to 64 letters, numbers, dashes or underscores." in capsys.readouterr().out
    assert not any("Continue without the webhook URL?" in prompt for prompt in transcript)


# Verifies no ntfy topic at all still reaches the question that switches the channel off
def test_no_ntfy_topic_at_all_still_offers_to_give_up(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    answers = minimal_answers()
    answers[6:7] = ["y", "2", "y"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "", ""], transcript=transcript)

    assert any("Continue without the webhook URL? Webhook alerts stay off until one is set" in prompt for prompt in transcript)


# Verifies a token pasted with its authorization scheme can be given up on without losing the topic already entered
def test_a_pasted_ntfy_authorization_scheme_can_be_abandoned(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = minimal_answers()
    answers[6:7] = ["y", "2", "y", "n", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "lol-monitor-alerts", "Bearer tk_secret"])
    dotenv_text = (tmp_path / ".env").read_text(encoding="utf-8")

    assert "Paste only the access token without a Bearer or Basic prefix." in capsys.readouterr().out
    assert "NTFY_ACCESS_TOKEN" not in dotenv_text
    assert 'WEBHOOK_URL="https://ntfy.sh/lol-monitor-alerts"' in dotenv_text


# Verifies a blank token is read as no token, so an optional answer cannot trap the wizard or save an empty secret
def test_a_blank_ntfy_access_token_means_no_token(tmp_path, monkeypatch, wizard_globals):
    answers = minimal_answers()
    answers[6:7] = ["y", "2", "y", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "lol-monitor-alerts", ""])

    assert "NTFY_ACCESS_TOKEN" not in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies an accepted ntfy token reaches the dotenv file and never the configuration
def test_an_ntfy_access_token_reaches_only_the_dotenv_file(tmp_path, monkeypatch, wizard_globals):
    answers = minimal_answers()
    answers[6:7] = ["y", "2", "y", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "lol-monitor-alerts", "tk_secret_value"])

    assert 'NTFY_ACCESS_TOKEN="tk_secret_value"' in (tmp_path / ".env").read_text(encoding="utf-8")
    assert "tk_secret_value" not in (tmp_path / "lol_monitor.conf").read_text(encoding="utf-8")


# Verifies the webhook question defaults to the saved switch, so a rerun over a configured webhook proposes keeping it
def test_the_webhook_question_defaults_to_the_saved_switch(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    answers = minimal_answers()
    answers[6:7] = ["n"]
    run_wizard(tmp_path, monkeypatch, answers, transcript=transcript)

    assert any(prompt.startswith("Set up webhook alerts (Discord, ntfy etc.)? [Y/n]") for prompt in transcript)


# Verifies the output section records the log choice and the CSV destination it was given
def test_the_output_section_records_the_log_and_csv_choices(tmp_path, monkeypatch, wizard_globals):
    answers = minimal_answers()
    answers[7:9] = ["n", str(tmp_path / "games.csv")]
    run_wizard(tmp_path, monkeypatch, answers)

    values = monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))

    assert values["DISABLE_LOGGING"] is True
    assert values["CSV_FILE"] == str(tmp_path / "games.csv")


# Verifies a blank CSV answer disables CSV output rather than storing an empty path as a file name
def test_a_blank_csv_answer_disables_csv_output(tmp_path, monkeypatch, wizard_globals, capsys):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    assert monitor.parse_config_content((tmp_path / "lol_monitor.conf").read_text(encoding="utf-8"))["CSV_FILE"] == ""
    assert "CSV output:                         disabled" in capsys.readouterr().out


# Verifies a CSV answer without an extension is saved as a .csv file while an explicit extension is left alone
@pytest.mark.parametrize("answer,expected", [("games", "games.csv"), ("games.tsv", "games.tsv"), ("", "")])
def test_the_csv_answer_gains_a_csv_extension_when_it_has_none(answer, expected):
    assert monitor._wizard_normalize_csv_path(answer) == expected


# Verifies an existing configuration is replaced only after the user agrees, and is backed up rather than overwritten
def test_an_existing_configuration_is_backed_up(tmp_path, monkeypatch, wizard_globals):
    config_path = tmp_path / "lol_monitor.conf"
    config_path.write_text("RIOT_ID = 'old'\n", encoding="utf-8")
    run_wizard(tmp_path, monkeypatch, ["y"] + minimal_answers())

    backups = list(tmp_path.glob("lol_monitor.conf.*.bak"))

    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "RIOT_ID = 'old'\n"
    assert written_config(tmp_path)["RIOT_ID"] == RIOT_ID


# Verifies setup keeps a copy of the replaced configuration but never of the replaced secrets
def test_setup_backs_up_the_config_but_not_the_dotenv(tmp_path, monkeypatch, wizard_globals):
    (tmp_path / "lol_monitor.conf").write_text("RIOT_ID = 'old'\n", encoding="utf-8")
    (tmp_path / ".env").write_text('SMTP_PASSWORD="old-password"\n', encoding="utf-8")
    run_wizard(tmp_path, monkeypatch, ["y"] + minimal_answers())

    assert len(list(tmp_path.glob("lol_monitor.conf.*.bak"))) == 1
    assert list(tmp_path.glob(".env.*.bak")) == []


# Verifies an existing config can be kept by sending the run to another path instead
def test_an_existing_config_can_be_redirected_to_another_path(tmp_path, monkeypatch, wizard_globals):
    (tmp_path / "lol_monitor.conf").write_text("RIOT_ID = 'old'\n", encoding="utf-8")
    run_wizard(tmp_path, monkeypatch, ["n", str(tmp_path / "other.conf")] + minimal_answers())

    assert (tmp_path / "lol_monitor.conf").read_text(encoding="utf-8") == "RIOT_ID = 'old'\n"
    assert written_config(tmp_path, "other.conf")["RIOT_ID"] == RIOT_ID


# Verifies naming no alternative for an existing config cancels rather than falling back to replacing it
def test_naming_no_alternative_for_an_existing_config_cancels(tmp_path):
    config_path = tmp_path / "lol_monitor.conf"
    config_path.write_text("RIOT_ID = 'old'\n", encoding="utf-8")

    assert monitor._wizard_choose_config_destination(config_path, input_func=scripted_input(["n", ""])) is None


# Verifies declining to replace an existing config and naming no alternative ends the run without writing
def test_declining_an_existing_config_without_an_alternative_writes_nothing(tmp_path, monkeypatch, wizard_globals, capsys):
    (tmp_path / "lol_monitor.conf").write_text("RIOT_ID = 'old'\n", encoding="utf-8")
    code = run_wizard(tmp_path, monkeypatch, ["n", ""])

    assert code == 1
    assert "Setup cancelled. Destination files were not changed." in capsys.readouterr().out
    assert (tmp_path / "lol_monitor.conf").read_text(encoding="utf-8") == "RIOT_ID = 'old'\n"


# Verifies editing a section reverts it to the saved value rather than to the shipped template default
def test_an_edited_section_reverts_to_the_saved_value(tmp_path, monkeypatch, wizard_globals):
    monkeypatch.setattr(monitor, "LOL_CHECK_INTERVAL", 600)
    answers = minimal_answers()
    answers[3] = ""
    answers[9:10] = ["2", "2", "", "", "1"]
    run_wizard(tmp_path, monkeypatch, answers)

    assert written_config(tmp_path)["LOL_CHECK_INTERVAL"] == 600


# Verifies a Riot ID the tool cannot read replaces the one Riot rejected rather than leaving it standing
def test_a_retried_target_does_not_keep_the_rejected_one(tmp_path, monkeypatch, wizard_globals, capsys):
    monkeypatch.setattr(monitor, "_wizard_verify_target", lambda _state: False)
    answers = minimal_answers()
    answers[5:5] = ["n", "no-tag-line", "n"]
    code = run_wizard(tmp_path, monkeypatch, answers)

    assert code == 0
    assert "No target selected." in capsys.readouterr().out
    assert written_config(tmp_path)["RIOT_ID"] == ""


# Verifies the mail server sign-in runs against the answers just collected and puts the previous settings back
def test_the_sign_in_check_applies_and_restores_the_settings(monkeypatch, wizard_globals):
    seen = {}
    monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda ssl, smtp_timeout=None: seen.update({"host": monitor.SMTP_HOST, "password": monitor.SMTP_PASSWORD, "ssl": ssl, "timeout": smtp_timeout}))
    values = {"SMTP_HOST": "smtp.gmail.com", "SMTP_PORT": 465, "SMTP_SSL": True, "SMTP_USER": "monitoring@example.test", "SENDER_EMAIL": "monitoring@example.test", "RECEIVER_EMAIL": "alerts@example.test"}

    assert verify_smtp(values, "typed-password") is None
    assert seen == {"host": "smtp.gmail.com", "password": "typed-password", "ssl": True, "timeout": monitor.WIZARD_SMTP_TIMEOUT}
    assert monitor.SMTP_HOST == monitor._config_template_defaults()["SMTP_HOST"]


# Verifies a blank password answer signs in with the password already stored, which is the one being proved
def test_a_blank_password_answer_signs_in_with_the_stored_one(monkeypatch, wizard_globals):
    seen = {}
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "stored-password")
    monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda ssl, smtp_timeout=None: seen.update({"password": monitor.SMTP_PASSWORD}))
    verify_smtp({"SMTP_HOST": "smtp.gmail.com"}, "")

    assert seen == {"password": "stored-password"}


# Verifies a refused sign-in is reported as advice rather than raised out of the wizard
def test_a_refused_sign_in_becomes_recovery_advice(monkeypatch, wizard_globals):
    def refuse(_ssl, smtp_timeout=None):
        raise monitor.smtplib.SMTPAuthenticationError(535, b"denied")

    monkeypatch.setattr(monitor, "smtp_connect_and_login", refuse)
    advice = verify_smtp({"SMTP_HOST": "smtp.gmail.com"}, "wrong-password")

    assert advice is not None
    assert advice.code == "smtp.authentication"


# Verifies a rerun that keeps the loaded secrets leaves every one of them out of the rebuilt configuration file
def test_a_rerun_keeps_loaded_secrets_out_of_the_configuration(tmp_path, monkeypatch, wizard_globals):
    (tmp_path / "lol_monitor.conf").write_text("RIOT_ID = 'old'\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "RIOT_API_KEY", API_KEY)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "loaded-mail-password")
    answers = ["y"] + minimal_answers()
    answers[6:6] = ["n"]
    code = run_wizard(tmp_path, monkeypatch, answers, secrets=[])

    config_text = (tmp_path / "lol_monitor.conf").read_text(encoding="utf-8")

    assert code == 0
    assert API_KEY not in config_text
    assert "loaded-mail-password" not in config_text
    assert not (tmp_path / ".env").exists()


# Verifies a secret already in the dotenv file is kept when the replacement is declined
def test_an_existing_dotenv_secret_is_kept_unless_the_replacement_is_confirmed(tmp_path, monkeypatch, wizard_globals):
    (tmp_path / ".env").write_text('SMTP_PASSWORD="saved-password"\n', encoding="utf-8")
    mail = ["smtp.gmail.com", "587", "y", "monitoring@example.test", "monitoring@example.test", "alerts@example.test"]
    answers = minimal_answers()
    answers[5:6] = ["y"] + mail + ["n", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "typed-password"])

    dotenv_text = (tmp_path / ".env").read_text(encoding="utf-8")

    assert 'SMTP_PASSWORD="saved-password"' in dotenv_text
    assert "typed-password" not in dotenv_text


# Verifies a confirmed replacement does reach the dotenv file
def test_a_confirmed_dotenv_secret_replacement_is_written(tmp_path, monkeypatch, wizard_globals):
    (tmp_path / ".env").write_text('SMTP_PASSWORD="saved-password"\n', encoding="utf-8")
    mail = ["smtp.gmail.com", "587", "y", "monitoring@example.test", "monitoring@example.test", "alerts@example.test"]
    answers = minimal_answers()
    answers[5:6] = ["y"] + mail + ["y", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "typed-password"])

    assert 'SMTP_PASSWORD="typed-password"' in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies the review can move the configuration file, since the summary shows a destination it could not change
def test_the_destination_section_moves_the_configuration_file(tmp_path, monkeypatch, wizard_globals):
    answers = minimal_answers()
    answers[9:10] = ["2", "7", str(tmp_path / "moved.conf"), str(tmp_path / ".env"), "1"]
    run_wizard(tmp_path, monkeypatch, answers)

    assert written_config(tmp_path, "moved.conf")["RIOT_ID"] == RIOT_ID
    assert not (tmp_path / "lol_monitor.conf").exists()


# Verifies moving the dotenv re-asks every section holding a secret, since a kept secret was never queued
def test_moving_the_dotenv_destination_re_asks_the_secret_sections(tmp_path, monkeypatch, wizard_globals, capsys):
    transcript = []
    answers = minimal_answers()
    answers[9:10] = ["2", "7", str(tmp_path / "lol_monitor.conf"), str(tmp_path / "moved.env"), "n", "n", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, API_KEY], transcript=transcript)
    asked = [prompt for prompt in transcript if prompt.startswith(("Riot API key:", "Configure email notifications", "Set up webhook alerts"))]

    assert "The dotenv destination changed. Re-enter authentication and notification settings that may contain secrets." in capsys.readouterr().out
    assert len(asked) == 6
    assert f'RIOT_API_KEY="{API_KEY}"' in (tmp_path / "moved.env").read_text(encoding="utf-8")


# Verifies one file cannot hold both, since saving the configuration would overwrite the secrets beside it
def test_the_dotenv_destination_cannot_be_the_configuration_file(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = minimal_answers()
    answers[9:10] = ["2", "7", str(tmp_path / "lol_monitor.conf"), str(tmp_path / "lol_monitor.conf"), str(tmp_path / ".env"), "1"]
    run_wizard(tmp_path, monkeypatch, answers)

    assert "The dotenv file has to be a different file from the configuration." in capsys.readouterr().out


# Verifies a destination that cannot be written is refused before the first question is asked
def test_an_unwritable_destination_is_refused_before_any_question(tmp_path, capsys):
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o500)
    try:
        code = monitor.run_setup_wizard(config_file=str(blocked / "lol_monitor.conf"), env_file=str(tmp_path / ".env"), interactive=True)
    finally:
        blocked.chmod(0o700)

    assert code == 1
    assert "is not writable through parent" in capsys.readouterr().out


# Verifies a directory given as a destination is refused rather than failing at the save step
def test_a_directory_destination_is_refused(tmp_path, capsys):
    code = monitor.run_setup_wizard(config_file=str(tmp_path), env_file=str(tmp_path / ".env"), interactive=True)

    assert code == 1
    assert "must be a file path, not a directory" in capsys.readouterr().out


# Verifies the disabled file settings are refused, since setup exists to write both files
@pytest.mark.parametrize("config_file,env_file,expected", [
    ("none", ".env", "--setup requires a config destination"),
    ("lol_monitor.conf", "none", "--setup requires a dotenv destination"),
])
def test_a_disabled_destination_is_refused(tmp_path, capsys, config_file, env_file, expected):
    code = monitor.run_setup_wizard(config_file=config_file, env_file=env_file, interactive=True)

    assert code == 1
    assert expected in capsys.readouterr().out


# Verifies a non-interactive run explains itself and names the alternative instead of hanging
def test_a_non_interactive_run_names_the_alternative(capsys):
    code = monitor.run_setup_wizard(interactive=False)
    printed = capsys.readouterr().out

    assert code == 1
    assert "The setup wizard needs an interactive terminal (TTY)." in printed
    assert "--generate-config" in printed


# Verifies the secret prompts do not repeat where secrets are stored, which the header already said once
def test_secret_prompts_do_not_repeat_the_destination(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    answers = minimal_answers()
    answers[6:7] = ["y", "1", "1"]
    run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, WEBHOOK_URL], transcript=transcript)

    for prompt in transcript:
        assert ".env" not in prompt


# Verifies the shared prompt wording is used, since a user of two of these tools learns it once
def test_the_shared_prompt_wording_is_used(tmp_path, monkeypatch, wizard_globals, capsys):
    run_wizard(tmp_path, monkeypatch, minimal_answers())
    printed = capsys.readouterr().out

    assert "This asks a few questions and writes a ready-to-run configuration." in printed
    assert "Press Enter to accept the shown default. Ctrl+C cancels." in printed
    assert "Secrets go to the dotenv file. Non-secret settings go to the config file." in printed


# Verifies prompts go through the shared colorized reader rather than a bare input call
@pytest.mark.parametrize("ask,arguments", [
    ("_wizard_ask_text", ("Question",)),
    ("_wizard_ask_yes_no", ("Question",)),
    ("_wizard_ask_duration", ("Question", 60)),
])
def test_wizard_prompts_are_colorized(colored, ask, arguments):
    seen = []
    getattr(monitor, ask)(*arguments, input_func=lambda prompt: seen.append(prompt) or "")

    assert seen and seen[0].startswith(colored["info"])


# Verifies hidden prompts are colorized like the visible ones, so one question does not look different
def test_hidden_prompts_are_colorized_like_the_visible_ones(colored):
    seen = []
    monitor._wizard_ask_secret("Riot API key", getpass_func=lambda prompt: seen.append(prompt) or "")

    assert seen == [monitor.colorize("info", "Riot API key: ")]


# Verifies debug output is off while a hidden wizard answer is read and restored afterwards
def test_a_hidden_wizard_answer_is_read_with_debug_output_off(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    seen = []
    monitor._wizard_ask_secret("Riot API key", getpass_func=lambda _prompt: seen.append(monitor.DEBUG_MODE) or "")

    assert seen == [False]
    assert monitor.DEBUG_MODE is True


# Verifies a prompt runs with Python's default Ctrl+C behavior, so the signal handler cannot pre-empt it
def test_prompts_restore_the_default_interrupt_handler():
    seen = []
    previous = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda *_args: None)
    try:
        monitor._wizard_ask_text("Question", input_func=lambda _prompt: seen.append(signal.getsignal(signal.SIGINT)) or "")
    finally:
        signal.signal(signal.SIGINT, previous)

    assert seen == [signal.default_int_handler]


# Verifies a hidden prompt takes the same Ctrl+C path as a visible one while staying a separate reader
def test_hidden_prompts_restore_the_default_interrupt_handler():
    seen = []
    previous = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda *_args: None)
    try:
        monitor._wizard_ask_secret("Riot API key", getpass_func=lambda _prompt: seen.append(signal.getsignal(signal.SIGINT)) or "")
    finally:
        signal.signal(signal.SIGINT, previous)

    assert seen == [signal.default_int_handler]


# Returns an input function that answers the script and then interrupts the next prompt, as Ctrl+C does
def answers_then_interrupt(answers):
    remaining = list(answers)

    def respond(_prompt):
        if not remaining:
            raise KeyboardInterrupt
        return remaining.pop(0)

    return respond


# Verifies an interrupt during questioning leaves the destination files untouched
def test_interrupting_the_questions_reports_untouched_files(tmp_path, monkeypatch, wizard_globals, capsys):
    code = run_wizard(tmp_path, monkeypatch, [], input_func=answers_then_interrupt([RIOT_ID, REGION]))

    assert code == 1
    assert "Setup cancelled. Destination files were not changed." in capsys.readouterr().out
    assert sorted(path.name for path in tmp_path.iterdir()) == []


# Verifies an interrupt at the doctor offer reports the saved setup instead of a cancellation
def test_interrupting_the_doctor_offer_keeps_the_saved_setup(tmp_path, monkeypatch, wizard_globals, capsys):
    code = run_wizard(tmp_path, monkeypatch, [], input_func=answers_then_interrupt(minimal_answers()[:-1]))
    printed = capsys.readouterr().out

    assert code == 0
    assert "Setup is saved. Use the commands below when ready." in printed
    assert "Setup cancelled." not in printed
    assert (tmp_path / "lol_monitor.conf").is_file()


# Verifies an interrupt at the launch offer reports the saved setup and points at the printed command
def test_interrupting_the_launch_offer_keeps_the_saved_setup(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = minimal_answers()
    answers[-1] = "y"
    code = run_wizard(tmp_path, monkeypatch, [], input_func=answers_then_interrupt(answers))
    printed = capsys.readouterr().out

    assert code == 0
    assert "Setup is saved. Start monitoring with the command above when ready." in printed
    assert "Setup cancelled." not in printed


# Verifies the interrupted prompt owns the line break, so the cancellation message is printed on its own line
def test_the_cancellation_message_starts_on_its_own_line(tmp_path, monkeypatch, wizard_globals, capsys):
    run_wizard(tmp_path, monkeypatch, [], input_func=answers_then_interrupt([RIOT_ID]))

    assert "\nSetup cancelled. Destination files were not changed.\n" in capsys.readouterr().out


# Runs the wizard with a real doctor call, so the values it hands over can be inspected
def run_wizard_with_doctor(tmp_path, monkeypatch, answers, secrets, observed, doctor_exit=0, transcript=None):
    def fake_doctor(**_kwargs):
        observed.update({name: getattr(monitor, name) for name in monitor.SECRET_KEYS})
        observed["RIOT_ID"] = monitor.RIOT_ID
        return doctor_exit

    monkeypatch.setattr(monitor, "validate_riot_api_key", lambda _key: True)
    monkeypatch.setattr(monitor, "run_doctor", fake_doctor)
    secret_answers = list(secrets)
    return monitor.run_setup_wizard(
        config_file=str(tmp_path / "lol_monitor.conf"),
        env_file=str(tmp_path / ".env"),
        input_func=scripted_input(answers, transcript),
        getpass_func=lambda _prompt: secret_answers.pop(0) if secret_answers else "",
        interactive=True,
    )


# Verifies the secrets just entered survive into doctor, which the config placeholders used to overwrite
def test_doctor_sees_the_secrets_setup_just_saved(tmp_path, monkeypatch, wizard_globals):
    observed = {}
    answers = minimal_answers()
    answers[-1] = "y"
    run_wizard_with_doctor(tmp_path, monkeypatch, answers + ["n"], [API_KEY], observed)

    assert observed["RIOT_API_KEY"] == API_KEY
    assert observed["RIOT_ID"] == RIOT_ID


# Verifies a secret exported before startup still wins over the value setup wrote, as it will when monitoring runs
def test_an_exported_secret_still_wins_after_setup(tmp_path, monkeypatch, wizard_globals):
    observed = {}
    monkeypatch.setattr(monitor, "EXPORTED_SECRET_KEYS", {"RIOT_API_KEY"})
    os.environ["RIOT_API_KEY"] = "exported-riot-key"
    answers = minimal_answers()
    answers[-1] = "y"
    run_wizard_with_doctor(tmp_path, monkeypatch, answers + ["n"], [API_KEY], observed)

    assert observed["RIOT_API_KEY"] == "exported-riot-key"


# Verifies the launch offer only follows a doctor run that passed, so a declined doctor ends at the printed commands
def test_declining_the_doctor_removes_the_launch_offer(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    code = run_wizard(tmp_path, monkeypatch, minimal_answers(), transcript=transcript)

    assert code == 0
    assert not any(prompt.startswith("Start monitoring now?") for prompt in transcript)


# Verifies a doctor run that passed is what unlocks the launch offer
def test_a_passed_doctor_run_unlocks_the_launch_offer(tmp_path, monkeypatch, wizard_globals):
    observed = {}
    transcript = []
    answers = minimal_answers()
    answers[-1] = "y"
    code = run_wizard_with_doctor(tmp_path, monkeypatch, answers + ["n"], [API_KEY], observed, transcript=transcript)

    assert code == 0
    assert any(prompt.startswith("Start monitoring now? Monitoring will continue until Ctrl+C.") for prompt in transcript)


# Verifies a doctor run that failed keeps the launch offer away and labels the command to run after the fix
def test_a_failed_doctor_run_removes_the_launch_offer(tmp_path, monkeypatch, wizard_globals, capsys):
    observed = {}
    transcript = []
    answers = minimal_answers()
    answers[-1] = "y"
    code = run_wizard_with_doctor(tmp_path, monkeypatch, answers, [API_KEY], observed, doctor_exit=1, transcript=transcript)

    assert code == 0
    assert not any(prompt.startswith("Start monitoring now?") for prompt in transcript)
    assert "After Doctor passes, start monitoring:" in capsys.readouterr().out


# Verifies the launch command carries the target when it was not persisted, so the started run monitors it
def test_the_launch_command_carries_an_unpersisted_target(monkeypatch):
    monkeypatch.setattr(monitor, "install_method", lambda: monitor.INSTALL_METHOD_SCRIPT)
    arguments = monitor._wizard_local_command_args(riot_id=RIOT_ID, region=REGION, config_path="/tmp/lol_monitor.conf", env_path="/tmp/.env")

    assert arguments[2:] == [RIOT_ID, REGION, "--config-file", "/tmp/lol_monitor.conf", "--env-file", "/tmp/.env"]


# Verifies a PyPI install is launched through the module rather than through a script path it may not have
def test_the_launch_command_suits_a_pypi_install(monkeypatch):
    monkeypatch.setattr(monitor, "install_method", lambda: monitor.INSTALL_METHOD_PYPI)
    arguments = monitor._wizard_local_command_args(config_path="/tmp/lol_monitor.conf")

    assert arguments[1:] == ["-m", "lol_monitor", "--config-file", "/tmp/lol_monitor.conf"]


# Verifies the saved files are listed by name, so the reader knows exactly what setup wrote
def test_the_saved_files_are_listed(tmp_path, monkeypatch, wizard_globals, capsys):
    run_wizard(tmp_path, monkeypatch, minimal_answers())
    printed = capsys.readouterr().out

    assert f"  Configuration: {tmp_path / 'lol_monitor.conf'}" in printed
    assert f"  Secrets:       {tmp_path / '.env'}" in printed


# Verifies a run that queued no secret leaves the dotenv file out of the saved list and the printed commands
def test_a_run_with_no_secret_writes_no_dotenv_file(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = minimal_answers()
    answers[5:5] = ["y"]
    code = run_wizard(tmp_path, monkeypatch, answers, secrets=[""])
    printed = capsys.readouterr().out

    assert code == 0
    assert not (tmp_path / ".env").exists()
    assert "Secrets:" not in printed
    assert "--env-file" not in printed


# Verifies the welcome screen offers the commands a newcomer needs next, in the order the siblings print them
def test_the_welcome_screen_offers_the_shared_commands(capsys):
    monitor.print_welcome_screen(interactive=False)
    lines = capsys.readouterr().out.splitlines()
    labels = [line for line in lines if line.endswith(":") or line.startswith(("Full options:", "Guide:"))]

    assert labels == [
        "Quickest start (already configured):",
        "Easiest start (guided setup wizard):",
        "Check setup before monitoring:",
        "Show recent matches and exit:",
        "Full options: " + monitor.render_command(["--help"], include_paths=False),
        "Guide:        " + monitor.QUICK_START_GUIDE_URL,
    ]


# Verifies the accepted forms come from the constants the wizard prompt and the target error already use
def test_the_welcome_screen_names_the_accepted_forms(capsys):
    monitor.print_welcome_screen(interactive=False)
    printed = capsys.readouterr().out

    assert printed.startswith(f"For <riot_id>, use a {monitor.RIOT_ID_FORMS}.\nFor <region>, use a {monitor.REGION_FORMS}.\n\n")


# Verifies the welcome commands are written for this install and leave the placeholders readable
def test_the_welcome_commands_suit_the_install(monkeypatch, capsys):
    monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, "pip")
    monitor.print_welcome_screen(interactive=False)
    printed = capsys.readouterr().out

    assert "    lol_monitor <riot_id> <region>\n" in printed
    assert "python3 lol_monitor.py" not in printed


# Verifies the suffix naming the prompt below appears only where that prompt does
@pytest.mark.parametrize("interactive,expected", [(True, True), (False, False)])
def test_the_setup_suffix_only_appears_beside_its_prompt(capsys, interactive, expected):
    monitor.print_welcome_screen(interactive=interactive, input_func=lambda _prompt: "n")
    printed = capsys.readouterr().out

    assert ("   (or just answer Y below)" in printed) is expected


# Verifies the screen is not offered when there is no terminal to answer on, where a bare run stays a usage error
def test_the_welcome_screen_does_not_offer_the_wizard_without_a_terminal(capsys):
    code = monitor.print_welcome_screen(interactive=False)

    assert code == 1
    assert "Run the guided setup wizard now?" not in capsys.readouterr().out


# Verifies answering no to the welcome offer exits cleanly, since the screen ended in a question that was answered
def test_declining_the_welcome_offer_exits_cleanly(capsys):
    code = monitor.print_welcome_screen(interactive=True, input_func=lambda _prompt: "n")

    assert code == 0
    assert "Setup cancelled." not in capsys.readouterr().out


# Verifies answering yes hands over to the wizard with the destinations the run was given
def test_accepting_the_welcome_offer_starts_the_wizard(tmp_path, monkeypatch, capsys):
    handed = {}
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **kwargs: handed.update(kwargs) or 7)
    code = monitor.print_welcome_screen(interactive=True, input_func=lambda _prompt: "y", config_file=str(tmp_path / "a.conf"), env_file=str(tmp_path / "a.env"))

    assert code == 7
    assert handed["config_file"] == str(tmp_path / "a.conf")
    assert handed["env_file"] == str(tmp_path / "a.env")


# Verifies Ctrl+C at the welcome offer reports one line instead of a traceback, since the prompt sits outside the wizard
def test_interrupting_the_welcome_offer_reports_a_cancellation(capsys):
    def interrupt(_prompt):
        raise KeyboardInterrupt

    code = monitor.print_welcome_screen(interactive=True, input_func=interrupt)
    printed = capsys.readouterr().out

    assert code == 1
    assert printed.rstrip().endswith("Setup cancelled.")
    assert "Destination files were not changed" not in printed


# Verifies pressing Enter at the offer starts the wizard, since the screen exists to get a newcomer into it
def test_the_welcome_offer_defaults_to_starting_the_wizard(tmp_path, monkeypatch):
    started = []
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: started.append(True) or 0)
    monitor.print_welcome_screen(interactive=True, input_func=lambda _prompt: "")

    assert started == [True]


# Verifies each labelled command is indented under its label and followed by one blank line, the shared block shape
def test_a_labelled_command_is_indented_under_its_label(capsys):
    monitor.print_labelled_command("Label:", "tool --flag")

    assert capsys.readouterr().out == "Label:\n    tool --flag\n\n"


# Verifies the command is coloured while the label is not, so the part worth copying stands out
def test_a_labelled_command_is_the_coloured_part(capsys, colored):
    monitor.print_labelled_command("Label:", "tool --flag", " (suffix)")
    printed = capsys.readouterr().out

    assert printed.startswith("Label:\n")
    assert f"    {colored['section']}tool --flag{monitor.ANSI_RESET}" in printed
    assert f"{colored['info']} (suffix){monitor.ANSI_RESET}" in printed


# Verifies the guide link opens the setup page the siblings link, with no section fragment
def test_the_welcome_guide_link_opens_the_shared_setup_page():
    assert monitor.QUICK_START_GUIDE_URL.endswith("/setup-and-first-run/")


# Verifies the screen closes with one blank line, the way it does in every sibling
def test_the_welcome_screen_closes_with_a_blank_line(capsys):
    monitor.print_welcome_screen(interactive=False)

    assert capsys.readouterr().out.endswith(f"{monitor.QUICK_START_GUIDE_URL}\n\n")


# Verifies a bare run reaches the welcome screen rather than the missing-target error
def test_a_bare_run_reaches_the_welcome_screen(tmp_path, monkeypatch, wizard_globals, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "clear_screen", lambda _enabled: None)
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor.signal, "signal", lambda *args: None)
    monkeypatch.setattr(monitor, "find_config_file", lambda _path=None: None)
    monkeypatch.setattr(monitor.sys, "argv", ["lol_monitor"])

    with pytest.raises(SystemExit) as exit_error:
        monitor.main()

    assert exit_error.value.code == 1
    assert "Easiest start (guided setup wizard):" in capsys.readouterr().out


# Verifies a saved target starts monitoring instead of being welcomed, which is what puts the screen after the config read
def test_a_saved_target_is_not_welcomed(tmp_path, monkeypatch, wizard_globals, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "clear_screen", lambda _enabled: None)
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor.signal, "signal", lambda *args: None)
    monkeypatch.setattr(monitor, "find_config_file", lambda _path=None: None)
    monkeypatch.setattr(monitor, "RIOT_ID", RIOT_ID)
    monkeypatch.setattr(monitor, "REGION", REGION)
    monkeypatch.setattr(monitor, "check_internet", lambda *args, **kwargs: False)
    monkeypatch.setattr(monitor.sys, "argv", ["lol_monitor"])

    with pytest.raises(SystemExit):
        monitor.main()

    assert "Easiest start (guided setup wizard):" not in capsys.readouterr().out


# Returns the transcript of driving the real wizard through a pseudo-terminal with scripted answers
def capture_wizard_pty(tmp_path, rules):
    pid, fd = pty.fork()
    if pid == 0:
        os.environ.update({"TERM": "dumb", "NO_COLOR": "1", "LOL_MONITOR_INSTALL_METHOD": "manual"})
        os.execv(sys.executable, [sys.executable, str(REPO_ROOT / "lol_monitor.py"), "--setup", "--config-file", str(tmp_path / "lol_monitor.conf"), "--env-file", str(tmp_path / ".env")])
    transcript = ""
    answered = ""
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.4)
        if ready:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            transcript += chunk.decode("utf-8", errors="replace")
            continue
        prompt = transcript.rsplit("\n", 1)[-1]
        if not prompt.strip() or prompt == answered:
            continue
        answer = next((value for pattern, value in rules if re.search(pattern, prompt)), None)
        if answer is None:
            break
        os.write(fd, answer.encode("utf-8"))
        answered = prompt
    try:
        os.close(fd)
    except OSError:
        pass
    _, status = os.waitpid(pid, 0)
    return transcript, os.waitstatus_to_exitcode(status)


# The answers a scripted terminal run gives, keyed by the prompt each one belongs to
PTY_RULES = [
    (r"Riot ID to monitor", "Faker#KR1\n"),
    (r"^Region ", "kr\n"),
    (r"Persist this target", "\n"),
    (r"polling interval", "\n"),
    (r"Riot API key:", "\n"),
    (r"Continue without the Riot API key", "y\n"),
    (r"Configure email notifications", "n\n"),
    (r"Set up webhook alerts", "n\n"),
    (r"Write the normal per-target log file", "\n"),
    (r"Optional CSV output path", "\n"),
    (r"^Choose \[1-", "1\n"),
    (r"Run doctor now", "n\n"),
]


@pytest.mark.skipif(sys.platform == "win32", reason="pty is not available on Windows")
# Verifies the wizard layout holds on the path a user walks, which is the seam unit tests cannot see
def test_the_wizard_transcript_holds_the_output_contract(tmp_path):
    transcript, code = capture_wizard_pty(tmp_path, PTY_RULES)
    lines = transcript.replace("\r\n", "\n").split("\n")

    assert code == 0, transcript
    header = lines.index("Setup Wizard")
    assert lines[header - 1] == ""
    assert lines[header + 1] == ""
    assert lines[header + 2] == "This asks a few questions and writes a ready-to-run configuration."
    assert lines[header + 3] == "Press Enter to accept the shown default. Ctrl+C cancels."
    assert lines[header + 4] == ""
    assert lines[header + 5] == "Secrets go to the dotenv file. Non-secret settings go to the config file."
    assert lines[header + 6] == ""
    assert lines[header + 7] == "Detected install method: manual"
    assert lines[header + 8] == f"Configuration:          {tmp_path / 'lol_monitor.conf'}"
    assert lines[header + 9] == f"Dotenv:                 {tmp_path / '.env'}"
    assert transcript.index("Setup summary") < transcript.index("Saved files") < transcript.index("Next steps")
    assert transcript.rstrip().endswith(f"Guide: {monitor.QUICK_START_GUIDE_URL}")


@pytest.mark.skipif(sys.platform == "win32", reason="pty is not available on Windows")
# Verifies Ctrl+C on the real terminal path reports one line and writes nothing, rather than a traceback
def test_an_interrupt_on_the_terminal_path_writes_nothing(tmp_path):
    transcript, code = capture_wizard_pty(tmp_path, [(r"Riot ID to monitor", "\x03")])

    assert code == 1
    assert "Setup cancelled. Destination files were not changed." in transcript
    assert "Traceback" not in transcript
    assert sorted(path.name for path in tmp_path.iterdir()) == []
