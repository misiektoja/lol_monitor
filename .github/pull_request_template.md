## What this changes

<!-- The behavior that changes for a user, and why. Link the issue when there is one. -->

## Checks

<!-- Which of these you ran and anything that failed. -->

- [ ] `python -m pytest`
- [ ] `python -m ruff check lol_monitor.py tools tests`
- [ ] Exercised against a real Riot Games account, for a monitoring, authentication or data-handling change

<!-- A monitoring or authentication change is not verified by the offline suite alone, which never
     contacts Riot Games. Say what you ran it against, without usernames or credentials. -->

## Documentation and release notes

- [ ] `docs/` updated, for user-facing behavior, and `mkdocs build --strict` passes
- [ ] `RELEASE_NOTES.md` entry added under the unreleased section

## Notes

<!-- Trade-offs, follow-up work or parts you are unsure about. -->

<!-- Never include Riot API keys, SMTP passwords or webhook URLs or the accounts you monitor in a pull request. -->
