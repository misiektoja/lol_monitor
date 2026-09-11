# lol_monitor

<p align="left">
  <img src="https://img.shields.io/github/v/release/misiektoja/lol_monitor?style=flat-square&color=blue" alt="GitHub Release" />
  <img src="https://img.shields.io/pypi/v/lol_monitor?style=flat-square&color=teal" alt="PyPI Version" />
  <img src="https://img.shields.io/github/stars/misiektoja/lol_monitor?style=flat-square&color=magenta" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/python-3.12+-blueviolet?style=flat-square" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/misiektoja/lol_monitor?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square" alt="Maintenance" />
  <img src="https://img.shields.io/github/last-commit/misiektoja/lol_monitor?style=flat-square&color=green" alt="Last Commit" />
</p>

Powerful tool for real-time monitoring of **LoL (League of Legends) players' activities**.

**Full documentation: [misiektoja.github.io/lol_monitor](https://misiektoja.github.io/lol_monitor/)**

<a id="-quick-install"></a>
<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/lol_monitor/installation/#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install lol_monitor
```

Run the setup wizard:

```sh
lol_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/lol_monitor/setup-and-first-run/) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](https://misiektoja.github.io/lol_monitor/installation/).

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/assets/lol_monitor.png" alt="lol_monitor_screenshot" width="90%"/>
</p>

## Features

- **Real-time tracking** of LoL players' gaming activity, including when a match starts and when it finishes
- **Detailed match reports** covering game mode, queue and map name, game type and version, victory or defeat, kills, deaths and assists, champion, achieved level, role, lane, both team rosters and banned champions
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

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](https://misiektoja.github.io/lol_monitor/usage/#command-format) for manual-script equivalents.

Replace the target placeholders with a Riot ID such as "Player#TAG" plus a region code such as euw1. Monitoring requires the [Riot API key](https://misiektoja.github.io/lol_monitor/setup-and-first-run/#riot-api-key) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `lol_monitor --setup` |
| Start monitoring with saved credentials | `lol_monitor "<riot_id>" <region>` |
| Check setup before monitoring | `lol_monitor --doctor "<riot_id>" <region>` |
| Enter or replace credentials through hidden prompts | `lol_monitor --set-riot-api-key` |
| Use a specific configuration and secrets file | `lol_monitor --config-file lol_monitor.conf --env-file .env "<riot_id>" <region>` |
| List recent matches | `lol_monitor "<riot_id>" <region> -l -n 10` |
| List every supported command-line option | `lol_monitor --help` |

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](https://misiektoja.github.io/lol_monitor/usage/). If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/lol_monitor/troubleshooting/#doctor-preflight).

## Documentation

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/lol_monitor/installation/) | Requirements, PyPI and manual installation, upgrading |
| [Setup & First Run](https://misiektoja.github.io/lol_monitor/setup-and-first-run/) | Getting a Riot API key, region codes, the first command to run |
| [Configuration](https://misiektoja.github.io/lol_monitor/configuration/) | Every setting the tool reads, SMTP, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/lol_monitor/usage/) | Monitoring and listing modes, notifications, CSV export, signal controls |
| [Utility Tools](https://misiektoja.github.io/lol_monitor/tools/) | The CSV format converter and the match history comparison tool |
| [Troubleshooting](https://misiektoja.github.io/lol_monitor/troubleshooting/) | What each error means and what to do about it |
| [Testing](https://misiektoja.github.io/lol_monitor/testing/) | Running the offline suite, the linter and the documentation build |

## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/lol_monitor/blob/main/RELEASE_NOTES.md) for details.

## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/lol_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/lol_monitor/blob/main/CODE_OF_CONDUCT.md).

## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/lol_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/lol_monitor/blob/main/SECURITY.md) covers the reporting process, the supported versions and the security posture of stored credentials and configuration loading.

## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/lol_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/lol_monitor/blob/main/THIRD_PARTY_NOTICES.md).

## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/lol_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
