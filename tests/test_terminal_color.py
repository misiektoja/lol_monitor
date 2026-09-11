"""Tests for the terminal colour engine: the theme, which colour lands on which token and where colour is applied."""

import argparse
from io import StringIO
import ast
import re
import sys
from pathlib import Path

import pytest

import lol_monitor as monitor

RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"


@pytest.fixture
# Switches colour on with the shipped theme, the way a run on a real terminal has it
def colored(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    styles = {name: monitor._build_ansi_sequence(style) for name, style in monitor.DEFAULT_COLOR_THEME.items()}
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: sequence for name, sequence in styles.items() if sequence})
    return styles


# Returns the source of the module under test
def module_source():
    return Path(monitor.__file__).read_text(encoding="utf-8")


# Returns the theme the configuration template ships commented out, with the comment markers removed
def template_theme():
    block = re.search(r"^# COLOR_THEME = \{$.*?^# \}$", monitor.CONFIG_BLOCK, re.S | re.M)
    assert block is not None, "the template no longer ships a commented-out COLOR_THEME block"
    uncommented = "\n".join(line[2:] if line.startswith("# ") else line[1:] for line in block.group(0).splitlines())
    return ast.literal_eval(uncommented.split("=", 1)[1].strip())


# Verifies the template a user edits ships the colours the tool actually uses, since nothing else notices it going stale
def test_the_template_theme_matches_the_built_in_theme():
    assert template_theme() == monitor.DEFAULT_COLOR_THEME


# Verifies the theme ships commented out, so the tool's own defaults apply and a later change reaches existing files
def test_the_template_ships_the_theme_commented_out():
    assert "\nCOLOR_THEME = {" not in monitor.CONFIG_BLOCK
    assert "COLOR_THEME" in monitor.COMMENTED_CONFIG_SETTINGS


# Verifies a configuration file that sets the commented-out setting still loads, since the template is the allowlist
def test_a_config_setting_only_the_theme_is_accepted():
    values = monitor.parse_config_content('COLOR_THEME = {"error": "bright_red"}\n', "<test>")

    assert values["COLOR_THEME"] == {"error": "bright_red"}


# Verifies every part the shipped theme offers is looked up somewhere, so the theme documents only colours a user can change
def test_every_theme_part_is_used():
    source = module_source()
    looked_up = set(re.findall(r"""colorize\(\s*["']([a-z_]+)["']""", source))
    looked_up |= set(re.findall(r"""_apply_style_nested\([^,]+,\s*["']([a-z_]+)["']""", source))
    looked_up |= set(re.findall(r"""_COLOR_STYLES\.get\(["']([a-z_]+)["']""", source))
    looked_up |= set(re.findall(r""",\s*["']([a-z_]+)["']\),?\s*$""", source, re.M))
    looked_up |= set(monitor.DOCTOR_MARK_STYLES.values())

    assert not set(monitor.DEFAULT_COLOR_THEME) - looked_up


# Verifies no call names a colour the theme does not ship, which would silently render plain
def test_every_colour_named_in_the_source_exists_in_the_theme():
    source = module_source()
    named = set(re.findall(r"""colorize\(\s*["']([a-z_]+)["']""", source))
    named |= set(re.findall(r"""_apply_style_nested\([^,]+,\s*["']([a-z_]+)["']""", source))
    named |= set(monitor.DOCTOR_MARK_STYLES.values())

    assert not named - set(monitor.DEFAULT_COLOR_THEME)


# Verifies a value drawn in the colour of the block enclosing it would disappear, so the two sets stay distinct
def test_a_block_style_never_hides_a_name(colored):
    for block in monitor.BLOCK_STYLE_PARTS:
        for name in monitor.NAME_STYLE_PARTS:
            assert colored[name] != colored[block], f"{name} is invisible inside a {block} line"


# Verifies the doctor's own section names are the ones the colouriser recognises as headings
def test_every_doctor_section_is_recognised_as_a_heading():
    unmatched = [section for section in monitor.DOCTOR_SECTIONS if not monitor._REPORT_SECTION_RE.match(section)]

    assert unmatched == []


# Verifies a style description turns into the escape sequence its parts name, and that an unknown part is dropped
@pytest.mark.parametrize("style,expected", [
    ("red", "\033[31m"),
    ("bright_cyan underline", "\033[96;4m"),
    ("bold+green", "\033[1;32m"),
    ("", ""),
    ("chartreuse", ""),
])
def test_a_style_description_builds_its_escape_sequence(style, expected):
    assert monitor._build_ansi_sequence(style) == expected


