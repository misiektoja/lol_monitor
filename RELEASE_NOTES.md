# lol_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.4 (24 May 2024)

**Features and Improvements**:

- **IMPROVE:** Information about log file name visible in the start screen
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime
- **IMPROVE:** Code cleanup - duration returned by print_match_history() and print_current_match() was never used in the code, so it has been removed (left-over from the Cassiopeia based code)
- **IMPROVE:** Due to recent erratic behavior of Spectator-V5 API, LOL_HANGED_INGAME_INTERVAL value has been decreased to 30 mins
- **IMPROVE:** pep8 style convention corrections

# Changes in 1.3 (15 May 2024)

**Features and Improvements**:

- **IMPROVE:** Improvements for running the code in Python under Windows
- **IMPROVE:** Updated mapping of regions & continents (region_to_continent dict)
- **IMPROVE:** Better checking for wrong command line arguments

**Bug fixes**:

- **BUGFIX:** Exception and error handling for Riot IDs in wrong format

# Changes in 1.2 (07 May 2024)

**Features and Improvements**:

- **NEW:** Info about player's role & lane added to the match summary
- **NEW:** Info about game mode, player's role & lane added to notification emails
- **NEW:** Mapping of games modes have been added
- **NEW:** Feature to handle cases where active in-game status hangs, so we try to get historical matches in such case (by default after 1 hour)
- **IMPROVE:** Updated mapping of regions
- **IMPROVE:** Changed logic of checking for new matches
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings
- **IMPROVE:** Strings have been converted to f-strings for better code visibility
- **IMPROVE:** Info about CSV file name in the start screen
- **IMPROVE:** Error message is displayed in the beginning if the region is not in regions_short_to_long dict or if the PUUID cannot be fetched
- **IMPROVE:** print_current_match() function has been rewritten to include more info in the notification emails
- **IMPROVE:** Accessing dict items via .get() to avoid errors when key is not available
- **IMPROVE:** In case of getting an exception in main loop we will send the error email notification only once (until the issue is resolved)

**Bug fixes**:

- **BUGFIX:** Match teams structure does not always contain correct team ids (for example for Arena game types), so we switched the method in print_match_history() function to get it from match participants structure instead (the same way as in print_current_match())
- **BUGFIX:** Fix for re-fetching the last match in case there was an error reported by RIOT API (in such case timestamps are assigned with value of 0 and it triggered the new duplicated historical match event)

# Changes in 1.1 (29 Apr 2024)

**Features and Improvements**:

- **NEW:** Tool has been rewritten to switch to pulsefire library as Cassiopeia still does not support recent RIOT API changes (lack for Spectator-V5 & RIOT IDs support -> calls are still based on Summoner names)
- **NEW:** Feature to handle situations when Spectator API is not available (outage); the tool will now notice it and report when new matches show up
- **NEW:** If listing mode is used (-l) together with saving to CSV file (-b), the tool will not only list recent matches, but also save it to the CSV file
- **NEW:** New parameter (--min_of_recent_matches / -m) which can be used in listing mode (-l) together with --number_of_recent_matches / -n to narrow down the range of matches to print / save

# Changes in 1.0 (23 Apr 2024)

**Features and Improvements**:

- **IMPROVE:** Showing the time passed from the last match (when the new one starts)

**Bug fixes**:

- **BUGFIX:** Fix for "object has already been loaded" issue after recent RIOT API updates
