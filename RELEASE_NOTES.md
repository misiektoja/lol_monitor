# lol_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.2 (07 May 2024)

**Features and Improvements**:

- Info about player's role & lane added to the match summary
- Info about game mode, player's role & lane added to notification emails
- Mapping of games modes have been added
- Feature to handle cases where active in-game status hangs, so we try to get historical matches in such case (by default after 1 hour)
- Updated mapping of regions
- Changed logic of checking for new matches
- Email sending function send_email() has been rewritten to detect invalid SMTP settings
- Strings have been converted to f-strings for better code visibility
- Info about CSV file name in the start screen
- Error message is displayed in the beginning if the region is not in regions_short_to_long dict or if the PUUID cannot be fetched
- print_current_match() function has been rewritten to include more info in the notification emails
- Accessing dict items via .get() to avoid errors when key is not available
- In case of getting an exception in main loop we will send the error email notification only once (until the issue is resolved)

**Bugfixes**:

- Match teams structure does not always contain correct team ids (for example for Arena game types), so we switched the method in print_match_history() function to get it from match participants structure instead (the same way as in print_current_match())
- Fix for refetching the last match in case there was an error reported by RIOT API (in such case timestamps are assigned with value of 0 and it triggered the new duplicated historical match event)

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
