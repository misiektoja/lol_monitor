# Utility Tools

The `tools/` directory holds two standalone scripts for working with the CSV match history the monitor writes. Neither one needs a Riot API key and neither one contacts Riot Games.

## CSV Format Converter

`lol_convert_csv_format.py` rewrites a CSV file from the format used by v1.7.2 and earlier into the format used by v1.8 and later.

Old columns:

`Match Start`, `Match Stop`, `Duration`, `Victory`, `Kills`, `Deaths`, `Assists`, `Champion`, `Team 1`, `Team 2`

New columns:

`Match Start`, `Match Stop`, `Duration`, `Game Mode`, `Victory`, `Kills`, `Deaths`, `Assists`, `Champion`, `Level`, `Role`, `Lane`, `Team 1`, `Team 2`

```sh
python3 tools/lol_convert_csv_format.py input.csv [-o output.csv]
```

Without `-o` the input is replaced only after the complete output has been written. Any existing output is first copied to a uniquely named `.bak` file, whose path is printed. Failed reads or writes leave the destination intact. Current-format fields are preserved, including reordered columns. Files containing both legacy and current rows with a standard header are supported. Unsupported headers or row lengths identify what needs correction before any replacement. Values the old format did not record are filled with `N/A`.

## Match History Comparison Tool

`lol_compare_csvs.py` compares two match history files and reports how likely it is that they belong to the same player. It weighs:

- Champion pool similarity
- KDA profile, mean and standard deviation
- Win rate similarity
- Average match duration
- Time-of-day playing patterns
- Teammate overlap
- Role and lane preferences
- Average champion level
- Game mode preferences
- Temporal overlap detection

```sh
python3 tools/lol_compare_csvs.py file1.csv file2.csv [--limit N] [--json] [--pretty] [--no-overlap-check] [--max-overlaps N|all]
```

| Option | Meaning |
| --- | --- |
| `--limit N` | Analyse only the first N matches of each file |
| `--json` | Print the result as JSON |
| `--pretty` | Indent the JSON output |
| `--no-overlap-check` | Skip temporal overlap analysis, which is faster and less thorough |
| `--max-overlaps N\|all` | How many temporal overlaps to display. Default 5 |

The output is a similarity score from 0 to 100 with a verdict. Use `--json` when something else has to read the result.

This script needs [pandas](https://pypi.org/project/pandas/), which the monitor itself does not:

```sh
pip install pandas
```
