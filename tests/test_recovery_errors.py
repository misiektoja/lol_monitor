"""Tests for the closed recovery taxonomy, the advice each failure carries and the shared error block."""

import ast
import inspect

import pytest

CONTEXTS = ("config", "credentials", "target.missing", "target.region", "target", "connectivity", "email", "webhook", "set_riot_api_key", "set_smtp_password", "set_webhook_url", "file", "file.exists", "file.unwritable", "runtime")


@pytest.fixture(autouse=True)
# Keeps rendered commands deterministic regardless of how the suite itself was started
def isolated_rendering(monkeypatch, lm_module):
    monkeypatch.delenv(lm_module.INSTALL_METHOD_ENV_VAR, raising=False)
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/lol_monitor"])
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "")


# Verifies a code outside the closed set is refused, so a typo cannot invent a category nothing handles
def test_an_unknown_recovery_code_is_refused(lm_module):
    with pytest.raises(ValueError):
        lm_module.make_recovery_advice("riot.exploded", "Summary", "Fix", False)


@pytest.mark.parametrize("context", CONTEXTS)
# Verifies every context produces a declared code, which is what makes the taxonomy closed rather than nominal
def test_the_classifier_only_produces_declared_codes(lm_module, context):
    advice = lm_module.classify_recovery_error(RuntimeError("something went wrong"), context=context)

    assert advice.code in lm_module.RECOVERY_CODES


