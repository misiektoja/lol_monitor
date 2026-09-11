"""Tests for the --verbose and --debug printers, the trace grammar and what each mode is allowed to print."""

import ast
import asyncio
import inspect
import re

import pytest

import test_monitoring_loop as loop


RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"

# The closed vocabulary every outbound trace line reports its result with
OUTCOMES = ("OK", "failed", "degraded", "skipped")

# The lines that bracket a check rather than perform an operation. A wait has no result to report, so requiring
# one would mean inventing an outcome for time passing
CHECK_BRACKETS = ("Starting check", "Next check", "Retry wait")


# Verifies a diagnostic line renders as an operation followed by named fields, which is what makes a trace scannable
def test_a_diagnostic_line_is_an_operation_and_named_fields(lm_module):
    assert lm_module.format_diagnostic_line("Riot account lookup", {"region": "eun1", "outcome": "OK"}) == "Riot account lookup: region=eun1, outcome=OK"


# Verifies a field with nothing in it is dropped, so a call site can pass an optional field without branching
def test_an_unset_field_is_dropped(lm_module):
    assert lm_module.format_diagnostic_line("Check", {"region": "eun1", "error": None}) == "Check: region=eun1"


# Verifies an operation with no fields renders alone rather than trailing an empty colon
def test_an_operation_without_fields_renders_alone(lm_module):
    assert lm_module.format_diagnostic_line("Check", {}) == "Check"


# Verifies debug output stays off until it is asked for, since a default run is not a trace
def test_debug_output_is_silent_by_default(lm_module, capsys):
    lm_module.debug_print("Check", region=REGION)

    assert capsys.readouterr().out == ""


# Verifies a debug line carries the shared timestamped prefix every sibling greps for
def test_a_debug_line_carries_the_shared_prefix(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)

    lm_module.debug_print("Riot account lookup", region=REGION, outcome="OK")

    assert re.fullmatch(r"\[DEBUG \d\d:\d\d:\d\d\] Riot account lookup: region=eun1, outcome=OK\n", capsys.readouterr().out)


# Verifies a secret interpolated by a call site is redacted inside the printer rather than at each site
def test_a_secret_in_a_debug_field_is_redacted(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "RGAPI-intraces-0000-0000-0000-000000000000")

    lm_module.debug_print("Careless call site", key=lm_module.RIOT_API_KEY)

    assert lm_module.RIOT_API_KEY not in capsys.readouterr().out


# Verifies verbose output stays off until it is asked for
def test_verbose_output_is_silent_by_default(lm_module, capsys):
    lm_module.verbose_print("Something happened")

    assert capsys.readouterr().out == ""


# Verifies a verbose line reads as part of the run rather than as instrumentation
def test_a_verbose_line_matches_ordinary_output(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "VERBOSE_MODE", True)

    lm_module.verbose_print("Email delivered to alerts@example.test")

    assert capsys.readouterr().out == "* Email delivered to alerts@example.test\n"


