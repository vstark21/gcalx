"""OAuth2 authentication for Google Calendar and Tasks APIs."""

from __future__ import annotations

import json
import socket
from contextlib import closing
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from rich.console import Console

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]

console = Console()


def _free_port() -> int:
    """Find a free local port."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def authenticate(
    client_id: str,
    client_secret: str,
    config_dir: Path,
) -> Credentials:
    """Run OAuth2 flow and save credentials.

    Opens a local server for the redirect. Prints the URL for the user
    to visit (useful on headless/remote machines).
    """
    flow = InstalledAppFlow.from_client_config(
        client_config={
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": (
                    "https://www.googleapis.com/oauth2/v1/certs"
                ),
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=SCOPES,
    )

    creds = None
    max_attempts = 5

    for attempt in range(max_attempts):
        port = _free_port()
        console.print(
            f"[dim]Starting auth server on port {port}...[/dim]"
        )
        console.print(
            "[dim]If on a remote machine, forward the port:[/dim]"
        )
        console.print(
            f"[dim]  ssh -L {port}:localhost:{port} user@host[/dim]\n"
        )
        try:
            creds = flow.run_local_server(open_browser=False, port=port)
            break
        except OSError as e:
            if e.errno == 98 and attempt < max_attempts - 1:
                console.print(f"[warning]Port {port} in use, retrying...[/warning]")
            else:
                raise

    if creds is None:
        raise RuntimeError("Failed to authenticate after multiple attempts.")

    _save_token(creds, config_dir)
    console.print("[success]Authentication successful![/success]")
    return creds


def load_credentials(config_dir: Path) -> Credentials | None:
    """Load saved credentials, refreshing if expired.

    Returns None if no token file exists or refresh fails.
    """
    token_path = config_dir / "token.json"
    if not token_path.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    except Exception:
        return None

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds, config_dir)
            return creds
        except Exception:
            return None

    return None


def _save_token(creds: Credentials, config_dir: Path) -> None:
    """Persist credentials to token.json."""
    config_dir.mkdir(parents=True, exist_ok=True)
    token_path = config_dir / "token.json"
    token_path.write_text(creds.to_json())
    # Restrict permissions — token contains secrets
    token_path.chmod(0o600)


def build_calendar_service(creds: Credentials):
    """Build the Google Calendar API v3 service."""
    from googleapiclient.discovery import build

    return build("calendar", "v3", credentials=creds)


def build_tasks_service(creds: Credentials):
    """Build the Google Tasks API v1 service."""
    from googleapiclient.discovery import build

    return build("tasks", "v1", credentials=creds)
