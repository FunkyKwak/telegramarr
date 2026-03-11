# telegramarr
Notification service from Radarr to Telegram (on new release)

This project provides a simple Python script packaged in Docker that polls a Radarr instance,
checks for monitored movies without files, and sends Telegram notifications when new releases
are available. It stores processed movie IDs in an SQLite database to avoid duplicate alerts.

## Configuration

Environment variables are used to configure the service. They can be defined in a `.env` file or
passed to `docker-compose`.

| Variable | Description |
|----------|-------------|
| `RADARR_HOST` | Hostname or IP of Radarr (e.g. `radarr`) |
| `RADARR_PORT` | Port Radarr listens on (default `7878`) |
| `RADARR_API_KEY` | Your Radarr API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Chat ID where notifications should be sent |
| `POLL_INTERVAL_MINUTES` | Loop interval in minutes (default `10`) |
| `SQLITE_DB_PATH` | Path to the SQLite file inside container (default `/app/data/seen.db`)


## Building and running

Use docker-compose to build the image and run the service:

```bash
# create a .env file or export the variables
export RADARR_HOST=radarr
export RADARR_PORT=7878
export RADARR_API_KEY="yourkey"
export TELEGRAM_BOT_TOKEN="bot_token"
export TELEGRAM_CHAT_ID="123456789"
export POLL_INTERVAL_MINUTES=5

# build and start
docker-compose up --build -d
```

A named volume `data` persists the SQLite database between restarts.

## Development

The Python code lives in `app/main.py`. Dependencies are listed in `requirements.txt`.

Feel free to tweak the logic or add logging as needed.

