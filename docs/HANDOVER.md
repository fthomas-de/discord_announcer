# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-24.

## Release

- Version **0.0.21** in `discord_announcer/__init__.py`, committed (`51aedef`)
- `CHANGELOG.md` split into `[0.0.18]`-`[0.0.21]` at the commits that raised
  the version; `[In Development]` is empty. Versions 0.0.10-0.0.17 were never
  written down, the history jumps from `[0.0.9]`
- Dev: migrations **0001-0005** applied to `aa_dev`, one configuration row
  saved, Alliance Auth 5.3.1, django-esi 9.10.0
- `manage.py check` and `makemigrations --check` clean, also with a different
  `TIME_DELTA`

## How posting works

One periodic task, `discord_announcer.tasks.discord_announcer_task`, without
arguments, runs every few minutes and only decides what is due. Every row of
`AnnouncerConfig` carries its own interval, which is both its rhythm and its
window: a row is due once its interval has passed since `last_run_at`, posts the
sales since then, and moves `last_run_at` on - also when there were no sales,
but not when sending was impossible. Never more often than once an hour.

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

1. **Live system** - not seen by me. It asked for `makemigrations` after
   0.0.18, which 0.0.19 fixes. To bring it up: deploy 0.0.21 with migrations
   0003-0005, `migrate discord_announcer`, delete the old periodic tasks with
   arguments, add the single `CELERYBEAT_SCHEDULE` entry from the README,
   restart AA and the Celery workers.
2. **End to end not verified by me.** AA-Discordbot and py-cord are not
   installed in dev, so no real post has gone out from there, and no real ESI
   call has run through the new code in a session - only mocked. "Check tokens"
   on a system with a real token is the first thing to try.
3. **Token choice.** `selects.get_corp_transaction_token` takes the first token
   with the wallet scope of any corporation member. If that character lacks the
   in-game role Accountant or Junior Accountant, the row fails every run although
   another member might work. "Check tokens" shows it; the fix would be to try
   the next token, or prefer characters with the role.
4. **Embed size.** A station with very many item types can exceed Discord's
   4096 characters per embed description; that post would be rejected. Not
   handled.
5. **No test suite.** The scenarios below were checked with scratch scripts
   that are gone with the session. Worth turning into `discord_announcer/tests/`.
6. **Leftovers from the example plugin**: `pyproject.toml` still names Peter
   Pfeufer as author, links the example plugin and lists Django 4.2;
   `REF_TYPE` in `app_settings.py` is read by nothing.
7. **No translations.** `locale/` is empty; page strings are marked for
   gettext. Decide whether a `de` catalogue is wanted.
8. **Before committing these notes**: `CLAUDE.md` and `docs/` name dev paths
   and the database name. If the GitHub repo is public, decide whether they
   belong in it.

## Checked scenarios

All with ESI, Discord and `save()` mocked:

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
