"""Tests that every path writing a configuration file backs it up first and replaces it atomically."""

import stat
import re
import os
import sys
from pathlib import Path

import pytest

import lol_monitor as monitor


# Verifies an existing config is copied to a private timestamped backup before anything replaces it
def test_a_replaced_config_is_backed_up_first(tmp_path):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("LOL_CHECK_INTERVAL = 111\n", encoding="utf-8")

    result = monitor.write_config_file(destination, "LOL_CHECK_INTERVAL = 222\n")

    assert destination.read_text(encoding="utf-8") == "LOL_CHECK_INTERVAL = 222\n"
    assert result["backup_path"] is not None
    backup = Path(result["backup_path"])
    assert backup.read_text(encoding="utf-8") == "LOL_CHECK_INTERVAL = 111\n"
    assert backup.name.endswith(".bak")


# Verifies the backup is readable only by its owner, since a config can hold a secret the user put there
@pytest.mark.skipif(os.name != "posix", reason="file modes are only meaningful on POSIX")
def test_a_backup_is_private(tmp_path):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("LOL_CHECK_INTERVAL = 111\n", encoding="utf-8")

    result = monitor.write_config_file(destination, "LOL_CHECK_INTERVAL = 222\n")

    assert Path(result["backup_path"]).stat().st_mode & 0o777 == 0o600


# Verifies a first write takes no backup, since there is nothing to lose yet
def test_a_first_write_takes_no_backup(tmp_path):
    destination = tmp_path / "nested" / "lol_monitor.conf"

    result = monitor.write_config_file(destination, "LOL_CHECK_INTERVAL = 222\n")

    assert result["backup_path"] is None
    assert destination.read_text(encoding="utf-8") == "LOL_CHECK_INTERVAL = 222\n"


# Verifies two writes in the same second still keep both backups rather than one overwriting the other
def test_backups_in_the_same_second_do_not_collide(tmp_path):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("first\n", encoding="utf-8")

    first = monitor.write_config_file(destination, "second\n")["backup_path"]
    second = monitor.write_config_file(destination, "third\n")["backup_path"]

    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "first\n"
    assert Path(second).read_text(encoding="utf-8") == "second\n"


