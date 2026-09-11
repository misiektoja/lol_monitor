# Setup & First Run

## Before You Start

Install the tool using [Installation](installation.md). You will need a Riot ID such as "Player#TAG" plus a region code such as euw1 and the [Riot API key](#riot-api-key). The wizard collects credentials through hidden prompts.

Open a terminal in the directory where you want to keep the configuration and monitoring output. Later commands should use that directory or explicitly select the same `--config-file` and `--env-file` paths. Manual installations use the [command equivalents](usage.md#command-format).

<a id="setup-wizard"></a>
## Guided Setup

The quickest way to a working configuration is to answer a few questions:

```sh
lol_monitor --setup
```

The wizard asks for the Riot ID and region, whether to save the target, separate polling intervals for active and idle players, your Riot API key, alerts and output files. Press Enter to accept a default. Review or change any section before choosing **Save**. Ctrl+C cancels without saving.

Enter the Riot ID as `riot_id_name#tag` and use a short code from [Region Codes](#region-codes). Setup checks the account with Riot once your API key is accepted. Intervals accept seconds or durations such as `30s`, `2m`, `1.5h`, `1h 30m` and `1d`.

For webhook alerts, setup asks which service receives them, then takes the Discord webhook URL or an ntfy topic. A bare ntfy.sh topic name is expanded to its full URL. For ntfy it also offers a separate access token.

Setup explains invalid answers and lets you retry or continue with the affected feature disabled. Email setup checks sign-in without sending a message. If the mail server is unreachable, check the saved settings later with `--doctor`.

Secrets go to `.env` and other settings go to `lol_monitor.conf`. Setup asks before replacing files or saved secrets. A rerun uses saved settings as defaults. Declining a section disables it. See [Storing Secrets](configuration.md#storing-secrets) for backup details.

Use `--config-file PATH` and `--env-file PATH` or the summary's **File destinations** section to choose other files. Both paths must be writable. `--config-file none` and `--env-file none` are not supported by setup.

After saving, setup offers [Doctor Preflight](troubleshooting.md#doctor-preflight) and can start monitoring once the checks pass.

Setup runs before any connectivity check, so a machine with no network can still be configured. If there is no terminal to answer on, setup says so and points at `--generate-config` instead of hanging.

With [`RIOT_ID` and `REGION`](configuration.md#target-profile) saved, running without arguments starts monitoring that player. Otherwise, it shows starting commands and offers the wizard in an interactive terminal.

## Quick Start

Run the tool with no arguments to see the commands to start from, and to be offered the guided setup:

```sh
lol_monitor
```

Or grab a [Riot API key](#riot-api-key) and track a player by passing their Riot ID and region:

```sh
lol_monitor --set-riot-api-key
lol_monitor "<riot_id>" <region>
```

Or if you installed [manually](installation.md#manual-installation):

```sh
python3 lol_monitor.py --set-riot-api-key
python3 lol_monitor.py "<riot_id>" <region>
```

A Riot ID is the game name plus the tag line, written as `riot_id_name#tag`. The region is the short code from [Region Codes](#region-codes) below, not the display name.

If a run does not start, check the setup before guessing at it:

```sh
lol_monitor --doctor <riot_id> <region>
```

That writes nothing and reports every part of the setup in one pass, described in [Doctor Preflight](troubleshooting.md#doctor-preflight).

To list every supported command-line argument, with worked examples for the common tasks at the end:

```sh
lol_monitor --help
```

The hidden prompt saves the key to a dotenv file. See [Storing Secrets](configuration.md#storing-secrets) for other supported sources.

## Riot API Key

Get a development Riot API key, valid for 24 hours, from [developer.riotgames.com](https://developer.riotgames.com).

For anything longer than a day, apply for a persistent personal or production key at [developer.riotgames.com/app-type](https://developer.riotgames.com/app-type). Approval takes a few days.

Provide the `RIOT_API_KEY` secret one of these ways:

- Answer the questions in `--setup`, which checks the key with Riot and saves it for you (recommended)
- Save and check it through a hidden prompt with [`--set-riot-api-key`](configuration.md#storing-secrets)
- Set it as an [environment variable](configuration.md#storing-secrets), for example `export RIOT_API_KEY=...`
- Add it to a [dotenv file](configuration.md#storing-secrets) as `RIOT_API_KEY=...` for persistent use
- Pass it at runtime with `-r` / `--riot-api-key`

As a fallback you can hard-code it in the configuration file or the source.

A development key expires every 24 hours, so a run that worked yesterday will report an unauthorized error today. If you keep the key in a dotenv file, you can replace the value and send `SIGHUP` to the running process to load the new key without restarting. See [Storing Secrets](configuration.md#storing-secrets) and [Signal Controls](usage.md#signal-controls-macoslinuxunix).

## Region Codes

Pass the short form of the region, not the display name:

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

A region that is not in this list is refused at startup rather than guessed at. The mapping from region to routing continent lives in the `REGION_TO_CONTINENT` setting, so a region Riot adds later can be added there without waiting for a release.

## Continue with Usage

Use [Usage](usage.md) for monitoring and output options or [Configuration](configuration.md) to adjust saved settings. If setup or monitoring fails, run [Doctor Preflight](troubleshooting.md#doctor-preflight) and follow the reported recovery steps.
