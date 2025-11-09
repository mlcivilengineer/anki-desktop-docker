#!/usr/bin/env python3
"""
Unified Anki setup script for Docker automation.

This script handles all setup operations:
- create-profile: Create prefs21.db with AnkiWeb sync settings
- install-addon: Download and install AnkiConnect add-on
- configure-addon: Configure AnkiConnect for API access
- setup-all: Run all operations in sequence

Designed to be idempotent and run inside Docker container on first start.
Supports environment variables for automated configuration.
"""

import argparse
import io
import json
import os
import pickle
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse
import zipfile

try:
    import requests
except ImportError:
    print("Error: requests library not installed")
    print("Install with: pip install requests zstandard")
    sys.exit(1)

try:
    import zstandard as zstd
except ImportError:
    print("Error: zstandard library not installed")
    print("Install with: pip install zstandard")
    sys.exit(1)


# Constants
ANKICONNECT_ADDON_ID = 2055492159
ANKIWEB_SYNC_URL = "https://sync21.ankiweb.net/"
ANKIWEB_HOST_KEY_URL = "https://sync21.ankiweb.net/sync/hostKey"
ANKIWEB_SHARED_URL = "https://ankiweb.net/shared/"
ANKI_VERSION = "2.1"
DEFAULT_PROFILE = "user"