# Verifies the terminal width a run measured is reported with the shared wording rather than a bare number
def test_the_measured_terminal_width_is_reported(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(lm_module.shutil, "get_terminal_size", lambda: FakeTerminalSize(132))

    assert lm_module.resolve_truncate_chars(None, lm_module.TERMINAL_WIDTH_SENTINEL, False) == 132
    assert "* The detected terminal screen width is: 132 characters" in capsys.readouterr().out


# Verifies a debug run says why it kept the screen it was started from, rather than looking like a broken setting
def test_debug_mode_says_why_the_screen_was_not_cleared(lm_module, monkeypatch, capsys):
    from test_cli_startup import run_main

    monkeypatch.setattr(lm_module, "CLEAR_SCREEN", True)
    monkeypatch.setattr(lm_module, "clear_screen", lambda _enabled: None)

    run_main(lm_module, monkeypatch, ["--debug", RIOT_ID, REGION])

    assert "Terminal screen clear skipped because debug mode is active" in capsys.readouterr().out


# Verifies a secret interpolated into a verbose line is redacted the same way a debug line is
def test_a_secret_in_a_verbose_line_is_redacted(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "a-long-enough-password")

    lm_module.verbose_print(f"Signed in with {lm_module.SMTP_PASSWORD}")

    assert "a-long-enough-password" not in capsys.readouterr().out


# Verifies the two modes stay independent, so asking for one does not deliver the other's noise
@pytest.mark.parametrize("mode,other", [("VERBOSE_MODE", "DEBUG_MODE"), ("DEBUG_MODE", "VERBOSE_MODE")])
def test_the_two_modes_are_independent(lm_module, monkeypatch, capsys, mode, other):
    monkeypatch.setattr(lm_module, mode, True)
    monkeypatch.setattr(lm_module, other, False)

    lm_module.verbose_print("verbose line")
    lm_module.debug_print("Debug line")

    output = capsys.readouterr().out
    assert ("verbose line" in output) is (mode == "VERBOSE_MODE")
    assert ("Debug line" in output) is (mode == "DEBUG_MODE")


# Verifies a swallowed exception still reaches a trace, so a silently degraded feature can be diagnosed
def test_a_swallowed_exception_is_traced(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)

    lm_module.debug_swallowed_exception("Champion mastery", ValueError("no data"))

    assert "Champion mastery: outcome=failed, error=ValueError: no data" in capsys.readouterr().out


# Verifies an explicit flag beats the configuration file, which is the point of applying it in two phases
def test_an_explicit_flag_beats_the_configuration_file(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "VERBOSE_MODE", False)
    monkeypatch.setattr(lm_module, "DEBUG_MODE", False)

    lm_module.apply_diagnostic_cli_flags(argparse_double(verbose=True, debug=True))

    assert (lm_module.VERBOSE_MODE, lm_module.DEBUG_MODE) == (True, True)


# Verifies an unset flag leaves whatever the configuration file chose, so the flag only ever turns a mode on
def test_an_unset_flag_leaves_the_configured_value(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(lm_module, "DEBUG_MODE", False)

    lm_module.apply_diagnostic_cli_flags(argparse_double(verbose=None, debug=None))

    assert (lm_module.VERBOSE_MODE, lm_module.DEBUG_MODE) == (True, False)


# Returns a stand-in for the parsed arguments carrying only the two diagnostic flags
def argparse_double(**flags):
    return type("Args", (), flags)()


# Verifies the technical detail line follows the run's own debug mode rather than a decision made at each call site
def test_the_technical_detail_line_follows_debug_mode(lm_module, monkeypatch):
    quiet = lm_module.render_recovery_error(RuntimeError("gaierror: name resolution failed"), context="connectivity")
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    loud = lm_module.render_recovery_error(RuntimeError("gaierror: name resolution failed"), context="connectivity")

    assert "The connectivity endpoint could not be reached" in quiet
    assert "Technical detail:" not in quiet
    assert "Technical detail: gaierror: name resolution failed" in loud


# Verifies a run reports what it read the configuration and each secret from, which is the first thing a broken setup needs
def test_a_debug_run_reports_configuration_and_secret_resolution(lm_module, monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RIOT_API_KEY", "RGAPI-intraces-0000-0000-0000-000000000000")
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)

    lm_module.load_secrets_from_environment({})

    output = capsys.readouterr().out
    assert "Secret resolved: name=RIOT_API_KEY, source=environment" in output
    assert "RGAPI-intraces-0000-0000-0000-000000000000" not in output


# Verifies the outbound calls a run makes are traced, since a trace with no request in it explains nothing
def test_a_debug_run_traces_the_connectivity_request(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    monkeypatch.setattr(lm_module.req, "get", lambda url, timeout=None, verify=True: None)

    assert lm_module.check_internet() is True

    output = capsys.readouterr().out
    assert "Connectivity check: url=" in output
    assert "outcome=OK" in output


# Verifies a failed outbound call reports the exception type, which is what tells one network failure from another
def test_a_failed_outbound_call_reports_its_exception(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)

    def refuse(url, timeout=None, verify=True):
        raise lm_module.req.ConnectionError("name resolution failed")

    monkeypatch.setattr(lm_module.req, "get", refuse)

    assert lm_module.check_internet(quiet=True) is False

    assert "outcome=failed, error=ConnectionError: name resolution failed" in capsys.readouterr().out


# Returns every debug_print call in the module paired with the line it sits on
def debug_print_calls(lm_module):
    tree = ast.parse(inspect.getsource(lm_module))
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "debug_print"]


# Renders one literal or f-string argument, using a marker for the parts only known at runtime
def render_literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else "{}" for value in node.values)
    return None


# Verifies every trace operation is a label rather than a sentence with values interpolated into it
def test_every_trace_operation_is_a_label(lm_module):
    checked = 0
    for call in debug_print_calls(lm_module):
        assert call.args, f"line {call.lineno}: debug_print was called with no operation"
        operation = render_literal(call.args[0])
        if operation is None:
            continue
        checked += 1
        assert "=" not in operation, f"line {call.lineno}: the operation carries a field: {operation}"
        assert not operation.endswith(":"), f"line {call.lineno}: the operation ends in a colon: {operation}"
        assert not operation.rstrip().endswith((" for", " with", " to", " from", " in", " of")), f"line {call.lineno}: the operation ends in a preposition: {operation}"
        assert operation[:1].isupper(), f"line {call.lineno}: the operation is not capitalised: {operation}"

    assert checked > 25, f"the sweep only rendered {checked} operations"


# Verifies outcome= only ever carries one of the four shared tokens, which is what keeps grepping a trace worthwhile
def test_the_outcome_vocabulary_is_closed(lm_module):
    checked = 0
    for call in debug_print_calls(lm_module):
        for keyword in call.keywords:
            if keyword.arg != "outcome":
                continue
            for value in ast_string_values(keyword.value):
                checked += 1
                assert value in OUTCOMES, f"line {call.lineno}: outcome={value} is outside {OUTCOMES}"

    assert checked > 10, f"the sweep only rendered {checked} outcomes"


# Returns every literal string one expression can evaluate to, following both arms of a conditional
def ast_string_values(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return ast_string_values(node.body) + ast_string_values(node.orelse)
    return []


# Verifies an operation does not repeat what a field already says, which states one thing twice
def test_no_trace_operation_repeats_its_own_outcome(lm_module):
    for call in debug_print_calls(lm_module):
        operation = render_literal(call.args[0]) if call.args else None
        if operation is None:
            continue
        assert not any(token in operation.casefold() for token in ("failed", "succeeded", "outcome")), f"line {call.lineno}: the operation states its own result: {operation}"


# Verifies the printer sanitizes a built local rather than an inlined expression, which a leak test matches on
def test_the_debug_printer_sanitizes_one_local(lm_module):
    source = inspect.getsource(lm_module.debug_print)

    assert "message = format_diagnostic_line(" in source
    assert "sanitize_error_text(message)" in source


# Verifies every outbound helper reports how its call went, since a line with no result leaves the reader waiting
@pytest.mark.parametrize("operation", ["Riot account lookup", "Summoner details", "Ranked information", "Champion mastery", "In-game check", "Live match details", "Live match snapshot", "Match ID fetch", "Total match count", "Match details", "Data Dragon champion data", "Email delivery", "Connectivity check", "Riot API key check", "Monitored account check", "SMTP sign-in check"])
def test_every_outbound_operation_reports_an_outcome(lm_module, operation):
    outcomes = [keyword for call in debug_print_calls(lm_module) if render_literal(call.args[0] if call.args else None) == operation for keyword in call.keywords if keyword.arg == "outcome"]

    assert outcomes, f"'{operation}' is traced without ever reporting an outcome"


# Verifies a real monitoring run leaves no operation in the trace whose result the reader has to guess
def test_a_traced_run_reports_the_result_of_every_operation(lm_module, riot_api, fake_clock, monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    loop.script_profile(riot_api, ranked_entries=[{"queueType": "RANKED_SOLO_5x5", "tier": "GOLD", "rank": "II", "leaguePoints": 44, "wins": 30, "losses": 25}], masteries=[{"championId": 103, "championLevel": 7, "championPoints": 123456}])
    loop.run_loop(lm_module, riot_api, cycles=[{"match_ids": ["EUN1_1"]}, {"match_ids": ["EUN1_1"], "live": loop.live_match_payload()}], initial_match_ids=["EUN1_0"])

    traced = {}
    for line in capsys.readouterr().out.splitlines():
        match = re.fullmatch(r"\[DEBUG \d\d:\d\d:\d\d\] ([^:]+)(?:: (.*))?", line)
        if match:
            traced.setdefault(match.group(1), []).append(match.group(2) or "")

    assert len(traced) > 5, f"the run only traced {sorted(traced)}"
    silent = sorted(operation for operation, lines in traced.items() if operation not in CHECK_BRACKETS and not any("outcome=" in fields for fields in lines))
    assert silent == [], f"operations traced without ever reporting a result: {', '.join(silent)}"


# Verifies a quiet monitoring cycle prints nothing in verbose, since a line per check buries the ones worth reading
def test_a_quiet_cycle_prints_nothing_in_verbose(lm_module):
    tree = ast.parse(inspect.getsource(lm_module))
    loop = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == "lol_monitor_user")
    periodic = [node.lineno for node in ast.walk(loop) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("verbose_print", "verbose_notice")]

    assert periodic == [], f"the monitoring loop prints verbose lines at {periodic}"


# Verifies a completed cycle is traced in debug with the wait before the next one, which is where a line per check belongs
def test_a_completed_cycle_is_traced_in_debug(lm_module):
    traced = {render_literal(call.args[0] if call.args else None): {keyword.arg for keyword in call.keywords} for call in debug_print_calls(lm_module)}
    waits = {operation: names for operation, names in traced.items() if operation in ("Next check", "Retry wait")}

    assert "outcome" in traced.get("Completed check", set()), "no completed cycle reports its result"
    assert set(waits) == {"Next check", "Retry wait"}, f"a wait is never traced: {sorted({'Next check', 'Retry wait'} - set(waits))}"
    assert all({"due_in", "reason"} <= names for names in waits.values()), "a wait is traced without saying how long it is and why"


# Verifies the answer Riot gives for a player who is not in a game is traced as a successful check
def test_the_ordinary_not_in_game_answer_is_traced_as_success(lm_module, monkeypatch, riot_api, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", not_found_error())

    assert asyncio.run(lm_module.is_user_in_match("puuid", REGION)) is False

    assert "In-game check: region=eun1, outcome=OK, in_game=False" in capsys.readouterr().out


# Verifies any other failure is traced as degraded, since the run treats it as not in game without having checked
def test_a_failed_in_game_check_is_traced_as_degraded(lm_module, monkeypatch, riot_api, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    riot_api.script("get_lol_spectator_v5_active_game_by_summoner", TimeoutError("the request timed out"))

    assert asyncio.run(lm_module.is_user_in_match("puuid", REGION)) is False

    assert "outcome=degraded, in_game=False, error=TimeoutError: the request timed out" in capsys.readouterr().out


class NotFoundError(Exception):
    """An error shaped like the 404 Riot answers with for a player who is not in a game."""

    status = 404


# Returns the 404 Riot answers with for a player who is not in a game
def not_found_error():
    return NotFoundError("404 Not Found")


class FakeTerminalSize:
    """A terminal size with only the column count the width probe reads."""

    def __init__(self, columns):
        self.columns = columns
        self.lines = 24
