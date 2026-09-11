"""Tests for width-aware terminal truncation: what gets cut, what does not and what the log file keeps."""

import sys

import pytest

import lol_monitor as monitor

RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"


@pytest.fixture
# Hides wcwidth from the import inside truncate_string_per_line, the way a machine without it behaves
def without_wcwidth(monkeypatch):
    monkeypatch.setitem(sys.modules, "wcwidth", None)


class FakeStream:
    """A stream stand-in that records what a writer sent to the terminal."""

    def __init__(self, interactive=True):
        self.interactive = interactive
        self.written = []

    def isatty(self):
        return self.interactive

    def write(self, message):
        self.written.append(message)
        return len(message)

    def flush(self):
        return

    @property
    def text(self):
        return "".join(self.written)


# Returns the visible width of text once colour sequences are removed
def visible_width(text):
    from wcwidth import wcswidth

    return wcswidth(monitor.SGR_SEQUENCE_RE.sub("", text))


# Verifies a line longer than the width is cut down to it, which is the whole point of the setting
def test_a_long_line_is_cut_to_the_width():
    assert visible_width(monitor.truncate_string_per_line("plain text that is much too long", 12)) == 12


# Verifies a line that already fits is returned untouched, marker included
def test_a_line_that_fits_is_left_alone():
    assert monitor.truncate_string_per_line("abcdefghij", 10) == "abcdefghij"
    assert monitor.truncate_string_per_line("abcdefghij", 40) == "abcdefghij"


# Verifies a cut line says it was cut, so a shortened value is never mistaken for the whole one
def test_a_cut_line_carries_the_marker():
    assert monitor.truncate_string_per_line("plain text that is much too long", 12).endswith(monitor.TRUNCATION_MARKER)


# Verifies the marker is counted against the width rather than added on top of it
def test_the_marker_fits_inside_the_width():
    assert visible_width(monitor.truncate_string_per_line("plain text that is much too long", 12)) == 12


# Verifies a width too small to hold the marker cuts without one instead of printing nothing but dots
def test_a_width_too_small_for_the_marker_cuts_without_one():
    assert monitor.truncate_string_per_line("abcdefghijk", 3) == "abc"


# Verifies a separator line is cut silently, since a marker there would report a loss that did not happen
@pytest.mark.parametrize("character", ["─", "-", "="])
def test_a_separator_line_is_cut_without_a_marker(character):
    assert monitor.truncate_string_per_line(character * 113, 20) == character * 20


# Verifies the rule that spares separators does not spare an ordinary line that repeats a character
def test_a_line_that_only_starts_like_a_separator_still_gets_the_marker():
    assert monitor.truncate_string_per_line("─" * 40 + " end of section", 20).endswith(monitor.TRUNCATION_MARKER)


# Verifies width is measured by how wide a character prints, not by how many characters there are
def test_a_wide_character_costs_two_columns():
    assert monitor.truncate_string_per_line("한국선", 6) == "한국선"
    assert monitor.truncate_string_per_line("한국선", 5) != "한국선"
    assert monitor.truncate_string_per_line("abc", 3) == "abc"


# Verifies the cut lands on a character boundary, so a wide glyph is never printed as half of itself
@pytest.mark.parametrize("width", range(4, 14))
def test_a_wide_character_never_straddles_the_edge(width):
    assert visible_width(monitor.truncate_string_per_line("ab한국선수이름", width)) <= width


# Verifies a character that prints nothing costs nothing, so a combining accent does not shorten the line
def test_a_zero_width_character_costs_no_width():
    assert monitor.truncate_string_per_line("e\u0301" * 6, 6) == "e\u0301" * 6
    assert monitor.truncate_string_per_line("e\u0301" * 7, 6) != "e\u0301" * 7


# Verifies a character wcwidth cannot measure is charged nothing rather than a column it may not use
def test_an_unmeasurable_character_costs_no_width():
    assert monitor.truncate_string_per_line("\x07" + "abcdef", 6) == "\x07" + "abcdef"


# Verifies a colour sequence costs nothing, since it is not drawn on screen
def test_a_colour_sequence_costs_no_width():
    coloured = f"\033[96mmisiektoja\033[0m and more text here"

    truncated = monitor.truncate_string_per_line(coloured, 14)

    assert "\033[96m" in truncated and "\033[0m" in truncated
    assert visible_width(truncated) == 14


