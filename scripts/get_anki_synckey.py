#!/usr/bin/env python3
"""
Retrieve AnkiWeb sync key using credentials.

This standalone script authenticates with AnkiWeb and retrieves
the sync key (hkey) for use in automated setups.

Default output: Just the 16-character sync key
Debug mode: Detailed protocol exchange information
"""

import argparse
import json
import sys

try:
    import requests
except ImportError:
    print("Error: requests library not installed", file=sys.stderr)
    print("Install with: pip install requests zstandard", file=sys.stderr)
    sys.exit(1)

try:
    import zstandard as zstd
except ImportError:
    print("Error: zstandard library not installed", file=sys.stderr)
    print("Install with: pip install zstandard", file=sys.stderr)
    sys.exit(1)


ANKIWEB_HOST_KEY_URL = "https://sync21.ankiweb.net/sync/hostKey"


def log_debug(message: str, debug: bool):
    """Print debug message if debug mode enabled."""
    if debug:
        print(f"[DEBUG] {message}", file=sys.stderr)


def get_sync_key(username: str, password: str, debug: bool = False) -> str:
    """
    Authenticate with AnkiWeb and retrieve sync key.

    Args:
        username: AnkiWeb email/username
        password: AnkiWeb password
        debug: Enable debug output

    Returns:
        Sync key string or empty string if failed
    """
    # Sanitize username for debug output (hide part of email)
    sanitized_user = username
    if '@' in username and debug:
        parts = username.split('@')
        sanitized_user = f"{parts[0][:2]}***@{parts[1]}"

    log_debug(f"Authenticating as: {sanitized_user if debug else '***'}", debug)

    payload = {"u": username, "p": password}
    body_json = json.dumps(payload).encode('utf-8')

    log_debug(f"Payload size: {len(body_json)} bytes", debug)

    # Compress body with zstd
    compressor = zstd.ZstdCompressor()
    compressed_body = compressor.compress(body_json)

    log_debug(f"Compressed size: {len(compressed_body)} bytes", debug)

    # Prepare sync header
    sync_header = {
        "v": 11,  # Sync version 11
        "k": "",  # Empty sync key for login
        "c": "anki,24.11.3 (dev),linux",
        "s": ""   # Empty session key for login
    }

    log_debug(f"Sync protocol version: {sync_header['v']}", debug)

    headers = {
        "anki-sync": json.dumps(sync_header),
        "Content-Type": "application/octet-stream",
        "User-Agent": "Anki"
    }

    log_debug(f"Sending POST to: {ANKIWEB_HOST_KEY_URL}", debug)

    try:
        response = requests.post(
            ANKIWEB_HOST_KEY_URL,
            data=compressed_body,
            headers=headers,
            timeout=30
        )

        log_debug(f"Response status: {response.status_code}", debug)
        log_debug(f"Response size: {len(response.content)} bytes", debug)

        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code} from AnkiWeb", file=sys.stderr)
            return ""

        # Decompress response
        try:
            decompressor = zstd.ZstdDecompressor()
            decompressed_body = decompressor.decompress(
                response.content,
                max_output_size=10*1024*1024
            )
            log_debug(f"Decompressed size: {len(decompressed_body)} bytes", debug)

            data = json.loads(decompressed_body)

            if debug:
                # Show response structure without sensitive data
                sanitized_data = {k: ('***' if k == 'key' else v) for k, v in data.items()}
                log_debug(f"Response data: {json.dumps(sanitized_data)}", debug)

            if "key" in data:
                sync_key = data["key"]
                log_debug(f"Sync key retrieved: {sync_key[:4]}***{sync_key[-4:]}", debug)
                return sync_key
            else:
                print("Error: No 'key' in AnkiWeb response", file=sys.stderr)
                return ""

        except zstd.ZstdError as e:
            log_debug(f"zstd error, trying streaming decompression", debug)
            # Try streaming decompression
            decompressor = zstd.ZstdDecompressor()
            with decompressor.stream_reader(response.content) as reader:
                decompressed_body = reader.read()
            data = json.loads(decompressed_body)

            if "key" in data:
                sync_key = data["key"]
                log_debug(f"Sync key retrieved: {sync_key[:4]}***{sync_key[-4:]}", debug)
                return sync_key
            else:
                print("Error: No 'key' in response", file=sys.stderr)
                return ""

    except requests.exceptions.Timeout:
        print("Error: Connection timeout", file=sys.stderr)
        return ""
    except requests.exceptions.RequestException as e:
        print(f"Error: Connection failed: {e}", file=sys.stderr)
        return ""
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON response: {e}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return ""


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve AnkiWeb sync key",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get sync key (quiet mode - just the key)
  %(prog)s --user user@example.com --password mypassword

  # Get sync key with debug output
  %(prog)s --user user@example.com --password mypassword --debug

  # Use in scripts
  SYNC_KEY=$(%(prog)s --user $USER --password $PASS)
  echo "ANKIWEB_SYNC_KEY=$SYNC_KEY" >> .env

Exit Codes:
  0 - Success (sync key retrieved)
  1 - Failure (authentication or connection error)
        """
    )

    parser.add_argument(
        "--user",
        required=True,
        help="AnkiWeb email/username"
    )

    parser.add_argument(
        "--password",
        required=True,
        help="AnkiWeb password"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed protocol information (to stderr)"
    )

    args = parser.parse_args()

    # Get sync key
    sync_key = get_sync_key(args.user, args.password, args.debug)

    if sync_key:
        # Output only the key to stdout (for scripting)
        print(sync_key)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
