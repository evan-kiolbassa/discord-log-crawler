# discord-log-crawler

Minimal toolchain to parse manually posted moderation logs from a Discord channel and store structured events in MySQL with basic entity resolution.

Example input lines (single Discord message may contain multiple lines):

Kick @ 8/25/2025, 11:08:52 PM OATS Dueltroit [Flourish to Duel Pit FFA Discord oatsduelyard] Swungbyjack6849 (6F26F3A5D9A2C314) FFA: You need to flourish to your opponent and wait on them to flourish back to start a duel. Flourish can be done with MMB, or L3+Square/X. FFA is allowed only in the pit, outside of the pit you aren't allowed to randomly attack (which includes; jabs, kicks, tackles, throwing items, arrows, etc.) other players.

Ban @ 8/27/2025, 11:22:37 PM OATS Duelanta [Flourish to Duel Pit FFA Discord oatsduelyard] Erol1600 (5B6F95CD14F6C21B) FFA: You need to flourish to your opponent and wait on them to flourish back to start a duel. Flourish can be done with MMB, or L3+Square/X. FFA is allowed only in the pit, outside of the pit you aren't allowed to randomly attack (which includes; jabs, kicks, tackles, throwing items, arrows, etc.) other players. 2 hours

## Quick start

1) Python 3.10+ recommended.

2) Install deps:

    pip install -r requirements.txt

3) Create a MySQL database and a `.env` file from the template:

    cp .env.example .env

   Edit values for DB and Discord credentials.

4) Ingest from a Discord channel (bot must be in server, Message Content Intent enabled):

    python -m discord_log_crawler.ingest fetch-discord --channel-id <CHANNEL_ID> --limit 5000

5) Or parse a local text file of pasted logs:

    python -m discord_log_crawler.ingest parse-file ./logs.txt

## Paste-To-Me Bot (DM)

Prefer a lightweight bot where users DM logs? Start the live bot which parses any message you DM it (and optionally specific channels):

1) Configure environment (via real env vars or a `.env` file):

   - `DISCORD_TOKEN`: your bot token (Message Content Intent must be enabled)
   - `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
   - Optional `DISCORD_ALLOWED_CHANNEL_IDS`: comma-separated channel IDs to also accept messages from (besides DMs)

2) Run the bot:

       python -m discord_log_crawler.bot

3) Users can now DM the bot and paste moderation logs directly. The bot replies with how many events were stored. Unknown lines are ignored.

## Test-Driven Development

- Local (Python installed):
  - Install dev deps: `pip install -r requirements.txt -r requirements-dev.txt`
  - Run tests: `pytest -q`

- With Docker Compose (spins up MySQL automatically):
  - `docker compose up --build --abort-on-container-exit`
  - Or iterate tests: `docker compose run --rm app pytest -q`

## CI with GitHub Actions

- Workflow at `.github/workflows/ci.yml`:
  - Brings up a MySQL service
  - Installs deps and runs `pytest`
  - Uses GitHub Actions Secrets for database credentials

### Required GitHub Secrets

Add these in: GitHub → Settings → Secrets and variables → Actions → New repository secret

- `MYSQL_ROOT_PASSWORD`: root password for the MySQL service
- `MYSQL_DATABASE`: database name to create for tests (e.g., `test_discord_logs`)
- `MYSQL_USER`: non-root user for tests (e.g., `ci_user`)
- `MYSQL_PASSWORD`: password for `MYSQL_USER`

The workflow injects these secrets into the MySQL service and test step environment, avoiding hard-coded credentials.


## What it stores

- players (unique by PlayFabId) with alias tracking for usernames
- moderation_events (Kick/Ban) with timestamp, location, reason, duration, and raw text

## Discord setup tips

- Create a bot in the Discord Developer Portal, invite it to your server with `Read Messages`, `Read Message History` permissions.
- In the bot settings, enable `MESSAGE CONTENT INTENT` so it can read message text.

## Notes on entity resolution

- Primary identity is the PlayFabId when present.
- All seen usernames for the same PlayFabId are stored as aliases.
- If PlayFabId is missing in a line, the resolver can optionally match by username using fuzzy similarity (disabled by default).