class AnkiSetup:
    """Main setup class for Anki Docker automation."""

    def __init__(
        self,
        config_dir: str,
        verbose: bool = False,
        ankiconnect_config: Optional[dict] = None
    ):
        self.config_dir = Path(config_dir)
        self.anki2_dir = self.config_dir / ".local" / "share" / "Anki2"
        self.prefs_db = self.anki2_dir / "prefs21.db"
        self.addons_dir = self.anki2_dir / "addons21"
        self.verbose = verbose
        self.ankiconnect_config = ankiconnect_config or {}

    def log(self, message: str):
        """Print log message if verbose mode enabled."""
        if self.verbose:
            print(f"  {message}")

    def info(self, message: str):
        """Print info message always."""
        print(message)

    # ========== Profile Creation ==========

    def get_sync_key_from_server(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate with AnkiWeb and retrieve sync key.

        Args:
            username: AnkiWeb email/username
            password: AnkiWeb password

        Returns:
            Sync key string or None if failed
        """
        payload = {"u": username, "p": password}
        body_json = json.dumps(payload).encode('utf-8')

        # Compress body with zstd
        compressor = zstd.ZstdCompressor()
        compressed_body = compressor.compress(body_json)

        # Prepare sync header
        sync_header = {
            "v": 11,  # Sync version 11
            "k": "",  # Empty sync key for login
            "c": "anki,24.11.3 (dev),linux",
            "s": ""   # Empty session key for login
        }

        headers = {
            "anki-sync": json.dumps(sync_header),
            "Content-Type": "application/octet-stream",
            "User-Agent": "Anki"
        }

        self.log(f"Authenticating with AnkiWeb as {username}")

        try:
            response = requests.post(
                ANKIWEB_HOST_KEY_URL,
                data=compressed_body,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                self.info(f"[ERROR] HTTP {response.status_code} from AnkiWeb")
                return None

            # Decompress response
            try:
                decompressor = zstd.ZstdDecompressor()
                decompressed_body = decompressor.decompress(
                    response.content,
                    max_output_size=10*1024*1024
                )
                data = json.loads(decompressed_body)

                if "key" in data:
                    self.log("Successfully retrieved sync key")
                    return data["key"]
                else:
                    self.info(f"[ERROR] No 'key' in AnkiWeb response")
                    return None

            except zstd.ZstdError:
                # Try streaming decompression
                decompressor = zstd.ZstdDecompressor()
                with decompressor.stream_reader(response.content) as reader:
                    decompressed_body = reader.read()
                data = json.loads(decompressed_body)

                if "key" in data:
                    self.log("Successfully retrieved sync key")
                    return data["key"]
                else:
                    self.info("[ERROR] No 'key' in response")
                    return None

        except requests.exceptions.RequestException as e:
            self.info(f"[ERROR] Connection error: {e}")
            return None
        except Exception as e:
            self.info(f"[ERROR] {e}")
            return None

    def create_profile(
        self,
        sync_user: str = "",
        sync_key: str = "",
        sync_password: Optional[str] = None,
        no_sync: bool = False
    ) -> bool:
        """
        Create prefs21.db profile database.

        Args:
            sync_user: AnkiWeb email/username
            sync_key: AnkiWeb sync key (takes precedence)
            sync_password: AnkiWeb password (retrieves key if no sync_key)
            no_sync: Skip sync setup entirely

        Returns:
            True if successful
        """
        if self.prefs_db.exists():
            self.info(f"[OK] Profile database already exists: {self.prefs_db}")
            return True

        self.info("[*] Creating profile database...")

        # Determine sync key
        final_sync_key = sync_key

        if not final_sync_key and sync_password and not no_sync:
            if not sync_user:
                self.info("[ERROR] sync_user required when using password")
                return False

            final_sync_key = self.get_sync_key_from_server(sync_user, sync_password)

            if not final_sync_key:
                self.info("[ERROR] Failed to retrieve sync key from AnkiWeb")
                return False

        # Ensure parent directory exists
        self.anki2_dir.mkdir(parents=True, exist_ok=True)

        # Create database
        conn = sqlite3.connect(str(self.prefs_db))
        cursor = conn.cursor()

        # Create profiles table
        cursor.execute("""
            CREATE TABLE profiles (
                name TEXT PRIMARY KEY COLLATE NOCASE,
                data BLOB NOT NULL
            )
        """)

        # Get language from environment or use default
        default_lang = os.getenv('ANKI_LANG', 'en_US')

        # Create _global record
        global_data = {
            "last_loaded_profile": DEFAULT_PROFILE,
            "defaultLang": default_lang,
            "firstRun": False
        }
        global_blob = pickle.dumps(global_data, protocol=4)
        cursor.execute(
            "INSERT INTO profiles (name, data) VALUES (?, ?)",
            ("_global", global_blob)
        )

        self.log(f"Created _global profile record")

        # Create user profile record
        profile_data = {
            "syncUser": sync_user if not no_sync else "",
            "syncKey": final_sync_key if not no_sync else "",
            "currentSyncUrl": ANKIWEB_SYNC_URL,
            "hostNum": 21,
            "autoSync": bool(final_sync_key),
            "syncMedia": bool(final_sync_key)
        }

        profile_blob = pickle.dumps(profile_data, protocol=4)
        cursor.execute(
            "INSERT INTO profiles (name, data) VALUES (?, ?)",
            (DEFAULT_PROFILE, profile_blob)
        )

        self.log(f"Created '{DEFAULT_PROFILE}' profile record")
        if sync_user:
            self.log(f"  syncUser: {sync_user}")
            self.log(f"  syncKey: {'*' * len(final_sync_key) if final_sync_key else '(empty)'}")

        conn.commit()
        conn.close()

        self.info(f"[OK] Profile database created: {self.prefs_db}")
        return True

    # ========== Add-on Installation ==========

    def get_int_version(self, year: int = 24, month: int = 11, patch: int = 3) -> int:
        """Convert version to Anki's int_version format."""
        return year * 10_000 + month * 100 + patch

    def download_addon(self, addon_id: int) -> Optional[dict]:
        """
        Download add-on from AnkiWeb.

        Returns dict with data, filename, metadata or None if failed
        """
        current_version = self.get_int_version()
        url = f"{ANKIWEB_SHARED_URL}download/{addon_id}?v={ANKI_VERSION}&p={current_version}"

        self.log(f"Downloading from: {url}")

        try:
            response = requests.get(url, allow_redirects=True, timeout=30)

            if response.status_code != 200:
                self.info(f"[ERROR] HTTP {response.status_code}")
                return None

            # Extract filename
            content_disp = response.headers.get("content-disposition", "")
            match = re.match(r"attachment; filename=(.+)", content_disp)
            filename = match.group(1) if match else f"{addon_id}.ankiaddon"

            # Extract metadata from URL
            parsed = urlparse(response.url)
            query = parse_qs(parsed.query)

            metadata = {
                "mod_time": int(query["t"][0]) if "t" in query else 0,
                "min_point_version": int(query["minpt"][0]) if "minpt" in query else 0,
                "max_point_version": int(query["maxpt"][0]) if "maxpt" in query else 0,
                "branch_index": int(query["bidx"][0]) if "bidx" in query else 0,
            }

            self.log(f"Downloaded: {filename} ({len(response.content)} bytes)")

            return {
                "data": response.content,
                "filename": filename,
                **metadata
            }

        except Exception as e:
            self.info(f"[ERROR] Download failed: {e}")
            return None

    def read_manifest_from_zip(self, zip_data: bytes) -> dict:
        """Read manifest.json from addon zip file."""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                with zf.open("manifest.json") as f:
                    return json.loads(f.read())
        except (KeyError, json.JSONDecodeError, zipfile.BadZipFile):
            return {}

    def install_addon(self) -> bool:
        """
        Download and install AnkiConnect add-on.

        Returns:
            True if successful
        """
        addon_folder = self.addons_dir / str(ANKICONNECT_ADDON_ID)

        if addon_folder.exists():
            self.info(f"[OK] AnkiConnect already installed: {addon_folder}")
            return True

        self.info("[*] Installing AnkiConnect add-on...")

        # Download
        result = self.download_addon(ANKICONNECT_ADDON_ID)
        if not result:
            self.info("[ERROR] Failed to download AnkiConnect")
            return False

        # Read manifest
        manifest = self.read_manifest_from_zip(result["data"])
        addon_name = manifest.get("name", f"Addon {ANKICONNECT_ADDON_ID}")

        self.log(f"Installing: {addon_name}")

        # Create addon folder
        self.addons_dir.mkdir(parents=True, exist_ok=True)
        addon_folder.mkdir(exist_ok=True)

        # Extract zip
        try:
            with zipfile.ZipFile(io.BytesIO(result["data"])) as zf:
                for member in zf.namelist():
                    if member.endswith("/"):
                        continue

                    target_path = addon_folder / member
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    with zf.open(member) as source:
                        target_path.write_bytes(source.read())

                    self.log(f"Extracted: {member}")

            # Create meta.json
            meta = {
                "name": addon_name,
                "mod": result.get("mod_time", 0),
                "min_point_version": result.get("min_point_version", 0),
                "max_point_version": result.get("max_point_version", 0),
                "branch_index": result.get("branch_index", 0),
                "disabled": False
            }

            # Merge manifest metadata
            for key in ["conflicts", "homepage"]:
                if key in manifest:
                    meta[key] = manifest[key]

            meta_path = addon_folder / "meta.json"
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

            self.log(f"Created meta.json")
            self.info(f"[OK] AnkiConnect installed: {addon_folder}")
            return True

        except Exception as e:
            self.info(f"[ERROR] Installation failed: {e}")
            return False

    # ========== Add-on Configuration ==========

    def configure_addon(self) -> bool:
        """
        Configure AnkiConnect for API access.

        Uses self.ankiconnect_config for custom settings.

        Returns:
            True if successful
        """
        addon_folder = self.addons_dir / str(ANKICONNECT_ADDON_ID)
        config_path = addon_folder / "config.json"

        if not addon_folder.exists():
            self.info(f"[ERROR] AnkiConnect not installed at: {addon_folder}")
            return False

        self.info("[*] Configuring AnkiConnect...")

        # Read existing config if present
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                self.log("Loaded existing config")
            except json.JSONDecodeError:
                config = {}
        else:
            config = {}

        # Default configuration
        default_config = {
            "apiKey": None,
            "apiLogPath": None,
            "ignoreOriginList": [],
            "webBindAddress": "0.0.0.0",
            "webBindPort": 8765,
            "webCorsOrigin": "http://localhost",
            "webCorsOriginList": ["*"]
        }

        # Merge with custom config
        config.update(default_config)
        config.update(self.ankiconnect_config)

        # Write configuration
        config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))

        self.log("Configuration:")
        self.log(f"  webBindAddress: {config['webBindAddress']}")
        self.log(f"  webBindPort: {config['webBindPort']}")
        self.log(f"  webCorsOriginList: {config['webCorsOriginList']}")
        if config.get('apiKey'):
            self.log(f"  apiKey: {'*' * 8}")

        self.info(f"[OK] AnkiConnect configured: {config_path}")
        return True

    # ========== Combined Operations ==========

    def setup_all(
        self,
        sync_user: str = "",
        sync_key: str = "",
        sync_password: Optional[str] = None,
        no_sync: bool = False
    ) -> bool:
        """
        Run complete setup: create profile, install addon, configure.

        Returns:
            True if all operations successful
        """
        self.info("=" * 60)
        self.info("Anki Docker Setup")
        self.info("=" * 60)

        # Check if already setup
        if self.prefs_db.exists():
            self.info("[OK] Setup already complete, skipping")
            return True

        # Run all setup operations
        operations = [
            ("Creating profile", lambda: self.create_profile(
                sync_user, sync_key, sync_password, no_sync
            )),
            ("Installing AnkiConnect", self.install_addon),
            ("Configuring AnkiConnect", self.configure_addon)
        ]

        for desc, operation in operations:
            if not operation():
                self.info(f"[ERROR] Failed: {desc}")
                return False

        self.info("=" * 60)
        self.info("[OK] Setup completed successfully")
        self.info("=" * 60)
        return True


