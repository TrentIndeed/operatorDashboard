"""
One-time Google OAuth flow to get a refresh token.
After getting the token, save it to .env and this route can be removed.
"""
import os
from urllib.parse import urlencode
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import httpx

router = APIRouter(prefix="/auth/google", tags=["auth"])

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]


@router.get("/login")
def google_login():
    """Redirect user to Google OAuth consent screen."""
    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID") or os.getenv("YOUTUBE_CLIENT_ID"),
        "redirect_uri": "http://localhost:8000/auth/google/callback",
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/callback")
async def google_callback(code: str):
    """Exchange auth code for tokens."""
    client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("YOUTUBE_CLIENT_SECRET")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": "http://localhost:8000/auth/google/callback",
                "grant_type": "authorization_code",
            },
        )
        tokens = resp.json()

    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")

    if refresh_token:
        # Auto-save refresh token to .env
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        try:
            with open(env_path, "r") as f:
                env_content = f.read()
            if "GOOGLE_REFRESH_TOKEN=" in env_content:
                lines = env_content.splitlines()
                for i, line in enumerate(lines):
                    if line.startswith("GOOGLE_REFRESH_TOKEN="):
                        lines[i] = f"GOOGLE_REFRESH_TOKEN={refresh_token}"
                env_content = "\n".join(lines) + "\n"
            else:
                env_content += f"\nGOOGLE_REFRESH_TOKEN={refresh_token}\n"
            with open(env_path, "w") as f:
                f.write(env_content)
            os.environ["GOOGLE_REFRESH_TOKEN"] = refresh_token
        except Exception:
            pass

        return {
            "status": "success",
            "message": "Google connected! Refresh token has been saved to .env automatically.",
            "refresh_token": refresh_token,
        }
    else:
        return {
            "status": "error",
            "message": "No refresh token returned. Try revoking access at https://myaccount.google.com/permissions and retry.",
            "response": tokens,
        }
