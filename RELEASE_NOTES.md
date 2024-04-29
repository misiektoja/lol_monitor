# lol_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.1 (29 Apr 2024)

**Features and Improvements**:

- Tool has been rewritten to switch to pulsefire library as Cassiopeia still does not support recent RIOT API changes (lack for Spectator-V5 & RIOT IDs support -> calls are still based on Summoner names)
- New feature to handle situations when Spectator API is not available (outage); the tool will now notice it and report when new matches show up
- If listing mode is used (-l) together with saving to CSV file (-b), the tool will not only list recent matches, but also save it to the CSV file
- New parametr (--min_of_recent_matches / -m) which can be used in listing mode (-l) together with --number_of_recent_matches / -n to narrow down the range of matches to print / save

# Changes in 1.0 (23 Apr 2024)

**Features and Improvements**:

- Support for showing the time passed from the last match (when the new one starts)

**Bugfixes**:

- Fix for "object has already been loaded" issue after recent RIOT API updates
