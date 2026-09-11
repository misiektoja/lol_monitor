# Offline test suite

These tests cover logic in `lol_monitor.py` that can run without network access.
Riot API calls are replaced with test doubles.

## Running

From the repository root:

```bash
pip install -e '.[test]'
python -m pytest
```

`pyproject.toml` puts the repository root first on `sys.path`, so the tests use the
working tree instead of an installed copy of the module.

Lint the same way CI does:

```bash
pip install -e '.[lint]'
python -m ruff check lol_monitor.py tools tests
```

Build the documentation the same way CI does, which fails on a broken link or a
page missing from the navigation:

```bash
pip install -r docs/requirements.txt
mkdocs build --strict
```

CI runs all three on every push and pull request, across Python 3.12 through 3.14,
and again before anything is published to PyPI.

## Layout

| File | Area under test |
| --- | --- |
| `conftest.py` | Import setup, deterministic globals and the Riot API, SMTP and clock test doubles |
| `test_cli_startup.py` | Command line handling, config and dotenv loading, startup validation, listing mode and the effective-settings banner |
| `test_config_loading.py` | Declarative config parsing, retired settings and refusal of executable config content |
| `test_csv_output.py` | The CSV match history, its columns and the custom game rows saved from a live snapshot |
| `test_documentation.py` | The documentation site: navigation, links into and out of it, page structure and claims about flags and tooling |
| `test_email_html.py` | The HTML notification body and escaping of names taken from Riot |
| `test_email_notifications.py` | SMTP validation, the delivered message and failure handling |
| `test_match_formatting.py` | Riot IDs, game type and patch labels, participant names, team rosters and ban lists |
| `test_match_reporting.py` | The finished-match report, the in-game report, live snapshots and match history listing |
| `test_monitoring_loop.py` | End-to-end monitoring runs: profile startup, new match detection, in-game and stopped alerts, custom game saves and error recovery |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and the CI contract |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_riot_api_client.py` | The Riot API wrappers, pagination, champion name lookup and rejected API keys |
| `test_runtime_controls.py` | Signal-driven toggles, interval changes, secret reload and the log output filter |
| `test_time_formatting.py` | Durations, timespans and timestamp formats |

## Conventions

* Keep every test offline. If a code path needs network access, stub it with
  `monkeypatch` rather than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a
  leaked global affects whatever runs next.
* Replace Riot Games calls and notification delivery with test doubles.
* Never use a real Riot API key, SMTP password or webhook URL.

A change to the monitoring loop, authentication or Riot Games data handling is not
verified by this suite alone. Exercise it against a real account and say so in the
pull request, without usernames or credentials.
