# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.0.22] - 2026-09-25

> [!NOTE]
>
> **Tokens need one more scope and a role check.** The token is chosen the way
> corptools chooses its own: every token of the corporation with the wallet
> scope and `esi-characters.read_corporation_roles.v1` is tried in turn, and
> the first whose character holds CEO, Director, Accountant or Junior
> Accountant is used. A token added without the roles scope is no longer
> picked; add it again. Migration `0006` has to be applied.

### Added

- A test suite, `discord_announcer/tests/`: the rhythm, the windows, the
  token choice, the form, both buttons and the migrations, with ESI and
  Discord replaced by stand-ins. The scratch scripts every change used to be
  checked with were gone with the session that wrote them.

### Changed

- Every window after a row's first starts after the newest transaction the
  previous one saw, not after a point in time (`last_transaction_id`,
  migration `0006`). Older pages are fetched with `from_id` when a window
  reaches back further than ESI's 2500 per answer, up to five pages.
- A row counts as due one minute before its interval has passed. The
  periodic task runs on a fixed tick and `last_run_at` carries the queue's
  latency, so a row run at 10:00:00.8 was not due at 11:00:00.5 and waited
  for the next tick - 75 minutes instead of 60, and a twelve hour row
  wandered by one tick per post.
- A row that fails - no token, a missing role, an invalid token - is tried
  again one interval later instead of on every tick (`last_attempt_at`,
  migration `0006`), and the failure is logged as one warning without a
  traceback. It used to write 96 tracebacks a day and count every 403 against
  the ESI error limit.
- The token is chosen with corptools' `get_corp_token`, see the note above.
  The first token with the wallet scope was taken before, and a row failed
  every run as soon as that character lacked the role, although another
  member would have worked.
- Amounts keep two decimals and pick their unit after rounding: 1.49 billion
  read "1 Billion", 999,999 read "1000 Thousand". "Isk" reads "ISK".
- Stations are listed by name, not by location id.
- Field names are in sentence case ("Wallet division", "Discord channel ID"),
  the help texts say what the row actually does - each post covers the sales
  since its previous run - and the channel ID's help text lives on the model
  instead of twice in two versions (migration `0006`).
- `pyproject.toml` requires Alliance Auth 5 and corptools: AA 4 has no
  `esi.openapi_clients`, and without corptools pip installed fine and Alliance
  Auth then failed to start. AA-Discordbot is an optional extra. Description,
  author and links are this app's, not the example plugin's.
- `testauth`, `runtests.py`, `tox.ini` and `.coveragerc` run this app now:
  they named the example plugin's package `example`, so nothing ever ran. The
  test project uses a sqlite database of its own.
- The task logs through Alliance Auth's extension logger like the rest of the
  app; its messages went to the Celery worker's log instead of
  `extensions.log`.

### Fixed

- **Sales could get lost.** ESI hands out the transactions from a cache of
  up to an hour, but a window ended at the time of the run. A sale made at
  10:50 appeared only after the 11:00 run had moved the window on - dated
  before it - and the window starting at 11:00 never posted it. With the
  watermark above, every sale is posted once, as the README says.
- Sales at a station or of an item type Corp Tools does not know yet were
  left out, and the window moved past them: lost for good. They are posted
  as "Location <id>" and "Type <id>" now, and "Post latest sale" posts them
  too instead of warning.
- The task could run twice at the same time after a worker outage and post
  the same sales twice. It runs through `QueueOnce`, as corptools' tasks do.
- Switching a row back on in the Django admin did not start a fresh window;
  only the configuration page did. The model does it now, for both.
- "Sales (last 1 hours)" reads "Sales (last 1 hour)".

### Removed

- The `REQUIRED_SCOPE` setting: ESI decides the scope, and any other value
  only ever made every row fail. `REF_TYPE`, which nothing read, and three
  commented out settings carrying a real corporation and channel ID.
- Leftovers of the example plugin: `test_example.py`, a commented out cogs
  hook, the isort heading "AA Example App", pre-commit hooks for JavaScript,
  CSS and GitHub workflows this repository does not have, and an empty
  provider subclass.

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

## [0.0.1] - [0.0.9] - 2022-03-12 to 2024-06-16

These versions are the example plugin this app was started from
(ppfeufer's aa-example-plugin). Their entries described the template, not
this app, and are left out.
