# Anki Desktop in Docker

This project is inspired by [pnorcross/anki-desktop-docker](https://github.com/pnorcross/anki-desktop-docker), with a few tweaks. It provides a `Dockerfile` that uses [linuxserver/docker-baseimage-kasmvnc](https://github.com/linuxserver/docker-baseimage-kasmvnc) as the base image to run the desktop version of Anki inside a container.

Why? Because it makes automating Anki (with addons like AnkiConnect) easier and is super handy if you're using FSRS, especially since AnkiDroid doesn’t support it.

The Anki desktop app runs in a browser (via VNC) on port `3000`. Your Anki data is stored in a volume mounted at `/config/app` inside the container.

---

## Requirements

- **Docker**
- **Docker Compose** (usually bundled with newer Docker versions)
- **Ubuntu** (focus is on Linux, but Docker can work on Windows too with a slightly different setup)
- **cron** (for scheduling tasks)
- **AnkiConnect addon** (to enable scripting Anki via port `8765`)
- **FSRS4Anki Helper addon** (to reschedule cards)

---

## Files in This Repo

### `Dockerfile`
Builds the container with Anki 25.02.7 You can change the Anki version, but compatibility may vary.

### `docker_installation`
Contains commands to install Docker on Ubuntu.

### `cleanup`
Helps clean up system resources. Anki seems to have a memory leak—on systems with only 1GB RAM, the container might become unresponsive after ~1 day. You can use `cron` to run cleanup every 12h.

### `backup`
Uses `curl` to call AnkiConnect (on port 8765) to create a backup. Schedule this with `cron` for daily backups.

### `sync`
Also uses `curl` to call AnkiConnect. It forces a sync and optionally reschedules cards (useful with FSRS + AnkiDroid combo).

---

## Docker Compose Setup

Create a `docker-compose.yml` in the root of the repo:

```yaml
services:
  anki-desktop:
    build:
      context: ./
      dockerfile: Dockerfile
    volumes:
      - ~/.local/share/Anki2:/config/app/Anki2
      - ~/backups:/config/app/backups
    ports:
      - 3000:3000  # Web UI
      - 8765:8765  # AnkiConnect
````

* The **first volume** maps your local Anki data (on Ubuntu it's usually at `~/.local/share/Anki2`) into the container.
* The **second volume** is for backups you extract via AnkiConnect.

To get started:

```bash
git clone <this-repo>
cd anki-desktop-docker
docker compose up --build -d
```

Then open your browser and head to:

```
http://localhost:3000
```

---

## AnkiConnect Configuration

Make sure your AnkiConnect config (inside Anki) looks like this:

```json
{
    "apiKey": null,
    "apiLogPath": null,
    "ignoreOriginList": [],
    "webBindAddress": "0.0.0.0",
    "webBindPort": 8765,
    "webCorsOrigin": "http://localhost",
    "webCorsOriginList": ["*"]
}
```

---

## Cron Example

Open your crontab:

```bash
crontab -e
```

And add:

```cron
0 8 * * * (~/anki-desktop-docker/sync && date) >> ~/sync.log 2>&1
0 9 * * * (~/anki-desktop-docker/backup && date) >> ~/backup.log 2>&1
0 10,22 * * * (~/anki-desktop-docker/cleanup && date) >> ~/cleanup.log 2>&1
```

This sets up:

* **8:00 UTC** — Sync
* **9:00 UTC** — Backup
* **10:00 & 22:00 UTC** — Cleanup