# Verifies a tab is measured as the columns it moves to, since the width of a raw tab is not one column
def test_a_tab_is_measured_as_the_columns_it_moves_to():
    assert monitor.truncate_string_per_line("a\tb", 12) == "a       b"
    assert visible_width(monitor.truncate_string_per_line("a\tbcdefghij", 10)) == 10


# Verifies each line is cut on its own, so one long line does not shorten the ones around it
def test_each_line_is_cut_on_its_own():
    truncated = monitor.truncate_string_per_line("a line that is far too long\nshort\n", 10)

    assert truncated.split("\n")[1:] == ["short", ""]
    assert visible_width(truncated.split("\n")[0]) == 10


# Verifies text is left in full without wcwidth, since cutting by character count would break wide glyphs
def test_text_is_left_alone_without_wcwidth(without_wcwidth):
    line = "plain text that is much too long"

    assert monitor.truncate_string_per_line(line, 12) == line


# Verifies the flag wins over the configured value, which is how one run is widened or narrowed
def test_the_flag_wins_over_the_setting():
    assert monitor.resolve_truncate_chars(40, 80, False) == 40


# Verifies the configured value applies when no flag was passed
def test_the_setting_applies_without_a_flag():
    assert monitor.resolve_truncate_chars(None, 80, False) == 80


# Verifies a run with no log file never truncates, since nothing else would hold the full line
def test_a_run_without_a_log_file_never_truncates():
    assert monitor.resolve_truncate_chars(40, 80, True) == 0


# Verifies a negative width is treated as off rather than cutting every line to nothing
def test_a_negative_width_switches_truncation_off():
    assert monitor.resolve_truncate_chars(-5, 0, False) == 0


# Verifies the sentinel is replaced by the measured terminal width instead of being used as a width
def test_the_sentinel_measures_the_terminal(monkeypatch):
    monkeypatch.setattr(monitor.shutil, "get_terminal_size", lambda: __import__("os").terminal_size((97, 24)))

    assert monitor.resolve_truncate_chars(monitor.TERMINAL_WIDTH_SENTINEL, 0, False) == 97


# Verifies the measured width is reported only when asked for, since the summary row already carries it
def test_the_measured_width_is_reported_only_under_verbose(monkeypatch, capsys):
    monkeypatch.setattr(monitor.shutil, "get_terminal_size", lambda: __import__("os").terminal_size((97, 24)))
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)

    monitor.resolve_truncate_chars(monitor.TERMINAL_WIDTH_SENTINEL, 0, False)
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monitor.resolve_truncate_chars(monitor.TERMINAL_WIDTH_SENTINEL, 0, False)
    assert "97" in capsys.readouterr().out


# Verifies nothing is cut while the setting is off, which is the default every existing run has
def test_nothing_is_cut_while_truncation_is_off(monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    line = "a line that is far too long to fit in any narrow terminal"

    assert monitor.truncate_for_terminal(line) == line


# Verifies the terminal is cut while the log file keeps the line in full, which is why truncation is safe
def test_the_terminal_is_cut_and_the_log_file_is_not(monkeypatch, tmp_path):
    log_path = tmp_path / "run.log"
    terminal = FakeStream()
    monkeypatch.setattr(monitor.sys, "stdout", terminal)
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 20)
    logger = monitor.Logger(str(log_path))
    line = "* Output logging:               /a/very/long/path/that/will/not/fit.log\n"

    logger.write(line)

    assert visible_width(terminal.text.rstrip("\n")) == 20
    assert log_path.read_text(encoding="utf-8").strip().endswith("fit.log")


# Verifies text the log file alone receives is never cut, since the terminal width has nothing to do with it
def test_log_only_output_is_never_cut(monkeypatch, tmp_path):
    log_path = tmp_path / "run.log"
    monkeypatch.setattr(monitor.sys, "stdout", FakeStream())
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 20)
    logger = monitor.Logger(str(log_path))

    logger.log_only("* Output logging:               /a/very/long/path/that/will/not/fit.log\n")

    assert log_path.read_text(encoding="utf-8").strip().endswith("fit.log")


# Verifies every writer that reaches the terminal cuts, since a run switches between them as logging is set up
@pytest.mark.parametrize("build,method", [
    (lambda stream, path: monitor.ColorStream(stream), "write"),
    (lambda stream, path: monitor.Logger(path), "write"),
    (lambda stream, path: monitor.Logger(path), "terminal_only"),
])
def test_every_terminal_writer_cuts(monkeypatch, tmp_path, build, method):
    terminal = FakeStream()
    monkeypatch.setattr(monitor.sys, "stdout", terminal)
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 20)
    writer = build(terminal, str(tmp_path / "run.log"))

    getattr(writer, method)("a line that is far too long to fit in a narrow terminal\n")

    assert visible_width(terminal.text.rstrip("\n")) == 20


