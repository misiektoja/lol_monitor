# Installation

Install from PyPI for the usual case, or download the single script if you would rather not install a package. Once it is installed, continue with [Setup & First Run](setup-and-first-run.md).

## Requirements

* Python 3.12 or higher
* Libraries: [pulsefire](https://github.com/iann838/pulsefire), `requests`, `python-dateutil`, `python-dotenv`
* Optional: [pandas](https://pypi.org/project/pandas/), needed only by the [match history comparison tool](tools.md#match-history-comparison-tool)
* Optional: [wcwidth](https://pypi.org/project/wcwidth/), needed only to measure display width for [terminal truncation](configuration.md#terminal-truncation)

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

## Install from PyPI

```sh
pip install lol_monitor
```

## Manual Installation

Download the *[lol_monitor.py](https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/lol_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install pulsefire requests python-dateutil python-dotenv
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

## Upgrading

To upgrade to the latest version when installed from PyPI:

```sh
pip install lol_monitor -U
```

If you installed manually, download the newest *[lol_monitor.py](https://raw.githubusercontent.com/misiektoja/lol_monitor/refs/heads/main/lol_monitor.py)* file to replace your existing installation.

If you are upgrading from v1.7.2 or earlier and you keep a CSV match history, its columns changed. The [CSV format converter](tools.md#csv-format-converter) rewrites an old file into the current format.
