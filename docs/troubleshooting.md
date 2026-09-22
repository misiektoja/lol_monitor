# Troubleshooting

Examples on this page use the PyPI command `lol_monitor`. If you installed the manual script, replace that command with the matching [command prefix](usage.md#command-format-by-installation-method).

<a id="doctor-preflight"></a>
## Doctor Preflight

`--doctor` checks a setup and prints one report instead of failing at the first problem:

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

<a id="common-problems"></a>
## Common Problems

Every failure is reported in the same three-part shape: what went wrong, a `To fix:` action and a `Guide:` link to the page that covers it. The fix command matches how you installed the tool and carries the `--config-file` or `--env-file` you started with, so it can be pasted as it is. `--debug` appends a `Technical detail:` line for bug reports. Secrets are redacted from all three.

| Symptom | Likely cause | Where to look |
| --- | --- | --- |
| `No Riot API key reached the tool` or `Riot rejected the configured API key` | The key is missing, expired or suspended | [Riot API Key](setup-and-first-run.md#riot-api-key) then run `--set-riot-api-key` |
| `That is not a complete Riot ID` | The Riot ID is missing its `#TAG` part, or the shell ate the `#` | Quote the whole value, for example `"Player#TAG"` |
| `'<region>' is not present in REGION_TO_CONTINENT` | The region code is not one of the supported platform routes | [Region Codes](setup-and-first-run.md#region-codes) |
| A match is missing from the output | Riot publishes match history with a delay, and some queues are excluded | [Check Intervals](usage.md#check-intervals) |
| The run stops naming a file and a line number | A configuration line is not a plain `SETTING = value` assignment | [Configuration File](configuration.md#configuration-file) |
| Emails never arrive | Incomplete SMTP settings | [SMTP Settings](configuration.md#smtp-settings) then run `lol_monitor --send-test-email` |
| Webhook alerts never arrive | Provider mismatch or a stale destination | [Webhook Settings](configuration.md#webhook-settings) then run `lol_monitor --send-test-webhook` |
| `lol_monitor` is not found after installation | The shell has not picked up the new command | [Installation and Command Problems](#installation-and-command-problems) |
| Escape sequences such as `[36m` printed as text or no colour at all | The terminal cannot display ANSI colour or colour was switched off | [Terminal Colours Look Wrong](#terminal-colours-look-wrong) |
| `The Riot API did not answer in time`, `The Riot API could not be reached` or `The Riot API is temporarily unavailable` | A network problem between this machine and the Riot API or a Riot outage | [Connection Problems](#connection-problems) |
| `This process ran out of file descriptors` | The operating system limit on open files was reached | [Too Many Open Files](#too-many-open-files) |

A continuing outage produces a `* Monitoring degraded` reminder once an hour, even when the [liveness reminder](usage.md#liveness-reminder) is switched off. `* Monitoring recovered` marks recovery. Use `--verbose` to see the first failed check.

If a dotenv file cannot be opened or is not UTF-8, monitoring stops with the file path and the repair step for that cause. Doctor reports the failed load and continues the remaining checks.

<a id="connection-problems"></a>
## Connection Problems

`The Riot API did not answer in time` and `The Riot API could not be reached` mean a check got no answer from the Riot API. `The Riot API is temporarily unavailable` means the Riot API answered with a server error. The report names the interval after which the check is retried, so a short outage needs no action. A failure that lasts produces the hourly `Monitoring degraded` reminder and `Monitoring recovered` when it clears.

If the failure continues, check the internet connection, DNS and any firewall or proxy between this machine and the Riot API. A certificate failure on a network that intercepts TLS is covered by [TLS Verification](configuration.md#tls-verification). A server error that lasts is a Riot outage, so wait for it to end.

To confirm that the Riot API is reachable from this machine, run:

```sh
lol_monitor --doctor
```

<a id="too-many-open-files"></a>
## Too Many Open Files

`This process ran out of file descriptors` means the operating system limit on open files was reached. It is a local limit and not a Riot API problem. Raise it with `ulimit -n 4096` in the shell that starts the tool or set `LimitNOFILE=` in the systemd unit, then restart the tool.

<a id="terminal-colours-look-wrong"></a>
## Terminal Colours Look Wrong

If escape sequences such as `[36m` appear as literal text, the terminal does not understand ANSI colour. Start the tool with `--no-color` or set `COLORED_OUTPUT = False` in the configuration file.

If colour is missing where you expect it, check in this order: `--no-color` on the command line, `COLORED_OUTPUT` in the configuration file, a `NO_COLOR` environment variable and whether output is redirected or piped. Colour is switched off in all of those cases and also when `TERM` is unset or set to `dumb`.

Log files never contain colour by design. To colour a saved log while reading it, see [Coloring Log Output with GRC](usage.md#coloring-log-output-with-grc).

To change which colours are used, see [Terminal Colours](configuration.md#terminal-colours).

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** reports activity changes and important errors
- **Verbose mode (`--verbose`)** adds occasional state changes, a line naming where each delivered alert went and a complete startup summary without private values. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without those delivery lines
- **Debug mode (`--debug`)** adds sanitized request flow, scheduling details and internal diagnostics

Delivery confirmations name the recipient or webhook provider. `DELIVERY_CONFIRMATIONS = False` hides these optional success messages. Monitoring events, send attempts and errors remain visible.

Both `--verbose` and `--debug` show the complete startup summary, including notification settings and credential sources. Use it to check which configuration is active without displaying private values.

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.

<a id="verbose-and-debug-output"></a>
## Verbose and Debug Output

`--verbose` adds the decisions a run made, in the same `*` lines as the rest of the output:

```sh
lol_monitor <riot_id> <region> --verbose
```

`--debug` traces what the tool is doing in timestamped `[DEBUG HH:MM:SS]` lines:

```sh
lol_monitor <riot_id> <region> --debug
```

Lines with details read `Operation: key=value, key=value`. Fields depend on the operation. Some results report `outcome=OK`, `failed`, `degraded` or `skipped`.

<a id="installation-and-command-problems"></a>
## Installation and Command Problems

If Python or `pip` is missing, use the [Python install walkthrough](installation.md#new-to-python-check-and-install).

If `lol_monitor` is not found after installation, close the terminal and open it again. On Windows with Python Install Manager, run `py install --refresh` to refresh command aliases. For a pipx installation, run `pipx ensurepath` then reopen the terminal. If you downloaded the script, use the [manual command](usage.md#command-format-by-installation-method) from its directory.

If `pip` reports an externally managed environment, follow the pipx steps in [Installation](installation.md#install-lol-monitor). Use `pipx upgrade lol_monitor` for later upgrades.

If the tool cannot import a dependency, install the dependencies with the same Python interpreter that runs the script. On macOS or Linux use `python3 -m pip install -r requirements.txt`. On Windows use `python -m pip install -r requirements.txt`. Match the requirements file to your downloaded script.

If a new terminal cannot find your saved settings, return to the directory used during setup or pass both `--config-file` and `--env-file` explicitly. Run `lol_monitor --doctor "<riot_id>" <region>` to see which settings are loaded.

<a id="invalid-saved-settings-and-state"></a>
## Invalid saved settings and state

If setup fails while saving, the configuration may already have changed. Correct the reported destination problem, rerun `--setup` with the same `--config-file` and `--env-file` paths then run `--doctor` before monitoring. The configuration backup restores non-secret settings only.

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.
