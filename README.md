# Anki Desktop

This is inspired by the work of https://github.com/pnorcross/anki-desktop-docker , with a couple of modifications. This repo provides a Dockerfile using as a base image https://github.com/linuxserver/docker-baseimage-kasmvnc for the desktop version of Anki, which is useful for automating anki using addons like Anki-Connect and much needed when using the FSRS algorithm and also AnkiDroid, which does not support it. The app is accessible via a web interface bound to port 3000. The anki configuration is bound to a volume mounted at /config/app in the container. 

## REQUIREMENTS
- docker
- docker-compose (does come bundled with newer versions of docker, no need to install it)
- ubuntu (this repo is linux focused, docker can work in windows as well but the installation of it, as well as other software might be different)
- cron (for scheduling)
- AnkiConnect addon (to curl into port 8765)
- FSRS4Anki Helper addon (to reschedule cards)


## Files

### Dockerfile

Used to build the container. Here we install Anki 23.10 (if you would like you can change the version of anki at the Dockerfile, but compatibility is not guaranteed)

### docker_installation file
This file provides the commands to install docker in an ubuntu distro.

### cleanup file
This file provides a way to clean up resources, because apparently Anki has a memory leak and after one day of the app being up, a machine containing only 1gb of RAM should halt and stop working. So we can use something like cron to schedule a cleanup every 12h.

### backup file
This file uses curl into the port 8765 of the container to extract a backup. We can then use cron and schedule daily backups.

### sync file
This file uses curl into the port 8765 of the container to force a sync and reschedule cards if using something like the FSRS algorithm and AnkiDroid, which does not support this algorithm and so we need to reschedule the cards every once in a while.

## Docker Compose Examples

You should create a docker-compose.yml file at the root of the repository containing something like this:

```
services: 
  anki-desktop: 
    build: 
      context: ./
      dockerfile: Dockerfile
    volumes:
      - ~/.local/share/Anki2:/config/app/Anki2
      - ~/backups:/config/app/backups
    ports: 
      - 3000:3000
      # Anki Connect port
      - 8765:8765
```

In this docker-compose file, the first volume provides anki with the configuration, which in linux normally resides in the ~/.local/share/Anki2 directory. This way, all the cards and addons will be there when you run the container, and any changes will persist to the host. The second volume provides a way to get backups out of the container and into the host machine, using something like curl posting to ankiconnect at port 8765. Clone the repository, edit the docker-compose.yml file to your needs (point to the right directory for the anki configuration files, which are normally at ~/.local/share/Anki2 at an ubuntu distroand use the following command in the terminal:

```bash
docker compose up --build
```

You now should be able to open anki at a browser with the following URL:
```
localhost:3000
```

If you also want to use AnkiConnect, make sure your AnkiConnect config looks something like this:
```
{
    "apiKey": null,
    "apiLogPath": null,
    "ignoreOriginList": [],
    "webBindAddress": "0.0.0.0",
    "webBindPort": 8765,
    "webCorsOrigin": "http://localhost",
    "webCorsOriginList": [
        "*"
    ]
}
```

## Cron example

Using the following command:
```bash
crontab -e
```

and pasting the following:

```bash

# Edit this file to introduce tasks to be run by cron.
# 
# Each task to run has to be defined through a single line
# indicating with different fields when the task will be run
# and what command to run for the task
# 
# To define the time you can provide concrete values for
# minute (m), hour (h), day of month (dom), month (mon),
# and day of week (dow) or use '*' in these fields (for 'any').
# 
# Notice that tasks will be started based on the cron's system
# daemon's notion of time and timezones.
# 
# Output of the crontab jobs (including errors) is sent through
# email to the user the crontab file belongs to (unless redirected).
# 
# For example, you can run a backup of all your user accounts
# at 5 a.m every week with:
# 0 5 * * 1 tar -zcf /var/backups/home.tgz /home/
# 
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command
0 8 * * * (~/anki-desktop-docker/sync && date) >> ~/sync.log 2>&1
0 9 * * * (~/anki-desktop-docker/backup && date) >> ~/backup.log 2>&1
0 10,22 * * * (~/anki-desktop-docker/cleanup && date) >> ~/cleanup.log 2>&1

```

should provide the following schedule:
- the sync command at 8h UTC
- the backup command at 9h UTC
- the cleanup command at 10h and 22h UTC