# Verifies colour is refused wherever the escapes would end up somewhere other than a terminal the user is watching
@pytest.mark.parametrize("interactive,environment,stdin_is_tty,expected", [
    (True, {"TERM": "xterm-256color"}, True, True),
    (False, {"TERM": "xterm-256color"}, True, False),
    (True, {"TERM": "xterm-256color", "NO_COLOR": "1"}, True, False),
    (True, {"TERM": "dumb"}, True, False),
    (True, {"TERM": ""}, True, False),
    (True, {"TERM": "xterm-256color"}, False, False),
])
def test_colour_support_is_detected_from_the_stream_and_the_environment(monkeypatch, interactive, environment, stdin_is_tty, expected):
    monkeypatch.delenv("NO_COLOR", raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(monitor.sys, "stdin", FakeStream(stdin_is_tty))

    assert monitor._stream_supports_color(FakeStream(interactive)) is expected


class FakeStream:
    """A stream stand-in that reports whatever the test needs isatty() to say."""

    def __init__(self, interactive):
        self.interactive = interactive
        self.written = []

    def isatty(self):
        return self.interactive

    def write(self, message):
        self.written.append(message)
        return len(message)

    def flush(self):
        return


# Verifies the setting switches the whole engine off, so nothing has to be checked at each call site
def test_the_setting_switches_colour_off(monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)

    monitor.init_color_output(FakeStream(True))

    assert monitor.COLOR_ENABLED is False
    assert monitor._COLOR_STYLES == {}
    assert monitor.colorize("error", "boom") == "boom"


# Verifies a theme in the configuration file wins over the default for the parts it names and leaves the rest alone
def test_a_configured_theme_overrides_only_the_parts_it_names(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setattr(monitor.sys, "stdin", FakeStream(True))
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setitem(monitor.__dict__, "COLOR_THEME", {"error": "bright_red"})

    monitor.init_color_output(FakeStream(True))

    assert monitor._COLOR_STYLES["error"] == "\033[91m"
    assert monitor._COLOR_STYLES["username"] == monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["username"])


# Verifies a part with no style produces no escape at all rather than an empty sequence
def test_a_part_with_no_style_is_left_plain(colored):
    assert monitor.colorize("timestamp_label", "Timestamp:") == "Timestamp:"


# Verifies each labelled row keeps its label plain and colours only the value it reports
@pytest.mark.parametrize("line,part,value", [
    ("Riot ID (name#tag):\t\tmisiektoja#EUNE", "username", "misiektoja#EUNE"),
    ("Riot PUUID:\t\t\ttest-puuid-value", "id", "test-puuid-value"),
    ("Match ID:\t\t\tEUN1_0", "id", "EUN1_0"),
    ("Champion:\t\t\tAhri", "champion", "Ahri"),
    ("Game mode:\t\t\tSummoner's Rift", "game_mode", "Summoner's Rift"),
    ("Match duration:\t\t\t30 minutes", "duration", "30 minutes"),
    ("* Target:                       misiektoja#EUNE (eun1)", "username", "misiektoja#EUNE (eun1)"),
])
def test_a_labelled_row_colours_its_value(colored, line, part, value):
    rendered = monitor._colorize_line(line)

    assert f"{colored[part]}{value}{monitor.ANSI_RESET}" in rendered
    assert rendered.startswith(line.split(":", 1)[0])


# Verifies the rows under the game mode stay plain, since four rows in one colour marked nothing
@pytest.mark.parametrize("line", ["Queue:\t\t\t\tRanked Solo/Duo", "Map:\t\t\t\tSummoner's Rift", "Game type:\t\t\tMatched"])
def test_the_rows_under_the_game_mode_stay_plain(colored, line):
    assert monitor._colorize_line(line) == line


# Verifies the target row and the account row agree, since a reader has to see them as the same player
def test_the_target_row_matches_the_account_row(colored):
    target = monitor._colorize_line(f"* Target:                       {RIOT_ID} ({REGION})")
    account = monitor._colorize_line(f"Riot ID (name#tag):\t\t{RIOT_ID}")

    assert target.count(colored["username"]) == 1
    assert account.count(colored["username"]) == 1


# Verifies the timestamp row dims its label and colours the time, which is the shape every sibling uses
@pytest.mark.parametrize("label", ["Timestamp:", "Liveness check, timestamp:"])
def test_a_timestamp_row_colours_only_its_value(colored, label):
    rendered = monitor._colorize_line(f"{label}\t\t\tThu 01 Jan 2026, 00:20:00")

    assert rendered == f"{label}\t\t\t{colored['timestamp_value']}Thu 01 Jan 2026, 00:20:00{monitor.ANSI_RESET}"


# Verifies a ranked row colours the standing and leaves the counts beside it plain, since only one of them is the result
def test_a_ranked_row_colours_the_standing_only(colored):
    rendered = monitor._colorize_line("Solo/Duo:\t\t\tGOLD II (44 LP) - Wins: 30 / Losses: 25 (Winrate: 54.5%)")

    assert f"{colored['rank']}GOLD II{monitor.ANSI_RESET}" in rendered
    assert "(44 LP)" in rendered.replace(colored["rank"], "").replace(monitor.ANSI_RESET, "")
    assert f"{colored['rank']}30" not in rendered


# Verifies having no rank is reported in the same colour as having one, so the row reads the same way either way
def test_an_unranked_row_colours_the_word(colored):
    assert f"{colored['rank']}Unranked{monitor.ANSI_RESET}" in monitor._colorize_line("Flex:\t\t\t\tUnranked")


# Verifies a roster entry names the player and the champion in their own colours
def test_a_roster_entry_colours_the_player_and_the_champion(colored):
    rendered = monitor._colorize_line("- misiektoja (Kai'Sa)")

    assert rendered == f"- {colored['username']}misiektoja{monitor.ANSI_RESET} ({colored['champion']}Kai'Sa{monitor.ANSI_RESET})"


# Verifies the monitored player's own entry is marked, so their line stands out among the nine others
def test_the_monitored_players_roster_entry_is_marked(colored, monkeypatch):
    monkeypatch.setattr(monitor, "MONITORED_PLAYER_NAME", "misiektoja")

    assert monitor._colorize_line("- misiektoja (Kai'Sa)").startswith(f"- {colored['monitored_username']}misiektoja{monitor.ANSI_RESET}")
    assert monitor._colorize_line("- rival (Zed)").startswith(f"- {colored['username']}rival{monitor.ANSI_RESET}")


# Verifies the marked name is recorded from the reported player, with anything unusable read as no player
def test_the_marked_player_is_recorded_from_the_report():
    monitor.set_monitored_player_name("  misiektoja  ")
    assert monitor.MONITORED_PLAYER_NAME == "misiektoja"

    monitor.set_monitored_player_name(None)
    assert monitor.MONITORED_PLAYER_NAME == ""


# Verifies a champion mastery entry colours the champion and leaves the level and points beside it plain
def test_a_mastery_entry_colours_the_champion(colored):
    rendered = monitor._colorize_line("\t\t\t\t1. Kai'Sa:            Level 7 (123,456 points)")

    assert f"{colored['champion']}Kai'Sa{monitor.ANSI_RESET}:" in rendered
    assert "Level 7 (123,456 points)" in rendered


# Verifies the two events this tool exists to report are coloured by what they mean
@pytest.mark.parametrize("line,part,phrase", [
    ("*** LoL user misiektoja is in game now (after 30 minutes)", "status_active", "is in game now"),
    ("*** LoL user misiektoja stopped playing !", "status_inactive", "stopped playing"),
    ("User is not in game currently", "status_inactive", "is not in game currently"),
])
def test_a_playing_event_is_coloured_by_what_it_means(colored, line, part, phrase):
    assert f"{colored[part]}{phrase}{monitor.ANSI_RESET}" in monitor._colorize_line(line)


# Verifies the monitored player named inside a sentence is coloured as a player and not as anything else
def test_the_player_named_in_a_sentence_is_coloured(colored):
    rendered = monitor._colorize_line("*** LoL user misiektoja is in game now (after 30 minutes)")

    assert f"{colored['username']}misiektoja{monitor.ANSI_RESET}" in rendered
    assert f"{colored['id']}misiektoja" not in rendered


# Verifies a diagnostic user field names its value, which is how a debug trace stays scannable
def test_a_diagnostic_user_field_is_coloured(colored):
    rendered = monitor._colorize_line("[DEBUG 23:47:21] Monitoring check: check=#1, user=misiektoja#EUNE, outcome=OK")

    assert f"{colored['username']}misiektoja#EUNE{monitor.ANSI_RESET}" in rendered


# Verifies a debug line keeps its own colours instead of being painted as the failure it records
def test_a_debug_line_is_not_painted_as_a_failure(colored):
    rendered = monitor._colorize_line("[DEBUG 23:47:21] Champion mastery: outcome=failed, error=ValueError: no data")

    assert not rendered.startswith(colored["error"])


# Verifies the words that report a real problem paint their line, so a failure is visible without being read
def test_a_failure_line_is_painted(colored):
    assert monitor._colorize_line("* Error: The SMTP server could not be reached").startswith(colored["error"])


# Verifies the recovery instruction is marked as guidance rather than as part of the failure above it
def test_the_recovery_instruction_is_marked_as_guidance(colored):
    assert monitor._colorize_line("To fix: Check SMTP_HOST, SMTP_PORT and SMTP_SSL").startswith(colored["info"])
    assert monitor._colorize_line("  To fix: Check SMTP_HOST").startswith(colored["info"])


# Verifies a warning marks its own opening word rather than painting the line, so the values in it stay readable
@pytest.mark.parametrize("opening", ["Warning:", "Note:"])
def test_a_warning_marks_its_opening_word(colored, opening):
    rendered = monitor._colorize_line(f"* {opening} something happened")

    assert rendered == f"* {colored['warning']}{opening}{monitor.ANSI_RESET} something happened"


# Verifies a reported signal names itself, which is the one part of the line that changes
def test_a_reported_signal_names_itself(colored):
    assert monitor._colorize_line("* Signal SIGUSR1 received") == f"* Signal {colored['signal']}SIGUSR1{monitor.ANSI_RESET} received"


# Verifies a delivery line is marked as one, so it is not read as the failure that sometimes follows it
def test_a_delivery_line_is_marked(colored):
    assert monitor._colorize_line("Sending email notification to alerts@example.test").startswith(colored["email"])


# Verifies a link is coloured wherever it appears and that trailing punctuation is left outside it
def test_a_link_is_coloured_without_its_punctuation(colored):
    rendered = monitor._colorize_line("Guide: https://misiektoja.github.io/lol_monitor/usage/.")

    assert f"{colored['link']}https://misiektoja.github.io/lol_monitor/usage/{monitor.ANSI_RESET}." in rendered


# Verifies each doctor marker carries the colour its status means, with the rest of the row left plain
@pytest.mark.parametrize("status,part", [("PASS", "boolean_true"), ("WARN", "warning"), ("FAIL", "error"), ("SKIP", "info")])
def test_a_doctor_marker_is_coloured_by_its_status(colored, status, part):
    rendered = monitor._colorize_line(f"[{status}] Something was checked")

    assert rendered == f"{colored[part]}[{status}]{monitor.ANSI_RESET} Something was checked"


# Verifies the four markers stay visually distinct, since a report is skimmed by their colour rather than read
def test_the_four_doctor_markers_are_distinct(colored):
    used = [colored[monitor.DOCTOR_MARK_STYLES[status]] for status in ("PASS", "WARN", "FAIL", "SKIP")]

    assert len(set(used)) == 4


# Verifies the pairs that exist to be told apart are drawn differently, since sharing a colour makes the pair useless
@pytest.mark.parametrize("first,second", [
    ("status_active", "status_inactive"),
    ("boolean_true", "boolean_false"),
    ("header", "section"),
    ("error", "warning"),
    ("date", "duration"),
])
def test_a_pair_that_exists_to_be_told_apart_uses_two_colours(colored, first, second):
    assert colored[first] != colored[second]


# Verifies the report's own headings are coloured, since they are what a reader scans the report by
@pytest.mark.parametrize("heading,part", [("Doctor", "header"), ("Summary", "header"), ("Next steps", "header"), ("Environment", "section"), ("Notifications", "section"), ("Ranked Information:", "section"), ("Banned champions:", "section")])
def test_a_heading_is_coloured(colored, heading, part):
    assert monitor._colorize_line(heading) == f"{colored[part]}{heading}{monitor.ANSI_RESET}"


# Verifies a labelled row is not mistaken for the heading that shares its first word
def test_a_labelled_row_is_not_read_as_a_heading(colored):
    rendered = monitor._colorize_line("* Target:                       misiektoja#EUNE (eun1)")

    assert not rendered.startswith(colored["section"])


# Verifies both notification summary rows colour their state word rather than the categories beside it
@pytest.mark.parametrize("channel", ["email", "webhook"])
@pytest.mark.parametrize("state,part", [("On", "boolean_true"), ("Off", "boolean_false")])
def test_the_notification_row_colours_its_state(colored, channel, state, part):
    label = f"* Notifications ({channel}):".ljust(32)
    rendered = monitor._colorize_line(f"{label}{state} (status changes)" if state == "On" else f"{label}{state}")

    assert f"{colored[part]}{state}{monitor.ANSI_RESET}" in rendered


# Verifies a delivery line is painted in the colour of the channel that sent it, so two channels read apart
@pytest.mark.parametrize("line,part", [
    ("Sending email notification to alerts@example.test", "email"),
    ("* Email sent successfully !", "email"),
    ("Sending webhook notification", "webhook"),
    ("* Webhook sent successfully !", "webhook"),
])
def test_each_delivery_line_is_painted_in_its_channel_colour(colored, line, part):
    rendered = monitor._colorize_line(line)

    assert rendered.startswith(colored[part])


# Verifies the one setting whose off state weakens a security property says so in colour
@pytest.mark.parametrize("state,part", [("On", "boolean_true"), ("Off", "boolean_false")])
def test_the_tls_row_colours_its_state(colored, state, part):
    rendered = monitor._colorize_line(f"* TLS verification:             {state}")

    assert rendered.startswith(f"* TLS verification:             {colored[part]}{state}{monitor.ANSI_RESET}")


# Verifies boolean settings are coloured by what they say, which is how a summary is skimmed
@pytest.mark.parametrize("value,part", [("True", "boolean_true"), ("False", "boolean_false"), ("Disabled", "boolean_false")])
def test_a_boolean_setting_is_coloured(colored, value, part):
    assert f"{colored[part]}{value}{monitor.ANSI_RESET}" in monitor._colorize_line(f"* Forbidden matches:            {value}")


# Verifies a settings row whose label contains a problem word is not painted as a failure
def test_a_settings_row_is_not_painted_as_a_failure(colored):
    rendered = monitor._colorize_line("* Forbidden matches:            False")

    assert not rendered.startswith(colored["error"])


# Verifies a date range is coloured as one rather than being split into two separate dates
def test_a_date_range_is_coloured_as_one(colored):
    rendered = monitor._colorize_line("Match start-end date:\t\tThu 01 Jan 2026, 00:20:00 - 00:50:00")

    assert f"{colored['date_range']}Thu 01 Jan 2026, 00:20:00 - 00:50:00{monitor.ANSI_RESET}" in rendered


# Verifies a single date is coloured as a date
def test_a_single_date_is_coloured(colored):
    assert f"{colored['date']}Thu 01 Jan 2026, 00:19:00{monitor.ANSI_RESET}" in monitor._colorize_line("Match creation:\t\t\tThu 01 Jan 2026, 00:19:00")


# Verifies how long something took is coloured wherever it is reported
def test_a_duration_is_coloured(colored):
    assert f"{colored['duration']}30 minutes{monitor.ANSI_RESET}" in monitor._colorize_line("* Retrying in 30 minutes")


# Verifies a quoted name keeps its own apostrophe instead of ending at it, which is the family's shared fix
def test_a_quoted_name_keeps_its_own_apostrophe():
    matches = monitor._QUOTED_CONTENT_RE.findall("Listing recent match for 'Tom Clancy's Rainbow Six Siege'")

    assert [match[1] for match in matches] == ["Tom Clancy's Rainbow Six Siege"]


# Verifies two quoted names on one line stay two names, which a greedy pattern would merge into one span
def test_two_quoted_names_on_one_line_stay_separate():
    matches = monitor._QUOTED_CONTENT_RE.findall("changed for user 'Ahri' to 'Zed'")

    assert [match[1] for match in matches] == ["Ahri", "Zed"]


# Verifies a quoted value is coloured as a name only where the words before it introduce one
def test_a_quoted_value_is_a_name_only_in_context(colored):
    named = monitor._colorize_line(f"Listing recent match for '{RIOT_ID}'")
    bare = monitor._colorize_line("'eun1' is not present in REGION_TO_CONTINENT")

    assert f"'{colored['username']}{RIOT_ID}{monitor.ANSI_RESET}'" in named
    assert colored["username"] not in bare


# Verifies a quoted value whose shape says it is not a name is left plain even in a naming context
@pytest.mark.parametrize("value", ["/var/log/lol.log", "lol_monitor.conf", ".env", "<riot_id>", "--env-file none", "?code=abc", "https://example.test"])
def test_a_quoted_value_that_is_not_a_name_stays_plain(colored, value):
    rendered = monitor._colorize_line(f"Listing recent match for '{value}'")

    assert colored["username"] not in rendered


# Verifies one rule cannot reclaim text another has already coloured, which would nest spans and reset early
def test_a_later_rule_cannot_reclaim_coloured_text(colored):
    already = f"before {colored['username']}misiektoja{monitor.ANSI_RESET} after"

    assert monitor._sub_outside_color(re.compile("misiektoja"), lambda mo: "TAKEN", already) == already


# Verifies a block style returns to itself after an inner value ends, so one value cannot end the block early
def test_a_block_style_survives_an_inner_value(colored):
    inner = f"failed for {colored['username']}misiektoja{monitor.ANSI_RESET} now"

    rendered = monitor._apply_style_nested(inner, "error")

    assert rendered.startswith(colored["error"])
    assert rendered.endswith(monitor.ANSI_RESET)
    assert rendered.count(colored["error"]) == 2


# Verifies the banner is coloured line by line, since one span around the block would leave every later line plain
def test_the_banner_uses_only_its_own_colours(colored, capsys):
    monitor.print_startup_banner()

    printed = capsys.readouterr().out.splitlines()
    art = [line for line in printed if line.strip() and "v" + monitor.VERSION not in line]
    assert art, "the banner printed nothing"
    for line in art:
        assert line.startswith(colored["header"]) and line.endswith(monitor.ANSI_RESET), line
    assert printed[-2].startswith(colored["info"])


# Verifies the art itself is unchanged once the colours are stripped, so a colour test cannot hide a broken drawing
def test_the_banner_art_survives_colouring(colored, capsys):
    monitor.print_startup_banner()

    stripped = monitor.ANSI_ESCAPE_RE.sub("", capsys.readouterr().out)
    assert monitor.STARTUP_BANNER in stripped


# Verifies output written through the real stack is coloured exactly once, whatever wrappers are installed
def test_one_colour_pass_through_the_real_stack(colored, monkeypatch, tmp_path):
    terminal = FakeStream(True)
    monkeypatch.setattr(monitor.sys, "stdout", monitor.ColorStream(terminal))
    logger = monitor.Logger(str(tmp_path / "run.log"))

    logger.write("Riot ID (name#tag):\t\tmisiektoja#EUNE\n")

    written = "".join(terminal.written)
    assert written.count(colored["username"]) == 1
    assert written.count(monitor.ANSI_RESET) == 1


# Verifies the logger writes past the early colouring stream instead of through it, which would colour twice
def test_the_logger_unwraps_the_early_terminal_stream(monkeypatch, tmp_path):
    terminal = FakeStream(True)
    monkeypatch.setattr(monitor.sys, "stdout", monitor.ColorStream(monitor.ColorStream(terminal)))

    logger = monitor.Logger(str(tmp_path / "run.log"))

    assert logger.terminal is terminal


# Verifies the log file stays plain text, so a log attached to a bug report is readable
@pytest.mark.parametrize("method", ["write", "log_only"])
def test_the_log_file_holds_no_escape_sequences(colored, monkeypatch, tmp_path, method):
    log_path = tmp_path / "run.log"
    monkeypatch.setattr(monitor.sys, "stdout", monitor.ColorStream(FakeStream(True)))
    logger = monitor.Logger(str(log_path))

    getattr(logger, method)("* Error: something failed\n")
    logger.flush()

    content = log_path.read_text(encoding="utf-8")
    assert "\x1b" not in content
    assert "* Error: something failed" in content


# Verifies the transient progress line carries no escapes, since it is erased by writing exactly its own width
def test_the_progress_line_carries_no_escapes(colored, monkeypatch):
    terminal = FakeStream(True)
    monkeypatch.setattr(monitor.sys, "stdout", monitor.ColorStream(terminal))
    monkeypatch.setattr(monitor, "DOCTOR_PROGRESS_WIDTH", 0)

    monitor.doctor_progress("connectivity")

    written = "".join(terminal.written)
    assert "\x1b" not in written
    assert written == "\r* Checking connectivity ..."


# Verifies argparse is stopped from adding a palette of its own on the interpreters that have one
@pytest.mark.parametrize("version,expected", [((3, 13, 0), {}), ((3, 14, 0), {"color": False})])
def test_argparse_is_told_not_to_colour_its_own_help(monkeypatch, version, expected):
    monkeypatch.setattr(monitor.sys, "version_info", version)

    assert monitor.argparse_color_kwargs() == expected


# Verifies the helper actually reaches the parser, since deleting the keyword would leave the check above passing
def test_the_argparse_guard_reaches_the_parser():
    tree = ast.parse(module_source())
    parsers = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "ColoredHelpParser"]

    assert parsers, "the source no longer builds an ArgumentParser"
    for parser in parsers:
        assert any(keyword.arg is None and getattr(keyword.value.func, "id", "") == "argparse_color_kwargs" for keyword in parser.keywords if isinstance(keyword.value, ast.Call)), "the parser is built without argparse_color_kwargs()"


