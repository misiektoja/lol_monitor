# lol_monitor

Real-time tracker for League of Legends players' activity, with detailed match reports and instant alerts.

- **Real-time tracking** of LoL players' gaming activity, including when a match starts and when it finishes
- **Detailed match reports** covering game mode, queue and map name, game type and version, victory or defeat, kills, deaths and assists, champion, achieved level, role, lane, both team rosters with a marker on the monitored player's team, and banned champions with pick turn
- **Player profile information** including ranked statistics for Solo/Duo and Flex, and top champion mastery
- **HTML email notifications** when a player starts or finishes a match, plus a match summary and error alerts
- **Discord and ntfy webhook alerts** carrying the same events, with each channel keeping its own alert settings
- **CSV export** of every reported match with timestamps, including custom games
- **Flexible configuration** through config files, dotenv files, environment variables and command-line arguments
- Possibility to **control the running copy** of the script via signals
- **Utility tools** for CSV format conversion and match history comparison
- **Functional, procedural Python** (minimal OOP)

## Get started

1. [Install it](installation.md)
2. [Set it up and run it for the first time](setup-and-first-run.md)
3. [Tune the configuration](configuration.md)

If something does not work, [Troubleshooting](troubleshooting.md) covers the failures that come up most often.

## Screenshots

![lol_monitor](https://raw.githubusercontent.com/misiektoja/lol_monitor/main/assets/lol_monitor.png)
