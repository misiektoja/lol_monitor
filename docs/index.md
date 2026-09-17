# lol_monitor

[![GitHub Release](https://img.shields.io/github/v/release/misiektoja/lol_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/lol_monitor/releases)
[![PyPI Version](https://img.shields.io/pypi/v/lol_monitor?style=flat-square&color=teal)](https://pypi.org/project/lol-monitor/)
[![GitHub Stars](https://img.shields.io/github/stars/misiektoja/lol_monitor?style=flat-square&color=magenta)](https://github.com/misiektoja/lol_monitor)
[![Python Versions](https://img.shields.io/badge/python-3.12+-blueviolet?style=flat-square)](https://pypi.org/project/lol-monitor/)
[![License](https://img.shields.io/github/license/misiektoja/lol_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/lol_monitor/blob/main/LICENSE)
[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Flol_monitor&query=%24.score&label=openssf%20scorecard&style=flat-square)](https://scorecard.dev/viewer/?uri=github.com/misiektoja/lol_monitor)
[![Last Commit](https://img.shields.io/github/last-commit/misiektoja/lol_monitor?style=flat-square&color=green)](https://github.com/misiektoja/lol_monitor/commits/main)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square)](https://github.com/misiektoja/lol_monitor)

Real-time tracker for League of Legends players' activity, with detailed match reports and instant alerts.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/assets/lol_monitor.png" alt="lol_monitor_screenshot" width="90%"/>
</p>

<a id="quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-check-and-install) first.

Install from PyPI:

```sh
pip install lol_monitor
```

Run the setup wizard:

```sh
lol_monitor --setup
```

The wizard asks for the Riot ID and region, the Riot API key and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for how to get the Riot API key and the region codes.

For the manual single-file method, optional dependencies and upgrade commands, see [Installation](installation.md).

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

* **Email alerts**: Receive match starts, finishes, summaries and errors.
* **Discord and ntfy**: Choose webhook events independently from email.
* **Champion artwork**: Include an optional icon in email, as a Discord thumbnail or as an ntfy attachment.

### ⚙️ Setup and Configuration

* **Guided setup**: Review and edit settings before saving with `--setup`.
* **Getting started**: Use the welcome screen, worked help examples and `--doctor` checks.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Runtime controls**: Adjust the running monitor through supported signals.
