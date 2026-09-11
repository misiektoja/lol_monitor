"""Tests for the parts of the interface shared with the sibling monitors, pinned here because their sources are not available to CI."""

from pathlib import Path

import pytest

import lol_monitor as monitor

RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"


@pytest.fixture
# Replaces the monitoring loop with a recorder so main() returns after startup
def monitor_calls(monkeypatch, lm_module, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(lm_module, "DEFAULT_CONFIG_FILENAME", "lol_monitor_test_only.conf")
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "none")
    monkeypatch.setattr(lm_module, "check_internet", lambda *args, **kwargs: True)
    recorded = []

    # Records the arguments the monitoring loop was started with
    async def fake_monitor(riotid, region, csv_file_name):
        recorded.append(riotid)

    monkeypatch.setattr(lm_module, "lol_monitor_user", fake_monitor)
    return recorded


@pytest.fixture(scope="module")
# Reads the tool's own source, which is where the shared wording is pinned against
def module_source():
    return Path(monitor.__file__).read_text(encoding="utf-8")


# Returns the leftmost column holding a glyph anywhere in a block of banner rows
def left_edge(rows):
    return min(len(row) - len(row.lstrip(" ")) for row in rows if row.strip())


# Returns the column each row of a banner block starts in, which is what shows one row shifted against its neighbours
def indents(rows):
    return tuple(len(row) - len(row.lstrip(" ")) for row in rows if row.strip())


