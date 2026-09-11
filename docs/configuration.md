# Configuration

Most settings can be passed as command-line arguments. Anything you want to keep between runs belongs in a configuration file, and anything secret belongs in a dotenv file or an environment variable. [`--setup`](setup-and-first-run.md#guided-setup) writes both files for you. This page covers changing them afterwards, or writing them by hand.

## Configuration File

Generate the default template and save it as `lol_monitor.conf`:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
lol_monitor --generate-config > lol_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
lol_monitor --generate-config lol_monitor.conf
```

!!! warning "Windows PowerShell"
    Do not use `>` for this command in PowerShell. Some versions write redirected text as UTF-16, which makes the tool report a "null bytes" error. Pass the filename to `--generate-config` instead and the tool writes a UTF-8 file itself.

Passing the filename is also the safer form. When the file already exists the tool asks before replacing it and keeps a timestamped `.bak` copy of the old one next to it, readable only by you. A `>` redirect cannot do that, because the shell empties the file before the tool starts.

Outside a terminal, where there is nobody to ask, the tool refuses and leaves the file alone. Pass `--force` to replace it anyway, which still writes the backup first:

```sh
lol_monitor --generate-config lol_monitor.conf --force
```

Edit the file and change whatever you need. Every setting carries a comment explaining what it does.

The file is read as data, not executed. Only documented `SETTING = value` lines with plain literal values are accepted, plus a setting that reuses another setting. Imports, function calls, expressions and control flow are rejected without being run, and the rejected line is named.

By default the tool looks for `lol_monitor.conf` in the current directory, then the home directory, then the script directory. If you saved it elsewhere or under another name, point at it with `--config-file`:

```sh
lol_monitor <riot_id> <region> --config-file /path/lol_monitor_new.conf
```

Disable the search entirely with `--config-file none`, so only the command line and the environment are read:

```sh
lol_monitor <riot_id> <region> --config-file none
```

This is worth doing in a container or a scheduled job, where a `lol_monitor.conf` left in the working directory would otherwise be picked up without anyone asking for it. The startup summary reports `Discovery disabled` when it is in effect.

## Target Profile

The Riot ID and the region are positional arguments. Both are required to start monitoring:

```sh
lol_monitor <riot_id> <region>
```

A Riot ID is the game name plus the tag line, written as `riot_id_name#tag`. The accepted region codes are listed under [Region Codes](setup-and-first-run.md#region-codes). Region codes are not case sensitive, and spaces around the `#` are ignored, so `" Name # TAG "` and `EUN1` are read the same as `Name#TAG` and `eun1`.

To stop repeating them, save the pair in the configuration file:

```ini
RIOT_ID = "riot_id_name#tag"
REGION = "eun1"
```

Then `lol_monitor` alone starts monitoring that player. A positional argument still wins, so you can watch someone else for one run without editing the file:

```sh
lol_monitor "other_name#tag" euw1
```

[`--setup`](setup-and-first-run.md#guided-setup) asks whether to save the target. Declining leaves `RIOT_ID` and `REGION` empty and the printed start commands include the Riot ID and region instead.

Path settings are validated before startup opens files. A monitoring run stops and names the setting to correct. `--doctor`, `--setup` and the `--set-...` commands report the same setting and continue on the built-in value, so it can still be repaired. Command-line path overrides still take precedence. `TRUNCATE_CHARS` must be an integer zero or greater. Use `0` to keep full lines or `999` to detect terminal width. A `--truncate` override also applies to Doctor.

## SMTP Settings

Private password entry preserves leading and trailing spaces. The exact value checked with the mail server is saved.

Private entry preserves literal `${...}` text in saved passwords and other secrets. Assignments that need this protection carry a `# monitor:literal` comment. Keep that comment when editing the value. Unmarked assignments retain their existing interpolation behavior. The marker is read by this monitor. Other dotenv readers or shells may still interpolate the value.

[`--setup`](setup-and-first-run.md#guided-setup) collects these for you and signs in to the mail server before saving them. To configure them by hand, set the SMTP settings in `lol_monitor.conf`.

Email notifications need the SMTP block in the configuration file filled in:

| Setting | Meaning |
| --- | --- |
| `SMTP_HOST` | Mail server hostname |
| `SMTP_PORT` | Mail server port |
| `SMTP_USER` | Account used to sign in |
| `SMTP_PASSWORD` | Password for that account, best kept in a dotenv file |
| `SMTP_SSL` | `True` for STARTTLS, `False` for a plain connection |
| `SENDER_EMAIL` | Address the alerts are sent from |
| `RECEIVER_EMAIL` | Address the alerts are sent to |

Email notifications stay switched off until `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SENDER_EMAIL` and `RECEIVER_EMAIL` all hold real values. A setting left as its shipped `your_...` placeholder counts as unset.

If any of them is missing while the rest are filled in, or if you asked for status emails with `-s`, startup names what is still missing:

```
* Email notifications are off because SMTP_PASSWORD, RECEIVER_EMAIL are not set
```

Check the settings by sending one real message:

```sh
lol_monitor --send-test-email
```

Which events produce mail is covered under [Email Notifications](usage.md#email-notifications).

### Champion Icon in Email

`EMAIL_IMAGES = True` embeds the champion icon at the end of the in-game and match summary emails, under the timestamp. The icon is the one the Data Dragon release serves for the champion the player used, downloaded at send time and attached to the message, so it shows without the mail client fetching anything remote.

Alerts that name no champion, such as an error alert, are unaffected. If the download fails or returns something that is not a small image, the email is sent as text only.

[`--setup`](setup-and-first-run.md#guided-setup) offers the setting once match emails are enabled.

## Webhook Settings

Discord templates must produce a JSON object. Dictionary templates and JSON strings are supported, including legacy strings with doubled object braces. Unsupported placeholders are reported before delivery. Alert text is kept literal and mentions are disabled. Reloaded settings apply to the next delivery.

Webhooks send the same alerts as email to a Discord channel or an ntfy topic. They are switched off until you set a destination. [`--setup`](setup-and-first-run.md#guided-setup) collects the service, the destination and the alert switches together:

| Setting | Meaning |
| --- | --- |
| `WEBHOOK_ENABLED` | Master switch for the channel |
| `WEBHOOK_PROVIDER` | `discord` or `ntfy` |
| `WEBHOOK_URL` | The private destination, best kept in a dotenv file |
| `WEBHOOK_USERNAME` | Discord display name, empty to use the webhook default |
| `WEBHOOK_AVATAR_URL` | Discord avatar URL, empty to use the webhook default |
| `WEBHOOK_STATUS_NOTIFICATION` | Send an alert when the player's status changes |
| `WEBHOOK_ERROR_NOTIFICATION` | Send an alert on monitoring errors, on by default |
| `WEBHOOK_HEADERS` | Extra request headers, for example ntfy options |
| `NTFY_ACCESS_TOKEN` | Bearer token for a private ntfy topic |
| `NTFY_IMAGES` | Attach the champion icon to ntfy alerts |

Save the destination without putting it in a file you might share:

```sh
lol_monitor --set-webhook-url
```

The URL is typed hidden, checked for shape, and written to the dotenv file with owner-only permissions. The command names the service it recognised so you can tell a mistyped destination from the right one.

The destination decides the service. A `https://ntfy.sh/...` link is treated as ntfy and a Discord webhook link as Discord, even when `WEBHOOK_PROVIDER` says otherwise. While `WEBHOOK_PROVIDER` is left at its default, that detection is silent and `--verbose` reports it. A warning appears only when your configuration file sets a provider the URL disagrees with. Pass `--webhook-provider` to override that for a self-hosted host the tool cannot recognise.

Send one real notification to check the setup:

```sh
lol_monitor --send-test-webhook
```

Email and webhooks are independent. Both can be on, and each keeps its own alert settings, so you can take errors on ntfy and status changes by mail.

### ntfy

`WEBHOOK_URL` is the complete topic URL, such as `https://ntfy.sh/your-private-topic`. Anyone who knows a public topic name can read it, so pick an unguessable one or use a private server with `NTFY_ACCESS_TOKEN`.

The alert body is sent as a native ntfy message with the subject as its title. ntfy rejects a message over 4 KB, so a long alert is cut with a note saying that it was.

Add ntfy options through `WEBHOOK_HEADERS`:

```python
WEBHOOK_HEADERS = {"X-Priority": "4", "X-Tags": "video_game"}
```

`NTFY_IMAGES = True` attaches the champion icon to the alerts that name a champion, taken from the same Data Dragon release the champion names come from. ntfy shows it as the notification image and the alert text travels beside it, so the message reads the same as without the icon. An alert with no champion is sent as text, and an attachment the server rejects is retried once as a text-only alert so the alert itself still arrives.

[`--setup`](setup-and-first-run.md#guided-setup) offers the setting when the destination is an ntfy topic and match alerts are enabled.

### Discord

`WEBHOOK_URL` is the link from **Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL**. Anyone holding it can post to that channel.

Alerts are sent as an embed built from `WEBHOOK_TEMPLATE`, which supports the `title`, `description`, `version`, `image_url`, `fields`, `fields_str`, `color`, `timestamp`, `username` and `avatar_url` placeholders. Mentions are disabled on every message the tool sends, whatever the template says.

`image_url` holds the champion icon on the alerts that name a champion, the in-game announcement and the finished match summary, taken from the Data Dragon release the run read its champion names from. The default template shows it as the embed thumbnail. Alerts with no champion leave it empty and the thumbnail is dropped rather than sent blank.

In the roster the monitored player's own line is sent in bold, since Discord renders markdown in an embed. Only Discord gets that wording: email uses its HTML body for the same emphasis and ntfy receives the plain roster.

`WEBHOOK_TRANSFORMS` applies string methods to those values before the payload is built:

```python
WEBHOOK_TRANSFORMS = [("title", "upper"), ("description", "replace", "**", "")]
```

### Delivery

A failed delivery is retried once. A rate-limited service is honoured up to five seconds and no longer, so a busy service cannot hold up a check. Redirects are never followed, so a hijacked destination cannot forward an alert somewhere else.

Errors name the service and the status code, never the URL, the token inside it or the response body:

```
* Error: The webhook service returned HTTP 401
```

Which events produce a webhook is covered under [Webhook Notifications](usage.md#webhook-notifications).

## Storing Secrets

Keep `RIOT_API_KEY`, `SMTP_PASSWORD`, `WEBHOOK_URL` and `NTFY_ACCESS_TOKEN` in an environment variable or a dotenv file rather than in the configuration file.

[`--setup`](setup-and-first-run.md#guided-setup) writes every secret it collects to the dotenv file, and never to the configuration file. To store one on its own afterwards, the tool can write the dotenv file for you. Each command reads the value hidden, checks it against the real service and only then saves it:

```sh
lol_monitor --set-riot-api-key
```

```sh
lol_monitor --set-smtp-password
```

```sh
lol_monitor --set-webhook-url
```

`--set-riot-api-key` checks the key with Riot. `--set-smtp-password` checks mail sign-in without sending a message. `--set-webhook-url` checks the HTTPS URL. Failed checks leave the saved value unchanged. Replacements require confirmation and the dotenv file has owner-only permissions. Use `--env-file PATH` to choose another file. An exported `SMTP_PASSWORD` overrides the saved value at startup.

Set environment variables with `export` on **Linux, Unix, macOS and WSL**:

```sh
export RIOT_API_KEY="your_riot_api_key"
export SMTP_PASSWORD="your_smtp_password"
```

On **Windows Command Prompt** use `set` instead of `export`, and on **Windows PowerShell** use `$env`.

Storing them in a dotenv file is usually easier:

```ini
RIOT_API_KEY="your_riot_api_key"
SMTP_PASSWORD="your_smtp_password"
WEBHOOK_URL="https://ntfy.sh/your-private-topic"
```

By default the tool searches for a file named `.env` in the current directory and then upward from it.

Select a specific file with the `DOTENV_FILE` setting or the `--env-file` flag:

```sh
lol_monitor <riot_id> <region> --env-file /path/.env-lol_monitor
```

Disable the search entirely with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
lol_monitor <riot_id> <region> --env-file none
```

As a fallback both values can also live in the configuration file or the source.

### Which Source Wins

When the same secret is available from more than one place, the tool takes the first match in this order:

1. The command line, such as `-r your_riot_api_key` or `--webhook-url`
2. An environment variable exported before the tool started
3. The dotenv file
4. The configuration file or the source

An exported variable applies on its own, with no dotenv file present. The startup summary reports which source each secret came from, by name and never by value, one row per source. Run with `--verbose` to see them:

```
* Secrets from dotenv:          SMTP_PASSWORD
* Secrets from environment:     RIOT_API_KEY
* Secrets from config file:     None
* Secrets from command line:    None
```

A forgotten `export` can shadow the dotenv file invisibly, so `--debug` names every secret and the source it resolved from, never the value:

```text
[DEBUG 12:00:00] Secret resolution: name=RIOT_API_KEY, source=environment, value=set, chars=42
[DEBUG 12:00:00] Secret resolution: name=SMTP_PASSWORD, source=dotenv file, value=set
```

A secret still holding its `your_...` placeholder counts as unset and is left out, and a run with no secret anywhere says so on one line. A length appears only for the secrets whose length the provider issues, never for a password you chose.

Secret commands update the selected value without changing other dotenv settings. Clearing a value removes its assignment.

### Reloading secrets and backup contents

On systems with SIGHUP, reloading applies changes from the selected dotenv file. Removing a file-owned
assignment restores its independently configured fallback or clears the value when no fallback exists.
A read or parsing failure keeps the last usable credentials and reports how to correct the file.
Values exported when the process started continue to take precedence during reload.

Setup keeps the saved `DOTENV_FILE` unless you choose another path with `--env-file`. When you move it, review the private settings before saving. Kept credentials are copied to the new destination and the old file stays intact. Values already in the new dotenv file take precedence unless you replace them. At startup, a nonempty exported secret overrides the dotenv file. A dotenv value, including an empty one, overrides the configuration.

Setup moves retained credentials from older configuration files into the selected dotenv file unless that file already defines the same key. It leaves the original configuration in place if it cannot preserve those credentials. Setup creates a timestamped configuration backup with inline secrets removed. General `--generate-config` backups can contain inline credentials. Replaced dotenv secrets are not backed up.

## Check Intervals

```sh
lol_monitor <riot_id> <region> -k 60 -c 120
```

| Setting | Flag | Meaning |
| --- | --- | --- |
| `LOL_CHECK_INTERVAL` | `-c` | Seconds between checks while the player is not in a game. Default 150 |
| `LOL_ACTIVE_CHECK_INTERVAL` | `-k` | Seconds between checks while the player is in a game. Default 45 |
| `LIVENESS_CHECK_INTERVAL` | | Seconds of quiet before the run says it is alive, and how often a lasting failure is repeated. Set to 0 to disable, which makes a failure print on every check instead. Default 86400 |
| `CHECK_INTERNET_TIMEOUT` | | Seconds allowed for the startup connectivity check. Default 5 |

Riot's development key allows 100 requests every two minutes, and each check while the player is in a game spends several of them. `--doctor` warns when `LOL_ACTIVE_CHECK_INTERVAL` drops below 10 seconds, which is where the extra calls a live match report makes stop fitting.

## TLS Verification

Every outbound connection verifies the server's TLS certificate: the Riot API, the Data Dragon champion data, the startup connectivity check and email delivery. Leave it that way unless you have a reason not to.

`VERIFY_SSL = False` turns verification off for all of them at once. Do this only on a network that inspects TLS with its own certificate authority, such as a corporate proxy, and only when you cannot install that authority's certificate instead. With verification off, an intercepted connection looks the same as the real service, so your Riot API key can be read in transit.

The startup summary reports the state as `TLS verification: On` or `Off, server certificates are not checked`. The row is only shown without `--verbose` while verification is off, since a run that stopped checking certificates should say so unasked.

## Output and Files

| Setting | Flag | Meaning |
| --- | --- | --- |
| `CSV_FILE` | `-b` | CSV file to append reported matches to. Empty disables it |
| `LOL_LOGFILE` | | Base name for the log file, written as `lol_monitor_<riot_id_name>.log`. May include a directory |
| `DISABLE_LOGGING` | `-d` | Switches the log file off |
| `ASCII_LOG_SEPARATORS` | | `"Auto"` uses ASCII separator lines on Windows only, `"On"` everywhere, `"Off"` nowhere. Terminal separators stay Unicode |
| `TRUNCATE_CHARS` | `--truncate N` | Max display width per screen line, `999` to auto-detect the terminal width. See [Terminal Truncation](#terminal-truncation) |
| `HORIZONTAL_LINE` | | Width of the separator line |
| `COLORED_OUTPUT` | `--no-color` | Whether terminal output is coloured. See [Coloured Output](#coloured-output) |
| `CLEAR_SCREEN` | | Whether the terminal is cleared at startup. A one-shot command such as `--doctor`, `-l` or `--help`, a `--debug` run and any redirected output are never cleared |
| `INCLUDE_FORBIDDEN_MATCHES` | `-f` | Whether matches that need an OAuth (RSO) access token are shown with a notice instead of skipped silently |
| `CHECK_INTERNET_URL` | | Endpoint used to verify connectivity at startup |
| `LOL_ACTIVE_CHECK_SIGNAL_VALUE` | | Seconds each `TRAP` or `ABRT` signal adds to or removes from the in-game interval |
| `REGION_TO_CONTINENT` | | Maps each region code to its routing continent |

## Terminal Truncation

Long paths, long game labels and long error text wrap across several screen lines and make a run hard to follow. `TRUNCATE_CHARS`, or `--truncate N` for a single run, cuts each screen line to a maximum display width and marks the cut with `...`. Set it to `999` to use the width of the terminal the run started in.

**The log file always keeps the full line**, so nothing is lost. That is also why truncation is ignored when logging is switched off with `-d`: without a log file there would be no full copy of a cut line.

Width is measured in display columns rather than characters, so a wide glyph in a Korean or Japanese player name costs two columns and is never printed as half of itself. This needs the optional [wcwidth](https://pypi.org/project/wcwidth/) library. Without it every character counts as one column and a line holding wide glyphs can run past the limit:

```bash
pip install wcwidth
```

Without it, lines are printed in full and `--doctor` says so. Truncation is off by default.

## Coloured Output

Colour is on by default and marks what a value is rather than decorating the line: player names, identifiers, champions, ranks, dates, links and the `[PASS]`/`[WARN]`/`[FAIL]`/`[SKIP]` markers each get their own colour. In a match roster the monitored player's own entry is bold, through the `monitored_username` part, so their line stands out among the nine others. The log file is never coloured, so a log attached to a bug report stays plain text. `COLORED_OUTPUT` and `COLOR_THEME` apply to monitoring output and to the [`--setup`](setup-and-first-run.md#guided-setup), `--doctor` and `--help` screens alike.

The `--help` screen is coloured too. Group headings, option names, the values those options take, the example commands and the comments above them each get their own colour, so the screen can be scanned instead of read.

Colour switches itself off when the output is not a terminal you are watching. That covers redirected or piped output, a `NO_COLOR` environment variable of any value, a `TERM` of `dumb` or empty and a `--no-color` run. The startup summary reports the resolved state next to the setting, so `False (setting: True)` means colour was configured but the terminal did not qualify.

To change a colour, uncomment the `COLOR_THEME` block in your configuration file and edit the parts you want. Every part you leave out keeps its built-in colour:

```python
COLOR_THEME = {
    "username": "bright_cyan underline",
    "error": "red",
}
```

A style is a space-separated list of one colour and any attributes. Colours are `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` and their `bright_` forms. Attributes are `bold`, `dim`, `underline` and `blink`. An empty string leaves that part uncoloured, and an unknown name is ignored.

The block ships commented out so the tool's own colours apply and later improvements reach existing configuration files. Overrides you added are written back as a real block when setup rebuilds the file, so they are not lost. Once you uncomment it, the parts inside it are pinned to whatever you saved, so delete the block again to go back to the current defaults.

## Diagnostics

| Setting | Flag | Meaning |
| --- | --- | --- |
| `VERBOSE_MODE` | `--verbose` | Extra startup and runtime detail in plain `* ` lines |
| `DEBUG_MODE` | `--debug` | Timestamped `[DEBUG]` traces of network activity, delivery and completed checks |
| `DELIVERY_CONFIRMATIONS` | - | Whether verbose output confirms each delivered email and webhook alert (default `True`) |

The first two are independent, so enable both to see everything. A flag always wins over the configuration file, and neither ever prints a secret value. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without the `* Email sent to ...` and `* Webhook sent through ...` lines, which is worth doing when alerts are frequent. What each mode reports is described in [Verbose and Debug Output](troubleshooting.md#verbose-and-debug-output).

## Install Method

The tool works out whether it is running as the `lol_monitor` console script from PyPI or as a downloaded `lol_monitor.py`, and prints every command in the form that works for that install. The startup summary reports what it detected.

Wrapper scripts and container images can defeat the detection. Set `LOL_MONITOR_INSTALL_METHOD` to `pip` or `manual` to pin it:

```sh
export LOL_MONITOR_INSTALL_METHOD=pip
```

Set `LOL_MONITOR_IN_CONTAINER=true` to have the summary say so.
