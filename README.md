# Anki Desktop in Docker

This project is inspired by [pnorcross/anki-desktop-docker](https://github.com/pnorcross/anki-desktop-docker), with a few tweaks. It provides a `Dockerfile` that uses [linuxserver/docker-baseimage-kasmvnc](https://github.com/linuxserver/docker-baseimage-kasmvnc) as the base image to run the desktop version of Anki inside a container.

Why? Because it makes automating Anki (with addons like AnkiConnect) easier.

The Anki desktop app runs in a browser (via VNC) on port `3000`. Your Anki data is stored in `anki_data` mounted as a volume at '/config` inside the container.

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

## How to run

If you want you can run this using the image `mlcivilengineer/anki-desktop-docker` which is automatically built using Github Actions in this repo. Use the following command:
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

Then open your browser and head to:

```
http://localhost:3000
```

Press Enter after Anki is installed for the first time. Now you can use it as normal. In order to sync with the other clients, put your sync information in the Sync tab.


## Docker Compose Setup

If you prefer docker compose instead, use the `docker-compose.yml` in the root of the repo:
```yaml
services:
  anki-desktop:
    image: mlcivilengineer/anki-desktop-docker:main
    build:
      context: ./
      dockerfile: Dockerfile
    environment:
      - PUID=1000
      - PGID=1000
    volumes:
      - ./anki_data:/config
    ports:
      - 3000:3000  # Web UI
      - 8765:8765  # AnkiConnect

````


To get started:

```bash
git clone <this-repo>
cd anki-desktop-docker
docker compose up -d
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

If you want to expose the Anki client to http requests, make sure to install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) Add-on and to configure the Add-on with:
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

