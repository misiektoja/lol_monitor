"""Tests for the closed recovery taxonomy, the advice each failure carries and the shared error block."""

import ast
import inspect
import re

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
        for error in (RuntimeError("rate limit exceeded"), RuntimeError("request timed out"), RuntimeError("connection refused"), RuntimeError("401 Unauthorized"), RuntimeError("404 not found"), RuntimeError("500 Internal Server Error"), RuntimeError("authentication failed"), RuntimeError("the settings are incorrect"), RuntimeError("name and tagline"), RuntimeError("does not exist"), RuntimeError("Could not read dotenv destination '.env'. Check that it is a readable UTF-8 file."), OSError(24, "Too many open files"), RuntimeError("something surprising")):
            produced.add(lm_module.classify_recovery_error(error, context=context).code)
    # A doctor row builds its own advice rather than going through the classifier, so those call sites count too
    for node in ast.walk(ast.parse(inspect.getsource(lm_module))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "make_recovery_advice" and node.args:
            code = node.args[0]
            if isinstance(code, ast.Constant) and isinstance(code.value, str):
                produced.add(code.value)

    assert produced == set(lm_module.RECOVERY_CODES), f"codes with no producer: {sorted(set(lm_module.RECOVERY_CODES) - produced)}"


# Verifies the refusal to replace an existing file names the placeholder the siblings use and its guide section
def test_the_existing_file_refusal_reads_the_way_the_siblings_report_it(lm_module):
    advice = lm_module.classify_recovery_error(context="file.exists")

    assert advice.code == "file.exists"
    assert "--generate-config <new-file>" in advice.fix
    assert f"Guide: {lm_module.CONFIG_GUIDE_URL}" in advice.fix


# Verifies a rate limited webhook is reported as itself, since waiting it out is not the fix for an unreachable host
def test_a_rate_limited_webhook_is_not_reported_as_unreachable(lm_module):
    class Throttled(RuntimeError):
        status = 429

    advice = lm_module.classify_recovery_error(Throttled("Too Many Requests"), context="webhook")

    assert advice.code == "webhook.rate_limited"
    assert advice.retryable is True
    assert "rate limiting deliveries" in advice.summary


# Verifies a delivery the service answered and refused is separated from one it could not parse
def test_a_refused_delivery_is_not_reported_as_a_bad_configuration(lm_module):
    refused = lm_module.classify_recovery_error(RuntimeError("the webhook no longer exists"), context="webhook")
    malformed = lm_module.classify_recovery_error(RuntimeError("the payload must contain content"), context="webhook")

    assert refused.code == "webhook.rejected"
    assert malformed.code == "webhook.invalid"


# Verifies a file that could not be read is separated from one that could not be written, since the fixes differ
def test_a_read_failure_is_never_reported_as_unwritable(lm_module):
    unreadable = lm_module.classify_recovery_error(context="file", detail="Could not read dotenv destination '.env'. Check that it is a readable UTF-8 file.")
    unwritable = lm_module.classify_recovery_error(context="file", detail="Could not write secrets to '.env'")

    assert unreadable.code == "file.unreadable"
    assert "readable UTF-8 text" in unreadable.fix
    assert f"Guide: {lm_module.SECRETS_GUIDE_URL}" in unreadable.fix
    assert unwritable.code == "file.unwritable"


# Verifies no delivery path prints at all, since a print there is an error line that skipped the recovery block
def test_no_delivery_path_prints_outside_the_recovery_block(lm_module):
    delivery = {"send_email", "send_webhook", "print_webhook_error", "smtp_connect_and_login", "post_webhook_request"}
    offenders = []
    for node in ast.walk(ast.parse(inspect.getsource(lm_module))):
        if not isinstance(node, ast.FunctionDef) or node.name not in delivery:
            continue
        offenders.extend(f"{node.name}:{call.lineno}" for call in ast.walk(node) if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "print")

    assert not offenders, "delivery paths printing outside the recovery block: " + ", ".join(offenders)


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
    assert lm_module.secret_fields("RGAPI-fullsize-0000-0000-0000-000000000000", "RIOT_API_KEY") == {"value": "set", "chars": 42}


# Verifies a value the user chose reports presence only, since its length is a real disclosure
def test_a_chosen_secret_reports_presence_only(lm_module):
    assert lm_module.secret_fields("hunter2-and-then-some", "SMTP_PASSWORD") == {"value": "set", "chars": None}


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


# Verifies the fix is rendered whenever this printer runs, since its caller only reaches it on a new failure
# category and the throttling of a lasting outage is the outage reporter's job rather than a second guard's
def test_the_printed_failure_carries_its_fix(lm_module, capsys):
    lm_module.print_recovery_error(RuntimeError("429 rate limit exceeded"), "runtime", retry_note="retrying in 5 seconds")

    printed = capsys.readouterr().out
    assert printed.startswith("* Error: Riot is rate limiting requests (retrying in 5 seconds)\n")
    assert "To fix: " in printed


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


# Verifies a failed CSV write reports through the recovery block, since the monitoring loop carries on past it
def test_no_csv_write_failure_prints_its_own_line(lm_module):
    csv_writers = {"init_csv_file", "write_csv_entry"}
    offenders = []
    guarded = 0
    for node in ast.walk(ast.parse(inspect.getsource(lm_module))):
        if not isinstance(node, ast.Try) or (node.body[-1].end_lineno or node.body[0].lineno) - node.body[0].lineno > 6:
            continue
        if not any(isinstance(inner, ast.Call) and getattr(inner.func, "id", "") in csv_writers for statement in node.body for inner in ast.walk(statement)):
            continue
        guarded += 1
        offenders.extend(f"line {statement.lineno}" for handler in node.handlers for statement in handler.body if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and getattr(statement.value.func, "id", "") == "print")

    assert guarded >= 3, f"only {guarded} CSV writes are guarded, so this no longer covers them"
    assert not offenders, "CSV write failures reported outside the recovery block:\n" + "\n".join(offenders)


# Verifies added context does not replace the error text the rules read, which used to make every such failure unknown
@pytest.mark.parametrize("message, expected", [("429 rate limit exceeded", "riot.rate_limited"), ("404 not found", "target.not_found")])
def test_a_caller_supplied_detail_does_not_hide_the_error(lm_module, message, expected):
    advice = lm_module.classify_recovery_error(Exception(message), detail="Cannot fetch the latest match IDs")

    assert advice.code == expected
    assert "Cannot fetch the latest match IDs" in advice.detail


# Every place that reports a problem without the classifier and the reason it cannot use one
CLASSIFIER_EXEMPTIONS = {
    "or higher required": "runs at import on an interpreter too old to load the rest of the file",
    "Couldn't find the Pulsefire library": "raised at import, while a dependency the classifier itself needs is missing",
    "Cannot clear the screen contents": "a cosmetic notice with nothing for the operator to recover from",
    "Setup needs a writable dotenv file": "an answer hint inside the question that re-asks, where the next prompt is the recovery",
    "Monitoring failure changed for": "a one-line note on a classified outage that already had its full report",
}

# Words that mark a printed line as a report of something going wrong
TROUBLE_WORDS = re.compile(r"error|cannot|can't|failed|failure|invalid|not valid|missing|not installed|no such|refused|unsupported|needs to be|could not|couldn't|unable to", re.IGNORECASE)


# Returns the literal text one print argument shows, leaving out the parts an f-string fills at runtime
def printed_text(node):
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else ""
    if isinstance(node, ast.JoinedStr):
        return "".join(printed_text(part) for part in node.values)
    if isinstance(node, ast.BinOp):
        return printed_text(node.left) + printed_text(node.right)
    return ""


# Returns every printed line that reads as a problem, paired with the line it sits on
def reported_problems(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}):
            continue
        text = " ".join(printed_text(argument) for argument in node.args)
        if TROUBLE_WORDS.search(text):
            found.append((node.lineno, " ".join(text.split())))
    return found


