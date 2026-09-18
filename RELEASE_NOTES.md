# lol_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 1.9.1 (TBD)

Version **1.9.1** reports an alert channel that still holds the values from the sample configuration as unset, instead of naming a mail server and a recipient no alert could reach.

**Bug fixes**:

- **BUGFIX:** **Unset alert channels are reported as unset** - The verbose startup summary read the values the sample configuration ships as a real destination, so a run that had never been given a mail server printed **`Email transport: your_smtp_server_ssl:587`**, a recipient of **`your_receiver_email`** and a webhook provider of **`Discord`**. Those rows now read **`Not configured`** and the channel rollup above them reads **`Off (not configured)`** rather than naming alert types nothing could deliver

# Changes in 1.9 (18 Sep 2026)

Version **1.9** adds **guided setup**, a read-only **Doctor preflight check**, **Discord and ntfy alerts** and **private credential entry**. **Coloured output**, startup summaries and verbose/debug modes make monitoring easier to follow. Alerts can include **champion artwork**, match checks recover from failures and CSV conversion preserves history. Configuration and credentials are protected and release downloads can be verified.

**Features and improvements**:

- **NEW:** **Guided setup** - `--setup` wizard collects the Riot ID, region, intervals, credentials, notifications and output files. Review or edit answers before saving and confirm replacements. Reruns preserve saved settings and move retained credentials to the private dotenv file. A first run without a saved target offers setup
- **NEW:** **Saved player and region** - Set `RIOT_ID` and `REGION` to start monitoring without arguments. Command-line targets override saved values. Region codes accept either case and spaces around `#` are ignored
- **NEW:** **Doctor preflight check** - `--doctor` checks configuration, Riot access, the monitored account, notifications and output destinations with suggested fixes. It writes no files and sends test notifications only after confirmation
- **NEW:** **Discord and ntfy alerts** - Choose player status and error alerts independently of email. Save the destination with `--set-webhook-url` and check delivery with `--send-test-webhook`. Protected ntfy topics are supported
- **NEW:** **Champion artwork and clearer rosters** - Enable `EMAIL_IMAGES` or `NTFY_IMAGES` for champion icons in in-game and match-summary alerts. Both are off by default and need no extra package. Discord shows champion thumbnails. Terminal and Discord rosters highlight the monitored player in bold
- **NEW:** **Private credential entry** - `--set-riot-api-key` and `--set-smtp-password` validate credentials before saving to the dotenv file. Entry is hidden and the mail check sends no message. Webhook setup validates the URL without contacting the service
- **NEW:** **Clearer output and diagnostics** - Coloured output and a short startup summary show the active settings. `--verbose` adds operational updates and `--debug` adds technical traces. Secrets are redacted and logs retain the full summary. `--truncate N` limits screen width while logs retain full lines. It works without `wcwidth`, which improves Unicode width measurements
- **IMPROVE:** **Clearer errors and recovery** - Temporary failures get one short retry before appearing on screen. `--verbose` still reports the first failure. Persistent outages produce hourly reminders and recovery notices. Enabled error alerts cover network and Riot outages after five minutes, while rejected credentials alert immediately. Failed channels retry without repeating successful deliveries
- **IMPROVE:** **Discord alerts match the email** - Discord now receives the same emphasis as the HTML email, with bold values and clickable links instead of plain text. ntfy keeps the plain body, since it would show the markers literally
- **IMPROVE:** **Documentation and verifiable downloads** - A [searchable guide](https://misiektoja.github.io/lol_monitor/) covers setup, usage and troubleshooting. Releases include checksums and signed build attestations

**Bug fixes**:

- **BUGFIX:** **Reliable match checks** - Failed checks preserve the previous player state. Temporarily unavailable match details are retried instead of permanently skipped. Accounts without matches show an empty history instead of a failure warning
- **BUGFIX:** **Protected CSV conversion** - The converter preserves current fields in mixed old/new files, backs up existing output and replaces it atomically
- **BUGFIX:** **Safer configuration loading** - Configuration files are read as settings instead of executed as Python. Plain values and references to other settings still work. Replace imports, function calls and calculations with plain settings
- **BUGFIX:** **Safer configuration and secret updates** - `--generate-config FILE` confirms replacement and creates a backup. Non-interactive replacement requires `--force`. Shell redirection with `>` bypasses these protections. Exported secrets work without a dotenv file. Command-line credentials and nonempty startup exports retain priority after `SIGHUP`. Change those values and restart to replace them. Reloads apply changed or removed file-owned secrets
- **BUGFIX:** **Safer email delivery** - Mail-server rejection messages redact credentials. Emails accepted by the mail server no longer become false failures if closing the connection fails, avoiding duplicate retries
- **BUGFIX:** **Reliable startup settings** - Invalid timing and unreadable dotenv files include repair guidance. Configured connectivity settings apply and redirected output avoids terminal-clearing errors

Smaller fixes and development changes are listed in the [full change history](https://github.com/misiektoja/lol_monitor/compare/v1.8.2...v1.9).

# Changes in 1.8.2 (04 Aug 2026)

**Bug fixes**:

- **BUGFIX:** Fixed indentation of ASCII log separators in summary screen

# Changes in 1.8.1 (04 Aug 2026)

Version **1.8.1** makes logs and configuration files more portable, adds downloadable release archives and handles incomplete Riot and comparison data more safely.

**Features and Improvements**:

- **IMPROVE:** **Consistent log alignment** - Tabs are expanded to spaces when saved to log files so columns stay aligned in viewers that render tabs differently. Terminal output is unchanged
- **IMPROVE:** **Portable log separators** - The new `ASCII_LOG_SEPARATORS` setting controls whether separator-only lines saved to log files use ASCII hyphens. `"Auto"` enables them on Windows by default, `"On"` enables them on every operating system and `"Off"` preserves Unicode separators. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.
- **IMPROVE:** **UTF-8 configuration generation** - `lol_monitor --generate-config FILENAME` now writes the template directly to the specified file as UTF-8. In Windows PowerShell, it should be used instead of output redirection to avoid UTF-16 files and `null bytes` errors
- **IMPROVE:** **Downloadable release archives** - Published GitHub Releases now receive automatically built zip and tar.gz source archives

**Bug fixes**:

- **BUGFIX:** **Safer Riot and CSV data handling** - Missing game modes and ranked fields now use stable fallback values while the CSV comparison utility handles missing or mixed report values consistently

# Changes in 1.8 (13 Dec 2025)

**Features and Improvements**:

- **NEW:** Implemented HTML formatting for email notifications for better readability
- **NEW:** Added star marker (⭐) to indicate monitored user's team in match reports
- **NEW:** Enhanced game information retrieval with comprehensive mappings for game queues, maps and game types
- **NEW:** Expanded summoner details retrieval with ranked information (Solo/Duo and Flex) and champion mastery functions
- **NEW:** Enhanced CSV logging with additional fields: Level, Role, Lane and Game Mode
- **NEW:** Support for custom game snapshots with automatic CSV saving for matches that don't appear in match history
- **NEW:** Fallback save mechanism for custom game matches if no completion appears within 5 minutes
- **NEW:** Utility tool for converting old CSV format (v1.7.2 and earlier) to new format with additional fields
- **NEW:** LoL Match History Comparison Tool for analyzing player similarities based on match data with multiple metrics
- **IMPROVE:** Enhanced match processing with caching support and improved error handling for forbidden matches
- **IMPROVE:** Optimized match history fetching by removing buffer and implementing incremental fetching for accessibility checks
- **IMPROVE:** Implemented pagination for fetching match IDs and added total match count retrieval
- **IMPROVE:** Refactored match handling to support any custom game snapshots

**Bug fixes**:

- **BUGFIX:** Use real match start timestamp from Spectator snapshot for custom game CSV entries
- **BUGFIX:** Prevent false 'stopped playing' messages when start was never confirmed
- **BUGFIX:** Update default values for kills, deaths and assists to 'N/A' in CSV match logging
- **BUGFIX:** Removed fetching of summoner id and account id due to Riot API changes

# Changes in 1.7.2 (13 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Fixed config file generation to work reliably on Windows systems

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
