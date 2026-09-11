# Setup & First Run

Printed commands use short names. Activate the tool's virtual environment before running them. For a downloaded script, run them from the script directory. Recovery commands retain selected configuration and dotenv paths.

Before replacing a configuration, setup copies retained inline credentials to the selected private dotenv file when that file has no value for the same key. An existing dotenv value, including an explicit empty value, keeps precedence. If preservation fails, the original configuration stays in place. Setup backups omit inline credentials.

When rebuilding an existing configuration, setup keeps its saved `DOTENV_FILE` unless you pass `--env-file PATH`. A nonempty exported secret takes precedence over the dotenv file. An explicit empty value in that file still overrides the configuration, both after saving and on the next run. Quoted dotenv keys receive the same replacement confirmation as unquoted keys.

Setup replaces each file separately. If saving secrets fails after the configuration was saved, setup stops and identifies the saved configuration. Correct the destination then rerun `--setup` with the same `--config-file` and `--env-file`, review the settings and run `--doctor` before monitoring. A crash between replacements can also leave a new configuration beside the previous dotenv file. The configuration backup can recover non-secret settings. Replaced secrets are not backed up.

## Before You Start

Install the tool using [Installation](installation.md). You will need a Riot ID such as "Player#TAG" plus a region code such as euw1 and the [Riot API key](#riot-api-key). The wizard collects credentials through hidden prompts.

Open a terminal in the directory where you want to keep the configuration and monitoring output. Later commands should use that directory or explicitly select the same `--config-file` and `--env-file` paths. Manual installations use the [command equivalents](usage.md#command-format).

<a id="setup-wizard"></a>
## Guided Setup

The quickest way to a working configuration is to answer a few questions:

```sh
lol_monitor --setup
```

It asks for the Riot ID and region to monitor, whether to save that target in the config file, how often to check while the player is in a game and while they are not, your Riot API key, whether you want email or webhook alerts and where output goes. The output questions ask whether to write the per-target log file and whether to write a CSV file, and the CSV path is asked for only after you say yes, so answering no clears a saved one. A CSV path with no extension is saved with `.csv` added. Enter accepts the shown default and Ctrl+C cancels. **Nothing is written until you choose Save**: the answers are held until the end, where a summary shows exactly what is about to be written and lets you go back and change **one section without losing the other answers**. The summary's **File destinations** section changes where the configuration and dotenv files are written. Moving the dotenv file asks the authentication and notification questions again, since a secret you chose to keep was never going to reach the new file.

Answers are accepted in the formats people actually paste. The Riot ID takes the game name plus the tag line written as `riot_id_name#tag`, and the region takes the short code from [Region Codes](#region-codes) rather than the display name. Intervals take **`30s`, `2m`, `1.5h`, `1h 30m`, `1d`** or a plain number of seconds. Supported units are `s`, `m`, `h` and `d`. Once the API key step has a key Riot accepts, setup asks Riot whether that account exists, so a mistyped game name or the wrong region is caught before anything is written.

For webhook alerts, setup asks which service receives them, then takes the Discord webhook URL or an ntfy topic. A bare ntfy.sh topic name is expanded to its full URL. For ntfy it also offers a separate access token.

Every answer setup cannot use offers a way out, so one value you cannot produce right now does not cost you the answers already given. A blank answer asks whether to continue without it and names what stops working, and a rejected one offers to enter it again. Declining switches the channel that needed it off, so half a mail server or a webhook with no destination is never written. Email setup signs in to the mail server before saving, so a wrong password or an unreachable host is caught during setup instead of at the first alert. No email is sent. A refused sign-in offers the mail server questions again, and if the server was only unreachable the answers are kept so `--doctor` can check them later.

Secrets are typed at a hidden prompt and go to the dotenv file. Non-secret settings go to the config file. Both destinations are checked before the first question, so an unwritable path or a directory given by mistake is reported straight away rather than after you have answered everything. `--setup` needs somewhere to put both files, so it refuses `--config-file none` and `--env-file none`. A configuration file already in place is replaced only after you agree, and setup offers to write somewhere else instead. The replaced file is backed up first. A rebuilt file starts from the settings already in place with your answers applied over them, and a setting you left alone keeps the wording the template ships. A section you decline is cleared rather than carried over, so declining email leaves no mail server behind. A secret already in the dotenv file is never replaced without asking. The dotenv file is replaced without a backup, so the secret you replaced is not left behind in a `.bak` file. When it finishes, setup offers to run [`--doctor`](troubleshooting.md#doctor-preflight) and prints the exact commands to start monitoring. It then offers to **start monitoring right away** once that doctor run passed.

Setup runs before any connectivity check, so a machine with no network can still be configured. If there is no terminal to answer on, setup says so and points at `--generate-config` instead of hanging.

If the config file names a target in [`RIOT_ID` and `REGION`](configuration.md#target-profile), running the tool with no arguments starts monitoring that player. With no saved target, running it **with no arguments at all** prints the commands worth starting with and offers to open the wizard. Answering that offer exits 0. With no terminal to answer on there is no offer, so the run exits 1 like the argument error it replaced.

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