# Verifies the settings that take effect before argument parsing are read from the configuration file
def test_the_early_peek_reads_the_output_settings(monkeypatch, tmp_path):
    config = tmp_path / "lol_monitor.conf"
    config.write_text('CLEAR_SCREEN = False\nCOLORED_OUTPUT = False\nCOLOR_THEME = {"error": "bright_red"}\n', encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["lol_monitor", "--config-file", str(config)])
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setitem(monitor.__dict__, "COLOR_THEME", {})

    monitor.apply_early_output_config()

    assert (monitor.CLEAR_SCREEN, monitor.COLORED_OUTPUT) == (False, False)
    assert monitor.__dict__["COLOR_THEME"] == {"error": "bright_red"}


# Verifies a run that switched config discovery off reads no config at all, not even a file named after the switch
def test_the_early_peek_respects_disabled_discovery(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "none").write_text("COLORED_OUTPUT = False\n", encoding="utf-8")
    (tmp_path / monitor.DEFAULT_CONFIG_FILENAME).write_text("COLORED_OUTPUT = False\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["lol_monitor", "--config-file", "none"])
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)

    monitor.apply_early_output_config()

    assert monitor.COLORED_OUTPUT is True


# Verifies a broken configuration file leaves the early peek silent, so the real load reports it once with detail
def test_the_early_peek_is_silent_about_a_broken_config(monkeypatch, tmp_path, capsys):
    config = tmp_path / "lol_monitor.conf"
    config.write_text("import os\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["lol_monitor", "--config-file", str(config)])
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)

    monitor.apply_early_output_config()

    assert monitor.COLORED_OUTPUT is True
    assert capsys.readouterr().out == ""


