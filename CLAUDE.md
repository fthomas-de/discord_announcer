# Working on discord_announcer

Posts the market sales of corporation wallet divisions to Discord, for
Alliance Auth 5. `README.md` says what the app does; this file says how to work
on it; `docs/HANDOVER.md` says where the work currently stands.

## Where things are

| | |
|---|---|
| This app | `~/aa-dev/working/discord_announcer/discord_announcer` |
| Alliance Auth instance | `~/aa-dev/working/myauth` (has `manage.py`) |
| Virtualenv | `~/aa-dev/venv` (app installed there with `pip install -e`) |
| Dev server | `http://127.0.0.1:8000`, app under `/discord_announcer/` |
| Reference apps | `~/aa-dev/working/eos-tax`, corptools in the venv's site-packages |

Everything runs from the Alliance Auth instance:

```bash
cd ~/aa-dev/working/myauth
```

## Commands

```bash
~/aa-dev/venv/bin/python manage.py check
```

```bash
~/aa-dev/venv/bin/python manage.py makemigrations discord_announcer --check --dry-run
```

```bash
~/aa-dev/venv/bin/python manage.py migrate discord_announcer --plan
```

`runserver` has not always picked up changed Python files on its own; after a
change to `urls.py` or `views.py`, a `NoReverseMatch` usually means the server
still runs the old code. Templates are read fresh on every request. The Celery
worker never reloads - restart it before testing anything the task does.

## The database is irreplaceable

`aa_dev` holds ESI-pulled corptools data that cannot be fetched again. There
is no binary log and there are no dumps.

- Never delete with a range filter on `EveCorporationInfo`; the cascade takes
  the wallet journal with it.
- Run `migrate --plan` and `sqlmigrate` first, and migrate only after the user
  said yes - per migration, not once for the session.
- Alliance Auth's own and corptools' tables are read, never changed. That
  includes `menu_menuitem`: if AA's menu sync breaks, fix the version mismatch
  between code and schema (see the 2026-09-23 note in the handover), not the
  table.

## Migrations

Model field attributes must not depend on settings. A value read from
`app_settings` and used as `default=` is frozen into the migration, and every
installation with another value is asked to run `makemigrations`. Use a
module level callable instead (`models.default_interval`) - migrations store
the reference, so it must never be deleted.

A callable default makes Django expect a hidden `initial-<field>` input, which
`{% bootstrap_field %}` does not render; the untouched empty formset row then
counts as changed and blocks saving. `AnnouncerConfigForm` switches
`show_hidden_initial` off for `time_delta` - do the same for any new field with
a callable default.

After generating a migration, check it with a different setting value too:
a scratch settings module that does `from myauth.settings.local import *` and
overrides the value, passed via `DJANGO_SETTINGS_MODULE` and `PYTHONPATH`.

Never tell the user to run `makemigrations` on a live system; migrations belong
in the repo.

## Code

English everywhere in the code, comments and docstrings. Comments say why, not
what.

Prefer an Alliance Auth or corptools pattern over inventing one, and name the
reference: the datalist for the corporation comes from AA's optimer, tooltips
are initialised per template the way `menu/menu-user.html` does it, ESI calls
follow `corptools/tasks/corporation/wallet.py`.

The django-esi 9 client returns objects, not dicts (`sale.date`, not
`sale['date']`), and raises `HTTPNotModified` on unchanged data unless called
with `use_etag=False`.

Messages posted to Discord are English and not translated: the channel's
language must not depend on who clicked a button.

## Tests

The suite lives in `discord_announcer/tests/`, run from the AA instance:

```bash
~/bin/eos-test discord_announcer
```

or on its own against the bundled sqlite test project:

```bash
~/aa-dev/venv/bin/python runtests.py discord_announcer
```

Nothing in it talks to ESI or Discord. `tests/base.py` has the fixtures: a
wallet transaction is a `SimpleNamespace` with the attributes the django-esi 9
client returns (`make_sale`), and `fake_discord()` stands in `discord` and
`aadiscordbot.tasks` through `sys.modules`, collecting every embed. ESI is
replaced at `selects.get_transactions`, so the watermark, paging and filters
above it run for real. Alliance Auth names extension loggers
`extensions.<module>`, which is what `assertLogs` needs.

Every change gets a test, and every new test gets checked against the broken
code: put the fault back, run the test, confirm it fails, restore the file
and compare its checksum.

`tests/` code belongs inside a `TestCase` only - `manage.py shell` writes
straight into `aa_dev`.

## Shell

The bridge from this session's Bash tool into WSL loses shell variables: a
`$x` or a `for` loop variable inside `wsl.exe ... bash -lc "..."` arrives
empty. Write commands out, or put a script into a file and run it by path.
Show commands to the user without the `wsl.exe` wrapper.

## Committing

The user commits, always. Never run `git commit` or `git push`.

`CHANGELOG.md` is written along with every change, unasked, under
`[In Development] - Unreleased`. When the user commits or asks for it:

1. If `discord_announcer/__init__.py` still has the version of the last commit,
   raise the patch digit and say which old and new version that is.
2. Split the running section across the versions, at the commit that raised
   the version in between (`git show <commit>:discord_announcer/__init__.py`).

There are no translation catalogues yet (`discord_announcer/locale/` is empty);
the page strings are marked for gettext.
