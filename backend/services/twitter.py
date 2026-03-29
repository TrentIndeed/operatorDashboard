"""Twitter/X API v2 integration using OAuth 1.0a user context."""
import os
import hashlib
import hmac
import time
import urllib.parse
import base64
import secrets
import httpx

TWITTER_API = "https://api.twitter.com/2"


def _oauth1_header(method: str, url: str, params: dict = None) -> str:
    """Generate OAuth 1.0a Authorization header."""
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY", "").strip()
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET", "").strip()
    access_token = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
    access_secret = os.getenv("TWITTER_ACCESS_SECRET", "").strip()

    if not all([consumer_key, consumer_secret, access_token, access_secret]):
        return ""

    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    # Combine all params for signature base
    all_params = {**oauth_params, **(params or {})}
    sorted_params = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )

    base_string = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(sorted_params, safe='')}"
    signing_key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(access_secret, safe='')}"

    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()

    oauth_params["oauth_signature"] = signature

    header = "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
    return header


def _has_oauth1_creds() -> bool:
    return all([
        os.getenv("TWITTER_CONSUMER_KEY", "").strip(),
        os.getenv("TWITTER_CONSUMER_SECRET", "").strip(),
        os.getenv("TWITTER_ACCESS_TOKEN", "").strip(),
        os.getenv("TWITTER_ACCESS_SECRET", "").strip(),
    ])


async def fetch_my_tweets(max_results: int = 20) -> list[dict]:
    """Fetch authenticated user's recent tweets with metrics using OAuth 1.0a."""
    if not _has_oauth1_creds():
        return []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Get user ID
            url = f"{TWITTER_API}/users/me"
            auth_header = _oauth1_header("GET", url)
            me_resp = await client.get(url, headers={"Authorization": auth_header})
            if me_resp.status_code != 200:
                return []
            user_id = me_resp.json().get("data", {}).get("id")
            username = me_resp.json().get("data", {}).get("username", "")
            if not user_id:
                return []

            # Get tweets with metrics
            tweets_url = f"{TWITTER_API}/users/{user_id}/tweets"
            params = {
                "max_results": str(min(max_results, 100)),
                "tweet.fields": "public_metrics,created_at",
            }
            auth_header = _oauth1_header("GET", tweets_url, params)
            tweets_resp = await client.get(
                tweets_url, headers={"Authorization": auth_header}, params=params,
            )
            if tweets_resp.status_code != 200:
                return []

            tweets = tweets_resp.json().get("data", [])
            results = []
            for t in tweets:
                metrics = t.get("public_metrics", {})
                views = metrics.get("impression_count", 0)
                likes = metrics.get("like_count", 0)
                retweets = metrics.get("retweet_count", 0)
                replies = metrics.get("reply_count", 0)
                quotes = metrics.get("quote_count", 0)

                tweet_id = t.get("id", "")

                results.append({
                    "external_id": tweet_id,
                    "title": t.get("text", "")[:120],
                    "platform": "twitter",
                    "views": views,
                    "likes": likes,
                    "saves": 0,
                    "shares": retweets + quotes,
                    "comments_count": replies,
                    "engagement_rate": round((likes + retweets + replies + quotes) / max(views, 1) * 100, 2),
                    "virality_score": round((retweets * 5 + quotes * 3 + replies * 2 + likes) / max(views, 1) * 100, 2),
                    "thumbnail_url": None,
                    "video_url": f"https://x.com/{username}/status/{tweet_id}",
                    "content_type": "tweet",
                    "topic": t.get("text", "")[:60],
                    "posted_at": t.get("created_at"),
                })

            return results
    except Exception:
        return []


async def fetch_twitter_profile_stats() -> dict | None:
    """Fetch Twitter profile stats using OAuth 1.0a."""
    if not _has_oauth1_creds():
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            url = f"{TWITTER_API}/users/me"
            params = {"user.fields": "public_metrics"}
            auth_header = _oauth1_header("GET", url, params)
            resp = await client.get(url, headers={"Authorization": auth_header}, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json().get("data", {})
            metrics = data.get("public_metrics", {})
            return {
                "platform": "twitter",
                "followers": metrics.get("followers_count", 0),
                "total_views": 0,
                "video_count": metrics.get("tweet_count", 0),
                "channel_name": data.get("username", ""),
            }
    except Exception:
        return None
