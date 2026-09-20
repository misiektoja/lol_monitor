# lol_monitor

[![GitHub Release](https://img.shields.io/github/v/release/misiektoja/lol_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/lol_monitor/releases)
[![PyPI Version](https://img.shields.io/pypi/v/lol_monitor?style=flat-square&color=teal)](https://pypi.org/project/lol-monitor/)
[![GitHub Stars](https://img.shields.io/github/stars/misiektoja/lol_monitor?style=flat-square&color=magenta)](https://github.com/misiektoja/lol_monitor)
[![Python Versions](https://img.shields.io/badge/python-3.12+-blueviolet?style=flat-square)](https://pypi.org/project/lol-monitor/)
[![License](https://img.shields.io/github/license/misiektoja/lol_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/lol_monitor/blob/main/LICENSE)
[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Flol_monitor&query=%24.score&label=openssf%20scorecard&style=flat-square)](https://scorecard.dev/viewer/?uri=github.com/misiektoja/lol_monitor)
[![Last Commit](https://img.shields.io/github/last-commit/misiektoja/lol_monitor?style=flat-square&color=green)](https://github.com/misiektoja/lol_monitor/commits/main)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square)](https://github.com/misiektoja/lol_monitor)

Powerful tool for real-time monitoring of **LoL (League of Legends) players' activities**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/assets/lol_monitor.png" alt="lol_monitor_screenshot" width="90%"/>
</p>

<a id="quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/lol_monitor/installation/#new-to-python-check-and-install) first.

Install from PyPI:

```sh
pip install lol_monitor
```

Run the setup wizard:

```sh
lol_monitor --setup
```

The wizard asks for the Riot ID and region, the Riot API key and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/lol_monitor/setup-and-first-run/) for how to get the Riot API key and the region codes.

For the manual single-file method, optional dependencies and upgrade commands, see [Installation](https://misiektoja.github.io/lol_monitor/installation/).

<a id="features"></a>
## Features

### 🔍 Match Tracking

* **Match activity**: Detect when a player starts and finishes a game.
* **Match reports**: Show results, kills, deaths, assists, champion, level, role and lane.
* **Game context**: Include mode, queue, map, version, both team rosters and champion bans.

### 📊 Player Insights and Tools

* **Ranked statistics**: View Solo/Duo and Flex ranks plus top champion mastery.
* **Match history**: List recent matches and export timestamped reports, including custom games.
* **CSV tools**: Convert older history files and compare match histories.

### 🔔 Notifications

* **Email alerts**: Receive match starts, finishes, summaries, monitoring failures and their recovery.
* **Discord and ntfy**: Choose webhook events independently from email.
* **Champion artwork**: Include an optional icon in email, as a Discord thumbnail or as an ntfy attachment.

### ⚙️ Setup and Configuration

* **Guided setup**: Review and edit settings before saving with `--setup`.
* **Getting started**: Use the welcome screen, worked help examples and `--doctor` checks.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Runtime controls**: Adjust the running monitor through supported signals.

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install--run) above for first-time setup. The table uses PyPI commands. For the manual script equivalents, see [Run Individual Commands](https://misiektoja.github.io/lol_monitor/setup-and-first-run/#run-individual-commands).

Replace the target placeholders with a Riot ID such as "Player#TAG" plus a region code such as euw1. Monitoring requires the [Riot API key](https://misiektoja.github.io/lol_monitor/setup-and-first-run/#riot-api-key) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `lol_monitor --setup` |
| Start monitoring with existing authentication | `lol_monitor "<riot_id>" <region>` |
| Check authentication, connectivity and one target | `lol_monitor --doctor "<riot_id>" <region>` |
| Enter or replace securely the Riot API key | `lol_monitor --set-riot-api-key` |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](https://misiektoja.github.io/lol_monitor/configuration/#webhook-settings) |
| Save an SMTP password for email alerts | `lol_monitor --set-smtp-password` |
| Send a test email | `lol_monitor --send-test-email` |
| Save a new webhook URL | `lol_monitor --set-webhook-url` |
| Send a test webhook | `lol_monitor --send-test-webhook` |
| List recent matches | `lol_monitor "<riot_id>" <region> -l -n 10` |
| Write every change to a CSV file | `lol_monitor "<riot_id>" <region> -b changes.csv` |
| Use a specific configuration and secrets file | `lol_monitor --config-file lol_monitor.conf --env-file .env "<riot_id>" <region>` |
| List every supported command-line flag | `lol_monitor --help` |

Running the tool with no arguments offers the wizard if you have not saved a player. If a player is already saved, it starts monitoring that player.

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence and run multiple copies to monitor several players.

For the API key, region codes, saved players and notification setup, see the [full Setup & First Run guide](https://misiektoja.github.io/lol_monitor/setup-and-first-run/).

For email and webhook setup, see [Configuration](https://misiektoja.github.io/lol_monitor/configuration/). For notification choices, listing commands and output files, see [Usage](https://misiektoja.github.io/lol_monitor/usage/).

If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/lol_monitor/troubleshooting/#doctor-preflight).

<a id="documentation"></a>
## Documentation

Full documentation is available at **[misiektoja.github.io/lol_monitor](https://misiektoja.github.io/lol_monitor/)**:

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/lol_monitor/installation/) | Python walkthrough, PyPI or manual installation, upgrades |
| [Setup & First Run](https://misiektoja.github.io/lol_monitor/setup-and-first-run/) | Setup wizard, the Riot API key, region codes, the first monitoring run |
| [Configuration](https://misiektoja.github.io/lol_monitor/configuration/) | Config file, SMTP, webhooks, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/lol_monitor/usage/) | Monitoring mode, listing mode, notifications, CSV export, signals, terminal output |
| [Utility Tools](https://misiektoja.github.io/lol_monitor/tools/) | The CSV format converter and the match history comparison tool |
| [Troubleshooting](https://misiektoja.github.io/lol_monitor/troubleshooting/) | `--doctor` preflight checks, what to do when something fails, `--verbose` and `--debug` output |
| [Testing](https://misiektoja.github.io/lol_monitor/testing/) | Running the offline suite, the linter and the docs build |
| [About](https://misiektoja.github.io/lol_monitor/about/) | Change log, contributing, security, license, support |

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/lol_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="contributing"></a>
## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/lol_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/lol_monitor/blob/main/CODE_OF_CONDUCT.md).

<a id="security"></a>
## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/lol_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/lol_monitor/blob/main/SECURITY.md) covers the reporting process, the supported versions and the security posture of stored credentials and configuration loading.

<a id="maintainers"></a>
## Maintainers

- **misiektoja** ([@misiektoja](https://github.com/misiektoja))

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/lol_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/lol_monitor/blob/main/THIRD_PARTY_NOTICES.md).

<a id="support"></a>
## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/lol_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
