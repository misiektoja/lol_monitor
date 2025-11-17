#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.0

Script to convert old lol_monitor CSV format (used by <=v1.7.2) to new CSV format (used by >=v1.8).

Old format:
"Match Start","Match Stop","Duration","Victory","Kills","Deaths","Assists","Champion","Team 1","Team 2"

New format:
"Match Start","Match Stop","Duration","Game Mode","Victory","Kills","Deaths","Assists","Champion","Level","Role","Lane","Team 1","Team 2"

Missing values are filled with "N/A".
"""

import csv
import sys
import argparse
from pathlib import Path


# Convert CSV file from old format to new format
def convert_csv_file(input_file, output_file=None):
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)

    if output_file is None:
        output_file = input_file
    else:
        output_path = Path(output_file)
        if output_path.exists() and output_path.samefile(input_path):
            print("Error: Output file cannot be the same as input file when specified explicitly.")
            sys.exit(1)

    # Old column order
    old_columns = ['Match Start', 'Match Stop', 'Duration', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Team 1', 'Team 2']

    # New column order
    new_columns = ['Match Start', 'Match Stop', 'Duration', 'Game Mode', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Level', 'Role', 'Lane', 'Team 1', 'Team 2']

    rows = []

    try:
        with open(input_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)

            header_row = next(reader, None)
            if header_row is None:
                print("Error: CSV file is empty or has no header.")
                sys.exit(1)

            # Normalize header
            header_normalized = [col.strip().strip('"').strip("'") for col in header_row]

            # Determine if we're reading old format (10 columns) or new format (14 columns)
            # Check by counting actual data columns vs header columns
            is_old_format = len(header_normalized) == len(old_columns) and all(col in header_normalized for col in old_columns)

            # If header has new columns but data rows might be old format, we'll detect by row length
            # Read first data row to check
            first_data_row = next(reader, None)
            if first_data_row is None:
                print("Error: CSV file has no data rows.")
                sys.exit(1)

            # Check if first row has old format (10 values) or new format (14 values)
            actual_old_format = len(first_data_row) == len(old_columns)

            # Reset file and skip header
            f.seek(0)
            reader = csv.reader(f)
            next(reader)  # Skip header

            for row in reader:
                new_row = {}

                # If row has old format (10 values), map them positionally
                if len(row) == len(old_columns):
                    # Map old format values by position
                    for i, old_col in enumerate(old_columns):
                        if i < len(row):
                            value = row[i]
                        else:
                            value = ""

                        # Preserve data types
                        if old_col in ['Kills', 'Deaths', 'Assists']:
                            try:
                                if value == "" or value is None:
                                    value = "N/A"
                                else:
                                    value = int(value)
                            except (ValueError, TypeError):
                                value = "N/A"
                        elif old_col == 'Victory':
                            # Convert to "Yes" or "No" string format, or "N/A" if empty
                            if value == "" or value is None:
                                value = "N/A"
                            elif isinstance(value, bool):
                                value = "Yes" if value else "No"
                            elif isinstance(value, str):
                                value_lower = value.lower().strip()
                                if value_lower in ('true', '1', 'yes'):
                                    value = "Yes"
                                elif value_lower in ('false', '0', 'no'):
                                    value = "No"
                                else:
                                    value = "N/A"
                            else:
                                value = "Yes" if bool(value) else "No"
                        else:
                            if value is None:
                                value = ""
                            else:
                                value = str(value)

                        new_row[old_col] = value
                else:
                    # Row already has new format or unexpected format - try to map by header
                    # This shouldn't happen for old format files, but handle it gracefully
                    for i, col in enumerate(new_columns):
                        if i < len(row):
                            value = row[i]
                        else:
                            value = ""

                        # Preserve data types
                        if col in ['Kills', 'Deaths', 'Assists']:
                            try:
                                if value == "" or value is None:
                                    value = "N/A"
                                else:
                                    value = int(value)
                            except (ValueError, TypeError):
                                value = "N/A"
                        elif col == 'Victory':
                            # Convert to "Yes" or "No" string format, or "N/A" if empty
                            if value == "" or value is None:
                                value = "N/A"
                            elif isinstance(value, bool):
                                value = "Yes" if value else "No"
                            elif isinstance(value, str):
                                value_lower = value.lower().strip()
                                if value_lower in ('true', '1', 'yes'):
                                    value = "Yes"
                                elif value_lower in ('false', '0', 'no'):
                                    value = "No"
                                else:
                                    value = "N/A"
                            else:
                                value = "Yes" if bool(value) else "No"
                        else:
                            if value is None:
                                value = ""
                            else:
                                value = str(value)

                        new_row[col] = value

                # Now build the final row in new column order, inserting new columns
                final_row = {}
                for col in new_columns:
                    if col == 'Game Mode':
                        final_row[col] = "N/A"
                    elif col in ['Level', 'Role', 'Lane']:
                        final_row[col] = "N/A"
                    else:
                        # Get value from new_row (which has old format values)
                        value = new_row.get(col, "")
                        final_row[col] = value

                rows.append(final_row)

    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=new_columns, quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Successfully converted {len(rows)} rows from '{input_file}' to '{output_file}'")

    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Convert CSV files from old format to new format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Old format columns:
  "Match Start","Match Stop","Duration","Victory","Kills","Deaths","Assists","Champion","Team 1","Team 2"

New format columns:
  "Match Start","Match Stop","Duration","Game Mode","Victory","Kills","Deaths","Assists","Champion","Level","Role","Lane","Team 1","Team 2"

Missing values are filled with "N/A".
        """
    )
    parser.add_argument('input_file', help='Input CSV file to convert')
    parser.add_argument('-o', '--output', dest='output_file', default=None, help='Output CSV file (default: overwrites input file)')

    args = parser.parse_args()

    convert_csv_file(args.input_file, args.output_file)


if __name__ == '__main__':
    main()
