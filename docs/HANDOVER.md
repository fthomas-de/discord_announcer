# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-25.

## Release

- Version **0.0.22** in `discord_announcer/__init__.py`, **not committed** -
  the review of 2026-09-25 sits in the working tree, under `[0.0.22]` in
  `CHANGELOG.md`. `51aedef` (0.0.21) is still the last commit
- `CHANGELOG.md`: `[0.0.18]`-`[0.0.21]` split at the commits that raised the
  version; 0.0.1-0.0.9 were the example plugin and are one line now;
  0.0.10-0.0.17 were never written down
- Dev: migrations **0001-0006** applied to `aa_dev`, including **0006**
  (watermark, last attempt, labels). One configuration row saved, Alliance
  Auth 5.3.1, django-esi 9.10.0
- 65 tests green (`discord_announcer/tests/`), each fix checked against the
  broken code
- `manage.py check` and `makemigrations --check` clean, also with a different
  `TIME_DELTA`

## How posting works

One periodic task, `discord_announcer.tasks.discord_announcer_task`, without
arguments, runs every few minutes and only decides what is due. Every row of
`AnnouncerConfig` carries its own interval, which is both its rhythm and its
rhythm: a row is due once its interval, less one minute, has passed since its
last attempt (`last_attempt_at`, or `last_run_at` for a row never tried). Its
window is not a time span but a watermark: it posts the sales after
`last_transaction_id`, the newest transaction the previous window saw, and
moves both on - also when there were no sales, but not when sending was
impossible. Only a row's first window, after creation or reactivation, is
cut by time. ESI caches the transactions for up to an hour, which is why a
time window lost sales. Never more often than once an hour; a failing row
waits one interval before the next attempt.

The token is corptools' `get_corp_token` with the wallet scope and the roles
CEO, Director, Accountant, Junior_Accountant - the same call corptools makes
for its own wallet sync. It needs the roles scope on the token.

The two buttons on the page work on saved rows and run in the request:
"Check tokens" reads each wallet once without cache and without posting;
"Post latest sale" posts each active row's newest sale and leaves
`last_run_at` alone.

## The 2026-09-23 menu crash

`/dashboard/` failed with `Field 'permission_mode' doesn't have a default
value` as soon as this app registered its menu entry. The database had been
migrated with Alliance Auth 5.3 (`menu.0003`, `admin_status.0003/0004`) while
the venv held 5.2.0, whose model does not know the column; AA's menu sync
inserts a row for every new menu hook and hit the NOT NULL column. Fixed by
installing 5.3 again, not by touching the table. If it ever comes back, compare
`django_migrations` with the installed migration files first.

## Open

1. **Live system** - not seen by me. To bring it up: deploy the new version
   with migrations 0003-0006, `migrate discord_announcer`, delete the old
   periodic tasks with arguments, add the single `CELERYBEAT_SCHEDULE` entry
   from the README, restart AA and the Celery workers. Tokens need the roles
   scope `esi-characters.read_corporation_roles.v1` now.
2. **End to end not verified by me.** AA-Discordbot and py-cord are not
   installed in dev; the suite stands them in. "Check tokens" on a system
   with a real token is the first thing to try.
3. **Embed size.** A station with very many item types can exceed Discord's
   4096 characters per embed description; that post would be rejected. Not
   handled.
4. **No translations.** `locale/` is empty; page strings are marked for
   gettext, the Makefile's language list is still the example plugin's.
   Decide whether a `de` catalogue is wanted.
5. **Before committing these notes**: `CLAUDE.md` and `docs/` name dev paths
   and the database name. If the GitHub repo is public, decide whether they
   belong in it.

Settled on 2026-09-25: the token choice (corptools' helper), the test suite,
the example plugin's leftovers in `pyproject.toml` and `REF_TYPE`.

## Checked scenarios

These were checked by hand before the suite existed; the suite covers them
now, most of them in `test_tasks.py` and `test_views.py`:

- Rhythm: first run uses the last interval; not due yet is skipped; a late run
  starts at `last_run_at` and names the real hours; no sales still advances;
  a failed send keeps the window; one failing row does not stop the next; the
  window start itself belongs to the previous window
- Form: the corporation is a text input bound to the datalist; a typed name
  resolves, an unknown one is rejected; an existing row shows the name; an
  untouched empty row is ignored, a half filled one reports its fields
- Check tokens: OK names the character and bypasses the cache; missing token,
  403 (missing role) and an invalid token each give their own message
- Post latest sale: without the bot nothing is fetched; no sales and an
  unknown station or type warn without posting; a post carries the dated title
  and leaves `last_run_at` alone
- Source line: "Corp [TICK] · Wallet division 5 (Verkauf)" from the real
  corptools division names, number only where no name is known, set on every
  embed by both the task and the button
