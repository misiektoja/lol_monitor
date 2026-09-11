# Troubleshooting

Every message the tool prints for a problem starts with `* Error:` or `* Warning:`. An error stops the run, a warning does not.

An error is printed as a block of up to three lines:

```
* Error: No Riot API key reached the tool
To fix: Pass it with -r, export RIOT_API_KEY or add it to a dotenv file, then run lol_monitor <riot_id> <region>
Guide: https://misiektoja.github.io/lol_monitor/configuration/#storing-secrets
```

`To fix:` is the one instruction worth trying first and the command in it is written for the way you installed the tool. `Guide:` appears when a page here covers the failure. The headings below are the `* Error:` line.

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

Both positionals are required to start monitoring. The message names whichever one is missing, and the fix line shows the complete command.

### `'<region>' is not present in REGION_TO_CONTINENT`

The region is not one of the codes the tool knows. Use the short form, not the display name, and check it against [Region Codes](setup-and-first-run.md#region-codes). `EUW` is not a region code, `euw1` is.

### `That is not a complete Riot ID`

A Riot ID has to be written as `name#tag`, and the tool refuses anything without the `#`. The part after the `#` is the tag line, not the region, which is a separate argument:

```sh
lol_monitor riot_id_name#tag euw1
```

### `Config file '<path>' does not exist`

`--config-file` names a file that is not there. The path is reported exactly as given, so check for a typo or an unexpanded `~`.

### `Line N: unsupported configuration setting`

The configuration file is read as data and only documented settings are accepted. The reported line names the setting. A file that fails leaves every setting at its previous value rather than applying the lines above the bad one.

`Line N: <setting> must be a plain value` means the line holds an expression, a function call or a reference the parser will not evaluate. Only literals and a reference to another setting are allowed.

### `Warning: dotenv file '<path>' does not exist`

`--env-file` or `DOTENV_FILE` names a file that is not there. This is a warning rather than an error because the secrets may still arrive from the environment, so the run continues.

### `Warning: Cannot load dotenv file ... 'python-dotenv' is not installed`

Install it with `pip install python-dotenv`, or supply the secrets through environment variables instead.

### `The connectivity endpoint could not be reached`

The startup check could not reach `CHECK_INTERNET_URL`, which defaults to a Riot endpoint. A proxy that needs configuring, DNS that is not resolving or a firewall will all produce this. The setting can be pointed at another URL if that endpoint is blocked in your network.

### `CSV file '<path>' cannot be opened for writing`

The path in `CSV_FILE` or `-b` is not writable. The tool checks this at startup rather than at the first match, so the run stops before it has anything to lose.

### Nothing arrives by email

Send one real message and read what happens:

```sh
lol_monitor --send-test-email
```

If the SMTP block is still filled with the shipped placeholders, email is switched off at startup and no message is attempted. See [SMTP Settings](configuration.md#smtp-settings).

### A match is missing from the output

Some matches need an OAuth (RSO) access token that the tool does not hold. By default those are skipped without a notice. Set `INCLUDE_FORBIDDEN_MATCHES = True` or pass `-f` to see a notice where each one was skipped.

## Reporting a Problem

Include the version and the exact message you saw:

```sh
lol_monitor --version
```

Never paste a Riot API key, an SMTP password or the contents of a dotenv file into an issue. Where to report what is covered in [SUPPORT.md](https://github.com/misiektoja/lol_monitor/blob/main/SUPPORT.md).