# Verifies the value of --config-file is found before argparse runs, in both forms a user can write it
@pytest.mark.parametrize("argv,expected", [
    (["--config-file", "x.conf"], "x.conf"),
    (["--config-file=x.conf"], "x.conf"),
    (["--verbose"], None),
    (["--config-file"], None),
])
def test_the_config_path_is_found_before_argparse(argv, expected):
    assert monitor.early_config_file_argument(argv) == expected


# Verifies the flag reaches the engine, which is the only thing that makes it worth having
def test_the_no_color_flag_switches_colour_off(monkeypatch, capsys, tmp_path):
    from test_cli_startup import run_main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DEFAULT_CONFIG_FILENAME", "lol_monitor_test_only.conf")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
    monkeypatch.setattr(monitor, "check_internet", lambda *args, **kwargs: True)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    async def fake_monitor(riotid, region, csv_file_name):
        return

    monkeypatch.setattr(monitor, "lol_monitor_user", fake_monitor)

    assert run_main(monitor, monkeypatch, [RIOT_ID, REGION, "--no-color"]) == 0

    assert monitor.COLOR_ENABLED is False
    assert "\x1b" not in capsys.readouterr().out


# Verifies the summary reports the resolved state alongside the setting, since colour also switches itself off
def test_the_summary_reports_the_resolved_colour_state(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)

    assert next(row.value for row in monitor.build_startup_summary() if row.label == "Coloured output") == "False (setting: True)"


