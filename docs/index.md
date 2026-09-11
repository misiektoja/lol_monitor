# lol_monitor

Real-time tracker for League of Legends players' activity, with detailed match reports and instant alerts.

<a id="-quick-install"></a>
<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install lol_monitor
```

Run the setup wizard:

```sh
lol_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](installation.md).

## Features

- **Real-time tracking** of LoL players' gaming activity, including when a match starts and when it finishes
- **Detailed match reports** covering game mode, queue and map name, game type and version, victory or defeat, kills, deaths and assists, champion, achieved level, role, lane, both team rosters with a marker on the monitored player's team, and banned champions with pick turn
- **Player profile information** including ranked statistics for Solo/Duo and Flex, and top champion mastery
- **HTML email notifications** when a player starts or finishes a match, plus a match summary and error alerts, optionally with the champion icon embedded at the end
- **Discord and ntfy webhook alerts** carrying the same events, with each channel keeping its own alert settings, the champion icon as a Discord thumbnail or an ntfy attachment
- **CSV export** of every reported match with timestamps, including custom games
- **Guided setup** through `--setup`, which asks a few questions and writes a ready-to-run configuration, with a review summary and per-section editing before anything is saved
- **A welcome screen on a bare run**, naming the commands worth starting from and offering the wizard, plus a `--help` screen that ends with worked examples for the common tasks
- **Flexible configuration** through config files, dotenv files, environment variables and command-line arguments
- Possibility to **control the running copy** of the script via signals
- **Utility tools** for CSV format conversion and match history comparison
- **Functional, procedural Python** (minimal OOP)

## Screenshots

![lol_monitor](https://raw.githubusercontent.com/misiektoja/lol_monitor/main/assets/lol_monitor.png)

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](usage.md#command-format) for manual-script equivalents.

Replace the target placeholders with a Riot ID such as "Player#TAG" plus a region code such as euw1. Monitoring requires the [Riot API key](setup-and-first-run.md#riot-api-key) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `lol_monitor --setup` |
| Start monitoring with saved credentials | `lol_monitor "<riot_id>" <region>` |
| Check setup before monitoring | `lol_monitor --doctor "<riot_id>" <region>` |
| Enter or replace credentials through hidden prompts | `lol_monitor --set-riot-api-key` |
| Use a specific configuration and secrets file | `lol_monitor --config-file lol_monitor.conf --env-file .env "<riot_id>" <region>` |
| List recent matches | `lol_monitor "<riot_id>" <region> -l -n 10` |
| List every supported command-line option | `lol_monitor --help` |

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](usage.md). If a run fails, start with [Doctor Preflight](troubleshooting.md#doctor-preflight).

## Documentation

* [Installation](installation.md) - Python setup, package or manual install and upgrades
* [Setup & First Run](setup-and-first-run.md) - credentials, target selection and the setup wizard
* [Configuration](configuration.md) - settings, notifications and secret storage
* [Usage](usage.md) - monitoring, output and command options
* [Troubleshooting](troubleshooting.md) - Doctor checks and recovery steps
