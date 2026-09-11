"""Tests for the three one-shot secret commands and the private dotenv file they write."""

import ast
import inspect
import os
import stat

import pytest

DISCORD_URL = "https://discord.com/api/webhooks/123456789/private-token-value"
NTFY_URL = "https://ntfy.sh/my-private-topic"


@pytest.fixture(autouse=True)
# Keeps rendered next-step commands deterministic regardless of how the suite itself was started
def isolated_rendering(monkeypatch, lm_module):
    monkeypatch.delenv(lm_module.INSTALL_METHOD_ENV_VAR, raising=False)
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", None)


# Answers one prompt from a scripted queue and records what it was asked
class ScriptedPrompt:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    # Returns the next scripted answer, or raises it when the script holds an exception
    def __call__(self, prompt=""):
        self.prompts.append(prompt)
        if not self.answers:
            raise AssertionError(f"the command asked {len(self.prompts)} questions but the script held fewer answers")
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer


# Fails the test rather than letting a command ask a question it should never reach
def refuse_prompt(prompt=""):
    raise AssertionError(f"the command asked {prompt!r} when it should not have")


# ---------------------------------------------------------------------------
# The private destination
# ---------------------------------------------------------------------------


# Verifies an unnamed destination is the dotenv file beside the run, never one found in a parent directory
def test_an_unnamed_destination_is_the_file_beside_the_run(lm_module, tmp_path):
    (tmp_path / ".env").write_text("", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()

    assert lm_module.resolve_secret_env_path(cwd=nested) == (nested / ".env").resolve()


# Verifies a named destination is expanded, so a path written with a tilde reaches the right home directory
def test_a_named_destination_is_expanded(lm_module, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    assert lm_module.resolve_secret_env_path("~/secrets.env") == (tmp_path / "secrets.env").resolve()


@pytest.mark.parametrize("sentinel", ["none", "None", "NONE"])
# Verifies the sentinel that switches the dotenv file off is refused, since a secret needs somewhere to go
def test_the_disabled_dotenv_sentinel_is_refused(lm_module, sentinel):
    with pytest.raises(lm_module.SecretConfigurationError, match="writable path"):
        lm_module.resolve_secret_env_path(sentinel)


@pytest.mark.parametrize("value,expected", [
    ("plain", '"plain"'),
    ('has "quotes"', '"has \\"quotes\\""'),
    ("has\\backslash", '"has\\\\backslash"'),
    ("has\nnewline", '"has\\nnewline"'),
    ("has\rreturn", '"has\\rreturn"'),
])
# Verifies a saved value is quoted and escaped, so nothing inside it can end the assignment early
def test_a_saved_value_is_quoted_and_escaped(lm_module, value, expected):
    assert lm_module._format_dotenv_value(value) == expected


# Verifies a value that is not text is refused rather than written as its repr
def test_a_value_that_is_not_text_is_refused(lm_module):
    with pytest.raises(TypeError):
        lm_module._format_dotenv_value(7)


@pytest.mark.parametrize("line,present", [
    ('RIOT_API_KEY="x"', True),
    ("  RIOT_API_KEY=x", True),
    ("export RIOT_API_KEY=x", True),
    ("RIOT_API_KEY_OLD=x", False),
    ("# RIOT_API_KEY=x", False),
    ("SMTP_PASSWORD=x", False),
])
# Verifies an existing assignment is recognised in every shape a dotenv file writes it, and only that key
def test_an_existing_assignment_is_recognised(lm_module, tmp_path, line, present):
    destination = tmp_path / ".env"
    destination.write_text(line + "\n", encoding="utf-8")

    assert lm_module._dotenv_contains_key(destination, "RIOT_API_KEY") is present


# Verifies a destination that does not exist yet holds nothing rather than failing the check
def test_a_missing_destination_holds_nothing(lm_module, tmp_path):
    assert lm_module._dotenv_contains_key(tmp_path / "absent.env", "RIOT_API_KEY") is False


# Verifies a destination the tool cannot read is reported rather than treated as empty and overwritten
def test_an_unreadable_destination_is_reported(lm_module, tmp_path):
    destination = tmp_path / ".env"
    destination.write_bytes(b"RIOT_API_KEY=\xff\xfe\n")

    with pytest.raises(lm_module.SecretConfigurationError, match="readable UTF-8"):
        lm_module._dotenv_contains_key(destination, "RIOT_API_KEY")


# ---------------------------------------------------------------------------
# The dotenv writer
# ---------------------------------------------------------------------------


# Verifies a new destination is created with the value and nothing else
def test_a_new_destination_is_created_with_the_value(lm_module, tmp_path):
    destination = tmp_path / "secrets" / ".env"

    result = lm_module.update_dotenv_file(destination, {"RIOT_API_KEY": "entered-riot-key"})

    assert destination.read_text(encoding="utf-8") == 'RIOT_API_KEY="entered-riot-key"\n'
    assert result["updated_keys"] == ("RIOT_API_KEY",)


# Verifies every other line survives a replacement, so a shared dotenv file is not rewritten around one secret
def test_every_other_line_survives_a_replacement(lm_module, tmp_path):
    destination = tmp_path / ".env"
    destination.write_text("# a comment\nOTHER=keep-me\nRIOT_API_KEY=old\n\nLAST=also-keep\n", encoding="utf-8")

    lm_module.update_dotenv_file(destination, {"RIOT_API_KEY": "new"})

    assert destination.read_text(encoding="utf-8") == '# a comment\nOTHER=keep-me\nRIOT_API_KEY="new"\n\nLAST=also-keep\n'


# Verifies the value is replaced where it already sits rather than appended below the stale one
def test_the_value_is_replaced_where_it_already_sits(lm_module, tmp_path):
    destination = tmp_path / ".env"
    destination.write_text("RIOT_API_KEY=old\nOTHER=x\n", encoding="utf-8")

    lm_module.update_dotenv_file(destination, {"RIOT_API_KEY": "new"})

    lines = destination.read_text(encoding="utf-8").splitlines()
    assert lines == ['RIOT_API_KEY="new"', "OTHER=x"]


# Verifies a duplicated assignment is collapsed, so no stale copy is left further down the file
def test_a_duplicated_assignment_is_collapsed(lm_module, tmp_path):
    destination = tmp_path / ".env"
    destination.write_text("RIOT_API_KEY=first\nOTHER=x\nRIOT_API_KEY=second\n", encoding="utf-8")

    lm_module.update_dotenv_file(destination, {"RIOT_API_KEY": "new"})

    assert destination.read_text(encoding="utf-8") == 'RIOT_API_KEY="new"\nOTHER=x\n'


# Verifies a cleared secret is removed rather than left as an empty assignment nothing would notice
def test_a_cleared_secret_is_removed(lm_module, tmp_path):
    destination = tmp_path / ".env"
    destination.write_text("RIOT_API_KEY=old\nOTHER=x\n", encoding="utf-8")

    lm_module.update_dotenv_file(destination, {"RIOT_API_KEY": ""})

    assert destination.read_text(encoding="utf-8") == "OTHER=x\n"


# Verifies a private settings file is readable only by its owner
@pytest.mark.skipif(os.name != "posix", reason="file modes are a POSIX concept")
def test_the_private_settings_file_is_owner_only(lm_module, tmp_path):
    destination = tmp_path / ".env"

    lm_module.update_dotenv_file(destination, {"RIOT_API_KEY": "value"})

    assert stat.S_IMODE(destination.stat().st_mode) == 0o600


# Verifies a replaced credential leaves no backup copy behind, since a stale secret on disk is the one thing not worth keeping
def test_a_replaced_credential_leaves_no_backup(lm_module, tmp_path):
    destination = tmp_path / ".env"
    destination.write_text("RIOT_API_KEY=old\n", encoding="utf-8")

    lm_module.update_dotenv_file(destination, {"RIOT_API_KEY": "new"})

    assert [path.name for path in tmp_path.iterdir()] == [".env"]
    assert "old" not in destination.read_text(encoding="utf-8")


# Verifies a failed write leaves no temporary file behind and leaves the original untouched
def test_a_failed_write_leaves_nothing_behind(lm_module, monkeypatch, tmp_path):
    destination = tmp_path / ".env"
    destination.write_text("RIOT_API_KEY=old\n", encoding="utf-8")

    def failing_replace(source, target):
        raise OSError("the replacement failed")

    monkeypatch.setattr(lm_module.os, "replace", failing_replace)

    with pytest.raises(OSError):
        lm_module.update_dotenv_file(destination, {"RIOT_API_KEY": "new"})

    assert destination.read_text(encoding="utf-8") == "RIOT_API_KEY=old\n"
    assert [path.name for path in tmp_path.iterdir()] == [".env"]


# Verifies only the tool's own secrets can be written, so a caller cannot use this to edit arbitrary settings
def test_only_the_tools_own_secrets_can_be_written(lm_module, tmp_path):
    with pytest.raises(ValueError, match="Unsupported dotenv key"):
        lm_module.update_dotenv_file(tmp_path / ".env", {"PATH": "/tmp"})
    with pytest.raises(ValueError, match="Unsupported dotenv key"):
        lm_module.update_dotenv_file(tmp_path / ".env", {"riot_api_key": "value"})


# Verifies every writable key is one the tool actually resolves as a secret
def test_every_writable_key_is_a_known_secret(lm_module):
    assert set(lm_module.SECRET_KEYS) >= {"RIOT_API_KEY", "SMTP_PASSWORD", "WEBHOOK_URL", "NTFY_ACCESS_TOKEN"}


# Verifies a value that is not text is refused before anything reaches the file
def test_a_non_text_value_never_reaches_the_file(lm_module, tmp_path):
    destination = tmp_path / ".env"

    with pytest.raises(TypeError):
        lm_module.update_dotenv_file(destination, {"RIOT_API_KEY": 7})

    assert not destination.exists()


# ---------------------------------------------------------------------------
# Checking a value before it is saved
# ---------------------------------------------------------------------------


# Verifies a Riot key is checked against the live service and the module is left holding its previous key
def test_a_riot_key_is_checked_without_keeping_it(lm_module, monkeypatch):
    probed = []

    async def fake_probe(region):
        probed.append(region)
        return {"id": region}

    monkeypatch.setattr(lm_module, "riot_api_key_probe", fake_probe)

    assert lm_module.validate_riot_api_key("entered-riot-key") is True
    assert probed == [lm_module.RIOT_API_KEY_PROBE_REGION]
    assert lm_module.RIOT_API_KEY == "riot-api-key-test-value"


# Verifies the configured region is preferred, so the check reaches the same host a real run would
def test_the_configured_region_is_preferred_for_the_check(lm_module, monkeypatch):
    probed = []

    async def fake_probe(region):
        probed.append(region)
        return {}

    monkeypatch.setattr(lm_module, "REGION", "eun1")
    monkeypatch.setattr(lm_module, "riot_api_key_probe", fake_probe)

    lm_module.validate_riot_api_key("entered-riot-key")

    assert probed == ["eun1"]


# Verifies a key Riot refuses reports failure and still leaves the previous key in place
def test_a_refused_riot_key_reports_failure(lm_module, monkeypatch):
    async def fake_probe(region):
        raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr(lm_module, "riot_api_key_probe", fake_probe)

    assert lm_module.validate_riot_api_key("entered-riot-key") is False
    assert lm_module.RIOT_API_KEY == "riot-api-key-test-value"


@pytest.mark.parametrize("candidate", ["", "   ", "your_riot_api_key"])
# Verifies an empty or placeholder key is refused without spending a request on it
def test_an_empty_or_placeholder_riot_key_is_refused(lm_module, monkeypatch, candidate):
    probed = []

    async def record(region):
        probed.append(region)
        return {}

    monkeypatch.setattr(lm_module, "riot_api_key_probe", record)

    assert lm_module.validate_riot_api_key(candidate) is False
    assert probed == []


# Verifies a password is checked by signing in and the module is left holding its previous password
def test_a_password_is_checked_by_signing_in(lm_module, smtp_double):
    assert lm_module.smtp_sign_in("entered-password") == "monitor@example.test"

    assert smtp_double.last.login_args == ("monitor@example.test", "entered-password")
    assert smtp_double.last.sent is None
    assert smtp_double.last.quit_called is True
    assert lm_module.SMTP_PASSWORD == "not-a-real-password"


# Verifies the previous password is restored even when the sign-in fails
def test_the_previous_password_is_restored_after_a_failed_sign_in(lm_module, monkeypatch):
    def failing_login(use_ssl, smtp_timeout=15):
        raise RuntimeError("535 authentication failed")

    monkeypatch.setattr(lm_module, "smtp_connect_and_login", failing_login)

    with pytest.raises(RuntimeError):
        lm_module.smtp_sign_in("entered-password")

    assert lm_module.SMTP_PASSWORD == "not-a-real-password"


@pytest.mark.parametrize("candidate", ["", "your_smtp_password"])
# Verifies an empty or placeholder password is refused without opening a connection
def test_an_empty_or_placeholder_password_is_refused(lm_module, candidate):
    with pytest.raises(lm_module.SecretConfigurationError, match="No SMTP password"):
        lm_module.smtp_sign_in(candidate)


# Verifies a sign-in is refused while the mail server itself is unconfigured
def test_a_sign_in_is_refused_while_the_mail_server_is_unconfigured(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "SMTP_HOST", "")

    with pytest.raises(lm_module.SecretConfigurationError, match="settings are incomplete"):
        lm_module.smtp_sign_in("entered-password")


@pytest.mark.parametrize("name", ["SMTP_HOST", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL"])
# Verifies every setting a sign-in needs is one the completeness check actually reads
def test_every_setting_a_sign_in_needs_is_checked(lm_module, monkeypatch, name):
    assert lm_module.mail_sign_in_settings_complete() is True

    monkeypatch.setattr(lm_module, name, "")

    assert lm_module.mail_sign_in_settings_complete() is False


# ---------------------------------------------------------------------------
# --set-riot-api-key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("runner,flag", [("run_set_riot_api_key", "--set-riot-api-key"), ("run_set_smtp_password", "--set-smtp-password"), ("run_set_webhook_url", "--set-webhook-url")])
# Verifies no secret command reads a value without a terminal, so nothing is typed where it would be echoed
def test_no_secret_command_reads_a_value_without_a_terminal(lm_module, tmp_path, runner, flag):
    with pytest.raises(lm_module.SecretConfigurationError, match="interactive terminal"):
        getattr(lm_module, runner)(env_file=tmp_path / ".env", interactive=False, input_func=refuse_prompt, getpass_func=refuse_prompt)


# Verifies a validated key is saved and the run says what to do next
def test_a_validated_riot_key_is_saved(lm_module, tmp_path, capsys):
    destination = tmp_path / ".env"

    lm_module.run_set_riot_api_key(env_file=destination, interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("  entered-riot-key  "), validator=lambda key: True)

    assert destination.read_text(encoding="utf-8") == 'RIOT_API_KEY="entered-riot-key"\n'
    output = capsys.readouterr().out
    assert "Riot API key is valid" in output
    assert "--doctor" in output
    assert "entered-riot-key" not in output


# Verifies a key the service refuses never reaches the file
def test_a_refused_riot_key_never_reaches_the_file(lm_module, tmp_path):
    destination = tmp_path / ".env"

    with pytest.raises(lm_module.SecretConfigurationError, match="was not changed"):
        lm_module.run_set_riot_api_key(env_file=destination, interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("refused-riot-key"), validator=lambda key: False)

    assert not destination.exists()


# Verifies a saved key is replaced only after the operator says so
def test_a_saved_riot_key_is_replaced_only_after_approval(lm_module, tmp_path):
    destination = tmp_path / ".env"
    destination.write_text('RIOT_API_KEY="old"\n', encoding="utf-8")

    lm_module.run_set_riot_api_key(env_file=destination, interactive=True, input_func=ScriptedPrompt("y"), getpass_func=ScriptedPrompt("replacement-riot-key"), validator=lambda key: True)

    assert destination.read_text(encoding="utf-8") == 'RIOT_API_KEY="replacement-riot-key"\n'


# Verifies a declined replacement reads as a decision rather than as a cancellation, and changes nothing
def test_a_declined_replacement_is_its_own_answer(lm_module, tmp_path):
    destination = tmp_path / ".env"
    destination.write_text('RIOT_API_KEY="old"\n', encoding="utf-8")

    with pytest.raises(lm_module.RecoveryError) as raised:
        lm_module.run_set_riot_api_key(env_file=destination, interactive=True, input_func=ScriptedPrompt("n"), getpass_func=refuse_prompt, validator=lambda key: True)

    assert raised.value.advice.summary == "The saved Riot API key was left as it is and the dotenv file was not changed"
    assert "answer y to replace" in raised.value.advice.fix
    assert destination.read_text(encoding="utf-8") == 'RIOT_API_KEY="old"\n'


@pytest.mark.parametrize("interruption", [EOFError(), KeyboardInterrupt()])
# Verifies a cancelled entry reads as a cancellation rather than as a refusal, and changes nothing
def test_a_cancelled_entry_is_its_own_answer(lm_module, tmp_path, interruption):
    destination = tmp_path / ".env"

    with pytest.raises(lm_module.RecoveryError) as raised:
        lm_module.run_set_riot_api_key(env_file=destination, interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt(interruption), validator=lambda key: True)

    assert raised.value.advice.summary == "Riot API key setup was cancelled and the dotenv file was not changed"
    assert "when you have the value ready" in raised.value.advice.fix
    assert not destination.exists()


# Verifies a cancelled confirmation is a cancellation too, since the operator never got to the value
def test_a_cancelled_confirmation_is_a_cancellation(lm_module, tmp_path):
    destination = tmp_path / ".env"
    destination.write_text('RIOT_API_KEY="old"\n', encoding="utf-8")

    with pytest.raises(lm_module.RecoveryError) as raised:
        lm_module.run_set_riot_api_key(env_file=destination, interactive=True, input_func=ScriptedPrompt(KeyboardInterrupt()), getpass_func=refuse_prompt, validator=lambda key: True)

    assert raised.value.advice.summary.endswith("was cancelled and the dotenv file was not changed")


# Verifies a destination the tool cannot write names the flag that chooses another one
def test_an_unwritable_destination_names_the_flag_that_moves_it(lm_module, monkeypatch, tmp_path):
    def failing_write(destination, updates):
        raise OSError("read-only file system")

    monkeypatch.setattr(lm_module, "update_dotenv_file", failing_write)

    with pytest.raises(lm_module.SecretConfigurationError, match="--env-file"):
        lm_module.run_set_riot_api_key(env_file=tmp_path / ".env", interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("replacement-riot-key"), validator=lambda key: True)


# ---------------------------------------------------------------------------
# --set-smtp-password
# ---------------------------------------------------------------------------


# Verifies a password the mail server accepts is saved and the run says what to do next
def test_an_accepted_password_is_saved(lm_module, tmp_path, capsys):
    destination = tmp_path / ".env"

    lm_module.run_set_smtp_password(env_file=destination, interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("  entered-password  "), sign_in=lambda password, timeout=None: "monitor@example.test")

    assert destination.read_text(encoding="utf-8") == 'SMTP_PASSWORD="entered-password"\n'
    output = capsys.readouterr().out
    assert "accepted the password for monitor@example.test" in output
    assert "--send-test-email" in output
    assert "entered-password" not in output


# Verifies the sign-in check waits far less than a real delivery, so an unreachable host cannot stall the prompt
def test_the_sign_in_check_uses_the_shorter_timeout(lm_module, tmp_path):
    seen = {}

    def sign_in(password, timeout=None):
        seen["timeout"] = timeout
        return "monitor@example.test"

    lm_module.run_set_smtp_password(env_file=tmp_path / ".env", interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("entered"), sign_in=sign_in)

    assert seen["timeout"] == lm_module.SECRET_ENTRY_SMTP_TIMEOUT


# Verifies the mail server is named before the prompt, so nobody types a password into an unexpected sign-in
def test_the_mail_server_is_named_before_the_prompt(lm_module, tmp_path, capsys):
    lm_module.run_set_smtp_password(env_file=tmp_path / ".env", interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("entered"), sign_in=lambda password, timeout=None: "monitor@example.test")

    assert "signing in to smtp.example.test as monitor@example.test. Nothing is sent" in capsys.readouterr().out


# Verifies an unconfigured mail server stops the command before anything is typed
def test_an_unconfigured_mail_server_stops_the_command_before_the_prompt(lm_module, monkeypatch, tmp_path):
    monkeypatch.setattr(lm_module, "SMTP_HOST", "")

    with pytest.raises(lm_module.SecretConfigurationError, match="settings are incomplete"):
        lm_module.run_set_smtp_password(env_file=tmp_path / ".env", interactive=True, input_func=refuse_prompt, getpass_func=refuse_prompt)


# Verifies the incomplete-settings message states the problem once and leaves the fix to the recovery line
def test_the_incomplete_settings_message_does_not_repeat_its_own_fix(lm_module):
    advice = lm_module.classify_recovery_error(lm_module.SecretConfigurationError(lm_module.MAIL_SETTINGS_INCOMPLETE_MESSAGE), context="set_smtp_password")

    assert advice.summary == "The mail server settings are incomplete"
    assert advice.fix.splitlines()[0] == "Set SMTP_HOST, SMTP_USER, SENDER_EMAIL and RECEIVER_EMAIL first"
    assert advice.fix.splitlines()[0] not in advice.summary


# Verifies a password the mail server refuses never reaches the file
def test_a_refused_password_never_reaches_the_file(lm_module, tmp_path):
    destination = tmp_path / ".env"

    def refuse(password, timeout=None):
        raise RuntimeError("535 authentication failed")

    with pytest.raises(lm_module.SecretConfigurationError, match="did not accept the password"):
        lm_module.run_set_smtp_password(env_file=destination, interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("wrong"), sign_in=refuse)

    assert not destination.exists()


# Verifies a refusal never echoes the password that was typed
def test_a_refusal_never_echoes_the_password(lm_module, tmp_path):
    def refuse(password, timeout=None):
        raise RuntimeError(f"535 rejected {password}")

    with pytest.raises(lm_module.SecretConfigurationError) as raised:
        lm_module.run_set_smtp_password(env_file=tmp_path / ".env", interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("s3cr3t-password"), sign_in=refuse)

    assert "s3cr3t-password" not in str(raised.value)


# ---------------------------------------------------------------------------
# --set-webhook-url
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url,provider", [(NTFY_URL, "ntfy"), (DISCORD_URL, "Discord")])
# Verifies a valid destination is saved and the service it belongs to is named back to the operator
def test_a_valid_destination_is_saved_and_its_service_named(lm_module, tmp_path, capsys, url, provider):
    destination = tmp_path / ".env"

    lm_module.run_set_webhook_url(env_file=destination, interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt(f"  {url}  "))

    assert destination.read_text(encoding="utf-8") == f'WEBHOOK_URL="{url}"\n'
    output = capsys.readouterr().out
    assert f"Webhook URL looks valid ({provider})" in output
    assert "--send-test-webhook" in output
    assert url not in output


# Verifies a destination on an unrecognised host is still saved, without naming a service the tool guessed
def test_a_destination_on_an_unrecognised_host_is_saved_without_a_service(lm_module, tmp_path, capsys):
    lm_module.run_set_webhook_url(env_file=tmp_path / ".env", interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("https://hooks.example.test/services/abc"))

    assert "* Webhook URL looks valid\n" in capsys.readouterr().out


# Verifies a value that is not a complete HTTPS link never reaches the file
def test_a_value_that_is_not_a_destination_never_reaches_the_file(lm_module, tmp_path):
    destination = tmp_path / ".env"

    with pytest.raises(lm_module.SecretConfigurationError, match="complete HTTPS webhook URL"):
        lm_module.run_set_webhook_url(env_file=destination, interactive=True, input_func=refuse_prompt, getpass_func=ScriptedPrompt("ntfy.sh/topic"))

    assert not destination.exists()


# ---------------------------------------------------------------------------
# Keeping the value off the screen
# ---------------------------------------------------------------------------


# Verifies debug tracing is off inside the block and restored afterwards, whatever the block did
def test_debug_tracing_is_off_inside_the_block_and_restored_after(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)

    with lm_module.debug_output_suppressed():
        lm_module.debug_print("Secret entry", value="s3cr3t")
        assert lm_module.DEBUG_MODE is False

    assert lm_module.DEBUG_MODE is True
    assert capsys.readouterr().out == ""


# Verifies the previous mode is restored even when the block raises
def test_the_previous_debug_mode_is_restored_after_a_failure(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)

    with pytest.raises(RuntimeError):
        with lm_module.debug_output_suppressed():
            raise RuntimeError("the block failed")

    assert lm_module.DEBUG_MODE is True


# Verifies each secret command is wrapped, so a debug run cannot trace the value being entered
@pytest.mark.parametrize("runner", ["run_set_riot_api_key", "run_set_smtp_password", "run_set_webhook_url"])
def test_every_secret_command_suppresses_debug_output(lm_module, monkeypatch, tmp_path, capsys, runner):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    seen = []

    def record(prompt=""):
        seen.append(lm_module.DEBUG_MODE)
        raise EOFError

    with pytest.raises(lm_module.RecoveryError):
        getattr(lm_module, runner)(env_file=tmp_path / ".env", interactive=True, input_func=record, getpass_func=record)

    assert seen == [False]
    assert lm_module.DEBUG_MODE is True
    assert "[DEBUG" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------


# Verifies each secret command is one the dotenv-writing check recognises, so no run warns about a file it creates
@pytest.mark.parametrize("flag", ["--set-riot-api-key", "--set-smtp-password", "--set-webhook-url", "--setup"])
def test_each_writing_command_is_recognised(lm_module, flag):
    assert lm_module.command_writes_dotenv([flag]) is True


# Verifies a command that only reads is not treated as one that writes
def test_a_reading_command_is_not_treated_as_a_writer(lm_module):
    assert lm_module.command_writes_dotenv(["--doctor"]) is False
    assert lm_module.command_writes_dotenv([]) is False


# Verifies every declared secret flag is one the command line actually offers, so the list cannot drift from the parser
def test_every_declared_secret_flag_is_offered(lm_module):
    offered = set()
    for node in ast.walk(ast.parse(inspect.getsource(lm_module))):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument":
            offered.update(argument.value for argument in node.args if isinstance(argument, ast.Constant) and isinstance(argument.value, str))

    assert set(lm_module.SECRET_ACTION_FLAGS) <= offered


# Verifies each flag is dispatched to its own command, so no secret is written by the wrong one
@pytest.mark.parametrize("flag,runner", [("--set-riot-api-key", "run_set_riot_api_key"), ("--set-smtp-password", "run_set_smtp_password"), ("--set-webhook-url", "run_set_webhook_url")])
def test_each_flag_is_dispatched_to_its_own_command(lm_module, flag, runner):
    source = inspect.getsource(lm_module)
    dest = flag.lstrip("-").replace("-", "_")

    assert f'"{flag}"' in source
    assert f"args.{dest}" in source
    assert f"{runner}(env_file=" in source


# Verifies an assignment the owner exported keeps its export, since dropping it changes what a shell sourcing the file exports
def test_an_exported_assignment_keeps_its_export(tmp_path, lm_module):
    destination = tmp_path / ".env"
    destination.write_text('export SMTP_PASSWORD="old"\nOTHER=keep\n', encoding="utf-8")

    lm_module.update_dotenv_file(destination, {"SMTP_PASSWORD": "new"})

    assert destination.read_text(encoding="utf-8") == 'export SMTP_PASSWORD="new"\nOTHER=keep\n'


# Verifies a line break inside a value is escaped rather than written through, since a raw one would split the assignment
def test_a_line_break_in_a_value_cannot_split_the_assignment(tmp_path, lm_module):
    destination = tmp_path / ".env"

    lm_module.update_dotenv_file(destination, {"SMTP_PASSWORD": "one\ntwo"})

    assert destination.read_text(encoding="utf-8") == 'SMTP_PASSWORD="one\\ntwo"\n'


# Verifies the writer refuses a key this tool does not ship, so a typo cannot put an unknown name in the private file
def test_the_writer_refuses_a_key_this_tool_does_not_ship(tmp_path, lm_module):
    with pytest.raises(ValueError):
        lm_module.update_dotenv_file(tmp_path / ".env", {"NOT_A_SECRET": "value"})


# Verifies the writer refuses a value that is not text, so a mistyped caller fails before the file is touched
def test_the_writer_refuses_a_value_that_is_not_text(tmp_path, lm_module):
    with pytest.raises(TypeError):
        lm_module.update_dotenv_file(tmp_path / ".env", {"SMTP_PASSWORD": 1234})