# Verifies nothing is coloured while colour is off, which is what every redirected run and every log write relies on
def test_nothing_is_coloured_while_colour_is_off(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    text = "Riot ID (name#tag):\t\tmisiektoja#EUNE\n* Error: something failed\n"

    assert monitor.apply_color_to_text(text) == text


# Verifies multi-line text keeps its line breaks, so a coloured block is not reflowed into one line
def test_colouring_preserves_line_breaks(colored):
    rendered = monitor.apply_color_to_text("Champion:\t\t\tAhri\nChampion:\t\t\tZed\n")

    assert monitor.ANSI_ESCAPE_RE.sub("", rendered) == "Champion:\t\t\tAhri\nChampion:\t\t\tZed\n"
    assert rendered.count(colored["champion"]) == 2


# Verifies a real transcript is coloured without leaving a surface entirely plain, which is what a reader notices
def test_a_real_transcript_colours_every_surface(colored):
    surfaces = {
        "account row": "Riot ID (name#tag):\t\tmisiektoja#EUNE",
        "heading": "Ranked Information:",
        "ranked row": "Solo/Duo:\t\t\tGOLD II (44 LP) - Wins: 30 / Losses: 25",
        "match row": "Match ID:\t\t\tEUN1_0",
        "roster entry": "- misiektoja (Ahri)",
        "timestamp": "Timestamp:\t\t\tThu 01 Jan 2026, 00:20:00",
        "event": "*** LoL user misiektoja is in game now (after 30 minutes)",
        "delivery": "Sending email notification to alerts@example.test",
        "failure": "* Error: The SMTP server could not be reached",
        "guidance": "To fix: Check SMTP_HOST",
        "guide link": "Guide: https://misiektoja.github.io/lol_monitor/usage/",
        "doctor row": "[PASS] Python 3.13.1 is supported",
        "summary row": "* Target:                       misiektoja#EUNE (eun1)",
    }
    plain = [name for name, line in surfaces.items() if "\x1b" not in monitor._colorize_line(line)]

    assert plain == [], f"surfaces that render entirely plain: {', '.join(plain)}"


# Verifies stdout is left as the test found it, since these tests replace it with doubles
@pytest.fixture(autouse=True)
def restore_stdout():
    original = sys.stdout
    yield
    sys.stdout = original


HELP_SAMPLE = """usage: monitor [-h] [--config-file PATH] [TARGET]

positional arguments:
  TARGET                The target to monitor

Configuration & dotenv files:
  --config-file PATH    Path to a config file
  -m, --check-interval SECONDS
                        Time between checks (default: 60)

Examples:

Getting started:
  # Guided setup, see https://example.invalid/guide/
  python3 monitor.py --setup <target>

Guide: https://example.invalid/guide/
"""

HELP_SAMPLE_EPILOG = HELP_SAMPLE[HELP_SAMPLE.index("Examples:"):]


# Enables colour with the shipped theme and returns the escape sequence of every part
@pytest.fixture
def help_palette(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    return styles


# Returns the sample help screen with the help palette applied
@pytest.fixture
def colored_help(help_palette):
    return monitor.colorize_help_text(HELP_SAMPLE, HELP_SAMPLE_EPILOG)


# Verifies colouring changes no character of the screen, since argparse laid out its columns on the plain text
def test_the_coloured_help_keeps_the_plain_layout(colored_help):
    assert monitor.ANSI_ESCAPE_RE.sub("", colored_help) == HELP_SAMPLE


# Verifies the argument groups and the example tasks share one heading colour, the anchors the reader scans for
def test_the_help_headings_carry_the_heading_colour(help_palette, colored_help):
    for heading in ("positional arguments:", "Configuration & dotenv files:", "Examples:", "Getting started:"):
        assert f"{help_palette['help_heading']}{heading}{monitor.ANSI_RESET}" in colored_help


# Verifies an option name and the value it takes are coloured apart, in the usage block and in the option rows
def test_the_help_option_names_and_their_values_are_coloured_apart(help_palette, colored_help):
    option = f"{help_palette['help_option']}--config-file{monitor.ANSI_RESET}"
    metavar = f"{help_palette['help_metavar']}PATH{monitor.ANSI_RESET}"

    assert f"{option} {metavar}" in colored_help
    assert f"[{option} {metavar}]" in colored_help
    assert f"{help_palette['help_usage']}usage:{monitor.ANSI_RESET}" in colored_help
    assert f"{help_palette['help_metavar']}TARGET{monitor.ANSI_RESET}                The target to monitor" in colored_help


# Verifies the examples separate the comment from the command and mark the value the reader has to replace
def test_the_help_examples_mark_comments_commands_and_placeholders(help_palette, colored_help):
    assert f"{help_palette['help_comment']}  # Guided setup" in colored_help
    assert f"{help_palette['help_command']}  python3 monitor.py --setup" in colored_help
    assert f"{help_palette['help_placeholder']}<target>{monitor.ANSI_RESET}" in colored_help


# Verifies a default note is dimmed and a documentation link keeps the shared link colour
def test_the_help_default_notes_and_links_stay_secondary(help_palette, colored_help):
    assert f"{help_palette['help_default']}(default: 60){monitor.ANSI_RESET}" in colored_help
    assert f"{help_palette['link']}https://example.invalid/guide/{monitor.ANSI_RESET}" in colored_help


# Verifies the help screen stays plain while colour is switched off, so --no-color and NO_COLOR clear all of it
def test_the_help_palette_switches_off_with_colour():
    assert monitor.colorize_help_text(HELP_SAMPLE, HELP_SAMPLE_EPILOG) == HELP_SAMPLE


# Verifies the finished help screen reaches the terminal untouched, past the colouriser that paints monitoring output
def test_the_help_screen_is_not_repainted_by_the_monitoring_rules(help_palette):
    buffer = StringIO()
    parser = monitor.ColoredHelpParser(prog="monitor", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config-file", metavar="PATH", help="Path to a config file")
    parser.print_help(monitor.ColorStream(buffer))

    written = buffer.getvalue()
    assert written == parser.format_help()
    assert help_palette["help_option"] in written


# Verifies the setup screens colour their links, since they print before the output stream colouriser is installed
def test_setup_screen_links_are_coloured(monkeypatch):
    link = monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["link"])
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {"link": link})

    assert monitor.colorize_links("Guide: https://example.test/page") == f"Guide: {link}https://example.test/page{monitor.ANSI_RESET}"


# Verifies no setup screen prints a link without colouring it, which is how a plain link gets in
def test_no_setup_screen_prints_a_plain_link():
    setup = re.compile(r"^(?:run_setup_wizard|run_scrobble_health_setup_wizard|_wizard_|run_set_|run_browser_cookie_import|print_welcome_screen|print_doctor_next_steps|print_spotify_scrobble_app_guidance)")
    tree = ast.parse(Path(monitor.__file__).read_text(encoding="utf-8"))
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    plain = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print"):
            continue
        nested = list(ast.walk(node))
        prints_link = any(isinstance(item, ast.Constant) and isinstance(item.value, str) and "http" in item.value for item in nested) or any(isinstance(item, ast.Name) and "URL" in item.id for item in nested)
        coloured = any(isinstance(item, ast.Name) and item.id in ("colorize", "colorize_links") for item in nested)
        owner, current = "", parents.get(node)
        while current is not None:
            if isinstance(current, ast.FunctionDef):
                owner = current.name
                break
            current = parents.get(current)
        if prints_link and not coloured and setup.match(owner):
            plain.append(f"{owner}:{node.lineno}")

    assert plain == []


# Verifies the early peek carries the theme, since --help is printed and exited from inside argparse before the config load
def test_the_early_output_config_carries_the_help_theme(monkeypatch, tmp_path):
    (tmp_path / "lol_monitor.conf").write_text('COLOR_THEME = {"help_heading": "bright_red"}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "COLOR_THEME", {})
    monkeypatch.setattr(monitor, "CONFIG_DISCOVERY_DISABLED", False)
    monkeypatch.setattr(monitor.sys, "argv", ["lol_monitor", "--help"])

    monitor.apply_early_output_config()

    assert monitor.COLOR_THEME == {"help_heading": "bright_red"}
