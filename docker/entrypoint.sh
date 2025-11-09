#!/bin/bash
set -e

# Anki Docker Entrypoint
# Simple passthrough to base image's /init script
# Automated setup happens in autostart (after user switch)

echo "========================================"
echo "Anki Desktop Docker"
echo "========================================"
echo "[*] Web UI will be available at http://localhost:3000"
echo "[*] AnkiConnect API at http://localhost:8765"
echo "========================================"

# Execute original entrypoint (KasmVNC)
# Note: /init must run as PID 1, so we exec it
exec /init