def get_env_config() -> dict:
    """Read configuration from environment variables."""
    config = {}

    # AnkiWeb sync settings
    config['sync_user'] = os.getenv('ANKIWEB_USER', '')
    config['sync_password'] = os.getenv('ANKIWEB_PASSWORD')
    config['sync_key'] = os.getenv('ANKIWEB_SYNC_KEY', '')

    # AnkiConnect settings
    ankiconnect_config = {}

    bind_addr = os.getenv('ANKICONNECT_BIND_ADDRESS')
    if bind_addr:
        ankiconnect_config['webBindAddress'] = bind_addr

    bind_port = os.getenv('ANKICONNECT_BIND_PORT')
    if bind_port:
        try:
            ankiconnect_config['webBindPort'] = int(bind_port)
        except ValueError:
            pass

    cors_origin = os.getenv('ANKICONNECT_CORS_ORIGIN')
    if cors_origin:
        try:
            ankiconnect_config['webCorsOriginList'] = json.loads(cors_origin)
        except json.JSONDecodeError:
            ankiconnect_config['webCorsOriginList'] = [cors_origin]

    api_key = os.getenv('ANKICONNECT_API_KEY')
    if api_key:
        ankiconnect_config['apiKey'] = api_key

    api_log_path = os.getenv('ANKICONNECT_API_LOG_PATH')
    if api_log_path:
        ankiconnect_config['apiLogPath'] = api_log_path

    config['ankiconnect_config'] = ankiconnect_config

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Unified Anki setup script for Docker automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Actions:
  create-profile     Create prefs21.db with sync settings
  install-addon      Download and install AnkiConnect
  configure-addon    Configure AnkiConnect for API access
  setup-all          Run all operations (default)