# Verifies a local file descriptor limit is reported as itself rather than as a failure of the call that hit it
def test_a_file_descriptor_limit_is_not_reported_as_a_service_failure(lm_module):
    try:
        try:
            raise OSError(24, "Too many open files")
        except OSError as inner:
            raise RuntimeError("the Riot request failed") from inner
    except RuntimeError as error:
        advice = lm_module.classify_recovery_error(error)

    assert advice.code == "resource.exhausted"
    assert advice.retryable is False
    assert "not a Riot problem" in advice.summary
    assert "ulimit -n 4096" in advice.fix


# Verifies the descriptor limit is matched as a whole errno, so errno 240 or 241 in a message is not mistaken for it
def test_a_neighbouring_errno_is_not_a_file_descriptor_limit(lm_module):
    assert lm_module.is_too_many_open_files(RuntimeError("[Errno 24] Too many open files")) is True
    assert lm_module.is_too_many_open_files(RuntimeError("[Errno 240] something else")) is False
    assert lm_module.is_too_many_open_files(RuntimeError("[Errno 241] something else")) is False


# Verifies a category change mid-outage keeps the outage start, so the alert delay and the reminder still elapse
def test_an_outage_that_changes_category_keeps_its_start(lm_module, monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(lm_module.time, "time", lambda: clock[0])
    reporter = lm_module.OutageReporter()
    first = lm_module.classify_recovery_error(RuntimeError("500 Internal Server Error"), context="runtime")
    second = lm_module.classify_recovery_error(OSError(24, "Too many open files"), context="runtime")
    assert first.code != second.code

    assert reporter.failed(first) == "full"
    for index in range(60):
        clock[0] += 15
        reporter.failed(second if index % 2 else first)

    assert reporter.since == 1000000
    assert reporter.recovered() == 900


# A problem reported without a category leaves the reader with a message and no next step
def test_every_reported_problem_goes_through_the_classifier(lm_module):
    unexplained = [f"line {line}: {text[:120]}" for line, text in reported_problems(inspect.getsource(lm_module)) if not any(marker in text for marker in CLASSIFIER_EXEMPTIONS)]

    assert unexplained == []


# An exemption list that stopped matching anything would quietly cover the whole file
def test_the_classifier_guard_still_inspects_the_source(lm_module):
    source = inspect.getsource(lm_module)
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}]

    problems = reported_problems(source)

    assert len(inspected) > 100
    assert all(any(marker in text for _, text in problems) for marker in CLASSIFIER_EXEMPTIONS), "an exemption stopped matching a printed line"


