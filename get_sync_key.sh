#!/bin/bash
# Get AnkiWeb Sync Key - User-facing wrapper script
#
# This script retrieves your AnkiWeb sync key using your credentials.
# The sync key can be used for automated setup without storing passwords.
#
# Usage:
#   ./get_sync_key.sh                          # Interactive prompts
#   ./get_sync_key.sh USER PASSWORD            # Direct arguments
#   ./get_sync_key.sh USER PASSWORD --debug    # With debug output

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    echo "Get AnkiWeb Sync Key"
    echo ""
    echo "Usage:"
    echo "  $0                          Interactive mode (prompts for credentials)"
    echo "  $0 USER PASSWORD            Direct mode"
    echo "  $0 USER PASSWORD --debug    Direct mode with debug output"
    echo ""
    echo "Examples:"
    echo "  # Interactive mode"
    echo "  $0"
    echo ""
    echo "  # Direct mode"
    echo "  $0 user@example.com mypassword"
    echo ""
    echo "  # Save to .env file"
    echo "  SYNC_KEY=\$($0 user@example.com mypassword)"
    echo "  echo \"ANKIWEB_SYNC_KEY=\$SYNC_KEY\" >> .env"
    echo ""
    echo "  # Use with Docker"
    echo "  docker run --rm mlcivilengineer/anki-desktop-docker:main \\"
    echo "    python3 /app/scripts/get_anki_synckey.py --user USER --password PASS"
}

# Check if help requested
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    print_usage
    exit 0
fi

# Method 1: Try to use the Python script directly (if available locally)
if [ -f "scripts/get_anki_synckey.py" ]; then
    echo -e "${GREEN}[*] Using local Python script${NC}" >&2

    if [ $# -eq 0 ]; then
        # Interactive mode
        read -p "AnkiWeb email/username: " USERNAME
        read -sp "AnkiWeb password: " PASSWORD
        echo "" >&2
        DEBUG_FLAG=""
    elif [ $# -eq 2 ]; then
        USERNAME="$1"
        PASSWORD="$2"
        DEBUG_FLAG=""
    elif [ $# -eq 3 ] && [ "$3" = "--debug" ]; then
        USERNAME="$1"
        PASSWORD="$2"
        DEBUG_FLAG="--debug"
    else
        echo -e "${RED}[ERROR] Invalid arguments${NC}" >&2
        print_usage
        exit 1
    fi

    # Check if Python3 and dependencies available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}[ERROR] python3 not found${NC}" >&2
        echo "Install Python 3 or use Docker method below" >&2
        exit 1
    fi

    # Check Python dependencies
    if ! python3 -c "import requests, zstandard" 2>/dev/null; then
        echo -e "${YELLOW}[WARNING] Missing Python dependencies${NC}" >&2
        echo "Installing: requests zstandard" >&2
        pip3 install requests zstandard || {
            echo -e "${RED}[ERROR] Failed to install dependencies${NC}" >&2
            exit 1
        }
    fi

    # Run the script
    python3 scripts/get_anki_synckey.py --user "$USERNAME" --password "$PASSWORD" $DEBUG_FLAG
    exit $?
fi

# Method 2: Use Docker if script not available locally
echo -e "${GREEN}[*] Using Docker method${NC}" >&2

if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker not found and local script not available${NC}" >&2
    echo "Install Docker or download get_anki_synckey.py from the repository" >&2
    exit 1
fi

if [ $# -eq 0 ]; then
    # Interactive mode
    read -p "AnkiWeb email/username: " USERNAME
    read -sp "AnkiWeb password: " PASSWORD
    echo "" >&2
    DEBUG_FLAG=""
elif [ $# -eq 2 ]; then
    USERNAME="$1"
    PASSWORD="$2"
    DEBUG_FLAG=""
elif [ $# -eq 3 ] && [ "$3" = "--debug" ]; then
    USERNAME="$1"
    PASSWORD="$2"
    DEBUG_FLAG="--debug"
else
    echo -e "${RED}[ERROR] Invalid arguments${NC}" >&2
    print_usage
    exit 1
fi

echo -e "${GREEN}[*] Retrieving sync key via Docker...${NC}" >&2

docker run --rm mlcivilengineer/anki-desktop-docker:main \
    python3 /app/scripts/get_anki_synckey.py \
    --user "$USERNAME" \
    --password "$PASSWORD" \
    $DEBUG_FLAG
