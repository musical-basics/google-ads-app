"""
One-time local script to mint a Google Ads OAuth refresh token.

Prereqs:
1. In Google Cloud Console, create OAuth 2.0 credentials of type "Desktop app".
   Download the client JSON (or copy client_id + client_secret).
2. Make sure the OAuth consent screen has the Google Ads API enabled and
   you're either a test user or the app is published.

Usage:
    GOOGLE_ADS_CLIENT_ID=... GOOGLE_ADS_CLIENT_SECRET=... \\
        python3 scripts/get_refresh_token.py

The script opens your browser, completes the OAuth flow, and prints the
refresh token to stdout. Paste it into Vercel env as GOOGLE_ADS_REFRESH_TOKEN.

You only need to run this once. The refresh token does not expire unless
explicitly revoked or unused for ~6 months.
"""
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/adwords"]


def main():
    client_id = os.environ.get("GOOGLE_ADS_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_ADS_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("set GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET first", file=sys.stderr)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    print()
    print("=" * 60)
    print("REFRESH TOKEN (paste this into Vercel env GOOGLE_ADS_REFRESH_TOKEN):")
    print()
    print(creds.refresh_token)
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