# The only advice that names no page, and the reason no page covers it
GUIDELESS_ADVICE = {
    "The connectivity endpoint did not answer in time": "no page covers this check and the doctor report already ends with the troubleshooting link",
    "The connectivity endpoint could not be reached": "no page covers this check and the doctor report already ends with the troubleshooting link",
}

# The guide sits in this positional slot for each builder, or inside the fix when the signature carries no slot
GUIDE_SLOT = {"advice": 4, "make_recovery_advice": 5}


# True when this builder attaches a documentation link in any of the three shapes the tool uses
def attaches_a_guide(node, source):
    slot = GUIDE_SLOT.get(getattr(node.func, "id", ""))
    if slot is not None and len(node.args) > slot:
        return True
    if any(keyword.arg in ("guide_url", "guide") for keyword in node.keywords):
        return True
    return "recovery_fix_with_guide" in (ast.get_source_segment(source, node.args[2]) or "")


# Returns every expression assigned to each plain name in the module, so a fix held in a variable can be read
def assigned_expressions(tree):
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    return assignments


# Returns the text of the summary or fix, resolving one level of plain-name assignment
def resolved_text(node, source, assignments):
    if isinstance(node, ast.Name):
        return " ".join(ast.get_source_segment(source, value) or "" for value in assignments.get(node.id, []))
    return ast.get_source_segment(source, node) or ""


