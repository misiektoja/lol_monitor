# Setup & First Run

## Quick Start

Grab a [Riot API key](#riot-api-key), then track a player by passing their Riot ID and region:

```sh
lol_monitor <riot_id> <region> -r "your_riot_api_key"
```

Or if you installed [manually](installation.md#manual-installation):

```sh
python3 lol_monitor.py <riot_id> <region> -r "your_riot_api_key"
```

A Riot ID is the game name plus the tag line, written as `riot_id_name#tag`. The region is the short code from [Region Codes](#region-codes) below, not the display name.

To list every supported command-line argument:

```sh
lol_monitor --help
```

Passing the key with `-r` puts it in your shell history. Once the first run works, move it into a dotenv file or an environment variable as described in [Storing Secrets](configuration.md#storing-secrets).

## Riot API Key

Get a development Riot API key, valid for 24 hours, from [developer.riotgames.com](https://developer.riotgames.com).

For anything longer than a day, apply for a persistent personal or production key at [developer.riotgames.com/app-type](https://developer.riotgames.com/app-type). Approval takes a few days.

Provide the `RIOT_API_KEY` secret one of these ways:

- Pass it at runtime with `-r` / `--riot-api-key`
- Set it as an [environment variable](configuration.md#storing-secrets), for example `export RIOT_API_KEY=...`
- Add it to a [dotenv file](configuration.md#storing-secrets) as `RIOT_API_KEY=...` for persistent use

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
