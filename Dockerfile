FROM lsiobase/kasmvnc:ubuntunoble

ARG ANKI_VERSION=25.07.5

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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download, Extract, and Install Anki
RUN dpkg --remove anki && \
  wget https://github.com/ankitects/anki/releases/download/${ANKI_VERSION}/anki-launcher-${ANKI_VERSION}-linux.tar.zst && \
  tar --use-compress-program=unzstd -xvf anki-launcher-${ANKI_VERSION}-linux.tar.zst && \
  cd anki-launcher-${ANKI_VERSION}-linux && ./install.sh &&  cd .. && \
  rm -rf anki-launcher-${ANKI_VERSION}-linux anki-launcher-${ANKI_VERSION}-linux.tar.zst

# Create a config directory to be mounted and add symbolic links to Anki's real config directories
RUN mkdir -p /config/.local/share && \
  ln -s /config/app/Anki  /config/.local/share/Anki  && \
  ln -s /config/app/Anki2 /config/.local/share/Anki2

COPY ./root /

EXPOSE 3000 8765