# Verifies cutting happens before colouring, so escape sequences never eat into the visible width
def test_cutting_happens_before_colouring(monkeypatch, tmp_path):
    terminal = FakeStream()
    monkeypatch.setattr(monitor.sys, "stdout", terminal)
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 30)
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(style) for name, style in monitor.DEFAULT_COLOR_THEME.items() if style})
    logger = monitor.Logger(str(tmp_path / "run.log"))

    logger.write("Riot ID (name#tag):\t\tmisiektoja#EUNE\n")

    assert "\x1b" in terminal.text
    assert visible_width(terminal.text.rstrip("\n")) == 30


# Verifies the transient progress line is left uncut, since it is erased by writing exactly the width it drew
def test_the_progress_line_is_not_cut(monkeypatch):
    terminal = FakeStream()
    monkeypatch.setattr(monitor.sys, "stdout", monitor.ColorStream(terminal))
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 10)
    monkeypatch.setattr(monitor, "DOCTOR_PROGRESS_WIDTH", 0)

    monitor.doctor_progress("the monitored account")

    assert terminal.text == "\r* Checking the monitored account ..."
    assert monitor.DOCTOR_PROGRESS_WIDTH == len(terminal.text) - 1


# Verifies the summary reports the width in effect and stays quiet in the concise view while truncation is off
@pytest.mark.parametrize("width,value,concise", [(0, "Disabled", False), (100, "100 chars", True)])
def test_the_summary_reports_the_width_in_effect(monkeypatch, width, value, concise):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", width)

    row = next(row for row in monitor.build_startup_summary() if row.label == "Terminal truncation")

    assert (row.value, row.concise) == (value, concise)


# Verifies the doctor reports the optional dependency by what this run would actually do with it
@pytest.mark.parametrize("present,width,status", [(True, 0, "PASS"), (True, 100, "PASS"), (False, 100, "WARN"), (False, 0, "SKIP")])
def test_the_doctor_reports_the_optional_dependency(monkeypatch, present, width, status):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", width)

    def spec_finder(name):
        return None if name == "wcwidth" and not present else object()

    checks = monitor.doctor_check_environment(spec_finder=spec_finder)
    row = next(check for check in checks if "wcwidth" in check.label)

    assert row.status == status
    assert row.detail


# Verifies the warning names a way out, since a doctor row nobody can act on is noise
def test_the_doctor_warning_names_a_fix(monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 100)

    checks = monitor.doctor_check_environment(spec_finder=lambda name: None if name == "wcwidth" else object())
    row = next(check for check in checks if "wcwidth" in check.label)

    assert row.advice is not None and "wcwidth" in row.advice.fix


# Verifies the flag reaches the width a run actually uses, which is the only thing that makes it worth having
def test_the_flag_reaches_the_resolved_width(monkeypatch, tmp_path):
    from test_cli_startup import run_main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DEFAULT_CONFIG_FILENAME", "lol_monitor_test_only.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "check_internet", lambda *args, **kwargs: True)

    async def fake_monitor(riotid, region, csv_file_name):
        return

    monkeypatch.setattr(monitor, "lol_monitor_user", fake_monitor)

    assert run_main(monitor, monkeypatch, [RIOT_ID, REGION, "--truncate", "42"]) == 0

    assert monitor.TRUNCATE_CHARS == 42


# Verifies switching logging off wins over the flag, so a run with no log file cannot lose output
def test_disabling_logging_wins_over_the_flag(monkeypatch, tmp_path):
    from test_cli_startup import run_main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DEFAULT_CONFIG_FILENAME", "lol_monitor_test_only.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "check_internet", lambda *args, **kwargs: True)

    async def fake_monitor(riotid, region, csv_file_name):
        return

    monkeypatch.setattr(monitor, "lol_monitor_user", fake_monitor)

    assert run_main(monitor, monkeypatch, [RIOT_ID, REGION, "--truncate", "42", "-d"]) == 0

    assert monitor.TRUNCATE_CHARS == 0


# Verifies stdout is left as the test found it, since these tests replace it with doubles
@pytest.fixture(autouse=True)
def restore_stdout():
    original = sys.stdout
    yield
    sys.stdout = original