# Returns every advice builder that names no page, paired with the summary it reports
def guideless_advice(source):
    tree = ast.parse(source)
    assignments = assigned_expressions(tree)
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT) or len(node.args) < 3:
            continue
        # A builder that re-wraps an already-classified advice carries whatever guide that advice was given
        if isinstance(node.args[2], ast.Attribute) and node.args[2].attr == "fix":
            continue
        if attaches_a_guide(node, source) or "recovery_fix_with_guide" in resolved_text(node.args[2], source, assignments):
            continue
        found.append((node.lineno, resolved_text(node.args[1], source, assignments)))
    return found


# A failure with no page to read leaves the operator with a one-line fix and nowhere to go next
def test_every_failure_names_a_page(lm_module):
    source = inspect.getsource(lm_module)
    unexplained = [f"line {line}: {summary[:100]}" for line, summary in guideless_advice(source) if not any(marker in summary for marker in GUIDELESS_ADVICE)]

    assert unexplained == []


# An allowlist that stopped matching anything would quietly cover every failure in the file
def test_the_guide_guard_still_inspects_the_source(lm_module):
    source = inspect.getsource(lm_module)
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT]
    bare = guideless_advice(source)

    assert len(inspected) > 40
    assert all(any(marker in summary for _, summary in bare) for marker in GUIDELESS_ADVICE), "an allowlisted summary stopped matching a builder"


# One concept carried three names across this family: a renderer taking a built advice, a renderer taking the
# failure itself, and a third pair named after the monitoring loop. Pinned here so a call copied from a sibling
# cannot quietly mean something else
def test_the_recovery_printers_share_one_contract(lm_module):
    advice_first = ("advice", "debug", "retry_note", "with_fix", "label")
    error_first = ("error", "context", "debug", "detail", "retry_note", "with_fix", "label")

    assert tuple(inspect.signature(lm_module.render_recovery_advice).parameters) == advice_first
    assert tuple(inspect.signature(lm_module.print_recovery_advice).parameters) == advice_first
    assert tuple(inspect.signature(lm_module.render_recovery_error).parameters) == error_first
    assert tuple(inspect.signature(lm_module.print_recovery_error).parameters) == error_first


# The advice pair prints what the caller built, so a summary the classifier would never produce survives the trip
def test_the_advice_printer_does_not_reclassify(lm_module, capsys):
    lm_module.DEBUG_MODE = False
    advice = lm_module.make_recovery_advice("network.timeout", "a summary no rule produces", "a fix of its own", True)

    returned = lm_module.print_recovery_advice(advice)

    assert capsys.readouterr().out == "* Error: a summary no rule produces\nTo fix: a fix of its own\n"
    assert returned is advice


# The error pair classifies what the caller hands it, which is the difference between the two front doors
def test_the_error_printer_classifies_what_it_was_given(lm_module, capsys):
    lm_module.DEBUG_MODE = False

    returned = lm_module.print_recovery_error(RuntimeError("429 rate limit exceeded"), context="runtime")

    assert returned.code != "unknown"
    assert capsys.readouterr().out.startswith(f"* Error: {returned.summary}\n")


# Both front doors reach the same renderer, so the retry note, the label and a suppressed fix behave the same way
def test_both_front_doors_render_the_same_line(lm_module):
    lm_module.DEBUG_MODE = False
    error = RuntimeError("429 rate limit exceeded")
    advice = lm_module.classify_recovery_error(error, "runtime")

    through_advice = lm_module.render_recovery_advice(advice, retry_note="retrying in 5 minutes", with_fix=False, label="Warning")
    through_error = lm_module.render_recovery_error(error, "runtime", retry_note="retrying in 5 minutes", with_fix=False, label="Warning")

    assert through_advice == through_error
    assert through_advice == f"* Warning: {advice.summary} (retrying in 5 minutes)"