# The startup banner every sibling opens with: a boxed glyph beside the tool name, the shared "Monitor"
# wordmark under it and the version on its own line. Pinned here because the sibling sources are not
# available to CI, so nothing else would notice the shape drifting away from the family
class TestTheStartupBanner:
    BOX_TOP = " .---------------."
    BOX_BOTTOM = " '---------------'"
    BOX_WIDTH = 18
    WORDMARK_COLUMN = 21

    # The geometry checks below pass for any drawing that fits the box, so the drawing itself is pinned here
    def test_the_selected_art_is_unchanged(self):
        assert monitor.STARTUP_BANNER == r"""
 .---------------.    _          _
|  \\        //  |   | |    ___ | |
|   \\======//   |   | |   / _ \| |
|   //======\\   |   | |__| (_) | |___
|  //        \\  |   |_____\___/|_____|
 '---------------'
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""

    # A console that cannot draw the character, a terminal narrower than the art and an editor that
    # strips trailing spaces are three ways the banner reaches a user looking wrong
    def test_the_art_is_ascii_bounded_and_free_of_trailing_whitespace(self):
        monitor.STARTUP_BANNER.encode("ascii")
        lines = monitor.STARTUP_BANNER.splitlines()
        assert max(map(len, lines)) <= 90
        assert all(line == line.rstrip() for line in lines)

    def test_the_glyph_sits_in_the_family_box(self):
        lines = monitor.STARTUP_BANNER.strip("\n").splitlines()
        assert lines[0].startswith(self.BOX_TOP)
        closing = next(index for index, line in enumerate(lines) if line.startswith(self.BOX_BOTTOM))
        for line in lines[1:closing]:
            # The side walls have to stand under the corners of the border rows, not one column short of them
            assert line[0] == "|" and line[self.BOX_WIDTH - 1] == "|", line[:self.BOX_WIDTH]

    def test_both_wordmarks_start_in_the_same_column(self):
        lines = monitor.STARTUP_BANNER.strip("\n").splitlines()
        closing = next(index for index, line in enumerate(lines) if line.startswith(self.BOX_BOTTOM))
        beside_box = [" " * self.BOX_WIDTH + line[self.BOX_WIDTH:] for line in lines[:closing]]
        below_box = lines[closing + 1:]
        assert len(beside_box) == 5 and len(below_box) == 5
        assert left_edge(beside_box) == self.WORDMARK_COLUMN, beside_box
        assert left_edge(below_box) == self.WORDMARK_COLUMN, below_box
        # The leftmost column alone cannot see one row shifted against the rest of its own letter, so every row is checked.
        # Both words come out of the standard font with an indent of one space on the first row and none on the other four
        assert indents(beside_box) == (self.WORDMARK_COLUMN + 1,) + (self.WORDMARK_COLUMN,) * 4, beside_box
        assert indents(below_box) == (self.WORDMARK_COLUMN + 1,) + (self.WORDMARK_COLUMN,) * 4, below_box
        assert "|  \\/  | ___  _ __ (_) |_ ___  _ __" in below_box[1]

    def test_the_printer_puts_the_version_under_the_wordmark(self, capsys):
        monitor.print_startup_banner()

        printed = capsys.readouterr().out.splitlines()
        banner_lines = monitor.STARTUP_BANNER.splitlines()
        assert printed[:len(banner_lines)] == banner_lines
        assert printed[-2] == f"{'':21}v{monitor.VERSION}"
        assert printed[-1] == ""

    # Verifies a run opens with the banner and opens with it once, which is what catches a second caller
    def test_a_run_opens_with_the_banner_exactly_once(self, lm_module, monkeypatch, capsys):
        from test_cli_startup import run_main

        assert run_main(lm_module, monkeypatch, ["--help"]) == 0

        output = capsys.readouterr().out
        assert output.count(self.BOX_TOP) == 1
        assert output.startswith("\n" + self.BOX_TOP)

    # Verifies the version answer stays one line, since it is read by scripts rather than by a person at a terminal
    def test_the_version_flag_prints_no_banner(self, lm_module, monkeypatch, capsys):
        from test_cli_startup import run_main

        assert run_main(lm_module, monkeypatch, ["--version"]) == 0

        output = capsys.readouterr().out
        assert self.BOX_TOP not in output
        assert output.strip().endswith(lm_module.VERSION)


# The screen clear: which commands are allowed to wipe the terminal, and which have to leave what they printed on it
class TestTheScreenClear:
    # Verifies a command whose output is read rather than watched keeps the screen it was run from
    @pytest.mark.parametrize("flag", ["--doctor", "--send-test-email", "--list-recent-matches", "-l", "--help", "-h"])
    def test_a_one_shot_command_keeps_the_terminal_history(self, lm_module, monkeypatch, flag):
        monkeypatch.setattr(lm_module.sys, "argv", ["lol_monitor", flag])

        assert lm_module.keep_terminal_history() is True

    # Verifies an ordinary monitoring run is still allowed to clear, since it repaints the screen as it goes
    def test_a_monitoring_run_does_not_keep_the_terminal_history(self, lm_module, monkeypatch):
        monkeypatch.setattr(lm_module.sys, "argv", ["lol_monitor", RIOT_ID, REGION])

        assert lm_module.keep_terminal_history() is False

    # Verifies a redirected run never clears, since there is no screen and the clear command reports its own missing TERM
    def test_a_redirected_run_never_clears(self, lm_module, monkeypatch):
        cleared = []
        monkeypatch.setattr(lm_module.os, "system", lambda command: cleared.append(command))
        monkeypatch.setattr(lm_module.sys, "stdout", FakeStdout(interactive=False))

        lm_module.clear_screen(True)

        assert cleared == []

    # Verifies a terminal is still cleared when the setting asks for it, so the guard did not switch the feature off
    def test_a_terminal_is_still_cleared(self, lm_module, monkeypatch):
        cleared = []
        monkeypatch.setattr(lm_module.os, "system", lambda command: cleared.append(command))
        monkeypatch.setattr(lm_module.sys, "stdout", FakeStdout(interactive=True))

        lm_module.clear_screen(True)

        assert cleared == ["cls" if lm_module.platform.system() == "Windows" else "clear"]

    # Verifies a real run asks to clear only when it is a monitoring run the user is watching
    @pytest.mark.parametrize("argv,expected", [
        ([RIOT_ID, REGION], True),
        ([RIOT_ID, REGION, "--debug"], False),
        (["--doctor", RIOT_ID, REGION], False),
    ])
    def test_only_a_watched_run_asks_to_clear_the_screen(self, lm_module, monkeypatch, monitor_calls, capsys, argv, expected):
        from test_cli_startup import run_main

        asked = []
        monkeypatch.setattr(lm_module, "clear_screen", lambda enabled=True: asked.append(bool(enabled)))
        monkeypatch.setattr(lm_module, "CLEAR_SCREEN", True)

        run_main(lm_module, monkeypatch, argv)

        assert asked == [expected]


# The wording shared with the sibling monitors. Every sentence below is printed verbatim by all eight of
# them, so a reader who has used one tool reads the same words here. Pinned because the sibling sources are
# not available to CI. Changing one of these is a family-wide decision, not a local edit
SHARED_SENTENCES = (
    "* Cannot clear the screen contents",
    "After Doctor passes, start monitoring:",
    "Another config destination or leave empty to cancel",
    "Authenticate this ntfy topic with a separate access token?",
    "Change Discord or ntfy details and events.",
    "Change SMTP details and email events.",
    "Change the configuration or dotenv output path.",
    "Check network, DNS, proxy and CHECK_INTERNET_URL settings",
    "Check setup before monitoring:",
    "Check the setup before relying on it",
    "Configuration file destination",
    "Configure email notifications?",
    "Could not create a unique backup for '",
    "Could not initialize CSV file '",
    "Disable coloured output in the terminal",
    "Disables the saved token. Authentication in the topic URL still works.",
    "Discard all entered answers and exit?",
    "Doctor test email delivery failed",
    "Easiest start (guided setup wizard):",
    "Edit one section without losing the other answers.",
    "Email alerts are enabled but unusable",
    "Email is configured but no alert types are selected",
    "Email notifications are disabled",
    "Enter the SMTP password privately, check it against the mail server and save it to the dotenv file",
    "Every outbound request checks the server certificate",
    "Guided setup, recommended for the first run",
    "Keeps the private value without displaying or changing it.",
    "Leave the destination files unchanged.",
    "Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set",
    "No SMTP connection was attempted and no email was sent",
    "No configuration file selected",
    "Nothing was read from a dotenv file, the environment, the configuration file or the command line",
    "Nothing would ever be delivered",
    "Off, server certificates are not checked",
    "One or more numeric settings are invalid",
    "One real test email was sent after confirmation",
    "One real test webhook was sent after confirmation",
    "Optional CSV output path (blank disables it)",
    "Paste the ntfy access token only",
    "Paste the ntfy topic URL or ntfy.sh topic name",
    "Review the SMTP error above and correct the email settings",
    "Review the webhook error above and correct the destination settings",
    "Run doctor now? It writes no files and offers real delivery tests only with separate approval.",
    "Run read-only preflight checks and report what is ready and what is not",
    "Run the guided setup and write a ready-to-run configuration",
    "Run the guided setup wizard now?",
    "SMTP connection and login succeeded",
    "Save a Discord or ntfy webhook URL through a hidden prompt",
    "Send one test email now? This will deliver a real message",
    "Send one test webhook without starting monitoring",
    "Send test email to verify SMTP settings",
    "Sends a native notification to one ntfy topic URL.",
    "Set VERIFY_SSL back to True unless this network intercepts TLS with its own certificate authority",
    "Set WEBHOOK_ENABLED to True, or turn the alert types off",
    "Set up webhook alerts (Discord, ntfy etc.)?",
    "Setup cancelled. Destination files were not changed.",
    "Setup is saved. Start monitoring with the command above when ready.",
    "Setup is saved. Use the commands below when ready.",
    "Start monitoring now? Monitoring will continue until Ctrl+C.",
    "TLS certificate verification is off",
    "TLS certificate verification is on",
    "Terminal only (logging disabled)",
    "The approved test email could not be delivered",
    "The approved test webhook could not be delivered",
    "The connectivity endpoint could not be reached",
    "The connectivity endpoint is reachable",
    "This test email was sent after approval in --doctor. Your SMTP delivery settings work.",
    "This test email was sent by --send-test-email. Your SMTP settings work.",
    "This test notification was sent after approval in --doctor. Your webhook delivery settings work.",
    "This test notification was sent by --send-test-webhook. Your webhook settings work.",
    "Turn on at least one email alert in the configuration file",
    "Turn on at least one webhook alert in the configuration file, or set WEBHOOK_ENABLED to False",
    "Using built-in defaults and command-line overrides",
    "Using environment variables and other configured sources",
    "Webhook URL, headers and alert choices look valid",
    "Webhook alert types are selected but webhooks are switched off",
    "Webhook alerts are on but no alert types are selected",
    "Webhook alerts stay off until one is set",
    "Which email notifications should be enabled?",
    "Which ntfy authentication should be used?",
    "Which setup section should be changed?",
    "Which webhook URL should be used?",
    "Which webhook alerts should be sent?",
    "Which webhook service should receive alerts?",
    "Write the displayed settings to the selected files.",
    "Write the normal per-target log file?",
    "You declined the real delivery test. Run doctor again and approve the email test when ready",
    "You declined the real delivery test. Run doctor again and approve the webhook test when ready",
)


class TestTheSharedWording:
    # Verifies every sentence the family shares is still printed with exactly the family's words
    @pytest.mark.parametrize("sentence", SHARED_SENTENCES)
    def test_a_shared_sentence_is_unchanged(self, sentence, module_source):
        assert sentence in module_source

    # Verifies the pinned list did not quietly shrink, which is how a removed sentence would slip through
    def test_the_shared_wording_covers_the_whole_contract(self):
        assert len(SHARED_SENTENCES) == 88
        assert len(set(SHARED_SENTENCES)) == len(SHARED_SENTENCES)


class FakeStdout:
    """A stdout replacement that reports whatever the test needs isatty() to say."""

    def __init__(self, interactive):
        self.interactive = interactive

    def isatty(self):
        return self.interactive

    def write(self, message):
        return len(message)

    def flush(self):
        return
