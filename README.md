# lol_monitor

lol_monitor is a tool for real-time monitoring of LoL (League of Legends) players' activities. 

<a id="features"></a>
## Features

- Real-time tracking of LoL users' gaming activity (including detection when a user starts or finishes a match)
- Most important statistics for finished matches:
  - game mode
  - victory or defeat
  - kills, deaths, assists
  - champion name
  - achieved level
  - role
  - lane
  - team members
- Email notifications for different events (player starts or finishes a match, match summary, errors)
- Saving all gaming activities with timestamps to a CSV file
- Possibility to control the running copy of the script via signals

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/assets/lol_monitor.png" alt="lol_monitor_screenshot" width="70%"/>
</p>

<a id="table-of-contents"></a>
## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
   * [Install from PyPI](#install-from-pypi)
   * [Manual Installation](#manual-installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
   * [Configuration File](#configuration-file)
   * [Riot API Key](#riot-api-key)
   * [SMTP Settings](#smtp-settings)
   * [Storing Secrets](#storing-secrets)
5. [Usage](#usage)
   * [Monitoring Mode](#monitoring-mode)
   * [Listing Mode](#listing-mode)
   * [Email Notifications](#email-notifications)
   * [CSV Export](#csv-export)
   * [Check Intervals](#check-intervals)
   * [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix)
   * [Coloring Log Output with GRC](#coloring-log-output-with-grc)
6. [Change Log](#change-log)
7. [License](#license)

<a id="requirements"></a>
## Requirements

* Python 3.12 or higher
* Libraries: [pulsefire](https://github.com/iann838/pulsefire), `requests`, `python-dateutil`, `python-dotenv`

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm), Ubuntu 24, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="installation"></a>
## Installation

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install lol_monitor
```

<a id="manual-installation"></a>
### Manual Installation

Download the *[lol_monitor.py](https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/lol_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install pulsefire requests python-dateutil python-dotenv
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

<a id="quick-start"></a>
## Quick Start

- Grab your [Riot API key](#riot-api-key) and track the gaming activities of the `riot_id_name#tag` in selected `region`:

```sh
lol_monitor <riot_id_name#tag> <region> -r "your_riot_api_key"
```

Or if you installed [manually](#manual-installation):

```sh
python3 lol_monitor.py <riot_id_name#tag> <region> -r "your_riot_api_key"
```

To get the list of all supported command-line arguments / flags:

```sh
lol_monitor --help
```

<a id="configuration"></a>
## Configuration

<a id="configuration-file"></a>
### Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, generate a default config template and save it to a file named `lol_monitor.conf`:

```sh
lol_monitor --generate-config > lol_monitor.conf

```

Edit the `lol_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

<a id="riot-api-key"></a>
### Riot API Key

Get the development Riot API key valid for 24 hours here: [https://developer.riotgames.com](https://developer.riotgames.com)

It is recommended to apply for persistent personal or production Riot API key here: [https://developer.riotgames.com/app-type](https://developer.riotgames.com/app-type)

It takes few days to get the approval.

Provide the `RIOT_API_KEY` secret using one of the following methods:
 - Pass it at runtime with `-r` / `--riot-api-key`
 - Set it as an [environment variable](#storing-secrets) (e.g. `export RIOT_API_KEY=...`)
 - Add it to [.env file](#storing-secrets) (`RIOT_API_KEY=...`) for persistent use

Fallback:
 - Hard-code it in the code or config file

If you store the `RIOT_API_KEY` in a dotenv file you can update its value and send a `SIGHUP` signal to the process to reload the file with the new API key without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix).

<a id="smtp-settings"></a>
### SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `lol_monitor.conf` file. 

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
lol_monitor --send-test-email
```

<a id="storing-secrets"></a>
### Storing Secrets

It is recommended to store secrets like `RIOT_API_KEY` or `SMTP_PASSWORD` as either an environment variable or in a dotenv file.

Set environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export RIOT_API_KEY="your_riot_api_key"
export SMTP_PASSWORD="your_smtp_password"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file (recommended):

```ini
RIOT_API_KEY="your_riot_api_key"
SMTP_PASSWORD="your_smtp_password"
```

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it. 

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
lol_monitor <riot_id_name#tag> <region> --env-file /path/.env-lol_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
lol_monitor <riot_id_name#tag> <region> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.

<a id="usage"></a>
## Usage

<a id="monitoring-mode"></a>
### Monitoring Mode

To monitor specific user activity, just type player's LoL Riot ID & region as command-line arguments (`riot_id_name#tag` and `region` in the example below):

```sh
lol_monitor <riot_id_name#tag> <region>
```

If you have not set`RIOT_API_KEY` secret, you can use `-r` flag:

```sh
lol_monitor <riot_id_name#tag> <region> -r "your_riot_api_key"
```

LoL Riot ID consists of Riot ID game name (`riot_id_name` in the example above) and tag line (`#tag`). 

For the `region` you need to use the short form of it. You can find the list below:

| Region short form | Description |
| ----------- | ----------- |
| eun1 | Europe Nordic & East (EUNE) |
| euw1 | Europe West (EUW) |
| tr1 | Turkey (TR1) |
| ru | Russia |
| na1 | North America (NA) - now the sole NA endpoint |
| br1 | Brazil (BR) |
| la1 | Latin America North (LAN) |
| la2 | Latin America South (LAS) |
| jp1 | Japan (JP) |
| kr | Korea (KR) |
| sg2 | Southeast Asia (SEA) - Singapore, Malaysia, Indonesia (+ Thailand & Philippines since Jan 9, 2025) |
| tw2 | Taiwan, Hong Kong & Macao (TW/HK/MO) |
| vn2 | Vietnam (VN) |
| oc1 | Oceania (OC) |

By default, the tool looks for a configuration file named `lol_monitor.conf` in:
 - current directory 
 - home directory (`~`)
 - script directory 

 If you generated a configuration file as described in [Configuration](#configuration), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:


```sh
lol_monitor <riot_id_name#tag> <region> --config-file /path/lol_monitor_new.conf
```

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple LoL players by running multiple instances of the script.

The tool automatically saves its output to `lol_monitor_<riot_id_name>.log` file. It can be changed in the settings via `LOL_LOGFILE` configuration option or disabled completely via `DISABLE_LOGGING` / `-d` flag.

<a id="listing-mode"></a>
### Listing Mode

There is also another mode of the tool which prints and/or saves the recent matches for the user (`-l` flag). You can also add `-n` to define how many recent matches you want to display/save; by default, it shows the last 2 matches:

```sh
lol_monitor <riot_id_name#tag> <region> -l -n 25
```

You can also define the range of matches to display/save by specifying the minimal match to display (`-m` flag). So for example, to display recent matches in the range of 20-50:

```sh
lol_monitor <riot_id_name#tag> <region> -l -m 20 -n 50
```

If you specify the `-b` flag (with a CSV file name) together with the `-l` flag, it will not only display the recent matches, but also save them to the specified CSV file. For example, to display and save recent matches in the range of 5-10 for the user:

```sh
lol_monitor <riot_id_name#tag> <region> -l -m 5 -n 10 -b lol_games_riot_id_name.csv
```

<a id="email-notifications"></a>
### Email Notifications

To enable email notifications when user's playing status changes:
- set `STATUS_NOTIFICATION` to `True`
- or use the `-s` flag

```sh
lol_monitor <riot_id_name#tag> <region> -s
```

To disable sending an email on errors (enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
lol_monitor <riot_id_name#tag> <region> -e
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/assets/lol_monitor_email_notifications.png" alt="lol_monitor_email_notifications" width="80%"/>
</p>

<a id="csv-export"></a>
### CSV Export

If you want to save all reported activities of the LoL user to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
lol_monitor <riot_id_name#tag> <region> -b lol_games_riot_id_name.csv
```

The file will be automatically created if it does not exist.

<a id="check-intervals"></a>
### Check Intervals

If you want to customize polling intervals, use `-k` and `-c` flags (or corresponding configuration options):

```sh
lol_monitor <riot_id_name#tag> <region> -k 60 -c 120
```

* `LOL_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the user is in a game (seconds)
* `LOL_CHECK_INTERVAL`, `-c`: check interval when the user is NOT in a game (seconds)

<a id="signal-controls-macoslinuxunix"></a>
### Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user's playing status changes (-s) |
| TRAP | Increase the check timer for player activity when user is in game (by 30 seconds) |
| ABRT | Decrease check timer for player activity when user is in game (by 30 seconds) |
| HUP | Reload secrets from .env file |

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "lol_monitor <riot_id_name#tag> <region>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
### Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to color logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 lol_monitor_<riot_id_name>.log
```

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/lol_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/lol_monitor/blob/main/LICENSE).
