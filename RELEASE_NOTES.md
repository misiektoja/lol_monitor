# lol_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.7.1 (09 Jun 2025)

**Features and Improvements**:

- **IMPROVE:** Tweaked printed message and added missing timestamp output

# Changes in 1.7 (26 May 2025)

**Features and Improvements**:

- **NEW:** Overhauled the core logic to detect new matches using unique match IDs instead of fragile timestamp-based mechanism, increasing reliability and robustness
- **NEW:** Email notifications for finished forbidden matches (requiring RSO token)
- **IMPROVE:** The new ID-based system better handles "forbidden" matches that previously lacked timestamp data
- **IMPROVE:** Better handling of "stuck" in-game status

# Changes in 1.6 (22 May 2025)

**Features and Improvements**:

- **NEW:** The tool can now be installed via pip: `pip install lol_monitor`
- **NEW:** Added support for external config files, environment-based secrets and dotenv integration with auto-discovery
- **IMPROVE:** Updated and centralized region-to-continent mapping in the config section to reflect latest Riot infrastructure changes
- **IMPROVE:** Enhanced startup summary to show loaded config and dotenv file paths
- **IMPROVE:** Simplified and renamed command-line arguments for improved usability
- **NEW:** Implemented SIGHUP handler for dynamic reload of secrets from dotenv files
- **IMPROVE:** Added configuration option to control clearing the terminal screen at startup
- **IMPROVE:** Changed connectivity check to use Riot API endpoint for reliability
- **IMPROVE:** Added check for missing pip dependencies with install guidance
- **IMPROVE:** Allow disabling liveness check by setting interval to 0 (default changed to 12h)
- **IMPROVE:** Improved handling of log file creation
- **IMPROVE:** Refactored CSV file initialization and processing
- **IMPROVE:** Added support for `~` path expansion across all file paths
- **IMPROVE:** Refactored code structure to support packaging for PyPI
- **IMPROVE:** Enforced configuration option precedence: code defaults < config file < env vars < CLI flags
- **IMPROVE:** Updated horizontal line for improved output aesthetics
- **IMPROVE:** Email notifications now auto-disable if SMTP config is invalid
- **IMPROVE:** Removed short option for `--send-test-email` to avoid ambiguity

**Bug fixes**:

- **BUGFIX:** Fixed handling of forbidden match entries that require RSO token

# Changes in 1.5 (17 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new parameter (**-z** / **--send_test_email_notification**) which allows to send test email notification to verify SMTP settings defined in the script
- **IMPROVE:** Support for float type of timestamps added in date/time related functions
- **IMPROVE:** Function get_short_date_from_ts() rewritten to display year if show_year == True and current year is different, also can omit displaying hour and minutes if show_hours == False
- **IMPROVE:** Checking if correct version of Python (>=3.12) is installed
- **IMPROVE:** Possibility to define email sending timeout (default set to 15 secs)

**Bug fixes**:

- **BUGFIX:** Fixed "SyntaxError: f-string: unmatched (" issue in older Python versions
- **BUGFIX:** Fixed "SyntaxError: f-string expression part cannot include a backslash" issue in older Python versions

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
