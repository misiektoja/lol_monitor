# Configuration

Most settings can be passed as command-line arguments. Anything you want to keep between runs belongs in a configuration file, and anything secret belongs in a dotenv file or an environment variable.

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

## Target Profile

The Riot ID and the region are positional arguments. Both are required to start monitoring:

```sh
lol_monitor <riot_id> <region>
```

A Riot ID is the game name plus the tag line, written as `riot_id_name#tag`. The accepted region codes are listed under [Region Codes](setup-and-first-run.md#region-codes).

## SMTP Settings

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

While `SMTP_HOST` is still the shipped placeholder, email notifications stay switched off.

Check the settings by sending one real message:

```sh
lol_monitor --send-test-email
```

Which events produce mail is covered under [Email Notifications](usage.md#email-notifications).

## Storing Secrets

Keep `RIOT_API_KEY` and `SMTP_PASSWORD` in an environment variable or a dotenv file rather than in the configuration file.

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

## Check Intervals

```sh
lol_monitor <riot_id> <region> -k 60 -c 120
```

| Setting | Flag | Meaning |
| --- | --- | --- |
| `LOL_CHECK_INTERVAL` | `-c` | Seconds between checks while the player is not in a game. Default 150 |
| `LOL_ACTIVE_CHECK_INTERVAL` | `-k` | Seconds between checks while the player is in a game. Default 45 |
| `LIVENESS_CHECK_INTERVAL` | | Seconds between liveness messages in the output. Set to 0 to disable. Default 43200 |
| `CHECK_INTERNET_TIMEOUT` | | Seconds allowed for the startup connectivity check. Default 5 |

## TLS Verification

Every outbound connection verifies the server's TLS certificate: the Riot API, the Data Dragon champion data, the startup connectivity check and email delivery. Leave it that way unless you have a reason not to.

`VERIFY_SSL = False` turns verification off for all of them at once. Do this only on a network that inspects TLS with its own certificate authority, such as a corporate proxy, and only when you cannot install that authority's certificate instead. With verification off, an intercepted connection looks the same as the real service, so your Riot API key can be read in transit.

The startup summary reports the state on every run, as `TLS verification: On` or `Off, server certificates are not checked`.

## Output and Files

| Setting | Flag | Meaning |
| --- | --- | --- |
| `CSV_FILE` | `-b` | CSV file to append reported matches to. Empty disables it |
| `LOL_LOGFILE` | | Base name for the log file, written as `lol_monitor_<riot_id_name>.log`. May include a directory |
| `DISABLE_LOGGING` | `-d` | Switches the log file off |
| `ASCII_LOG_SEPARATORS` | | `"Auto"` uses ASCII separator lines on Windows only, `"On"` everywhere, `"Off"` nowhere. Terminal separators stay Unicode |
| `HORIZONTAL_LINE` | | Width of the separator line |
| `CLEAR_SCREEN` | | Whether the terminal is cleared at startup |
| `INCLUDE_FORBIDDEN_MATCHES` | `-f` | Whether matches that need an OAuth (RSO) access token are shown with a notice instead of skipped silently |
| `CHECK_INTERNET_URL` | | Endpoint used to verify connectivity at startup |
| `LOL_ACTIVE_CHECK_SIGNAL_VALUE` | | Seconds each `TRAP` or `ABRT` signal adds to or removes from the in-game interval |
| `REGION_TO_CONTINENT` | | Maps each region code to its routing continent |

## Install Method

The tool works out whether it is running as the `lol_monitor` console script from PyPI or as a downloaded `lol_monitor.py`, and prints every command in the form that works for that install. The startup summary reports what it detected.

Wrapper scripts and container images can defeat the detection. Set `LOL_MONITOR_INSTALL_METHOD` to `pip` or `manual` to pin it:

```sh
export LOL_MONITOR_INSTALL_METHOD=pip
```

Set `LOL_MONITOR_IN_CONTAINER=true` to have the summary say so.
