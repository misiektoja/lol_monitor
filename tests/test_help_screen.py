"""Tests the --help screen: the shared argument groups, the shared one-shot sentences and the examples block."""

from command_expectations import runtime_command
import re
import subprocess
import sys
from pathlib import Path

import pytest

import lol_monitor as monitor

REPO_ROOT = Path(__file__).resolve().parents[1]

# The argument groups every sibling prints, in the order they print them
SHARED_GROUPS = (
    "Configuration & dotenv files",
    "API credentials",
    "Email notifications",
    "Webhook notifications",
    "Intervals & timers",
    "User information & listing",
    "Features & output",
)

# One sentence per shared one-shot flag, copied from the sibling monitors. Changing one here means changing it there
SHARED_FLAG_SENTENCES = {
    "--setup": "Run the guided setup and write a ready-to-run configuration",
    "--doctor": "Run read-only preflight checks and report what is ready and what is not",
    "--set-webhook-url": "Save a Discord or ntfy webhook URL through a hidden prompt",
    "--set-smtp-password": "Enter the SMTP password privately, check it against the mail server and save it to the dotenv file",
    "--send-test-email": "Send test email to verify SMTP settings",
    "--send-test-webhook": "Send one test webhook without starting monitoring",
}

# The one-shot flags whose wording is this tool's own, since the siblings name a different service or command
LOCAL_FLAG_SENTENCES = {
    "--set-riot-api-key": "Enter the Riot API key privately, check it with Riot and save it to the dotenv file",
    "--force": "Let --generate-config replace an existing file, after a timestamped backup",
}

# The example headings, in the order the block prints them
EXAMPLE_HEADINGS = ("Getting started", "Notifications", "Match history", "Information and diagnostics")


@pytest.fixture(scope="module")
# Runs the real script once with --help and returns what a reader sees
def help_output():
    result = subprocess.run([sys.executable, str(REPO_ROOT / "lol_monitor.py"), "--help"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "120"})
    assert result.returncode == 0, result.stderr
    return result.stdout


# Verifies the shared argument groups appear in the shared order, matched as headings rather than as help text
def test_the_shared_argument_groups_appear_in_order(help_output):
    positions = [help_output.index(f"\n{title}:\n") for title in SHARED_GROUPS if f"\n{title}:\n" in help_output]

    assert len(positions) == len(SHARED_GROUPS), [title for title in SHARED_GROUPS if f"\n{title}:\n" not in help_output]
    assert positions == sorted(positions)


# Verifies the email group is named for what it holds, since a bare 'Notifications' next to it reads as the parent of both
def test_the_email_group_is_not_named_as_the_parent_of_both(help_output):
    assert "\nNotifications:\n" not in help_output.split("Examples:", 1)[0]


# Verifies all four one-shot commands sit in the files group, which is where a reader looks for them first
@pytest.mark.parametrize("flag", ["--setup", "--doctor", "--generate-config", "--set-riot-api-key", "--set-smtp-password", "--set-webhook-url"])
def test_every_one_shot_command_is_in_the_files_group(help_output, flag):
    group = help_output.split("\nConfiguration & dotenv files:\n", 1)[1].split("\n\n", 1)[0]

    assert flag in group


# Verifies each shared flag carries the shared sentence, so a reader of two of these tools sees one wording
@pytest.mark.parametrize("flag,sentence", sorted(SHARED_FLAG_SENTENCES.items()))
def test_every_shared_flag_carries_its_shared_sentence(help_output, flag, sentence):
    collapsed = re.sub(r"\s+", " ", help_output)

    assert f"{flag} {sentence}" in collapsed


# Verifies each flag this tool words for itself still says what it does, in the shape the shared sentences use
@pytest.mark.parametrize("flag,sentence", sorted(LOCAL_FLAG_SENTENCES.items()))
def test_every_local_flag_carries_its_sentence(help_output, flag, sentence):
    collapsed = re.sub(r"\s+", " ", help_output)

    assert f"{flag} {sentence}" in collapsed


# Verifies the banner is printed exactly once, since argparse exits from inside parse_args
def test_the_banner_appears_exactly_once(help_output):
    assert help_output.count(monitor.STARTUP_BANNER.splitlines()[1]) == 1


# Verifies the examples open with the one command a first-time reader can run without knowing anything
def test_the_examples_open_with_the_guided_setup(help_output):
    block = help_output.split("Examples:\n\n", 1)[1].splitlines()

    assert block[0] == "Getting started:"
    assert block[1] == "  # Guided setup, recommended for the first run"
    assert block[2].endswith("--setup")


# Verifies the example headings appear in order, so the block is grouped by task rather than listed flat
def test_the_example_headings_appear_in_order(help_output):
    block = help_output.split("Examples:\n\n", 1)[1]
    positions = [block.index(f"{title}:") for title in EXAMPLE_HEADINGS if f"{title}:" in block]

    assert len(positions) == len(EXAMPLE_HEADINGS)
    assert positions == sorted(positions)


# Verifies every example command has a comment directly above it, so no command is left unexplained
def test_every_example_command_has_a_comment_above_it(help_output):
    lines = help_output.split("Examples:\n\n", 1)[1].splitlines()
    commands = [index for index, line in enumerate(lines) if line.startswith("  ") and not line.startswith("  #") and line.strip()]

    assert commands
    for index in commands:
        assert lines[index - 1].startswith("  # "), lines[index]


# Verifies the block ends with the shared guide link and nothing after it
def test_the_examples_end_with_the_guide_link(help_output):
    assert help_output.rstrip().endswith(f"Guide: {monitor.QUICK_START_GUIDE_URL}")


# Verifies the block stays in the range that is worth reading, since a flag reference already lists every flag
def test_the_examples_stay_in_the_readable_range(help_output):
    block = help_output.split("Examples:\n\n", 1)[1]

    assert 10 <= block.count("\n  # ") <= 13


# Verifies no heading is left standing over an empty group, which reads as a missing example rather than a choice
@pytest.mark.parametrize("heading", EXAMPLE_HEADINGS)
def test_every_example_group_carries_at_least_one_command(help_output, heading):
    block = help_output.split("Examples:\n\n", 1)[1]
    group = block.split(f"{heading}:\n", 1)[1].split("\n\n", 1)[0]

    assert [line for line in group.splitlines() if line.startswith("  ") and not line.startswith("  #")]


# Verifies every example command is rendered for the install this run detected rather than hardcoded
def test_every_example_command_suits_the_install(monkeypatch):
    monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, "pip")
    rendered = monitor.help_examples()

    assert runtime_command("python3 lol_monitor.py") not in rendered
    assert rendered.count(runtime_command("\n  lol_monitor ")) == rendered.count("\n  # ")


# Verifies a note with no command is rendered as a comment rather than as a blank command line
def test_an_entry_with_no_command_is_a_note():
    rendered = monitor.render_help_examples((("Group", (("A note\nover two lines", ""),)),), "https://example.test/")

    assert rendered == "Examples:\n\nGroup:\n  # A note\n  # over two lines\n\nGuide: https://example.test/\n"
