# Troubleshooting

If a dotenv file cannot be opened or is not UTF-8, monitoring stops with the file path and the repair step for that cause. Doctor reports the failed load and continues the remaining checks.

Every message the tool prints for a problem starts with `* Error:` or `* Warning:`. An error stops the run, a warning does not.

An error is printed as a block of up to three lines:

```
* Error: No Riot API key reached the tool
To fix: Pass it with -r, export RIOT_API_KEY or add it to a dotenv file, then run lol_monitor <riot_id> <region>
Guide: https://misiektoja.github.io/lol_monitor/configuration/#storing-secrets
```

`To fix:` is the one instruction worth trying first and the command in it is written for the way you installed the tool. `Guide:` appears when a page here covers the failure. The headings below are the `* Error:` line.

Most setup problems are easier to find before a run starts. `--doctor` reports all of them at once, described in the next section.

## Doctor Preflight

Before monitoring anything, `--doctor` checks whether the setup is actually ready and reports what is not:

```sh
lol_monitor --doctor <riot_id> <region>
```

Doctor writes no files. It checks **Environment**, **Configuration**, **Authentication**, **Connectivity**, **Target** and **Notifications**. Results use `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`. Follow the `To fix:` actions and guide links for warnings and failures.

Configuration checks cover the selected files, secret sources, timing settings and [TLS verification](configuration.md#tls-verification). Secret values are not displayed. The report also checks region routing.

Doctor checks whether the log and CSV destinations are writable.

Authentication validates the API key with Riot. The target check verifies the Riot ID in the selected region.

The Notifications section **signs in to the configured SMTP server** without sending anything, then checks the webhook destination, its headers and its alert choices without contacting the service. The private webhook URL is never displayed. Each ready row lists the **alert categories** that channel would deliver.

In an interactive terminal, Doctor offers one real test message per ready channel. Each needs separate approval and defaults to No. Noninteractive runs send no test messages.

The report ends with a **Next steps** block naming the command that starts monitoring, carrying the same `--config-file` and `--env-file` this run checked. It carries the target this run used, leaves it out when the configuration file already supplies both values and otherwise shows `<riot_id> <region>` for you to replace. While a check is failing it asks for the failures first.

It exits `0` when every check passed and `1` when any check or the approved delivery test failed, so it can be used as a container healthcheck or a CI smoke test. A `[WARN]` row never changes the exit code: running the preflight without naming a player warns that nothing will be monitored and still exits `0` when the rest of the setup is sound, the same as in the sibling monitors.

```sh
lol_monitor --doctor <riot_id> <region> && echo "ready"
```

Running doctor without a target checks everything except the monitored account. An explicitly selected dotenv path that does not exist is reported as a warning with the path and the recovery command.

## Verbose and Debug Output

Two flags control how much the tool explains about itself.

`--verbose` reports what the tool is doing in plain `* ` lines: which notification categories were switched off and why, and each message that was delivered. The delivery lines name the recipient or the webhook provider. Set `DELIVERY_CONFIRMATIONS = False` to drop them and keep the rest of verbose mode. During monitoring it stays quiet, so a run that finds nothing prints nothing beyond the liveness banner described under [What a Long Run Prints](#what-a-long-run-prints). Use `--debug` when you want a line per completed check.

Delivery confirmations name the email recipient or webhook provider without repeating the subject or message body. `DELIVERY_CONFIRMATIONS = False` hides those optional success receipts. Event output, send attempts and errors remain visible. Explicit notification tests report their result once. Generated email subjects and webhook titles use readable service names without a program-name prefix.

```sh
lol_monitor <riot_id> <region> --verbose
```

`--debug` traces the whole run in timestamped `[DEBUG HH:MM:SS]` lines. Each line names the operation, then lists its details as comma-separated `key=value` fields, so a long trace stays scannable:

```
[DEBUG 23:47:21] Riot account lookup: riot_id=Faker#KR1, region=kr, continent=asia
[DEBUG 23:47:21] Riot account lookup: riot_id=Faker#KR1, outcome=OK
```

Debug traces cover configuration loading, connectivity, monitoring API calls, notification delivery and file operations. Coverage varies by operation. One-shot lookups and calls made internally by dependencies do not always have matching result lines:

```sh
lol_monitor <riot_id> <region> --debug
```

`--debug` also appends the `Technical detail:` line to an error block whose underlying exception says something the summary did not, which is what a bug report needs. It also leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen. `--verbose` clears it like an ordinary run.

The two modes are independent, so pass both to see everything. Either can also be turned on permanently with the `VERBOSE_MODE` and `DEBUG_MODE` configuration settings. A flag on the command line always wins, so `--debug` still applies when the configuration file sets `DEBUG_MODE = False`.

Debug mode is the fastest way to find out why part of a report is missing. Ranked information, champion mastery and champion name lookups each degrade quietly when Riot refuses them, and debug names the call that failed.

Secret values are never printed by either mode. Redaction happens inside both printers rather than at each call site, so a known secret is replaced with `<redacted>` no matter which line interpolates it.

## What a Long Run Prints

During quiet monitoring, `* Monitoring healthy for <riot_id>` confirms the tool is still running and reports whether the player is in a match. `LIVENESS_CHECK_INTERVAL` defaults to 86400 seconds (24 hours). Set it to `0` to disable this reminder.

Temporary failures are reported after a short retry fails. Problems that need your action, such as a rejected API key, are reported immediately with a `To fix:` action. Use `--verbose` to see the first failed check.

Continuing outages produce a `* Monitoring degraded` reminder once an hour, even when liveness reminders are disabled. `* Monitoring recovered` marks recovery.

Follow any new instructions if the failure changes.

Temporary failures get one short retry before normal polling resumes. Rate limits use Riot's requested wait, subject to a safety cap. Rejected API keys need correction.

Error alerts follow the same throttling. A failure worth retrying is alerted once it has lasted **5 minutes**, so a blip of a check or two reaches nobody, while a rejected API key is alerted at once. Any monitoring failure delivers **one email and one webhook per outage**, not one per check, however the failure changes along the way. The next alert waits for a check to succeed first. Turn them off with `ERROR_NOTIFICATION = False` and the webhook error setting.

## When Something Goes Wrong

### `No Riot API key reached the tool`

No key reached the tool, or the key is still the shipped `your_riot_api_key` placeholder. Pass one with `-r`, export it, or put it in a dotenv file. See [Riot API Key](setup-and-first-run.md#riot-api-key).

### `Riot rejected the configured API key`

A development key expires 24 hours after it is issued, so this normally means the key aged out rather than that anything is wrong with the setup. Get a fresh key from [developer.riotgames.com](https://developer.riotgames.com), or apply for a persistent one.

If the key lives in a dotenv file you can replace the value and send `SIGHUP` to the running process instead of restarting it:

```sh
pkill -HUP -f "lol_monitor <riot_id> <region>"
```

### `No Riot ID was provided` or `No region was provided`

Both positionals are required to start monitoring. The message names whichever one is missing, and the fix line shows the complete command. A run with no arguments at all shows the [welcome screen](setup-and-first-run.md#quick-start) instead, since there is nothing yet to be missing.

### `'<region>' is not present in REGION_TO_CONTINENT`

The region is not one of the codes the tool knows. Use the short form, not the display name, and check it against [Region Codes](setup-and-first-run.md#region-codes). `EUW` is not a region code, `euw1` is. Capitalisation does not matter, so this is never about `EUN1` against `eun1`.

### `That is not a complete Riot ID`

A Riot ID has to be written as `name#tag`, and the tool refuses anything without the `#`. The part after the `#` is the tag line, not the region, which is a separate argument:

```sh
lol_monitor riot_id_name#tag euw1
```

### `Config file '<path>' does not exist`

`--config-file` names a file that is not there. The path is reported exactly as given, so check for a typo or an unexpanded `~`.

### `Config file '<path>' already exists and there is no terminal to confirm replacing it`

`--generate-config <filename>` will not overwrite a file it cannot ask about, which is what happens in a script, a cron job or a container build. Write to a different path, or pass `--force` to replace it after a timestamped backup.

### `Line N: unsupported configuration setting`

The configuration file is read as data and only documented settings are accepted. The reported line names the setting. A file that fails leaves every setting at its previous value rather than applying the lines above the bad one.

`Line N: <setting> must be a plain value` means the line holds an expression, a function call or a reference the parser will not evaluate. Only literals and a reference to another setting are allowed.

### `Warning: dotenv file '<path>' does not exist`

`--env-file` or `DOTENV_FILE` names a file that is not there. This is a warning rather than an error because the secrets may still arrive from the environment, so the run continues.

### `Warning: Cannot load dotenv file ... 'python-dotenv' is not installed`

Install it with `pip install python-dotenv`, or supply the secrets through environment variables instead.

### `The connectivity endpoint could not be reached`

The startup check could not reach `CHECK_INTERNET_URL`, which defaults to a Riot endpoint. A proxy that needs configuring, DNS that is not resolving or a firewall will all produce this. The setting can be pointed at another URL if that endpoint is blocked in your network.

### `certificate verify failed`

The certificate the server presented could not be traced to a trusted authority. On a corporate network this usually means a proxy is inspecting TLS with its own certificate authority, and the fix is to install that authority's certificate on this machine. `VERIFY_SSL = False` switches the check off everywhere as a last resort, with the cost described under [TLS Verification](configuration.md#tls-verification).

### `CSV file '<path>' cannot be opened for writing`

The path in `CSV_FILE` or `-b` is not writable. The tool checks this at startup rather than at the first match, so the run stops before it has anything to lose.

### Nothing arrives by email

Send one real message and read what happens:

```sh
lol_monitor --send-test-email
```

If any SMTP setting is still a shipped placeholder, email is switched off at startup and no message is attempted. Run with `--verbose` to have startup name the settings that are missing, or use `--doctor`, which reports the same thing in its Notifications section. See [SMTP Settings](configuration.md#smtp-settings).

### Nothing arrives by webhook

Send one real notification and read what happens:

```sh
lol_monitor --send-test-webhook
```

`--doctor` reports the same setup without sending anything. A destination that is not a complete HTTPS link, an unsupported provider, an invalid header or a transform naming a method that does not exist all fail the report by name. See [Webhook Settings](configuration.md#webhook-settings).

### `The webhook service returned HTTP <code>`

The service answered and refused the delivery. `401` or `403` usually means the webhook was deleted or the ntfy topic needs a token, `404` means the Discord webhook no longer exists and `413` means the message was too large for the service. The URL is never printed with the error, so check the saved destination with `--doctor` rather than reading it back from the screen.

### `The webhook service could not be reached`

The host did not answer. The delivery is retried once and then reported. Monitoring continues, so a webhook outage never stops a run.

### `Warning: Configured webhook provider did not match the URL`

`WEBHOOK_PROVIDER` says one service and `WEBHOOK_URL` points at the other. The URL wins, since a Discord payload posted to an ntfy topic is rejected. Set `--webhook-provider` explicitly if you are using a self-hosted host the tool cannot recognise.

### `That does not look like a complete HTTPS webhook URL`

`--set-webhook-url` refuses anything that is not a complete `https://` link with a path, and anything carrying a username or password in the URL. Copy the whole link from the service rather than the topic name or the channel name.

### `<flag> requires an interactive terminal`

`--set-riot-api-key`, `--set-smtp-password` and `--set-webhook-url` read the value hidden, which needs a terminal. In a script or a container write the dotenv file directly instead.

### `The setup wizard needs an interactive terminal (TTY)`

[`--setup`](setup-and-first-run.md#guided-setup) asks questions, so it needs a terminal to answer on. In a script or a container use `--generate-config` and edit the files instead.

### `--setup requires a config destination`

[`--setup`](setup-and-first-run.md#guided-setup) writes both files, so it cannot run with `--config-file none` or `--env-file none`. Give each one a writable path.

### `Setup cancelled` from the welcome screen

Ctrl+C at the welcome screen's `Run the guided setup wizard now?` offer ends the run with exit code 1. Nothing had been asked yet, so nothing was written. The wizard itself reports the longer message below.

### A bare run exits 1 in a script

Running with no arguments and no terminal to answer on prints the welcome screen and exits 1, the same as the argument error it replaced. Pass the Riot ID and region, or save them in the configuration file, and the run starts monitoring.

### `Setup cancelled. Destination files were not changed`

Ctrl+C during the questions, or choosing to discard the answers, ends setup without writing anything. Nothing reaches disk until you choose Save, so the previous configuration is still in place. An interrupt after the save says the setup is saved instead, and only skips the optional doctor run or launch.

### `The mail server settings are incomplete`

`--set-smtp-password` signs in before it saves, so it needs `SMTP_HOST`, `SMTP_USER`, `SENDER_EMAIL` and `RECEIVER_EMAIL` first. The message ends by naming the ones still unset and it appears before the password prompt, so nothing has to be typed first. Fill those in, then run it again. `--send-test-email` reports the same thing.

### A match is missing from the output

Some matches need an OAuth (RSO) access token that the tool does not hold. By default those are skipped without a notice. Set `INCLUDE_FORBIDDEN_MATCHES = True` or pass `-f` to see a notice where each one was skipped.

### Long lines wrap and make the output hard to read

Set `TRUNCATE_CHARS` or pass `--truncate N` to cut each screen line to a maximum width, with `999` to use the width of the terminal. The log file keeps the full line, which is also why the setting is ignored when logging is off with `-d`. Wide glyphs need the optional `wcwidth` library to be measured correctly and `--doctor` says whether that is installed. See [Terminal Truncation](configuration.md#terminal-truncation).

## Reporting a Problem

Include the version and the exact message you saw:

```sh
lol_monitor --version
```

Never paste a Riot API key, an SMTP password, a webhook URL or the contents of a dotenv file into an issue. Where to report what is covered in [SUPPORT.md](https://github.com/misiektoja/lol_monitor/blob/main/SUPPORT.md).

## Installation and Command Problems

If Python or `pip` is missing, use the [Python install walkthrough](installation.md#new-to-python-install-everything).

If `lol_monitor` is not found after installation, close the terminal and open it again. On Windows with Python Install Manager, run `py install --refresh` to refresh command aliases. For a pipx installation, run `pipx ensurepath` then reopen the terminal. If you downloaded the script, use the [manual command](usage.md#command-format) from its directory.

If `pip` reports an externally managed environment, follow the pipx steps in [Installation](installation.md#install-lol-monitor-after-python-check). Use `pipx upgrade lol_monitor` for later upgrades.

If the tool cannot import a dependency, install the dependencies with the same Python interpreter that runs the script. On macOS or Linux use `python3 -m pip install -r requirements.txt`. On Windows use `python -m pip install -r requirements.txt`. Match the requirements file to your downloaded script.

If a new terminal cannot find your saved settings, return to the directory used during setup or pass both `--config-file` and `--env-file` explicitly. Run `lol_monitor --doctor "<riot_id>" <region>` to see which settings are loaded.

## Invalid saved settings and state

If setup fails while saving, the configuration may already have changed. Correct the reported destination problem, rerun `--setup` with the same `--config-file` and `--env-file` paths then run `--doctor` before monitoring. The configuration backup restores non-secret settings only.

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.