Environment Variables:
  ANKIWEB_USER                  AnkiWeb email/username
  ANKIWEB_PASSWORD              AnkiWeb password
  ANKIWEB_SYNC_KEY              AnkiWeb sync key (preferred over password)
  ANKICONNECT_BIND_ADDRESS      Bind address (default: 0.0.0.0)
  ANKICONNECT_BIND_PORT         Bind port (default: 8765)
  ANKICONNECT_CORS_ORIGIN       CORS origin list as JSON array
  ANKICONNECT_API_KEY           Optional API key for authentication
  ANKICONNECT_API_LOG_PATH      Optional log file path

Examples:
  # Complete setup with password
  %(prog)s setup-all --config-dir /config \\
      --sync-user user@example.com \\
      --sync-password mypassword

  # Complete setup with sync key
  %(prog)s setup-all --config-dir /config \\
      --sync-user user@example.com \\
      --sync-key abc123xyz

  # Setup without sync
  %(prog)s setup-all --config-dir /config --no-sync

  # Use environment variables
  ANKIWEB_USER=user@example.com ANKIWEB_PASSWORD=pass %(prog)s setup-all --config-dir /config
        """
    )

    parser.add_argument(
        "action",
        nargs="?",
        default="setup-all",
        choices=["create-profile", "install-addon", "configure-addon", "setup-all"],
        help="Setup action to perform (default: setup-all)"
    )

    parser.add_argument(
        "--config-dir",
        default=os.getenv('CONFIG_DIR', '/config'),
        help="Anki configuration directory (default: $CONFIG_DIR or /config)"
    )

    parser.add_argument(
        "--sync-user",
        default=None,
        help="AnkiWeb email/username (overrides $ANKIWEB_USER)"
    )

    parser.add_argument(
        "--sync-key",
        default=None,
        help="AnkiWeb sync key (overrides $ANKIWEB_SYNC_KEY)"
    )

    parser.add_argument(
        "--sync-password",
        default=None,
        help="AnkiWeb password (overrides $ANKIWEB_PASSWORD)"
    )

    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip sync setup (create local-only profile)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed progress information"
    )

    args = parser.parse_args()

    # Get config from environment
    env_config = get_env_config()

    # Command-line args override environment variables
    sync_user = args.sync_user or env_config['sync_user']
    sync_key = args.sync_key or env_config['sync_key']
    sync_password = args.sync_password or env_config['sync_password']

    # Initialize setup
    setup = AnkiSetup(
        args.config_dir,
        verbose=args.verbose,
        ankiconnect_config=env_config['ankiconnect_config']
    )

    # Execute action
    success = False

    if args.action == "create-profile":
        success = setup.create_profile(
            sync_user,
            sync_key,
            sync_password,
            args.no_sync
        )
    elif args.action == "install-addon":
        success = setup.install_addon()
    elif args.action == "configure-addon":
        success = setup.configure_addon()
    elif args.action == "setup-all":
        success = setup.setup_all(
            sync_user,
            sync_key,
            sync_password,
            args.no_sync
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