# Verifies every declared code has a producer, so the set records what the tool reports rather than what it might
def test_every_declared_code_is_reachable(lm_module):
    produced = set()
    for context in CONTEXTS:
        for error in (RuntimeError("rate limit exceeded"), RuntimeError("request timed out"), RuntimeError("connection refused"), RuntimeError("401 Unauthorized"), RuntimeError("404 not found"), RuntimeError("500 Internal Server Error"), RuntimeError("authentication failed"), RuntimeError("the settings are incorrect"), RuntimeError("name and tagline"), RuntimeError("does not exist"), RuntimeError("something surprising")):
            produced.add(lm_module.classify_recovery_error(error, context=context).code)
    # A doctor row builds its own advice rather than going through the classifier, so those call sites count too
    for node in ast.walk(ast.parse(inspect.getsource(lm_module))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "make_recovery_advice" and node.args:
            code = node.args[0]
            if isinstance(code, ast.Constant) and isinstance(code.value, str):
                produced.add(code.value)

    assert produced == set(lm_module.RECOVERY_CODES), f"codes with no producer: {sorted(set(lm_module.RECOVERY_CODES) - produced)}"


# Verifies a rate limit is retryable, since the tool waits it out rather than asking the user to act
def test_a_rate_limit_is_retryable(lm_module):
    advice = lm_module.classify_recovery_error(RuntimeError("429 rate limit exceeded"))

    assert advice.code == "riot.rate_limited"
    assert advice.retryable is True


# Verifies a rejected key is not retryable, since retrying it forever hides the one thing the user must change
def test_a_rejected_api_key_is_not_retryable(lm_module):
    advice = lm_module.classify_recovery_error(RuntimeError("401 Unauthorized"))

    assert advice.code == "auth.api_key_invalid"
    assert advice.retryable is False
    assert lm_module.RIOT_API_KEY_REGISTRATION_URL in advice.fix


# Verifies a Riot outage is retryable while a missing account is not, since only one of them resolves itself
def test_an_outage_and_a_missing_account_are_separated(lm_module):
    outage = lm_module.classify_recovery_error(RuntimeError("500 Internal Server Error"))
    missing = lm_module.classify_recovery_error(RuntimeError("404 not found"))

    assert (outage.code, outage.retryable) == ("riot.unavailable", True)
    assert (missing.code, missing.retryable) == ("target.not_found", False)


# Verifies both connectivity failures name the same four things to check, since the reader cannot tell them apart
@pytest.mark.parametrize("error,code", [(TimeoutError("timed out"), "network.timeout"), (OSError("connection refused"), "network.unavailable")])
def test_a_connectivity_failure_names_what_to_check(lm_module, error, code):
    advice = lm_module.classify_recovery_error(error, context="connectivity")

    assert advice.code == code
    assert advice.fix.startswith("Check network, DNS, proxy and CHECK_INTERNET_URL settings")
    assert advice.retryable is True


# Verifies an HTTP status on the error is read directly, so a client that carries one is classified by it
def test_the_http_status_is_read_from_the_error(lm_module):
    class Rejected(Exception):
        status = 403

    assert lm_module.classify_recovery_error(Rejected("nothing quotable")).code == "auth.api_key_invalid"
    assert lm_module.recovery_http_status(Rejected()) == 403
    assert lm_module.recovery_http_status(RuntimeError("no status here")) is None


# Verifies each positional failure reaches its own code, since the two are fixed in different places
def test_each_positional_failure_has_its_own_code(lm_module):
    assert lm_module.classify_recovery_error(context="target.missing").code == "target.missing"
    assert lm_module.classify_recovery_error(context="target.region").code == "target.region"
    assert lm_module.classify_recovery_error(RuntimeError("name and tagline"), context="target").code == "target.invalid"


# Verifies a fix carries its guide on its own line, which is what lets a reader open the page that covers the row
def test_a_fix_carries_its_guide_link(lm_module):
    advice = lm_module.classify_recovery_error(context="target.region")

    assert advice.fix.endswith(f"\nGuide: {lm_module.REGION_GUIDE_URL}")
    assert advice.fix.count("Guide:") == 1


# Verifies advice survives an exception boundary unchanged, so a caller cannot reclassify a decided failure
def test_advice_survives_an_exception_boundary(lm_module):
    advice = lm_module.make_recovery_advice("riot.unavailable", "Riot is down", "Wait", True)

    raised = lm_module.RecoveryError(advice, cause=RuntimeError("original"))

    assert lm_module.classify_recovery_error(raised) is advice
    assert isinstance(raised.__cause__, RuntimeError)


# Verifies the technical detail stays hidden by default, since it is noise for everyone who is not debugging
def test_the_rendered_block_hides_technical_detail_by_default(lm_module):
    rendered = lm_module.render_recovery_error(RuntimeError("connection refused by 10.0.0.1"))

    assert rendered.startswith("* Error: ")
    assert "To fix: " in rendered
    assert "Technical detail" not in rendered


# Verifies the technical detail is available when asked for, so a failing request can still be identified
def test_the_technical_detail_is_shown_when_requested(lm_module):
    rendered = lm_module.render_recovery_error(RuntimeError("connection refused by 10.0.0.1"), debug=True)

    assert "Technical detail: connection refused by 10.0.0.1" in rendered


# Verifies a detail that only repeats the summary is dropped, so no block says the same thing twice
def test_a_detail_that_repeats_the_summary_is_dropped(lm_module):
    rendered = lm_module.render_recovery_error(context="file", debug=True, detail="The log file could not be opened")

    assert rendered.count("The log file could not be opened") == 1


# Verifies a configured secret never reaches the advice, since these blocks are pasted into public bug reports
def test_a_secret_never_reaches_the_advice(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "RGAPI-inadvice-0000-0000-0000-000000000000")

    advice = lm_module.classify_recovery_error(RuntimeError(f"401 for key {lm_module.RIOT_API_KEY}"))

    assert lm_module.RIOT_API_KEY not in advice.detail
    assert "<redacted>" in advice.detail


# Verifies advice built at a call site is redacted by the constructor, since not every producer goes through the classifier
def test_the_constructor_redacts_advice_built_directly(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "RGAPI-fullsize-0000-0000-0000-000000000000")

    advice = lm_module.make_recovery_advice("config.invalid", f"Config holds {lm_module.RIOT_API_KEY}", f"Remove {lm_module.RIOT_API_KEY} from the file", False, f"seen at {lm_module.RIOT_API_KEY}")

    assert lm_module.RIOT_API_KEY not in advice.summary + advice.fix + advice.detail
    assert advice.summary.endswith("<redacted>")
    assert "<redacted>" in advice.fix and "<redacted>" in advice.detail


# Verifies the header pulsefire sends the key in is redacted whatever the value looks like
def test_the_riot_credential_header_is_redacted(lm_module):
    sanitized = lm_module.sanitize_error_text("headers={'X-Riot-Token': 'a-key-of-no-particular-shape'}")

    assert "a-key-of-no-particular-shape" not in sanitized
    assert "<redacted>" in sanitized


# Verifies a Riot key is redacted by its own shape, so one in a traceback is covered without the header around it
def test_a_riot_key_is_redacted_by_its_shape(lm_module):
    sanitized = lm_module.sanitize_error_text("401 for RGAPI-9999zzzz-8888-7777-6666-555544443333 at the account endpoint")

    assert "RGAPI-9999zzzz" not in sanitized
    assert sanitized.startswith("401 for <redacted> at")


# Verifies a short value configured as a secret leaves ordinary output alone, since it is also an ordinary word
def test_a_short_secret_does_not_redact_ordinary_words(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "Ashe")

    assert lm_module.sanitize_error_text("Champion: Ashe won the match") == "Champion: Ashe won the match"
    assert lm_module.sanitize_error_text("SMTP_PASSWORD = Ashe") == "SMTP_PASSWORD = <redacted>"


# Verifies a full-length secret is still replaced wherever it appears, which is what the floor must not weaken
def test_a_full_length_secret_is_replaced_anywhere(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "correct-horse-battery-staple")

    assert lm_module.sanitize_error_text("login failed for correct-horse-battery-staple") == "login failed for <redacted>"


# Verifies a name Riot supplies cannot repaint the terminal it is printed to
@pytest.mark.parametrize("hostile, expected", [
    ("\x1b[31mRed\x1b[0m", "Red"),
    ("\x1b[2J\x1b[HCleared", "Cleared"),
    ("Line\nBreak", "LineBreak"),
    ("Bell\x07Rings", "BellRings"),
    ("  padded  ", "padded"),
])
def test_untrusted_text_is_stripped_of_control_sequences(lm_module, hostile, expected):
    assert lm_module.sanitize_untrusted_text(hostile) == expected


# Verifies a long name is cut with a visible marker rather than filling the line it appears on
def test_untrusted_text_is_truncated_with_a_marker(lm_module):
    sanitized = lm_module.sanitize_untrusted_text("A" * 300, max_length=64)

    assert sanitized == "A" * 64 + "..."


# Verifies an absent value becomes empty text rather than the word None reaching a match report
def test_untrusted_text_handles_an_absent_value(lm_module):
    assert lm_module.sanitize_untrusted_text(None) == ""


# Verifies a participant name is sanitized where it is read, so every report and roster gets the clean one
@pytest.mark.parametrize("field", ["riotIdGameName", "summonerName"])
def test_a_participant_name_is_sanitized_at_the_boundary(lm_module, field):
    assert lm_module.get_participant_display_name({field: "\x1b[31mFaker\x1b[0m"}) == "Faker"


# Verifies a participant with nothing usable still reads as unknown rather than as an empty column
def test_a_participant_without_a_name_reads_as_unknown(lm_module):
    assert lm_module.get_participant_display_name({"riotIdGameName": "\x1b[0m"}) == "unknown"


# Verifies a game type Riot does not map is sanitized before the fallback formats it, since the escape corrupts both
def test_an_unmapped_game_type_is_sanitized(lm_module):
    assert lm_module.humanize_game_type("\x1b[31mFUTURE_MODE") == "Future Mode"
    assert lm_module.humanize_game_type("\x1b[31mCUSTOM_GAME") == "Custom"


# Verifies a fixed-length credential reports its length, which is how a truncated paste is spotted
def test_a_fixed_length_secret_reports_its_length(lm_module):
    assert lm_module.secret_fingerprint("RGAPI-fullsize-0000-0000-0000-000000000000", "RIOT_API_KEY") == "set, 42 chars"


# Verifies a value the user chose reports presence only, since its length is a real disclosure
def test_a_chosen_secret_reports_presence_only(lm_module):
    assert lm_module.secret_fingerprint("hunter2-and-then-some", "SMTP_PASSWORD") == "set"


# Verifies one predicate decides whether any setting holds a real value, so a placeholder never reads as configured
@pytest.mark.parametrize("value,expected", [
    ("RGAPI-fullsize-0000-0000-0000-000000000000", True),
    ("smtp.example.test", True),
    ("your_riot_api_key", False),
    ("  your_smtp_server_ssl", False),
    ("", False),
    ("   ", False),
    (None, False),
    (0, False),
    (True, False),
])
def test_a_placeholder_is_not_a_value(lm_module, value, expected):
    assert lm_module.doctor_value_is_set(value) is expected


# Verifies an absent or placeholder secret is named as absent rather than reading as a value that is present
@pytest.mark.parametrize("value", [None, "", "   ", "your_riot_api_key"])
def test_an_absent_secret_is_reported_as_not_set(lm_module, value):
    assert lm_module.secret_fingerprint(value, "RIOT_API_KEY") == "not set"


# Verifies no fingerprint discloses any part of the value, since these lines reach public bug reports
def test_a_fingerprint_discloses_no_part_of_the_value(lm_module):
    secret = "RGAPI-fullsize-0000-0000-0000-000000000000"

    fingerprint = lm_module.secret_fingerprint(secret, "RIOT_API_KEY")

    for length in range(2, len(secret) + 1):
        assert secret[:length] not in fingerprint
        assert secret[-length:] not in fingerprint


# Verifies the same category twice renders its hint once, so a lasting outage does not repeat the advice every cycle
def test_a_repeated_failure_renders_one_hint(lm_module):
    tracker = lm_module.RecoveryHintTracker()
    advice = lm_module.classify_recovery_error(RuntimeError("429 rate limit exceeded"))

    assert tracker.should_render(advice) is True
    assert tracker.should_render(advice) is False


# Verifies a changed category renders again, since the new failure is not the one already explained
def test_a_changed_failure_category_renders_again(lm_module):
    tracker = lm_module.RecoveryHintTracker()

    assert tracker.should_render(lm_module.classify_recovery_error(RuntimeError("429 rate limit exceeded"))) is True
    assert tracker.should_render(lm_module.classify_recovery_error(RuntimeError("401 Unauthorized"))) is True


# Verifies a successful cycle clears the suppression, so a recurrence is explained rather than whispered
def test_a_successful_cycle_clears_suppression(lm_module):
    tracker = lm_module.RecoveryHintTracker()
    advice = lm_module.classify_recovery_error(RuntimeError("429 rate limit exceeded"))
    tracker.should_render(advice)

    tracker.reset()

    assert tracker.should_render(advice) is True


# Verifies every action line keeps the shared shape: the renderer owns the prefix, one capitalised instruction, no trailing period
def test_every_action_line_keeps_the_shared_shape(lm_module):
    # Renders one argument as text, standing in {} for the parts an f-string fills at runtime
    def literal_text(node):
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, str) else None
        if isinstance(node, ast.JoinedStr):
            return "".join(str(part.value) if isinstance(part, ast.Constant) else "{}" for part in node.values)
        return None

    offenders = []
    checked = 0
    for node in ast.walk(ast.parse(inspect.getsource(lm_module))):
        if not isinstance(node, ast.Call) or ast.unparse(node.func) not in {"make_recovery_advice", "advice"} or len(node.args) < 3:
            continue
        fix = literal_text(node.args[2])
        if fix is None:
            continue
        checked += 1
        if fix.startswith("To fix"):
            offenders.append(f"{node.lineno}: the action repeats the prefix the renderer adds")
        if fix[:1].islower():
            offenders.append(f"{node.lineno}: the action does not start with a capital")
        if fix.rstrip().endswith("."):
            offenders.append(f"{node.lineno}: the action ends with a full stop")
        if "Guide:" in fix:
            offenders.append(f"{node.lineno}: the action embeds its guide instead of passing one")

    assert checked, "no recovery advice is built with a literal action"
    assert not offenders, "action lines outside the shared shape:\n" + "\n".join(offenders)


# Verifies the documentation links point at the published site, so a fix line cannot send a reader to a dead host
def test_every_guide_link_points_at_the_documentation_site(lm_module):
    guides = {name: value for name, value in vars(lm_module).items() if name.endswith("_GUIDE_URL")}

    assert guides, "the module declares no guide links"
    for name, url in guides.items():
        assert url.startswith(f"{lm_module.DOCS_BASE_URL}/"), f"{name} does not point at the documentation site"


# Verifies every context the tool passes to the classifier is one this file exercises, so a new branch cannot go untested
def test_every_context_the_tool_uses_is_covered(lm_module):
    used = set()
    for node in ast.walk(ast.parse(inspect.getsource(lm_module))):
        if not isinstance(node, ast.Call) or getattr(node.func, "id", "") not in ("classify_recovery_error", "print_recovery_error", "render_recovery_error"):
            continue
        for keyword in node.keywords:
            if keyword.arg == "context" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                used.add(keyword.value.value)
        if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
            used.add(node.args[1].value)

    assert used <= set(CONTEXTS), f"contexts this file never exercises: {sorted(used - set(CONTEXTS))}"
