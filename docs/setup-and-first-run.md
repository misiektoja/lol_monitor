# Setup & First Run

<a id="run-the-setup-wizard"></a>
## Run the setup wizard

Already installed? Run the setup command below for your installation and follow the prompts. Otherwise, start with [Installation](installation.md).

Setup asks who to monitor, your Riot API key, how often to check and which alerts and output files you want. You can review your answers before saving. Regular settings go in `lol_monitor.conf` and private values go in `.env`. Keep `.env` private.

Press Enter to accept a default or Ctrl+C to cancel. Cancelling before saving leaves your files untouched. Cancelling after saving keeps the saved settings. For changes to an existing setup, see [Configuration File](configuration.md#configuration-file).

After saving, follow the offered Doctor checks and monitoring steps.

=== "PyPI"

    ```sh
    lol_monitor --setup
    ```

=== "Manual Python script on macOS or Linux"

    ```sh
    python3 lol_monitor.py --setup
    ```

=== "Manual Python script on Windows"

    ```powershell
    python lol_monitor.py --setup
    ```

A **target** is the League of Legends player you want to monitor. Enter the Riot ID as `riot_id_name#tag` and use a short code from [Region Codes](#region-codes). The wizard asks for your Riot API key and checks the account with Riot once the key is accepted. See [Riot API Key](#riot-api-key) for how to get one.

The polling prompts accept plain seconds or the `s`, `m`, `h` and `d` units. They show both the seconds and a readable form of the default.

With a saved target, running LoL Monitor without a target starts monitoring that player. If no target is saved, an interactive no-argument run offers setup.

<a id="before-you-start"></a>
## Before you start

You need three things before the first monitoring run:

1. A Riot ID. This is the game name plus the tag line, written as `riot_id_name#tag`.
2. A region code. Use the short form from [Region Codes](#region-codes), not the display name.
3. A Riot API key. See [Riot API Key](#riot-api-key).

<a id="riot-api-key"></a>
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

<a id="region-codes"></a>
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

<a id="not-sure-which-command-you-need"></a>
## Not sure which command you need?

| I want to... | Run this |
| --- | --- |
| Set up LoL Monitor for the first time | Use the setup command for your installation above |
| Start monitoring with an existing API key | `lol_monitor "<riot_id>" <region>` |
| Start the player saved in `RIOT_ID` and `REGION` | `lol_monitor --config-file lol_monitor.conf` |
| Check the API key, connectivity and one player | `lol_monitor --doctor "<riot_id>" <region>` |
| Most securely enter or replace `RIOT_API_KEY` | Run `lol_monitor --set-riot-api-key` and enter the key at the hidden prompt |
| Save an SMTP password for email alerts | Run `lol_monitor --set-smtp-password` |
| Send a test email | Run `lol_monitor --send-test-email` |
| Set up webhook alerts | Run the setup wizard and choose webhook alerts |
| Save a new webhook URL | Run `lol_monitor --set-webhook-url` |
| Send a test webhook | Run `lol_monitor --send-test-webhook` |
| List the ten most recent matches | `lol_monitor "<riot_id>" <region> -l -n 10` |
| Write every change to a CSV file | `lol_monitor "<riot_id>" <region> -b changes.csv` |
| List every supported command-line flag | `lol_monitor --help` |

<a id="run-individual-commands"></a>
## Run Individual Commands

The examples below use PyPI. For a manual script, replace `lol_monitor` with `python3 lol_monitor.py` on macOS or Linux. Use `python lol_monitor.py` on Windows and run it from the directory holding the script or give its full path. See [Command Format by Installation Method](usage.md#command-format-by-installation-method).

Throughout this page `<riot_id>` means the Riot ID written as `riot_id_name#tag` and `<region>` means its short region code.

<a id="save-the-riot-api-key"></a>
### Save the Riot API key

To configure credentials without the wizard, `--set-riot-api-key` is the recommended and most secure entry method. It reads the key through a hidden prompt, so the value does not appear on screen or in the command line. It checks the key with Riot before updating only `RIOT_API_KEY`. If the check fails, it does not change the `.env` file.

```sh
lol_monitor --set-riot-api-key
```

Use `--env-file PATH` to select another `.env` file. The `-r` and `--riot-api-key` options still work, but their values may appear in shell history or process listings.

<a id="save-notification-credentials"></a>
### Save notification credentials

The SMTP password is entered through a hidden prompt, checked against the mail server and saved as `SMTP_PASSWORD` in `.env`:

```sh
lol_monitor --set-smtp-password
```

A webhook URL is the private address used to deliver notifications. Treat it like a password because anyone who has it may be able to post through it. Follow the [webhook setup steps](configuration.md#webhook-settings) then save the link:

```sh
lol_monitor --set-webhook-url
```

The link is entered through a hidden prompt and saved as `WEBHOOK_URL` in `.env`. This command only saves the link. It does not turn on webhook alerts or send a message. See [Webhook Settings](configuration.md#webhook-settings) to choose your alerts then run `lol_monitor --send-test-webhook` to test them.

<a id="start-monitoring"></a>
### Start monitoring

The first example passes the player directly. The second uses a saved `RIOT_ID` and `REGION`:

```sh
lol_monitor "<riot_id>" <region>
lol_monitor --config-file lol_monitor.conf
```

For a [manual script](installation.md#install-the-manual-script):

```sh
python3 lol_monitor.py "<riot_id>" <region>
```

If a run does not start, check the setup before guessing at it:

```sh
lol_monitor --doctor "<riot_id>" <region>
```

That writes nothing and reports every part of the setup in one pass, described in [Doctor Preflight](troubleshooting.md#doctor-preflight).

To list every supported command-line argument, with worked examples for the common tasks at the end:

```sh
lol_monitor --help
```

<a id="next-step"></a>
## Next Step

Run [Doctor](troubleshooting.md#doctor-preflight) before an unattended run to confirm the API key, connectivity and notification settings.

With the API key saved and a first run working, continue to [Configuration](configuration.md) for the target player, SMTP, webhooks and secrets. See [Usage](usage.md) for command formats, monitoring, listing commands, notifications and output files.
