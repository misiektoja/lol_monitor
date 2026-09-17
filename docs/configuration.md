# Configuration

Examples on this page use the PyPI command `lol_monitor`. Manual script users should keep the shown options and use the matching prefix under [Command Format by Installation Method](usage.md#command-format-by-installation-method).

<a id="configuration-file"></a>
## Configuration File

You can pass most settings as command-line options or save them in a configuration file for later runs.

The easiest way to create this file is `lol_monitor --setup`.

To edit every available setting yourself, generate a default configuration file:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
lol_monitor --generate-config > lol_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
lol_monitor --generate-config lol_monitor.conf
```

> **Windows PowerShell:** Pass the filename directly to `--generate-config`. PowerShell redirection can write UTF-16, which the tool rejects with a "null bytes" error.

When the named file already exists, `--generate-config` asks before replacing it and keeps a timestamped `.bak` backup next to it. Add `--force` to replace it without the question.

The file contains a short explanation above each setting.

A configuration file is read as data, not executed. The tool accepts only `SETTING = value` lines where the name is one of the documented settings and the value is a plain literal such as a string, number, `True`, `False`, `None`, a list or a dictionary. Comments and blank lines are fine.

Imports, function calls, expressions and unknown settings are rejected with the setting and line number to correct.

If the same setting appears in more than one place, the item later in this list wins:

1. Built-in defaults
2. The discovered or explicitly selected configuration file
3. Values from the selected `.env` file
4. Secret environment variables
5. Command-line options

By default the tool looks for a configuration file named `lol_monitor.conf` in the current directory, the home directory (`~`) and the script directory. Use `--config-file` to name another location, or `--config-file none` to disable automatic config discovery for one run.

<a id="monitored-target"></a>
## Monitored Target

The Riot ID and the region are positional arguments. Both are required to start monitoring:

```sh
lol_monitor <riot_id> <region>
```

A Riot ID is the game name plus the tag line, written as `riot_id_name#tag`. The accepted region codes are listed under [Region Codes](setup-and-first-run.md#region-codes). Region codes are not case sensitive, and spaces around the `#` are ignored, so `" Name # TAG "` and `EUN1` are read the same as `Name#TAG` and `eun1`.

To stop repeating them, save the pair in the configuration file:

```ini
RIOT_ID = "riot_id_name#tag"
REGION = "eun1"
```

Then `lol_monitor` alone starts monitoring that player. A positional argument still wins, so you can watch someone else for one run without editing the file:

```sh
lol_monitor "other_name#tag" euw1
```

<a id="smtp-settings"></a>
## SMTP Settings

Email notifications need SMTP server details for the sending account. Add them to `lol_monitor.conf` or use the setup wizard. Setup checks the login without sending an email. To replace only the password, run `lol_monitor --set-smtp-password`. Password entry is hidden and preserves spaces.

Send one test message to verify the settings:

```sh
lol_monitor --send-test-email
```

<a id="champion-icon-in-email"></a>
### Champion Icon in Email

`EMAIL_IMAGES = True` embeds the champion icon at the end of the in-game and match summary emails, under the timestamp. The icon is the one the Data Dragon release serves for the champion the player used, downloaded at send time and attached to the message, so it shows without the mail client fetching anything remote.

Alerts that name no champion, such as an error alert, are unaffected. If the download fails or returns something that is not a small image, the email is sent as text only.

[`--setup`](setup-and-first-run.md#run-the-setup-wizard) offers the setting once match emails are enabled.

<a id="webhook-settings"></a>
## Webhook Settings

Webhooks send the same alerts as email to a Discord channel or an ntfy topic. They are switched off until you set a destination. [`--setup`](setup-and-first-run.md#run-the-setup-wizard) collects the service, the destination and the alert switches together:

| Setting | Meaning |
| --- | --- |
| `WEBHOOK_ENABLED` | Master switch for the channel |
| `WEBHOOK_PROVIDER` | `discord` or `ntfy` |
| `WEBHOOK_URL` | The private destination, best kept in a dotenv file |
| `WEBHOOK_USERNAME` | Discord display name, empty to use the webhook default |
| `WEBHOOK_AVATAR_URL` | Discord avatar URL, empty to use the webhook default |
| `WEBHOOK_STATUS_NOTIFICATION` | Send an alert when the player's status changes |
| `WEBHOOK_ERROR_NOTIFICATION` | Send an alert on monitoring errors, on by default |
| `WEBHOOK_HEADERS` | Extra request headers, for example ntfy options |
| `NTFY_ACCESS_TOKEN` | Bearer token for a private ntfy topic |
| `NTFY_IMAGES` | Attach the champion icon to ntfy alerts |

Save the destination without putting it in a file you might share:

```sh
lol_monitor --set-webhook-url
```

The URL is typed hidden, checked for shape, and written to the dotenv file with owner-only permissions. The command names the service it recognised so you can tell a mistyped destination from the right one.

The destination decides the service. A `https://ntfy.sh/...` link is treated as ntfy and a Discord webhook link as Discord, even when `WEBHOOK_PROVIDER` says otherwise. While `WEBHOOK_PROVIDER` is left at its default, that detection is silent and `--verbose` reports it. A warning appears only when your configuration file sets a provider the URL disagrees with. Pass `--webhook-provider` to override that for a self-hosted host the tool cannot recognise.

Send one real notification to check the setup:

```sh
lol_monitor --send-test-webhook
```

Email and webhooks are independent. Both can be on, and each keeps its own alert settings, so you can take errors on ntfy and status changes by mail.

<a id="ntfy"></a>
### ntfy

`WEBHOOK_URL` is the complete topic URL, such as `https://ntfy.sh/your-private-topic`. Anyone who knows a public topic name can read it, so pick an unguessable one or use a private server with `NTFY_ACCESS_TOKEN`.

The alert body is sent as a native ntfy message with the subject as its title. ntfy rejects a message over 4 KB, so a long alert is cut with a note saying that it was.

Add ntfy options through `WEBHOOK_HEADERS`:

```python
WEBHOOK_HEADERS = {"X-Priority": "4", "X-Tags": "video_game"}
```

`NTFY_IMAGES = True` attaches the champion icon to the alerts that name a champion, taken from the same Data Dragon release the champion names come from. ntfy shows it as the notification image and the alert text travels beside it, so the message reads the same as without the icon. An alert with no champion is sent as text, and an attachment the server rejects is retried once as a text-only alert so the alert itself still arrives.

[`--setup`](setup-and-first-run.md#run-the-setup-wizard) offers the setting when the destination is an ntfy topic and match alerts are enabled.

<a id="discord"></a>
### Discord

`WEBHOOK_URL` is the link from **Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL**. Anyone holding it can post to that channel.

Alerts are sent as an embed built from `WEBHOOK_TEMPLATE`, which supports the `title`, `description`, `version`, `image_url`, `fields`, `fields_str`, `color`, `timestamp`, `username` and `avatar_url` placeholders. Mentions are disabled on every message the tool sends, whatever the template says.

`image_url` holds the champion icon on the alerts that name a champion, the in-game announcement and the finished match summary, taken from the Data Dragon release the run read its champion names from. The default template shows it as the embed thumbnail. Alerts with no champion leave it empty and the thumbnail is dropped rather than sent blank.

Discord alerts carry the same emphasis as the HTML email, since Discord renders markdown in an embed. Bold values stay bold, links stay clickable and the monitored player's own roster line is marked. Only Discord gets that wording: ntfy receives the plain body, because it would show the markers literally.

<a id="advanced-discord-format-customization"></a>
### Advanced Discord-format customization

`WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` change the sender name and HTTPS avatar for Discord-format payloads. Leave either empty to keep the webhook's own value:

```ini
WEBHOOK_USERNAME = "LoL Monitor"
WEBHOOK_AVATAR_URL = "https://example.com/path/avatar.png"
```

`WEBHOOK_TEMPLATE` controls the Discord-format request body. It supports these placeholders:

- `{title}`
- `{description}`
- `{version}`
- `{image_url}`
- `{fields}` and `{fields_str}`
- `{color}`
- `{timestamp}`
- `{username}`
- `{avatar_url}`

Discord templates must produce a JSON object. Use a dictionary or a JSON string encoding an object, including legacy strings with doubled object braces. Lists, non-JSON strings and unsupported placeholders are rejected before delivery. Alert text is kept literal and all payloads replace `allowed_mentions` with `{"parse": []}` so alert text cannot trigger Discord mentions. Reloaded settings apply to the next delivery.

`WEBHOOK_TRANSFORMS` applies string methods to shared placeholder values before the template and headers are rendered:

```ini
WEBHOOK_TRANSFORMS = [
    ("title", "upper"),
    ("description", "replace", "**", ""),
    ("description", "strip"),
]
```

The tuple format is `(field_to_target, method_name, *optional_arguments)`. Invalid templates, avatar URLs, transforms or formatted headers fail before a request is attempted. `WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` apply only to the Discord request format and are ignored when `WEBHOOK_PROVIDER` is `"ntfy"`. ntfy continues to use its native publish API while transformations and header placeholders use the same shared title and description values.

<a id="storing-secrets"></a>
## Storing Secrets

Keep `RIOT_API_KEY`, `SMTP_PASSWORD`, `WEBHOOK_URL` and `NTFY_ACCESS_TOKEN` in an environment variable or a dotenv file rather than in the configuration file.

[`--setup`](setup-and-first-run.md#run-the-setup-wizard) writes every secret it collects to the dotenv file, and never to the configuration file. To store one on its own afterwards, the tool can write the dotenv file for you. Each command reads the value hidden, checks it against the real service and only then saves it:

```sh
lol_monitor --set-riot-api-key
```

```sh
lol_monitor --set-smtp-password
```

```sh
lol_monitor --set-webhook-url
```

`--set-riot-api-key` checks the key with Riot. `--set-smtp-password` checks mail sign-in without sending a message. `--set-webhook-url` checks the HTTPS URL. Failed checks leave the saved value unchanged. Replacements require confirmation and the dotenv file has owner-only permissions. Use `--env-file PATH` to choose another file. An exported `SMTP_PASSWORD` overrides the saved value at startup.

Set environment variables with `export` on **Linux, Unix, macOS and WSL**:

```sh
export RIOT_API_KEY="your_riot_api_key"
export SMTP_PASSWORD="your_smtp_password"
```

On **Windows Command Prompt** use `set` instead of `export`, and on **Windows PowerShell** use `$env`.

Storing them in a dotenv file is usually easier:

```ini
RIOT_API_KEY="your_riot_api_key"
SMTP_PASSWORD="your_smtp_password"
WEBHOOK_URL="https://ntfy.sh/your-private-topic"
```

By default the tool searches for a file named `.env` in the current directory and then upward from it.

Select a specific file with the `DOTENV_FILE` setting or the `--env-file` flag:

```sh
lol_monitor <riot_id> <region> --env-file /path/.env-lol_monitor
```

Disable the search entirely with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
lol_monitor <riot_id> <region> --env-file none
```

As a fallback both values can also live in the configuration file or the source.

<a id="terminal-colours"></a>
## Terminal Colours

Colour is on by default and marks what a value is rather than decorating the line: player names, identifiers, champions, ranks, dates, links and the `[PASS]`/`[WARN]`/`[FAIL]`/`[SKIP]` markers each get their own colour. In a match roster the monitored player's own entry is bold, through the `monitored_username` part, so their line stands out among the nine others. The log file is never coloured, so a log attached to a bug report stays plain text. `COLORED_OUTPUT` and `COLOR_THEME` apply to monitoring output and to the [`--setup`](setup-and-first-run.md#run-the-setup-wizard), `--doctor` and `--help` screens alike.

The `--help` screen is coloured too. Group headings, option names, the values those options take, the example commands and the comments above them each get their own colour, so the screen can be scanned instead of read.

Colour switches itself off when the output is not a terminal you are watching. That covers redirected or piped output, a `NO_COLOR` environment variable of any value, a `TERM` of `dumb` or empty and a `--no-color` run. The startup summary reports the resolved state next to the setting, so `False (setting: True)` means colour was configured but the terminal did not qualify.

To change a colour, uncomment the `COLOR_THEME` block in your configuration file and edit the parts you want. Every part you leave out keeps its built-in colour:

```python
COLOR_THEME = {
    "username": "bright_cyan underline",
    "error": "red",
}
```

A style is a space-separated list of one colour and any attributes. Colours are `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` and their `bright_` forms. Attributes are `bold`, `dim`, `underline` and `blink`. An empty string leaves that part uncoloured, and an unknown name is ignored.

The block ships commented out so the tool's own colours apply and later improvements reach existing configuration files. Overrides you added are written back as a real block when setup rebuilds the file, so they are not lost. Once you uncomment it, the parts inside it are pinned to whatever you saved, so delete the block again to go back to the current defaults.

<a id="tls-verification"></a>
## TLS Verification

Every outbound connection verifies the server's TLS certificate: the Riot API, the Data Dragon champion data, the startup connectivity check and email delivery. Leave it that way unless you have a reason not to.

`VERIFY_SSL = False` turns verification off for all of them at once. Do this only on a network that inspects TLS with its own certificate authority, such as a corporate proxy, and only when you cannot install that authority's certificate instead. With verification off, an intercepted connection looks the same as the real service, so your Riot API key can be read in transit.

The startup summary reports the state as `TLS verification: On` or `Off, server certificates are not checked`. The row is only shown without `--verbose` while verification is off, since a run that stopped checking certificates should say so unasked.
