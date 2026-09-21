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
| `test_notification_receipts.py` | SMTP acceptance despite cleanup failures, receipt controls and unchanged notification content |
| `test_configuration_notification_boundaries.py` | Invalid output settings, CLI precedence and strict webhook fields with legacy JSON support |
| `test_boundary_regressions.py` | Real notification transports, literal secret resolution and malformed startup paths |
| `test_resource_boundaries.py` | Optional network work stops after real transport resource exhaustion |
| `test_release_boundaries.py` | Real HTTP retries, Discord mention safety, unrenderable templates, SMTP password round trips, split terminal writes and the width cap without wcwidth |
| `test_compact_commands.py` | Literal short command prefixes, real help output and dependency hints |
| `test_release_safety.py` | Credential preservation, private error rendering, runtime timing validation and immutable setup defaults |
| `test_recovery_safety.py` | Real dotenv reloads, setup backups, oversized counts and provider-error privacy |
| `test_secret_policy.py` | Shared credential priority, reload ownership and setup destination conflicts |
| `test_smtp_error_privacy.py` | Short and escaped passwords in rejected SMTP sign-ins through commands, setup, Doctor and delivery |
| `test_setup_resolution_regressions.py` | Saved dotenv destinations, empty secrets, export precedence and recovery paths |
| `test_dotenv_quoted_keys.py` | Quoted dotenv keys, export prefixes, multiline values and duplicate removal |
| `test_documentation_layout.py` | Unique anchors, main screenshot placement and matching entry-page feature summaries |
| `data/config_templates/` | One configuration template per released shape, replayed through the current parser |
| `conftest.py` | Import setup, deterministic globals and the Riot API, SMTP, webhook and clock test doubles |
| `test_cli_startup.py` | Command line handling, config and dotenv loading, startup validation, listing mode and the effective-settings banner |
| `test_config_loading.py` | Declarative config parsing, retired settings and refusal of executable config content |
| `test_config_writing.py` | Backups, atomic replacement and the prompt guarding a generated configuration file |
| `test_csv_output.py` | The CSV match history, its columns and the custom game rows saved from a live snapshot |
| `test_doctor_report.py` | The `--doctor` preflight: every check branch, the rendered report, the delivery offer and the exit code |
| `test_diagnostics.py` | The `--verbose` and `--debug` printers, the trace grammar and what each mode is allowed to print |
| `test_family_contract.py` | The surfaces shared with the sibling monitors: the startup banner, the screen clear and the wording every tool prints |
| `test_documentation.py` | The documentation site: navigation, links into and out of it, page structure and claims about flags and tooling |
| `test_email_html.py` | HTML notification bodies: escaping, the Discord markdown form and the plain-text match |
| `test_email_notifications.py` | SMTP validation, the delivered message and failure handling |
| `test_help_screen.py` | The `--help` screen: option group names and order, the shared help sentences and the worked examples |
| `test_install_method_commands.py` | Install-method detection and the printed commands built from it, including the files a run carries into them |
| `test_match_formatting.py` | Riot IDs, game type and patch labels, participant names, team rosters and ban lists |
| `test_notification_images.py` | The champion icon: the bounded download, the inline email attachment and the ntfy attachment with its text fallback |
| `test_offline_e2e.py` | One end-to-end run of the real CLI against Riot and Data Dragon fixtures served over loopback |
| `test_match_reporting.py` | The finished-match report, the in-game report, live snapshots and match history listing |
| `test_monitoring_loop.py` | End-to-end monitoring runs: profile startup, new match detection, in-game and stopped alerts, custom game saves and error recovery |
| `test_properties.py` | Property-based checks on the Riot ID, region and duration normalizers and on the values that reach the dotenv file |
| `test_recovery_errors.py` | The closed recovery taxonomy, the advice each failure carries, secret redaction and the shared error block |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating, the supported Python floor and the CI contract |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_setup_wizard.py` | The guided setup wizard: what each answer collects, what reaches which file and what an interrupt leaves behind |
| `test_partial_setup_save.py` | Real wizard inputs and filesystem failures after configuration replacement |
| `test_secret_precedence.py` | Which source supplies each secret, the reload that keeps that order and how it is reported |
| `test_secret_commands.py` | The one-shot `--set-riot-api-key`, `--set-smtp-password` and `--set-webhook-url` commands and the private dotenv file they write |
| `test_riot_api_client.py` | The Riot API wrappers, pagination, champion name lookup and rejected API keys |
| `test_runtime_controls.py` | Signal-driven toggles, interval changes, secret reload and the log output filter |
| `test_tls_verification.py` | The TLS verification switch reaching connectivity, Data Dragon, email and the Riot API client |
| `test_startup_summary.py` | The startup summary: the shared row order, the two views and what each one shows |
| `test_terminal_color.py` | The colour engine: the theme, which colour lands on which token and where colour is applied |
| `test_target_normalization.py` | The canonical Riot ID and region stored at the boundary and the routing continent they resolve to |
| `test_terminal_truncation.py` | Width-aware terminal truncation: what gets cut, what does not and what the log file keeps |
| `test_time_formatting.py` | Durations, timespans and timestamp formats |
| `test_webhook_notifications.py` | The Discord and ntfy webhook channel: what is built, what is sent, what is refused and what the private URL never reveals |
| `test_moved_private_settings.py` | Kept credentials across dotenv destination changes and startup error handling |
| `test_real_polling.py` | Real Riot and webhook clients across outages, completion retries and independent channels |
| `test_csv_conversion.py` | Lossless CSV conversion, backups and operating system write failures |

## Conventions

* Keep every test offline. If a code path needs network access, stub it with
  `monkeypatch` rather than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a
  leaked global affects whatever runs next.
* Replace Riot Games calls and notification delivery with test doubles.
* Never use a real Riot API key, SMTP password or webhook URL.
* Write a fake credential so a secret scanner can tell it is fake. Keep the shape
  the code parses, such as the `RGAPI-` prefix, then use a word saying what the
  test does with it and pad the rest with repeated digits, as in
  `RGAPI-exported-0000-0000-0000-000000000000`. A random-looking value is reported
  as a leaked credential by the scan CI runs over the full history.

A change to the monitoring loop, authentication or Riot Games data handling is not
verified by this suite alone. Exercise it against a real account and say so in the
pull request, without usernames or credentials.
