"""TikTok data fetching via session cookie (unofficial)."""
import os
import httpx

TIKTOK_API = "https://www.tiktok.com/api"


async def fetch_my_tiktok_videos(max_results: int = 20) -> list[dict]:
    """Fetch user's TikTok videos using session cookie."""
    session_id = os.getenv("TIKTOK_SESSION_ID")
    if not session_id:
        return []

    cookies = {"sessionid": session_id}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.tiktok.com/",
    }

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Get user info first
            resp = await client.get(
                "https://www.tiktok.com/api/user/detail/",
                cookies=cookies,
                headers=headers,
            )
            if resp.status_code != 200:
                return []

            user_data = resp.json()
            user_info = user_data.get("userInfo", {})
            user = user_info.get("user", {})
            sec_uid = user.get("secUid", "")

            if not sec_uid:
                return []

            # Fetch videos
            vid_resp = await client.get(
                "https://www.tiktok.com/api/post/item_list/",
                params={
                    "secUid": sec_uid,
                    "count": max_results,
                    "cursor": 0,
                },
                cookies=cookies,
                headers=headers,
            )

            if vid_resp.status_code != 200:
                return []

            videos = vid_resp.json().get("itemList", [])
            results = []
            for v in videos:
                stats = v.get("stats", {})
                views = stats.get("playCount", 0)
                likes = stats.get("diggCount", 0)
                comments = stats.get("commentCount", 0)
                shares = stats.get("shareCount", 0)
                saves = stats.get("collectCount", 0)

                # Cover image
                cover = v.get("video", {}).get("cover", "")
                vid_id = v.get("id", "")
                author = v.get("author", {}).get("uniqueId", "")

                results.append({
                    "external_id": vid_id,
                    "title": v.get("desc", "")[:120],
                    "platform": "tiktok",
                    "views": views,
                    "likes": likes,
                    "saves": saves,
                    "shares": shares,
                    "comments_count": comments,
                    "engagement_rate": round((likes + comments + saves + shares) / max(views, 1) * 100, 2),
                    "virality_score": round((saves * 3 + shares * 5 + comments * 2 + likes) / max(views, 1) * 100, 2),
                    "thumbnail_url": cover,
                    "video_url": f"https://www.tiktok.com/@{author}/video/{vid_id}",
                    "content_type": "short_video",
                    "topic": v.get("desc", "")[:60],
                    "posted_at": None,
                })

            return results
    except Exception:
        return []


async def fetch_tiktok_profile_stats() -> dict | None:
    """Fetch TikTok profile stats."""
    session_id = os.getenv("TIKTOK_SESSION_ID")
    if not session_id:
        return None

    cookies = {"sessionid": session_id}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.tiktok.com/",
    }

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.tiktok.com/api/user/detail/",
                cookies=cookies,
                headers=headers,
            )
            if resp.status_code != 200:
                return None

            user_info = resp.json().get("userInfo", {})
            stats = user_info.get("stats", {})
            user = user_info.get("user", {})

            return {
                "platform": "tiktok",
                "followers": stats.get("followerCount", 0),
                "total_views": stats.get("heartCount", 0),
                "video_count": stats.get("videoCount", 0),
                "channel_name": user.get("uniqueId", ""),
            }
    except Exception:
        return None
