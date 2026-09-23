# Discord Announcer<a name="discord-announcer"></a>

A plugin for [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) (AA) that
posts the market sales of corporation wallet divisions to Discord channels, at a
fixed interval per configuration.

![License](https://img.shields.io/badge/license-GPLv3-green)
![python](https://img.shields.io/badge/python-3.10+-informational)
![allianceauth](https://img.shields.io/badge/allianceauth-5.x-informational)

______________________________________________________________________

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [Discord Announcer](#discord-announcer)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Permissions](#permissions)
  - [Configuration](#configuration)
  - [When a Message Is Posted](#when-a-message-is-posted)
  - [Settings](#settings)
  - [Upgrading From 0.0.17 or Earlier](#upgrading-from-0017-or-earlier)
  - [Development](#development)

<!-- mdformat-toc end -->

______________________________________________________________________

## Features<a name="features"></a>

- Own entry in the AA sidebar, leading to a page where any number of
  announcements are maintained: corporation, wallet division, Discord channel
  and interval
- One Discord embed per station, listing every item type sold with quantity and
  total ISK, headed by the corporation (with logo) and wallet division it comes
  from
- Every sale is posted exactly once: each post covers the sales since the
  previous post of the same configuration
- At most one post per hour and configuration
- A broken configuration (missing token, ESI error) is logged and does not stop
  the others
- Buttons to check the tokens of all configurations and to post the latest sale
  of each one on demand

## Requirements<a name="requirements"></a>

- Alliance Auth 5.x
- [AA-Discordbot](https://github.com/Solar-Helix-Independent-Transport/allianceauth-discordbot),
  installed and configured; without it nothing is sent
- [Corp Tools](https://github.com/Solar-Helix-Independent-Transport/allianceauth-corp-tools),
  for station and item names
- For every announced corporation, a character of that corporation with:
  - an ESI token with the scope `esi-wallet.read_corporation_wallets.v1`, for
    example the one created when adding the corporation to Corp Tools
  - the in-game role Accountant or Junior Accountant

## Installation<a name="installation"></a>

Install the app into the virtual environment of your AA installation:

```bash
pip install git+https://github.com/fthomas-de/discord_announcer.git
```

Add it to `INSTALLED_APPS` in `settings/local.py`:

```python
INSTALLED_APPS += [
    # ...
    "discord_announcer",
]
```

Add the periodic task to `settings/local.py`. It only checks which
configurations are due, so it should run more often than the shortest interval
you intend to use:

```python
CELERYBEAT_SCHEDULE["discord_announcer_task"] = {
    "task": "discord_announcer.tasks.discord_announcer_task",
    "schedule": crontab(minute="*/15"),
}
```

Run the migrations, collect static files, and restart AA and the Celery workers:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## Permissions<a name="permissions"></a>

| Permission                            | Grants                                          |
| ------------------------------------- | ----------------------------------------------- |
| `discord_announcer.basic_access`      | The sidebar entry and the configuration page     |

Everybody with this permission can change every configuration, so grant it only
to the people maintaining the announcements.

## Configuration<a name="configuration"></a>

Open **Discord Announcer** in the sidebar. Every row is one announcement:

| Field              | Meaning                                                                                       |
| ------------------ | --------------------------------------------------------------------------------------------- |
| Name               | Label to tell the rows apart                                                                  |
| Corporation        | Corporation whose wallet is read. Type to search, then pick one of the suggestions            |
| Wallet Division    | Wallet division to read, 1 to 7                                                               |
| Discord Channel ID | Channel to post to. In Discord, enable Developer Mode, then right-click the channel → "Copy Channel ID" |
| Interval (hours)   | How often the row posts, and at the same time the span each post covers. At least 1          |
| Active             | Switched off rows are skipped                                                                 |

The last row of the table is always empty and adds a new announcement when
filled in. Tick **Remove** and save to delete a row.

Two buttons below the table work on the saved rows, so save changes first:

- **Check tokens** reads the wallet of every row once, the way the periodic task
  does, without posting. For each row it reports which character's token is
  used, or what is missing: a token with the wallet scope, the in-game role, or a
  token that can still be refreshed.
- **Post latest sale** posts the newest sale ESI still returns for every active
  row, however old, after asking for confirmation. The regular rhythm of the rows
  is not changed.

## When a Message Is Posted<a name="when-a-message-is-posted"></a>

On every run of the periodic task, each active row is handled like this:

1. If its interval has not passed since its last run, nothing happens.
2. Otherwise, the sales since its last run are read from ESI. On the first run
   after the row was created or switched back on, the sales of the last interval
   are read instead.
3. If there were sales, one message per station is posted. Its title names the
   hours actually covered, which can be a little longer than the interval when
   the periodic task ran late.
4. The row's last run moves to now, also when there were no sales.

If nothing could be sent because AA-Discordbot is missing, or reading the sales
failed, the last run stays where it was, and the sales are posted with the next
run that succeeds.

Sales at stations or of item types that Corp Tools does not know yet are left
out of the message.

## Settings<a name="settings"></a>

Optional, in `settings/local.py`:

| Name             | Default                                    | Description                               |
| ---------------- | ------------------------------------------ | ----------------------------------------- |
| `TIME_DELTA`     | `12`                                       | Interval in hours preset for new rows     |
| `REQUIRED_SCOPE` | `"esi-wallet.read_corporation_wallets.v1"` | Scope a token needs to be used by the app |

## Upgrading From 0.0.17 or Earlier<a name="upgrading-from-0017-or-earlier"></a>

Up to 0.0.17, every announcement was a periodic task of its own, with interval,
corporation ID, division and channel ID as its arguments. The task no longer
takes arguments, so these periodic tasks fail from now on.

1. Enter every former periodic task as a row on the configuration page.
2. Delete the old periodic tasks in the Django admin under
   **Periodic Tasks → Periodic tasks**.
3. Add the single periodic task from [Installation](#installation).

## Development<a name="development"></a>

With AA, its virtual environment and this repository under one folder, install
the app in editable mode:

```bash
pip install -e discord_announcer
```

Then add it to `INSTALLED_APPS` of your dev AA, run `python manage.py check` and
`python manage.py migrate`, and restart the server.
