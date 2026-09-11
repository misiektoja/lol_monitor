# Usage

<a id="command-format"></a>
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

## Starting Point

Run the tool with no arguments to see the commands worth starting from and to be offered the [guided setup](setup-and-first-run.md#guided-setup):

```sh
lol_monitor
```

If the configuration file already names a player in `RIOT_ID` and `REGION`, the same bare command starts monitoring them instead.

`--help` lists every flag, grouped by what it configures, and ends with worked examples for the common tasks:

```sh
lol_monitor --help
```

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

## Startup Summary

Every run opens with the settings that are actually in effect, one per line:

```
* Target:                       Faker#KR1 (kr)
* Polling intervals:            [NOT in game: 2 minutes, 30 seconds] [in game: 45 seconds]
* Notifications (email):        On (status changes, errors)
* Output:                       lol_monitor_Faker.log
* Config:                       lol_monitor.conf
* Dotenv:                       .env
* Liveness output:              12 hours
* CSV output:                   matches.csv
* More details:                 use --verbose or --debug
```

The short view names the target, where alerts go, where output goes and each optional feature that is switched on. A feature that is off is left out, apart from TLS verification, which appears while it is **off**.

Use `--verbose` or `--debug` for the full startup summary, including region routing, notification settings, secret sources and runtime information. The log file always keeps the full summary.

Each channel's own settings are indented under it, so the mail rows and the webhook rows read as one block rather than as separate entries.

No secret value appears in either view. The secret rows list names only, the webhook row names the service but no part of the URL that carries an ntfy topic or a Discord token, and the recipient address is masked down to the first and last character of its local part.

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

## A Run That Finds Nothing

Monitoring is quiet by design: a check that finds no new match and no change in whether the player is in a game prints nothing. So that silence can be told apart from a dead process, the run prints a liveness banner once per `LIVENESS_CHECK_INTERVAL` of quiet:

```
* Monitoring healthy for Faker#KR1. The user is not in a match with no match change since the last check
Liveness check, timestamp:	Thu 01 Jan 2026, 00:50:00
```

A failure that lasts is reported once the short retry has failed too, then reminded once an hour with a count of the failed checks, and it says when it started:

```
* Error: The Riot API is temporarily unavailable (retrying in 2 minutes, 30 seconds)
To fix: This is usually a Riot outage. The tool will keep retrying
Timestamp:			Thu 01 Jan 2026, 00:20:05

* Monitoring degraded for Faker#KR1. The Riot API is temporarily unavailable since Thu 01 Jan 2026, 00:20:00, 26 failed checks
Liveness check, timestamp:	Thu 01 Jan 2026, 01:20:05

* Monitoring recovered for Faker#KR1 after 1 hour, 10 minutes
Timestamp:			Thu 01 Jan 2026, 01:30:05
```

Each block closes with its timestamp and a horizontal rule, so no line is left looking like a run that stopped there.

[What a Long Run Prints](troubleshooting.md#what-a-long-run-prints) covers the retry and alert behaviour behind these lines.

## Signal Controls (macOS/Linux/Unix)

Signals change the behaviour of a running copy without restarting it:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when the player's status changes (`-s`) |
| TRAP | Increase the in-game check interval by `LOL_ACTIVE_CHECK_SIGNAL_VALUE` seconds |
| ABRT | Decrease the in-game check interval by `LOL_ACTIVE_CHECK_SIGNAL_VALUE` seconds |
| HUP | Reload secrets from the dotenv file, reporting each one that changed |

Send them with `kill` or `pkill`:

```sh
pkill -USR1 -f "lol_monitor <riot_id> <region>"
```

A reload names each secret it replaced and how it looks, never its value:

```
* Reloaded RIOT_API_KEY from .env (set, 42 chars)
* Reloaded SMTP_PASSWORD from .env (set)
```

A Riot API key is always 42 characters, so a shorter one means the paste was cut. A password you chose reports presence only, since its length is a real disclosure.

A secret you exported before starting the tool is left alone by a reload, the same way it wins at startup. Rotate that one by exporting the new value and restarting, which is the only way to change an exported value in a running process anyway.

Windows supports too few signals for this, so it is available on Linux, Unix and macOS only.

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
