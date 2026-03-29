"""YouTube Data API integration."""
import os
import httpx

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"


async def get_access_token() -> str | None:
    """Get a fresh access token using the refresh token."""
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("YOUTUBE_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data={
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
        })
        data = resp.json()
        return data.get("access_token")


async def fetch_my_videos(max_results: int = 20) -> list[dict]:
    """Fetch the authenticated user's uploaded videos with stats."""
    token = await get_access_token()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15) as client:
        # Get the user's channel and uploads playlist
        ch_resp = await client.get(f"{YOUTUBE_API}/channels", headers=headers, params={
            "part": "contentDetails,statistics,snippet",
            "mine": "true",
        })
        channels = ch_resp.json().get("items", [])
        if not channels:
            return []

        channel = channels[0]
        uploads_playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]
        channel_stats = channel.get("statistics", {})

        # Get videos from uploads playlist
        pl_resp = await client.get(f"{YOUTUBE_API}/playlistItems", headers=headers, params={
            "part": "snippet",
            "playlistId": uploads_playlist,
            "maxResults": max_results,
        })
        items = pl_resp.json().get("items", [])

        if not items:
            return []

        # Get video statistics and status (to filter out private videos)
        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in items]
        stats_resp = await client.get(f"{YOUTUBE_API}/videos", headers=headers, params={
            "part": "statistics,snippet,status",
            "id": ",".join(video_ids),
        })
        video_stats = {v["id"]: v for v in stats_resp.json().get("items", [])}

        results = []
        for item in items:
            vid_id = item["snippet"]["resourceId"]["videoId"]
            vid_data = video_stats.get(vid_id, {})

            # Skip private and unlisted videos
            privacy = vid_data.get("status", {}).get("privacyStatus", "public")
            if privacy != "public":
                continue

            snippet = item["snippet"]
            stats = vid_data.get("statistics", {})

            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))

            # Thumbnails: try maxres, then high, then medium, then default
            thumbs = snippet.get("thumbnails", {})
            thumb_url = (
                thumbs.get("maxres", {}).get("url") or
                thumbs.get("high", {}).get("url") or
                thumbs.get("medium", {}).get("url") or
                thumbs.get("default", {}).get("url") or
                ""
            )

            results.append({
                "external_id": vid_id,
                "title": snippet.get("title", ""),
                "platform": "youtube",
                "views": views,
                "likes": likes,
                "saves": 0,
                "shares": 0,
                "comments_count": comments,
                "engagement_rate": round((likes + comments) / max(views, 1), 4),
                "virality_score": round((likes + comments * 2) / max(views, 1) * 10, 2),
                "thumbnail_url": thumb_url,
                "video_url": f"https://youtube.com/watch?v={vid_id}",
                "content_type": "video",
                "topic": snippet.get("title", ""),
                "posted_at": snippet.get("publishedAt"),
            })

        return results


async def fetch_channel_stats() -> dict | None:
    """Fetch channel-level stats (subscribers, total views)."""
    token = await get_access_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{YOUTUBE_API}/channels", headers=headers, params={
            "part": "statistics,snippet",
            "mine": "true",
        })
        channels = resp.json().get("items", [])
        if not channels:
            return None
        ch = channels[0]
        stats = ch.get("statistics", {})
        return {
            "platform": "youtube",
            "followers": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "channel_name": ch.get("snippet", {}).get("title", ""),
        }
