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

## Deployment with Coolify & Traefik

If you're deploying this application with [Coolify](https://coolify.io/) using **Raw Compose Deployment**, the docker-compose.yml is already configured with the necessary Traefik labels and networks.

### Prerequisites

1. Coolify v4 installed with Traefik as reverse proxy
2. A domain name pointing to your Coolify server
3. DNS configuration:
   - **Main domain**: `anki.yourdomain.com` → Your Coolify server IP
   - **API subdomain**: `api.anki.yourdomain.com` → Your Coolify server IP
   - **OR** use wildcard DNS: `*.yourdomain.com` → Your Coolify server IP

### Setup Steps

1. **Create a new service in Coolify:**
   - Go to your Coolify dashboard
   - Create a new "Docker Compose" resource
   - Select "Raw Compose Deployment" mode

2. **Paste the docker-compose.yml content:**
   - Copy the entire content of `docker-compose.yml` from this repository
   - Paste it into Coolify's compose editor

3. **Configure environment variables in Coolify UI:**

   Coolify will automatically inject most variables, but you may need to set:
   - `SERVICE_FQDN_ANKI_DESKTOP` - Your domain (e.g., `anki.yourdomain.com`)
   - `IMAGE_TAG` - Docker image tag (default: `main`)
   - `PUID` / `PGID` - User/Group IDs (default: `1000`)

   Coolify automatically provides these variables:
   - `COOLIFY_RESOURCE_UUID` - Unique resource identifier
   - `COOLIFY_CONTAINER_NAME` - Container name with timestamp
   - `COOLIFY_APPLICATION_ID` - Application ID
   - `SERVICE_URL_ANKI_DESKTOP` - Full service URL
   - All other `COOLIFY_*` variables

4. **Deploy:**
   - Click "Deploy" in Coolify
   - Wait for the deployment to complete
   - Access your services:
     - **Web UI**: `https://anki.yourdomain.com` (port 3000 internally)
     - **AnkiConnect API**: `https://api.anki.yourdomain.com` (port 8765 internally)

### Features

- **Automatic HTTPS**: Let's Encrypt certificates via Traefik for both domains
- **HTTP → HTTPS redirect**: Automatic redirect configured
- **Gzip compression**: Enabled for better performance
- **Health checks**: Container health monitoring with auto-restart
- **Persistent storage**: Data stored in named volume with UUID
- **Network isolation**: Uses both `coolify` and resource-specific networks
- **Dual domain setup**:
  - Web UI on main domain: `${SERVICE_FQDN_ANKI_DESKTOP}`
  - API on subdomain: `api.${SERVICE_FQDN_ANKI_DESKTOP}`

### Domain Configuration

The application is configured to serve:
- **Web Interface (KasmVNC)**: `https://anki.yourdomain.com`
- **AnkiConnect API**: `https://api.anki.yourdomain.com`

Both domains are automatically derived from the `SERVICE_FQDN_ANKI_DESKTOP` environment variable:
- If you set `SERVICE_FQDN_ANKI_DESKTOP=anki.example.com`
- Web UI will be at: `https://anki.example.com`
- API will be at: `https://api.anki.example.com`

**To disable external API access**, comment out the AnkiConnect labels in `docker-compose.yml` (lines 68-78).

### Important Notes

- **Raw Compose Deployment** means the compose file is the single source of truth
- All environment variables must be defined in the compose file using `${VARIABLE}` syntax
- Coolify will inject variables through its UI, no `.env` file needed
- The `coolify` and `${COOLIFY_RESOURCE_UUID}` networks must exist (Coolify creates them automatically)

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

After deployment, you need to install and configure the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) Add-on:

1. Open Anki in the web interface at `https://anki.yourdomain.com`
2. Install AnkiConnect add-on (code: `2055492159`)
3. Configure the add-on with the following settings:

```json
{
    "apiKey": null,
    "apiLogPath": null,
    "ignoreOriginList": [],
    "webBindAddress": "0.0.0.0",
    "webBindPort": 8765,
    "webCorsOrigin": "https://api.anki.yourdomain.com",
    "webCorsOriginList": [
        "https://api.anki.yourdomain.com",
        "http://localhost",
        "*"
    ]
}
```

4. Restart Anki for changes to take effect
5. Test the API at `https://api.anki.yourdomain.com`

**Example API request:**
```bash
curl -X POST https://api.anki.yourdomain.com \
  -H "Content-Type: application/json" \
  -d '{"action": "version", "version": 6}'
```

---

## Cron Example

When using Coolify deployment with the API subdomain, you can access AnkiConnect remotely. Open your crontab:

```bash
crontab -e
```

And add (replace `api.anki.yourdomain.com` with your actual domain):

```cron
# Using remote API endpoint
0 8 * * * curl -X POST https://api.anki.yourdomain.com -H "Content-Type: application/json" -d '{"action":"sync","version":6}' >> ~/anki-sync.log 2>&1
0 9 * * * curl -X POST https://api.anki.yourdomain.com -H "Content-Type: application/json" -d '{"action":"exportPackage","version":6,"params":{"deck":"All","path":"/config/backup.apkg"}}' >> ~/anki-backup.log 2>&1
```

**For local deployment**, you can use the original scripts:

```cron
0 8 * * * (~/anki-desktop-docker/sync && date) >> ~/sync.log 2>&1
0 9 * * * (~/anki-desktop-docker/backup && date) >> ~/backup.log 2>&1
0 10,22 * * * (~/anki-desktop-docker/cleanup && date) >> ~/cleanup.log 2>&1
```

This sets up:

* **8:00 UTC** — Sync
* **9:00 UTC** — Backup
* **10:00 & 22:00 UTC** — Cleanup (only needed for local deployment)

