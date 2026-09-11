"""Tests for lossless CSV migration and failed output writes."""

import csv
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.lol_convert_csv_format import NEW_COLUMNS, OLD_COLUMNS, convert_csv_file


# Writes an input table with the given column order and values
def write_table(path, columns, values):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerow(values)


# Preserves all current fields even when a user rearranged the columns
@pytest.mark.parametrize("columns", [NEW_COLUMNS, list(reversed(NEW_COLUMNS)), OLD_COLUMNS])
def test_conversion_preserves_populated_fields(tmp_path, columns):
    path = tmp_path / "history.csv"
    original = {key: f"value for {key}" for key in columns}
    write_table(path, columns, [original[key] for key in columns])
    before = path.read_bytes()
    convert_csv_file(path)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows == [{key: original.get(key, "N/A") for key in NEW_COLUMNS}]
    assert [backup.read_bytes() for backup in tmp_path.glob("*.bak")] == [before]


# Keeps malformed tables intact and names the repair instead of guessing the missing columns
@pytest.mark.parametrize("content", ["", ",".join(OLD_COLUMNS) + "\nshort,row\n", "Unknown,Header\n1,2\n"])
def test_malformed_conversion_does_not_replace_history(tmp_path, capsys, content):
    path = tmp_path / "history.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as stopped:
        convert_csv_file(path)
    assert stopped.value.code == 1
    assert path.read_text(encoding="utf-8") == content
    assert "destination was not replaced" in capsys.readouterr().out


# Uses a real operating system write limit to prove an in-place conversion cannot truncate its input
@pytest.mark.skipif(os.name != "posix", reason="RLIMIT_FSIZE is a POSIX limit")
def test_write_failure_preserves_original_bytes(tmp_path):
    path = tmp_path / "history.csv"
    write_table(path, OLD_COLUMNS, ["preserved history"] * len(OLD_COLUMNS))
    before = path.read_bytes()
    script = "import resource, signal, sys; from tools.lol_convert_csv_format import convert_csv_file; signal.signal(signal.SIGXFSZ, signal.SIG_IGN); resource.setrlimit(resource.RLIMIT_FSIZE, (24, 24)); convert_csv_file(sys.argv[1])"
    result = subprocess.run([sys.executable, "-c", script, str(path)], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert result.returncode == 1
    assert "destination was not replaced" in result.stdout
    assert path.read_bytes() == before


# Keeps a separate destination's earlier contents recoverable when replacing it with fewer rows
def test_existing_output_has_a_complete_backup(tmp_path):
    source, destination = tmp_path / "old.csv", tmp_path / "current.csv"
    write_table(source, OLD_COLUMNS, ["one"] * len(OLD_COLUMNS))
    destination.write_text("longer accumulated history\n" * 10, encoding="utf-8")
    before = destination.read_bytes()
    convert_csv_file(source, destination)
    backups = list(tmp_path.glob("current.csv.*.bak"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == before
    assert len(list(csv.DictReader(io.StringIO(destination.read_text(encoding="utf-8"))))) == 1


# Preserves mixed rows written before and after the schema gained match details
def test_mixed_old_and_current_rows_are_preserved(tmp_path):
    path = tmp_path / "history.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(OLD_COLUMNS)
        writer.writerow(["old"] * len(OLD_COLUMNS))
        writer.writerow(["current"] * len(NEW_COLUMNS))
    convert_csv_file(path)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0] == {key: "old" if key in OLD_COLUMNS else "N/A" for key in NEW_COLUMNS}
    assert rows[1] == dict.fromkeys(NEW_COLUMNS, "current")
