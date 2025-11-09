# Anki Desktop in Docker

This project is inspired by [pnorcross/anki-desktop-docker](https://github.com/pnorcross/anki-desktop-docker), with a few tweaks. It provides a `Dockerfile` that uses [linuxserver/docker-baseimage-kasmvnc](https://github.com/linuxserver/docker-baseimage-kasmvnc) as the base image to run the desktop version of Anki inside a container.

Why? Because it makes automating Anki (with addons like AnkiConnect) easier.

The Anki desktop app runs in a browser (via VNC) on port `3000`. Your Anki data is stored in `anki_data` mounted as a volume at '/config` inside the container.

## Features

- **Fully Automated Setup** - Configure via environment variables, no manual steps required
- **AnkiConnect Pre-installed** - API ready on port 8765 for automation
- **Web-based Access** - Access Anki desktop via browser on port 3000
- **Docker-based** - Consistent environment across all platforms
- **Cron-ready** - Scripts for automated backup, sync, and cleanup

---

## Requirements

- **Docker**
- **Docker Compose** (usually bundled with newer Docker versions)
- **Ubuntu** (focus is on Linux, but Docker can work on Windows too with a slightly different setup)
- **cron** (for scheduling tasks)
- **AnkiConnect addon** (to enable scripting Anki via port `8765`)

---

## Files in This Repo

### `Dockerfile`
Builds the container with Anki 25.07.5 You can change the Anki version, but compatibility may vary.

### `docker_installation`
Contains commands to install Docker on Ubuntu.

### `cleanup`
Helps clean up system resources. Anki seems to have a memory leak—on systems with only 1GB RAM, the container might become unresponsive after ~1 day. You can use `cron` to run cleanup every 12h.

### `backup`
Uses `curl` to call AnkiConnect (on port 8765) to create a backup. Schedule this with `cron` for daily backups.

### `sync`
Also uses `curl` to call AnkiConnect. It forces a sync and optionally reschedules cards (useful with FSRS + AnkiDroid combo).

---

## Quick Start

### Fully Automated Setup (Recommended)

Run with AnkiWeb credentials - everything configured automatically:

```bash
docker run -d \
    --name anki-desktop \
    -e PUID=1000 \
    -e PGID=1000 \
    -e ANKIWEB_USER=your-email@example.com \
    -e ANKIWEB_PASSWORD=your-password \
    -v "$(pwd)/anki_data:/config" \
    -p 3000:3000 \
    -p 8765:8765 \
    mlcivilengineer/anki-desktop-docker:main
```

No manual configuration needed! AnkiConnect will be installed and configured automatically.

**More secure option** - Use sync key instead of password:
```bash
# Get sync key first
./get_sync_key.sh your-email@example.com your-password

# Then use it
docker run -d \
    --name anki-desktop \
    -e PUID=1000 \
    -e PGID=1000 \
    -e ANKIWEB_USER=your-email@example.com \
    -e ANKIWEB_SYNC_KEY=your-16-char-key \
    -v "$(pwd)/anki_data:/config" \
    -p 3000:3000 \
    -p 8765:8765 \
    mlcivilengineer/anki-desktop-docker:main
```

### Manual Setup

If you prefer not to provide credentials, run without them:

```bash
docker run -d \
    --name anki-desktop \
    -e PUID=1000 \
    -e PGID=1000 \
    -v "$(pwd)/anki_data:/config" \
    -p 3000:3000 \
    -p 8765:8765 \
    mlcivilengineer/anki-desktop-docker:main
```

Then open http://localhost:3000 and:
1. Complete Anki setup wizard
2. Install AnkiConnect addon (code: 2055492159)
3. Configure AnkiConnect (see [AnkiConnect Configuration](#ankiconnect-configuration))
4. Set up AnkiWeb sync in Settings


## Docker Compose Setup

For easier configuration management, use docker-compose with environment file:

1. **Clone repository**:
   ```bash
   git clone https://github.com/mlcivilengineer/anki-desktop-docker
   cd anki-desktop-docker
   ```

2. **Create `.env` file**:
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` and configure**:
   ```bash
   # Required for automated setup
   ANKIWEB_USER=your-email@example.com
   ANKIWEB_PASSWORD=your-password    # OR use ANKIWEB_SYNC_KEY

   # Optional settings
   AUTO_SYNC_ON_START=false          # Set to true for auto-sync
   ANKICONNECT_BIND_PORT=8765
   ```

4. **Start container**:
   ```bash
   docker compose up -d
   ```

The `docker-compose.yml` automatically loads variables from `.env` file. See [.env.example](.env.example) for all available options.

---

## Environment Variables

### AnkiWeb Sync
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ANKIWEB_USER` | AnkiWeb email/username | For auto-setup | - |
| `ANKIWEB_PASSWORD` | AnkiWeb password | One of password/key | - |
| `ANKIWEB_SYNC_KEY` | AnkiWeb sync key (preferred) | One of password/key | - |
| `AUTO_SYNC_ON_START` | Auto-sync on container start | No | `false` |

### AnkiConnect Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `ANKICONNECT_BIND_ADDRESS` | Bind address | `0.0.0.0` |
| `ANKICONNECT_BIND_PORT` | Bind port | `8765` |
| `ANKICONNECT_CORS_ORIGIN` | CORS origins (JSON array) | `["*"]` |
| `ANKICONNECT_API_KEY` | Optional API key for auth | - |
| `ANKICONNECT_API_LOG_PATH` | Optional log file path | - |

### System
| Variable | Description | Default |
|----------|-------------|---------|
| `PUID` | User ID for permissions | `1000` |
| `PGID` | Group ID for permissions | `1000` |
| `TZ` | Timezone | `UTC` |

---

## Getting Your Sync Key

For security, use sync key instead of password:

**Using the included script**:
```bash
./get_sync_key.sh your-email@example.com your-password
```

**Using Docker directly**:
```bash
docker run --rm mlcivilengineer/anki-desktop-docker:main \
  python3 /app/scripts/get_anki_synckey.py \
  --user your-email@example.com \
  --password your-password
```

**With debug output**:
```bash
./get_sync_key.sh your-email@example.com your-password --debug
```

The script outputs only the 16-character key, perfect for scripting:
```bash
echo "ANKIWEB_SYNC_KEY=$(./get_sync_key.sh user@email.com pass)" >> .env
```

---

## Optional: CJK Font Support

If you need support for Chinese, Japanese, or Korean (CJK) characters in your Anki cards, you can enable this by uncommenting the following environment variables in the `docker-compose.yml` file:

```yaml
environment:
  - PUID=1000
  - PGID=1000
  # Uncomment the following lines to enable CJK font support
  - DOCKER_MODS=linuxserver/mods:universal-package-install
  - INSTALL_PACKAGES=language-pack-zh-hans|fonts-arphic-ukai|fonts-arphic-uming|fonts-ipafont-mincho|fonts-ipafont-gothic|fonts-unfonts-core
```

After making these changes, rebuild your container for the changes to take effect.

## AnkiConnect Configuration

### Automated Setup
When using automated setup (with `ANKIWEB_USER` + password/key), AnkiConnect is **automatically installed and configured**. No manual steps needed!

### Manual Setup
If setting up manually via web UI, install [AnkiConnect addon 2055492159](https://ankiweb.net/shared/info/2055492159) and configure with:

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

### Custom Configuration
Use environment variables to customize AnkiConnect:
```bash
-e ANKICONNECT_BIND_PORT=8765 \
-e ANKICONNECT_CORS_ORIGIN='["http://myapp.com"]' \
-e ANKICONNECT_API_KEY=my-secret-key
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

