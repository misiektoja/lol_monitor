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

### Match Tracking

* **Match activity**: Detect when a player starts and finishes a game.
* **Match reports**: Show results, kills, deaths, assists, champion, level, role and lane.
* **Game context**: Include mode, queue, map, version, both team rosters and champion bans.

### Player Insights and Tools

* **Ranked statistics**: View Solo/Duo and Flex ranks plus top champion mastery.
* **Match history**: List recent matches and export timestamped reports, including custom games.
* **CSV tools**: Convert older history files and compare match histories.

### Notifications

* **Email alerts**: Receive match starts, finishes, summaries and errors.
* **Discord and ntfy**: Choose webhook events independently from email.
* **Champion artwork**: Include an optional icon in email, as a Discord thumbnail or as an ntfy attachment.

### Setup and Configuration

* **Guided setup**: Review and edit settings before saving with `--setup`.
* **Getting started**: Use the welcome screen, worked help examples and `--doctor` checks.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Runtime controls**: Adjust the running monitor through supported signals.

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