# A detail that only repeats the summary spends a line saying nothing, so the block drops it and keeps a real one
def test_a_detail_repeating_the_summary_is_dropped(lm_module):
    repeated = lm_module.make_recovery_advice("unknown", "the same sentence twice", "a fix", False, "the same sentence twice")
    differing = lm_module.make_recovery_advice("unknown", "the summary", "a fix", False, "the raw cause")

    assert "Technical detail:" not in lm_module.render_recovery_advice(repeated, debug=True)
    assert "Technical detail: the raw cause" in lm_module.render_recovery_advice(differing, debug=True)


# A run that already prints the technical cause cannot be told to re-run for it
def test_the_unrecognized_failure_fix_follows_the_diagnostic_mode(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", False)
    plain = lm_module.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    debugging = lm_module.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix

    assert "--debug" in plain
    assert "--debug" not in debugging


# Verifies a channel that could not deliver the error alert is held for five minutes, then for twice the previous wait
def test_a_failed_channel_backs_off_before_it_is_tried_again(lm_module, capsys):
    state = lm_module.ErrorAlertState()
    attempts = []
    for offset in (0, 60, 299, 300, 600, 899, 900, 1200):
        now = 1_700_000_000 + offset
        if state.pending("email", True, now):
            attempts.append(offset)
            state.record("email", True, False, now)
    assert attempts == [0, 300, 900]
    assert state.email_failures == 3
    assert state.email_retry_at == 1_700_000_000 + 900 + 1200
    output = capsys.readouterr().out
    assert "* The email alert is on hold for 5 minutes after 1 attempt, then tried again" in output
    assert "* The email alert is on hold for 10 minutes after 2 attempts, then tried again" in output
    assert "* The email alert is on hold for 20 minutes after 3 attempts, then tried again" in output


# Verifies the wait stops growing at one hour, so a channel that is down for a day is still tried every hour
def test_the_backoff_is_capped(lm_module, capsys):
    state = lm_module.ErrorAlertState()
    for _ in range(6):
        state.record("webhook", True, False, 0)
    assert state.webhook_retry_at == lm_module.ERROR_ALERT_RETRY_MAX_SECONDS
    assert "on hold for 1 hour after 6 attempts" in capsys.readouterr().out


# Verifies a delivery, a reset and an unattempted channel leave no hold behind, while a disabled channel is never pending
def test_a_delivery_or_a_reset_clears_the_hold(lm_module, capsys):
    state = lm_module.ErrorAlertState()
    state.record("email", True, False, 0)
    state.record("webhook", False, False, 0)
    assert state.pending("email", True, 100) is False
    assert state.pending("email", True, 300) is True
    assert state.pending("webhook", True, 0) is True
    assert state.pending("webhook", False, 0) is False
    state.record("email", True, True, 300)
    assert state.email_sent is True
    assert (state.email_failures, state.email_retry_at) == (0, 0)
    assert state.pending("email", True, 300) is False
    state.reset()
    assert state.pending("email", True, 0) is True
    assert "on hold" in capsys.readouterr().out


# Verifies every alert site in the loop asks the state before sending and records the outcome, so no channel is tracked by a loose flag
def test_the_loop_tracks_the_error_alert_through_the_state(lm_module):
    source = inspect.getsource(lm_module)
    assert source.count("error_alert = ErrorAlertState()") == 1
    assert source.count("error_alert.reset()") >= 1
    assert source.count('error_alert.pending("email"') == source.count('error_alert.record("email"') >= 1
    assert source.count('error_alert.pending("webhook"') == source.count('error_alert.record("webhook"') >= 1
    assert not re.search(r"^\s*error_(email|webhook)_sent = ", source, re.MULTILINE)
