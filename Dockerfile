FROM lsiobase/kasmvnc:ubuntunoble

ARG ANKI_VERSION=26.08.1

# Install dependencies (fix openbox autostart error by installing python3-pyxdg)
RUN apt-get update && \
    apt-get install -y \
        anki \
        wget \
        zstd \
        xdg-utils \
        libxcb-xinerama0 \
        libxcb-cursor0 \
        python3-xdg \
        lame \
        mplayer \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download, Extract, and Install Anki
RUN dpkg --remove anki && \
  wget https://github.com/ankitects/anki/releases/download/${ANKI_VERSION}/anki-${ANKI_VERSION}-linux-x86_64.tar.zst && \
  tar --use-compress-program=unzstd -xvf anki-${ANKI_VERSION}-linux-x86_64.tar.zst && \
  ls -a1 && \
  cd anki-linux && ./install.sh &&  cd .. && \
  rm -rf anki-linux- anki-${ANKI_VERSION}-linux_x86_64.tar.zst

# Remove some unused packages
RUN apt autoremove -y

# Create a config directory to be mounted
RUN mkdir -p /config/.local/share

COPY ./root /

EXPOSE 3000 8765