# Verifies a failed write leaves the original in place, since the replacement only happens once the file is complete
def test_a_failed_write_leaves_the_original(tmp_path, monkeypatch):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("LOL_CHECK_INTERVAL = 111\n", encoding="utf-8")

    def refuse(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(monitor.os, "replace", refuse)
    with pytest.raises(OSError):
        monitor.write_config_file(destination, "LOL_CHECK_INTERVAL = 222\n")

    assert destination.read_text(encoding="utf-8") == "LOL_CHECK_INTERVAL = 111\n"
    assert not [entry for entry in tmp_path.iterdir() if entry.name.endswith(".tmp")]


# Verifies a generated config over an existing file is refused outside a terminal, so a script cannot replace one silently
def test_a_generated_config_is_refused_without_a_terminal(tmp_path):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("OLD = 1\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        monitor.write_generated_config(destination, "NEW = 2\n", interactive=False)

    assert destination.read_text(encoding="utf-8") == "OLD = 1\n"


# Verifies --force replaces without asking, which is how a script does it on purpose
def test_force_replaces_without_asking(tmp_path):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("OLD = 1\n", encoding="utf-8")

    backup_path, written = monitor.write_generated_config(destination, "NEW = 2\n", force=True, interactive=False)

    assert written is True
    assert backup_path is not None
    assert destination.read_text(encoding="utf-8") == "NEW = 2\n"
    assert Path(backup_path).read_text(encoding="utf-8") == "OLD = 1\n"


# Verifies a declined prompt changes nothing, so answering no is a real answer rather than a delay
def test_a_declined_replacement_changes_nothing(tmp_path):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("OLD = 1\n", encoding="utf-8")

    backup_path, written = monitor.write_generated_config(destination, "NEW = 2\n", interactive=True, input_func=lambda _: "n")

    assert (backup_path, written) == (None, False)
    assert destination.read_text(encoding="utf-8") == "OLD = 1\n"
    assert not [entry for entry in tmp_path.iterdir() if entry.name.endswith(".bak")]


# Verifies an accepted prompt replaces the file and keeps the backup the prompt promised
def test_an_accepted_replacement_keeps_the_promised_backup(tmp_path):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("OLD = 1\n", encoding="utf-8")

    backup_path, written = monitor.write_generated_config(destination, "NEW = 2\n", interactive=True, input_func=lambda _: "y")

    assert written is True
    assert backup_path is not None
    assert destination.read_text(encoding="utf-8") == "NEW = 2\n"
    assert Path(backup_path).read_text(encoding="utf-8") == "OLD = 1\n"


# Verifies an interrupted prompt is a decline rather than a crash, since Ctrl+C at a prompt means stop
def test_an_interrupted_prompt_declines(tmp_path, capsys):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("OLD = 1\n", encoding="utf-8")

    def interrupt(_):
        raise KeyboardInterrupt

    assert monitor.write_generated_config(destination, "NEW = 2\n", interactive=True, input_func=interrupt) == (None, False)
    assert destination.read_text(encoding="utf-8") == "OLD = 1\n"
    capsys.readouterr()


# Verifies a new file the prompt never sees is written without one, so the common case stays quiet
def test_a_new_file_is_written_without_a_prompt(tmp_path):
    destination = tmp_path / "lol_monitor.conf"

    def refuse(_):
        raise AssertionError("a new file must not prompt")

    backup_path, written = monitor.write_generated_config(destination, "NEW = 2\n", interactive=True, input_func=refuse)

    assert (backup_path, written) == (None, True)
    assert destination.read_text(encoding="utf-8") == "NEW = 2\n"


# Verifies the shipped template is accepted by the parser that reads it back, so a generated config always loads
def test_the_generated_template_parses():
    content = monitor.CONFIG_BLOCK.strip("\n") + "\n"

    monitor.validate_config_content(content, "lol_monitor.conf")


# Verifies the command line path is the one that backs up, since a helper nothing calls protects nothing
def test_the_generate_config_command_uses_the_shared_writer(tmp_path, monkeypatch, capsys):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("OLD = 1\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["lol_monitor", "--generate-config", str(destination), "--force"])

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    output = capsys.readouterr().out
    assert raised.value.code == 0
    assert "Previous config backed up to:" in output
    assert "RIOT_API_KEY" in destination.read_text(encoding="utf-8")


# Verifies the command line path refuses rather than replacing when there is no terminal to ask
def test_the_generate_config_command_refuses_without_a_terminal(tmp_path, monkeypatch, capsys):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("OLD = 1\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["lol_monitor", "--generate-config", str(destination)])
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: False)

    with pytest.raises(SystemExit) as raised:
        monitor.main()

    output = capsys.readouterr().out
    assert raised.value.code == 1
    assert "already exists" in output
    assert "--force" in output
    assert destination.read_text(encoding="utf-8") == "OLD = 1\n"


# Verifies the backup name every tool in this family writes, so one documented shape covers them all
def test_the_backup_carries_the_family_name_and_mode(tmp_path, lm_module):
    destination = tmp_path / "monitor.conf"
    destination.write_text("SETTING = 1\n", encoding="utf-8")

    backup_path = lm_module.create_timestamped_backup(destination)

    assert re.fullmatch(r"monitor\.conf\.\d{14}\.bak", Path(backup_path).name)
    assert Path(backup_path).read_text(encoding="utf-8") == "SETTING = 1\n"
    assert stat.S_IMODE(Path(backup_path).stat().st_mode) == 0o600


# Verifies a second backup in the same second takes its own name rather than overwriting the first
def test_a_second_backup_in_the_same_second_keeps_the_first(tmp_path, lm_module):
    destination = tmp_path / "monitor.conf"
    destination.write_text("first\n", encoding="utf-8")
    first = lm_module.create_timestamped_backup(destination)
    destination.write_text("second\n", encoding="utf-8")

    second = lm_module.create_timestamped_backup(destination)

    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "first\n"
    assert Path(second).read_text(encoding="utf-8") == "second\n"


# Verifies a destination that is not there yet earns no backup, since there is nothing to copy
def test_a_missing_destination_earns_no_backup(tmp_path, lm_module):
    assert lm_module.create_timestamped_backup(tmp_path / "absent.conf") is None


# A parent path that is a file is a write failure, not an existing config, so the advice must not say --force
def test_a_file_in_the_way_of_the_parent_directory_is_not_an_existing_config(tmp_path):
    blocker = tmp_path / "configs"
    blocker.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(OSError) as raised:
        monitor.write_generated_config(blocker / "lol_monitor.conf", "SMTP_PORT = 587\n", interactive=False)

    assert not isinstance(raised.value, monitor.ConfigExistsError)
    assert blocker.read_text(encoding="utf-8") == "not a directory\n"


# Refusing to replace a config without a terminal is its own error, so the generate-config path can tell it apart
def test_refusing_to_replace_a_config_without_a_terminal_raises_its_own_error(tmp_path):
    destination = tmp_path / "lol_monitor.conf"
    destination.write_text("SMTP_PORT = 587\n", encoding="utf-8")

    with pytest.raises(monitor.ConfigExistsError):
        monitor.write_generated_config(destination, "SMTP_PORT = 465\n", interactive=False)

    assert destination.read_text(encoding="utf-8") == "SMTP_PORT = 587\n"
