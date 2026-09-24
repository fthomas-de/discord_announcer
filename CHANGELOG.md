# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [In Development] - Unreleased

## [0.0.21] - 2026-09-23

### Added

- The configuration page shows the app version in its title

### Fixed

- Saving the configuration page failed with "This field is required" on the
  empty last row whenever that row was left untouched, so existing rows could
  not be changed (since 0.0.19)

## [0.0.20] - 2026-09-23

### Added

- Every Discord message names the corporation and wallet division it comes
  from, as its author line with the corporation logo, e.g.
  "Corp Name [TICK] · Wallet division 5 (Sales)"; the division name is taken
  from Corp Tools and left out when it is not known

## [0.0.19] - 2026-09-23

### Added

- The corporation is picked by typing its name, with suggestions from an HTML5
  datalist, the same approach as AA's own optimer
- "Check tokens" button: reads the wallet of every saved configuration once,
  without posting, and reports per configuration whether it works, which
  character's token is used, or what is missing (token, in-game role, valid
  refresh)
- "Post latest sale" button: posts the newest sale of every active
  configuration once, however old, without moving its regular rhythm

### Fixed

- Installations whose `TIME_DELTA` differs from 12 were asked to run
  `makemigrations`, because the setting's value had been frozen into the
  migrations as the interval default; the default is now a callable
  (migration `0005`)
- A station whose sold item types Corp Tools does not know yet no longer
  produces a Discord message with an empty text

## [0.0.18] - 2026-09-23

> [!NOTE]
>
> **This version needs Alliance Auth v5.** The periodic tasks with arguments
> used so far stop working: enter them as rows on the new configuration page,
> delete them in the admin, and add the single periodic task described in the
> README.

### Added

- Sidebar menu entry and settings page (`discord_announcer:index`) to manage
  announcer configurations (corporation, wallet division, Discord channel,
  interval) instead of hand-configuring a Celery Beat periodic task with
  positional arguments per corp/channel combination; field help is shown as
  tooltips in the column headers
- `AnnouncerConfig` model, one row per configuration; supports any number of
  configurations at once
- `AnnouncerConfigAdmin` fallback editor in Django admin

### Changed

- `discord_announcer_task` no longer takes `(delta, corporation_id, division,
  channel_id)` arguments; it now takes none and processes every active
  `AnnouncerConfig` itself. Existing per-variant periodic tasks in Celery Beat
  must be replaced with a single periodic task calling
  `discord_announcer.tasks.discord_announcer_task` with no arguments, running
  more often than the shortest interval (e.g. every 15 minutes)
- The interval of a configuration is both its posting rhythm and its window:
  a configuration posts once its interval has passed since its last run,
  covering exactly the sales since that run, so sales are neither posted twice
  nor skipped; never more often than once per hour. The window also moves on
  when there were no sales, but not when sending was impossible. Reactivating
  a configuration starts a fresh window
- A failing configuration (missing token, ESI error) is logged and no longer
  stops the remaining configurations of the same run
- README rewritten for this app, replacing the example plugin text: requirements,
  installation, permissions, configuration, posting behaviour and the upgrade
  path from per-variant periodic tasks

### Removed

- `LastRun` model, superseded by `AnnouncerConfig.last_run_at`

### Fixed

- Compatibility with Alliance Auth v5 / django-esi 9.x: `pyproject.toml` no longer
  pins `allianceauth<5`
- ESI client migrated from the removed `esi.clients.EsiClientProvider` to the new
  `esi.openapi_clients.ESIClientProvider` (`provider.py`, `selects.py`), including
  the renamed wallet transactions operation and passing the `Token` object instead
  of a raw access token string
- ESI results are read as objects instead of dicts (`selects.py`,
  `utilities.py`), and fetched without the ETag check, which would otherwise
  raise `HTTPNotModified` whenever the data had not changed
- `discord_bot.py`: `discord_bot_active()` was hardcoded to always return `True`
  instead of actually checking whether AADiscordBot is installed, so sending a
  message would crash with `ModuleNotFoundError` on any install without it; now
  performs the real `apps.is_installed("aadiscordbot")` check
- `discord_bot.py`: the "AADiscordBot not installed" error log was attached to a
  `for...else` instead of the intended `if/else`, so it never actually fired

## [0.0.9] - 2024-06-16

### Removed

- Support for Python 3.8 and Python 3.9

## [0.0.8] - 2024-03-16

> [!NOTE]
>
> **This version needs at least Alliance Auth v4.0.0!**

### Added

- Compatibility to Alliance Auth v4
  - Bootstrap 5
  - Django 4.2

### Removed

- Compatibility to Alliance Auth v3

## [0.0.7] - 2023-09-27

> [!NOTE]
>
> **This is the last version compatible with Alliance Auth v3.**

### Changed

- Moved the build process to PEP 621 / pyproject.toml
- Test suite updated

## [0.0.6] - 2023-07-23

### Added

- Ukrainian to language handling in `Makefile`

## [0.0.5] - 2023-04-18

### Added

- Directory for translation files

## [0.0.4] - 2022-11-26

### Added

- Directory for static files

### Changed

- GitHub actions updated
- `pre-commit` config updated and applied
- Example test improved

## [0.0.3] - 2022-09-15

### Added

- `SITE_URL` to test settings

## [0.0.2] - 2022-08-17

### Added

- Build artifact to GitHub workflows
- `MANIFEST.in` re-added

### Changed

- Test settings updated for Alliance Auth v3
- Package name in setup.cfg for PyPi

## [0.0.1] - 2022-03-12

### Added

- Initial version
