#!/usr/bin/env python3
"""Convert legacy LoL match CSV files while preserving existing fields and history."""

import argparse
import csv
import os
import shutil
import tempfile
from pathlib import Path


OLD_COLUMNS = ['Match Start', 'Match Stop', 'Duration', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Team 1', 'Team 2']
NEW_COLUMNS = ['Match Start', 'Match Stop', 'Duration', 'Game Mode', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Level', 'Role', 'Lane', 'Team 1', 'Team 2']


# Converts known CSV schemas without discarding columns or replacing history before the write completes
def convert_csv_file(input_file, output_file=None):
    input_path = Path(input_file).expanduser().resolve()
    output_path = Path(output_file).expanduser().resolve() if output_file is not None else input_path
    if output_file is not None and output_path == input_path:
        print("Error: Output file cannot be the same as input file when specified explicitly.")
        raise SystemExit(1)
    temporary_path = None
    try:
        with input_path.open("r", newline="", encoding="utf-8-sig") as source:
            reader = csv.reader(source, strict=True)
            header = next(reader, None)
            if not header:
                raise ValueError("CSV file is empty or has no header")
            header = [name.strip() for name in header]
            if len(set(header)) != len(header) or set(header) not in (set(OLD_COLUMNS), set(NEW_COLUMNS)):
                raise ValueError("Header must contain the legacy 10 columns or current 14 columns exactly once. Keep additional columns in a separate file")
            rows = []
            for row in reader:
                if not row:
                    continue
                row_columns = header
                # Earlier monitors appended new rows to files whose header still described the old schema
                if len(row) != len(header) and header in (OLD_COLUMNS, NEW_COLUMNS) and len(row) in (len(OLD_COLUMNS), len(NEW_COLUMNS)):
                    row_columns = OLD_COLUMNS if len(row) == len(OLD_COLUMNS) else NEW_COLUMNS
                if len(row) != len(row_columns):
                    raise ValueError(f"CSV row ending at line {reader.line_num} has {len(row)} fields, expected {len(header)}. Correct the row before converting")
                values = dict(zip(row_columns, row, strict=True))
                if len(row_columns) == len(OLD_COLUMNS):
                    victory = values["Victory"].strip().casefold()
                    if victory in ("true", "1", "yes"):
                        values["Victory"] = "Yes"
                    elif victory in ("false", "0", "no"):
                        values["Victory"] = "No"
                rows.append({name: values.get(name, "N/A") for name in NEW_COLUMNS})
            if not rows:
                raise ValueError("CSV file has no data rows")
        with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8", dir=output_path.parent, prefix=output_path.name + ".", suffix=".tmp", delete=False) as target:
            temporary_path = Path(target.name)
            writer = csv.DictWriter(target, fieldnames=NEW_COLUMNS, quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()
            writer.writerows(rows)
            target.flush()
            os.fsync(target.fileno())
        if output_path.exists():
            os.chmod(temporary_path, output_path.stat().st_mode & 0o777)
            with output_path.open("rb") as original, tempfile.NamedTemporaryFile(mode="wb", dir=output_path.parent, prefix=output_path.name + ".", suffix=".bak", delete=False) as backup:
                shutil.copyfileobj(original, backup)
                backup.flush()
                os.fsync(backup.fileno())
                print(f"Original output saved to backup: {backup.name}")
        os.replace(temporary_path, output_path)
        temporary_path = None
        print(f"Successfully converted {len(rows)} rows from '{input_file}' to '{output_path}'")
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"Error converting CSV: {exc}. The destination was not replaced.")
        raise SystemExit(1) from None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


# Parses the conversion paths and runs the checked conversion
def main():
    parser = argparse.ArgumentParser(description="Convert legacy LoL match CSV files to the current 14-column schema")
    parser.add_argument("input_file", help="Input CSV file to convert")
    parser.add_argument("-o", "--output", dest="output_file", default=None, help="Output CSV file (default: atomically replaces input after keeping a backup)")
    args = parser.parse_args()
    convert_csv_file(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
