# Usage

<a id="command-format-by-installation-method"></a>
## Command Format by Installation Method

Examples use the PyPI command. For a downloaded script, run commands from the directory containing `lol_monitor.py` and keep the same arguments:

| Installation | Command |
| --- | --- |
| PyPI or pipx | `lol_monitor [OPTIONS]` |
| Manual script on macOS or Linux | `python3 lol_monitor.py [OPTIONS]` |
| Manual script on Windows | `python lol_monitor.py [OPTIONS]` |

For example, `lol_monitor --setup` becomes `python3 lol_monitor.py --setup` on macOS or Linux. Use `python` on Windows. Replace placeholders such as `"<riot_id>" <region>` with a Riot ID such as "Player#TAG" plus a region code such as euw1.

Activate the tool's virtual environment before running these commands. For a downloaded script, run them from the directory containing `lol_monitor.py`.

For first-time configuration, follow [Setup & First Run](setup-and-first-run.md). Use [Doctor Preflight](troubleshooting.md#doctor-preflight) to check a setup before monitoring.

<a id="monitoring-mode"></a>
## Monitoring Mode

Pass the player's Riot ID and region and the tool watches them until you stop it:

```sh
lol_monitor <riot_id> <region>
```

If you have not stored the `RIOT_API_KEY` secret yet, pass it with `-r`:

```sh
lol_monitor <riot_id> <region> -r "your_riot_api_key"
```

A Riot ID is the game name plus the tag line, written as `riot_id_name#tag`. The region is the short code from [Region Codes](setup-and-first-run.md#region-codes).

The tool runs until interrupted with `Ctrl+C`. Use `tmux` or `screen` if you want it to survive a closed terminal.

To watch several players, run several copies.

Output is saved to `lol_monitor_<riot_id_name>.log`. Change the name with `LOL_LOGFILE` or switch the file off with `DISABLE_LOGGING` or `-d`.

<a id="terminal-output"></a>
## Terminal Output

Use `--help` for examples grouped by task and matched to your installation.

Monitoring mode prints the settings that are actually in effect before the first check.

Optional features appear once you switch them on.

Use `--verbose` or `--debug` for the full startup summary, including output paths, notification settings, secret sources and runtime information.

Use `--truncate N` or `TRUNCATE_CHARS` to limit screen line width. Set it to `999` to detect the terminal width automatically. Truncation does not change log files and is ignored when logging is disabled with `-d`.

The tool clears the terminal when monitoring starts. Set `CLEAR_SCREEN` to `False` to keep whatever is already on the screen.

The screen is never cleared when output is redirected to a file or a pipe, in debug mode, or for a command that prints a result and exits, such as `--doctor`, `--help` and the test senders.

Two settings add detail to what a run prints. `VERBOSE_MODE` adds the decisions the run made and `DEBUG_MODE` adds timestamped technical traces. Both are off by default, both are independent of each other and both have a flag that wins over the file, `--verbose` and `--debug`. `DELIVERY_CONFIRMATIONS` is on by default and controls whether verbose mode confirms each delivered email and webhook alert. See [Verbose and Debug Output](troubleshooting.md#verbose-and-debug-output).

<a id="coloured-terminal-output"></a>
### Coloured Terminal Output

LoL Monitor colours live terminal output and help by default. Saved log files stay plain text.

Turn colour off for one run with `--no-color` or permanently with `COLORED_OUTPUT = False`. Colour is also disabled for redirected output, `NO_COLOR` or an unsupported terminal. See [Terminal Colours](configuration.md#terminal-colours) for details.

Override individual colours with `COLOR_THEME`. It is merged over the built-in theme, so you only name the parts you want to change:

```ini
COLOR_THEME = { "champion": "bright_magenta bold", "username": "green" }
```

See [Terminal Colours](configuration.md#terminal-colours) for the accepted colour and style names.

<a id="listing-mode"></a>
## Listing Mode

`-l` prints the player's recent matches and exits instead of monitoring. `-n` sets how many, defaulting to the last 2:

```sh
lol_monitor <riot_id> <region> -l -n 25
```

`-m` sets the lowest match index, so a range is `-m` plus `-n`. This lists matches 20 through 50:

```sh
lol_monitor <riot_id> <region> -l -m 20 -n 50
```

`-a` fetches every match available rather than a fixed count.

Adding `-b` with a filename saves the listed matches to CSV as well as printing them:

```sh
lol_monitor <riot_id> <region> -l -m 5 -n 10 -b lol_games_riot_id_name.csv
```

<a id="email-notifications"></a>
## Email Notifications

To get mail when the player's status changes, set `STATUS_NOTIFICATION` to `True` or pass `-s`:

```sh
lol_monitor <riot_id> <region> -s
```

Mail on errors is on by default. Switch it off with `ERROR_NOTIFICATION = False` or `-e`:

```sh
lol_monitor <riot_id> <region> -e
```

Fill in the [SMTP settings](configuration.md#smtp-settings) first, otherwise nothing is sent. `--doctor` signs in to the mail server without sending anything and reports which alerts would be delivered, described in [Doctor Preflight](troubleshooting.md#doctor-preflight).

Messages go out in both plain text and HTML, so match details stay readable in any mail client. In the HTML body the monitored player's own roster line is bold, and `EMAIL_IMAGES = True` adds the champion icon at the end of the message, described under [Champion Icon in Email](configuration.md#champion-icon-in-email).

Example email:

![lol_monitor email notification](https://raw.githubusercontent.com/misiektoja/lol_monitor/main/assets/lol_monitor_email_notifications.png)

<a id="webhook-notifications"></a>
## Webhook Notifications

The same alerts can go to a Discord channel or an ntfy topic. Point the tool at a destination and switch the channel on:

```sh
lol_monitor <riot_id> <region> --webhook --webhook-status
```

`--webhook-status` sends an alert when the player's status changes and `--webhook-errors` sends one on monitoring errors. Either flag switches the channel on by itself, so the shortest form is one flag. `--no-webhook` switches the whole channel off for one run and `--no-webhook-error-notify` silences only the error alert.

Save the destination once with `--set-webhook-url` rather than passing it on every run, since a URL on the command line stays in your shell history. `--webhook-url` is there for a one-off run.

Email and webhooks are independent. A run can use one, both or neither, and each keeps its own alert settings.

Each service shows the alert the way it renders best. Discord gets the champion icon as the embed thumbnail and the monitored player's roster line in bold, while ntfy gets the plain roster and, with `NTFY_IMAGES = True`, the icon as the notification image.

Check the setup by sending one real notification:

```sh
lol_monitor --send-test-webhook
```

`--doctor` reports whether the destination, the headers and the alert choices are usable without contacting the service, then offers to send one real notification after a separate confirmation.

The settings behind all of this are covered under [Webhook Settings](configuration.md#webhook-settings).

<a id="csv-export"></a>
## CSV Export

Set `CSV_FILE` or pass `-b` to append every reported match to a CSV file:

```sh
lol_monitor <riot_id> <region> -b lol_games_riot_id_name.csv
```

The file is created if it does not exist. Columns:

- `Match Start`, `Match Stop`, `Duration`
- `Game Mode`, for example `CLASSIC`, `ARAM` or `URF`
- `Victory`, win or loss
- `Kills`, `Deaths`, `Assists`
- `Champion`
- `Level`, the champion level reached
- `Role`, for example `DUO_CARRY` or `JUNGLE`
- `Lane`, for example `TOP`, `MIDDLE` or `BOTTOM`
- `Team 1`, `Team 2`, the team rosters

Files written by v1.7.2 or earlier use the older column set. The [CSV format converter](tools.md#csv-format-converter) rewrites them.

<a id="check-intervals"></a>
## Check Intervals

If you want to customize the polling intervals, use the `-k` and `-c` flags (or the corresponding configuration options):

```sh
lol_monitor <riot_id> <region> -k 60 -c 120
```

* `LOL_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the player is in a game (seconds)
* `LOL_CHECK_INTERVAL`, `-c`: check interval when the player is not in a game (seconds)

`CHECK_INTERNET_TIMEOUT` sets the seconds allowed for the startup connectivity check (default: 5).

Riot's development key allows 100 requests every two minutes, and each check while the player is in a game spends several of them. `--doctor` warns when `LOL_ACTIVE_CHECK_INTERVAL` drops below 10 seconds, which is where the extra calls a live match report makes stop fitting.

<a id="liveness-reminder"></a>
### Liveness Reminder

While nothing changes, the tool prints one reminder that it is still running:

```
* Monitoring healthy for <riot_id>. The user is not in a match with no match change since the last check
Liveness check, timestamp:	Mon 08 Sep 2026, 09:15:05
```

The reminder is timed in seconds, so it arrives at the same rate whichever check interval is in use. Set `LIVENESS_CHECK_INTERVAL` to change it (default: 86400, i.e. 24 hours), or to 0 to switch it off.

Anything the tool prints about the target restarts the countdown, so a busy run stays quiet.

<a id="signal-controls-macoslinuxunix"></a>
## Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when the player's status changes (`-s`) |
| TRAP | Increase the in-game check interval by `LOL_ACTIVE_CHECK_SIGNAL_VALUE` seconds |
| ABRT | Decrease the in-game check interval by `LOL_ACTIVE_CHECK_SIGNAL_VALUE` seconds |
| HUP | Reload secrets from the dotenv file, reporting each one that changed |

`SIGHUP` keeps command-line credentials and nonempty environment values exported before startup. Change those values and restart to replace them.

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "lol_monitor <riot_id> <region>"
```

A reload names each secret it replaced and how it looks, never its value:

```
* Reloaded RIOT_API_KEY from .env (set, 42 chars)
* Reloaded SMTP_PASSWORD from .env (set)
```

A Riot API key is always 42 characters, so a shorter one means the paste was cut. A password you chose reports presence only, since its length is a real disclosure.

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
## Coloring Log Output with GRC

[GRC](https://github.com/garabik/grc) can colour the log file.

The bundled recipe follows the same colours as the live output. It also covers the other monitors in the family, so one copy in `~/.grc/` colours every tool's logs.

Add this to your GRC config at `~/.grc/grc.conf`:

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Copy [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/grc/conf.monitor_logs) to `~/.grc/` and the log reads in colour:

```sh
grc tail -F -n 100 lol_monitor_<riot_id_name>.log
```
