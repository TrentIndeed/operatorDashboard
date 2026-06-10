"""
Signal Scanner — fetches posts from Reddit and filters by keywords.

Scans target subreddits for people posting about problems ParameshAI solves,
deduplicates against existing leads, and stores new ones.
"""
import os
import time
import httpx
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from db.database import Lead

SUBREDDITS = [
    "onshape", "cad", "SolidWorks", "FusionDesign",
    "3Dprinting", "3Dscanning", "mechanicalengineering",
    "engineering", "reverseengineering",
]

# Source terms: the mesh/scan INPUT we handle
SOURCE_TERMS = [
    "stl", "obj file", ".obj", ".ply", " ply ", "mesh file", "triangle mesh",
    "polygon mesh", "3d scan", "photogrammetry", "point cloud", "scanned part",
    "scanned model", "mesh from", "lidar scan",
]

# Target terms: parametric/CAD OUTPUT or CAD context
TARGET_TERMS = [
    "cad", "parametric", "onshape", "solidworks", "fusion 360", "fusion360",
    "step file", ".step", "stp file", "feature tree", "solid body", "solid model",
    "editable", "reverse engineer", "re-engineer", "rebuild", "digitize",
    "freecad", "inventor", "creo", "sketch",
]

# Negative terms — if present, reject the match (false positive filters)
NEGATIVE_TERMS = [
    # Not-CAD contexts
    "mesh network", "mesh networking", "service mesh", "wifi mesh", "mesh wifi",
    "mesh router", "mesh vpn", "mesh gateway", "kubernetes mesh", "istio",
    "linkerd", "hair mesh", "fabric mesh", "cable mesh", "metal mesh",
    "reverse engineer claude", "reverse engineer our neural", "reverse engineer llm",
    "reverse engineer the model", "reverse engineer chatgpt", "reverse engineer gpt",
    "seo", "screaming frog",
]

# Geometry terms the TOOL CANNOT HANDLE — if these dominate the post, reject.
# ParameshAI only does prismatic parts (brackets, plates, mounts, enclosures).
# It cannot do lofts, sweeps, freeform/organic surfaces, or sculpted shapes.
UNSUPPORTED_GEOMETRY_TERMS = [
    # CAD operations we can't produce
    "loft", "lofting", "lofted", "loft between",
    "sweep along", "swept profile", "sweep a profile",
    # Non-prismatic geometry
    "organic shape", "organic shapes", "organic model", "organic form",
    "freeform surface", "free-form surface", "free form surface",
    "nurbs", "class a surface", "class-a surface",
    "subdivision surface", "subdiv ", " subd ",
    "t-spline", "t spline", "bezier surface",
    # Artistic / sculptural
    "sculpt", "sculpting", "sculpted", "sculpture",
    "character model", "character mesh", "animation mesh",
    "creature", "figurine", "statue", "bust",
    "clay model", "zbrush", "mudbox", "blender sculpt",
    # Bio / medical
    "anatomy", "anatomical", "medical model", "body scan",
    "face scan", "facial", "portrait", "dental",
    "patient", "prosthetic",
    # Non-mechanical scans
    "terrain", "landscape mesh", "mesh terrain", "geologic",
    "architecture scan", "room scan", "house scan", "building scan",
    "historical artifact", "archaeological",
    # Game / VFX / entertainment
    "game asset", "game ready", "video game", "vfx",
    "unreal engine", "unity", "animation rig",
    # Non-CAD use cases picked up from photogrammetry sub
    "photogrammetry service", "colmap", "reality capture workflow",
]

# Geometry terms the TOOL EXCELS AT — only unambiguous mechanical phrases.
# (single words like "case", "housing", "mount" removed — they match too broadly)
SUPPORTED_GEOMETRY_TERMS = [
    # Specific part types
    "bracket", "l-bracket", "l bracket", "u-bracket", "u bracket",
    "mounting plate", "mount plate", "base plate", "baseplate",
    "motor mount", "pcb mount", "motor bracket", "mounting bracket",
    "adapter plate", "cover plate", "end plate", "back plate",
    "fixture plate", "jig plate", "machined part", "machined plate",
    # Enclosures (in CAD context, not SaaS/animal/etc)
    "electronics enclosure", "project enclosure", "pcb enclosure",
    "electronic enclosure", "battery enclosure", "sensor enclosure",
    # Mechanical features
    "bolt pattern", "bolt holes", "mounting holes", "through hole pattern",
    "countersink", "counterbore", "chamfered edge", "filleted edge",
    "prismatic part", "prismatic geometry", "rectilinear part",
    # Classic mechanical vocabulary
    "flange", "gusset", "standoff", "spacer", "boss", "rib feature",
    # Common mesh-to-CAD targets
    "replacement part", "reproduction part", "spare part scan",
    "replicate a part", "recreate the part", "remake this part",
]

# High-intent phrases — must be very specific to mesh-to-parametric context
# (general terms like "reverse engineer" are in TARGET_TERMS only, not here)
HIGH_INTENT_PHRASES = [
    "mesh to cad", "mesh to parametric", "stl to step", "stl to parametric",
    "scan to cad", "scan to parametric", "convert stl", "convert mesh",
    "import stl into", "stl to onshape", "editable cad from stl",
    "how do i convert stl", "how can i convert stl", "convert scan to",
    "spent hours rebuilding", "manual rebuild from", "rebuild from scan",
    "rebuild from stl", "rebuild from mesh", "parametric from stl",
    "parametric from mesh", "reverse engineer stl", "reverse engineer mesh",
    "reverse engineer a scan", "reverse engineer the scan",
]

# Reddit OAuth: set REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET in env
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")

# Cloudflare Worker proxy for Reddit (deploys 15-line worker to cloudflare.com)
# Set REDDIT_PROXY_URL to something like https://reddit-proxy.yourname.workers.dev
REDDIT_PROXY_URL = os.environ.get("REDDIT_PROXY_URL", "")

USER_AGENT = "ParameshAI-LeadScanner/1.0 by u/TrentIndeed"
REDDIT_DELAY_SECONDS = 1.5
_reddit_token: str = ""
_reddit_token_expires: float = 0

# PullPush fallback for when neither OAuth nor proxy is configured
PULLPUSH_URL = "https://api.pullpush.io/reddit/submission/search"

# Hacker News Algolia (free, no auth)
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"

# Onshape Forum API (Vanilla Forums, public, no auth)
ONSHAPE_FORUM_API = "https://forum.onshape.com/api/v2"


def _get_reddit_token() -> str:
    """Get Reddit OAuth bearer token via client credentials (application-only auth)."""
    global _reddit_token, _reddit_token_expires
    if _reddit_token and time.time() < _reddit_token_expires:
        return _reddit_token
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return ""
    try:
        resp = httpx.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            _reddit_token = data.get("access_token", "")
            _reddit_token_expires = time.time() + data.get("expires_in", 3600) - 60
            print(f"[Scanner] Got Reddit OAuth token (expires in {data.get('expires_in', 3600)}s)")
            return _reddit_token
        else:
            print(f"[Scanner] Reddit OAuth failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"[Scanner] Reddit OAuth error: {e}")
    return ""


def _matches_keywords(text: str) -> tuple[bool, int, dict]:
    """
    Check if text matches keywords and is a geometry fit for ParameshAI.

    Returns (matches, score, signals) where signals is a dict with
    'supported_geometry' (count) and 'unsupported_geometry' (count).
    """
    lower = text.lower()

    # Reject if any hard-negative term present
    for neg in NEGATIVE_TERMS:
        if neg in lower:
            return False, 0, {}

    # Count unsupported geometry hits
    unsupported_hits = sum(1 for t in UNSUPPORTED_GEOMETRY_TERMS if t in lower)
    supported_hits = sum(1 for t in SUPPORTED_GEOMETRY_TERMS if t in lower)

    # Reject if post is dominantly about unsupported geometry with no supported signals
    # (e.g. "I need to loft these 6 profiles" — we can't help them)
    if unsupported_hits >= 2 and supported_hits == 0:
        return False, 0, {"unsupported_geometry": unsupported_hits}
    if unsupported_hits >= 1 and supported_hits == 0:
        # Single unsupported term + no supported context — likely not a fit
        return False, 0, {"unsupported_geometry": unsupported_hits}

    # Count matches in each category
    source_hits = sum(1 for t in SOURCE_TERMS if t in lower)
    target_hits = sum(1 for t in TARGET_TERMS if t in lower)
    high_intent_hits = sum(1 for p in HIGH_INTENT_PHRASES if p in lower)

    signals = {
        "supported_geometry": supported_hits,
        "unsupported_geometry": unsupported_hits,
        "high_intent": high_intent_hits,
        "source": source_hits,
        "target": target_hits,
    }

    # Supported geometry bonus: posts about brackets/plates/mounts get auto-match
    # even without target term (source term alone is enough if they mention a part type we do)
    if supported_hits >= 1 and source_hits >= 1:
        return True, (supported_hits * 3) + source_hits + target_hits + (high_intent_hits * 5), signals

    # High intent phrases bypass the source+target requirement
    if high_intent_hits > 0:
        return True, (high_intent_hits * 5) + source_hits + target_hits, signals

    # Otherwise require at least one from each category
    if source_hits >= 1 and target_hits >= 1:
        return True, source_hits + target_hits, signals

    return False, 0, signals


def _classify_tier(text: str, subreddit: str) -> tuple[int, str]:
    """
    Tier classification based on geometry fit + platform + intent.

    Tier 1 = High fit: explicitly asking about mesh→prismatic conversion, OR
             Onshape user + supported geometry mentioned
    Tier 2 = Medium fit: mesh→CAD conversion, supported geometry present
    Tier 3 = Adjacent: tangentially related, lower priority
    """
    lower = text.lower()
    is_onshape = subreddit.lower() == "onshape" or "onshape" in lower
    is_solidworks = "solidworks" in subreddit.lower() or "solidworks" in lower
    is_fusion = "fusion" in subreddit.lower() or "fusion 360" in lower

    has_supported_geometry = any(t in lower for t in SUPPORTED_GEOMETRY_TERMS)
    has_unsupported_geometry = any(t in lower for t in UNSUPPORTED_GEOMETRY_TERMS)

    asking_for_tool = any(p in lower for p in [
        "is there a tool", "looking for", "anyone know how",
        "how do i convert", "how can i convert", "is there a way",
        "what software", "what tool", "best way to",
    ])
    expressing_pain = any(p in lower for p in [
        "spent hours", "takes forever", "so painful", "tedious",
        "manually rebuilding", "hate having to", "rebuild from scratch",
        "pain in the", "hours to rebuild",
    ])

    # TIER 1: Explicitly asking AND has supported geometry (e.g. "convert scanned bracket")
    if has_supported_geometry and (asking_for_tool or expressing_pain):
        return 1, "Asking about converting mesh to supported part type (bracket/plate/mount/enclosure)"

    # TIER 1: Onshape user with supported geometry context
    if is_onshape and has_supported_geometry:
        return 1, "Onshape user mentioning a supported part type"

    # TIER 2: Supported geometry mentioned, mesh→CAD context (any platform)
    if has_supported_geometry:
        return 2, "Supported part type mentioned in mesh-to-CAD context"

    # TIER 2: Onshape user asking general conversion questions
    if is_onshape and (asking_for_tool or expressing_pain):
        return 2, "Onshape user asking about conversion (part type unclear)"

    # TIER 2: Solidworks/Fusion user asking about conversion
    if (is_solidworks or is_fusion) and (asking_for_tool or expressing_pain):
        return 2, "CAD user asking about mesh conversion"

    # TIER 2: Onshape user, general topic
    if is_onshape:
        return 2, "Onshape user discussing adjacent topic"

    # TIER 3: Has unsupported geometry — we can't help but monitor
    if has_unsupported_geometry:
        return 3, "Mentions geometry we don't handle (lofts/sweeps/organic)"

    # Default
    return 3, "Adjacent discussion (scanning, photogrammetry, general mesh editing)"


def _fetch_reddit_oauth(subreddit: str, limit: int = 25) -> list[dict]:
    """Fetch new posts via Reddit OAuth API (requires client credentials)."""
    token = _get_reddit_token()
    if not token:
        return []
    url = f"https://oauth.reddit.com/r/{subreddit}/new"
    try:
        resp = httpx.get(
            url,
            params={"limit": limit},
            headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"[Scanner] r/{subreddit} OAuth returned {resp.status_code}")
            return []
        data = resp.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            full_text = f"{post.get('title', '')} {post.get('selftext', '')}"
            posts.append({
                "subreddit": subreddit,
                "username": post.get("author", ""),
                "title": post.get("title", ""),
                "text": full_text.strip(),
                "url": f"https://www.reddit.com{post.get('permalink', '')}",
                "created_utc": post.get("created_utc", 0),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
            })
        return posts
    except Exception as e:
        print(f"[Scanner] OAuth fetch error r/{subreddit}: {e}")
        return []


def _fetch_reddit_pullpush(subreddit: str, limit: int = 25, days_back: int = 30) -> list[dict]:
    """Fallback: fetch from PullPush archive (may be stale)."""
    cutoff_ts = int(time.time() - (days_back * 86400))
    params = {
        "subreddit": subreddit,
        "size": limit,
        "sort": "desc",
        "sort_type": "created_utc",
        "after": cutoff_ts,
    }
    try:
        resp = httpx.get(PULLPUSH_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=20)
        if resp.status_code != 200:
            return []
        data = resp.json().get("data", [])
        posts = []
        for post in data:
            full_text = f"{post.get('title', '')} {post.get('selftext', '')}"
            permalink = post.get("permalink", "")
            post_url = f"https://www.reddit.com{permalink}" if permalink and not permalink.startswith("http") else (post.get("url", "") or permalink)
            posts.append({
                "subreddit": subreddit,
                "username": post.get("author", ""),
                "title": post.get("title", ""),
                "text": full_text.strip(),
                "url": post_url,
                "created_utc": post.get("created_utc", 0),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
            })
        return posts
    except Exception:
        return []


def _fetch_reddit_via_proxy(subreddit: str, limit: int = 25) -> list[dict]:
    """Fetch Reddit posts via Cloudflare Worker proxy."""
    if not REDDIT_PROXY_URL:
        return []
    url = f"{REDDIT_PROXY_URL.rstrip('/')}/r/{subreddit}/new.json?limit={limit}"
    try:
        resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        if resp.status_code != 200:
            print(f"[Scanner] Reddit proxy r/{subreddit} returned {resp.status_code}")
            return []
        data = resp.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            full_text = f"{post.get('title', '')} {post.get('selftext', '')}"
            posts.append({
                "subreddit": subreddit,
                "username": post.get("author", ""),
                "title": post.get("title", ""),
                "text": full_text.strip(),
                "url": f"https://www.reddit.com{post.get('permalink', '')}",
                "created_utc": post.get("created_utc", 0),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
            })
        return posts
    except Exception as e:
        print(f"[Scanner] Reddit proxy error r/{subreddit}: {e}")
        return []


def _fetch_reddit_posts(subreddit: str, limit: int = 25, days_back: int = 30) -> list[dict]:
    """Fetch posts from a subreddit. Tries proxy, OAuth, then PullPush."""
    cutoff_ts = time.time() - (days_back * 86400)

    if REDDIT_PROXY_URL:
        posts = _fetch_reddit_via_proxy(subreddit, limit)
        return [p for p in posts if p.get("created_utc", 0) >= cutoff_ts]

    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        posts = _fetch_reddit_oauth(subreddit, limit)
        return [p for p in posts if p.get("created_utc", 0) >= cutoff_ts]

    return _fetch_reddit_pullpush(subreddit, limit, days_back)


def _fetch_hackernews(query: str, limit: int = 30, days_back: int = 30) -> list[dict]:
    """Search Hacker News via Algolia API (free, no auth, no blocks)."""
    cutoff_ts = int(time.time() - (days_back * 86400))
    try:
        resp = httpx.get(
            HN_SEARCH_URL,
            params={
                "query": query,
                "tags": "story",
                "hitsPerPage": limit,
                "numericFilters": f"created_at_i>{cutoff_ts}",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"[Scanner] HN returned {resp.status_code}")
            return []
        hits = resp.json().get("hits", [])
        posts = []
        for h in hits:
            title = h.get("title") or h.get("story_title") or ""
            text = f"{title} {h.get('story_text') or h.get('comment_text') or ''}"
            posts.append({
                "subreddit": "hackernews",
                "username": h.get("author", ""),
                "title": title,
                "text": text.strip(),
                "url": f"https://news.ycombinator.com/item?id={h.get('objectID', '')}",
                "created_utc": h.get("created_at_i", 0),
                "score": h.get("points", 0),
                "num_comments": h.get("num_comments", 0),
            })
        return posts
    except Exception as e:
        print(f"[Scanner] HN error: {e}")
        return []


def _fetch_onshape_forum(category_slug: str = "", limit: int = 30, days_back: int = 30) -> list[dict]:
    """Fetch recent discussions from forum.onshape.com (Vanilla Forums public API)."""
    cutoff_ts = time.time() - (days_back * 86400)
    try:
        params = {"limit": limit, "sort": "-dateInserted"}
        resp = httpx.get(
            f"{ONSHAPE_FORUM_API}/discussions",
            params=params,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"[Scanner] Onshape Forum returned {resp.status_code}")
            return []
        discussions = resp.json()
        posts = []
        for d in discussions:
            # Parse ISO date
            date_str = d.get("dateInserted", "")
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                created_ts = dt.timestamp()
            except Exception:
                created_ts = 0
            if created_ts < cutoff_ts:
                continue
            name = d.get("name", "")
            body = d.get("excerpt") or d.get("body") or ""
            # Strip HTML tags from body
            body_clean = re.sub(r"<[^>]+>", " ", body)
            body_clean = re.sub(r"\s+", " ", body_clean).strip()
            full_text = f"{name} {body_clean}"
            posts.append({
                "subreddit": "onshape_forum",
                "username": d.get("insertUser", {}).get("name", "anonymous"),
                "title": name,
                "text": full_text.strip(),
                "url": d.get("url", ""),
                "created_utc": created_ts,
                "score": d.get("score") or 0,
                "num_comments": d.get("countComments") or 0,
            })
        return posts
    except Exception as e:
        print(f"[Scanner] Onshape Forum error: {e}")
        return []


def _process_post(post: dict, source: str, db: Session) -> Lead | None:
    """Create a Lead from a post dict if it matches keywords and is new. Returns Lead or None."""
    if not post.get("username") or post["username"] in ("[deleted]", "anonymous"):
        return None
    matches, _score, _signals = _matches_keywords(post["text"])
    if not matches:
        return None
    # Deduplicate by post URL
    existing = db.query(Lead).filter(Lead.post_url == post["url"]).first()
    if existing:
        return None
    tier, tier_reason = _classify_tier(post["text"], source)
    post_dt = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc) if post["created_utc"] else None

    # Platform name for display
    if source == "hackernews":
        platform = "hackernews"
        profile_url = f"https://news.ycombinator.com/user?id={post['username']}"
    elif source == "onshape_forum":
        platform = "onshape_forum"
        profile_url = f"https://forum.onshape.com/profile/{post['username']}"
    else:
        platform = f"reddit_{source}"
        profile_url = f"https://www.reddit.com/user/{post['username']}"

    lead = Lead(
        username=post["username"],
        platform=platform,
        message=post["title"][:200] if post.get("title") else post["text"][:200],
        source_url=post["url"],
        post_url=post["url"],
        post_text=post["text"][:2000],
        post_date=post_dt,
        profile_url=profile_url,
        tier=tier,
        tier_reason=tier_reason,
        category="hot" if tier == 1 else "warm" if tier == 2 else "curious",
        status="new",
    )
    db.add(lead)
    return lead


def scan_reddit(db: Session, subreddits: list[str] = None, limit_per_sub: int = 100, days_back: int = 30) -> list[Lead]:
    """Scan Reddit subreddits for leads matching keywords (requires proxy or OAuth)."""
    subs = subreddits or SUBREDDITS
    new_leads = []
    scanned = 0

    for i, sub in enumerate(subs):
        if i > 0:
            time.sleep(REDDIT_DELAY_SECONDS)
        posts = _fetch_reddit_posts(sub, limit_per_sub, days_back)
        scanned += len(posts)
        for post in posts:
            lead = _process_post(post, sub, db)
            if lead:
                new_leads.append(lead)

    db.commit()
    for lead in new_leads:
        db.refresh(lead)
    print(f"[Scanner] Reddit: scanned {scanned} posts across {len(subs)} subs. Created {len(new_leads)} leads.")
    return new_leads


def scan_hackernews(db: Session, days_back: int = 30) -> list[Lead]:
    """Scan Hacker News for leads matching our keywords."""
    queries = [
        '"mesh to CAD"', '"STL to STEP"', '"scan to CAD"',
        '"reverse engineer" CAD', '"parametric" STL',
        '"convert STL"', "Onshape mesh", "STEP from mesh",
    ]
    new_leads = []
    scanned = 0
    seen_urls = set()

    for q in queries:
        posts = _fetch_hackernews(q, limit=30, days_back=days_back)
        for post in posts:
            if post["url"] in seen_urls:
                continue
            seen_urls.add(post["url"])
            scanned += 1
            lead = _process_post(post, "hackernews", db)
            if lead:
                new_leads.append(lead)

    db.commit()
    for lead in new_leads:
        db.refresh(lead)
    print(f"[Scanner] HN: scanned {scanned} unique posts. Created {len(new_leads)} leads.")
    return new_leads


def scan_onshape_forum(db: Session, days_back: int = 30) -> list[Lead]:
    """Scan the Onshape Forum for leads matching keywords."""
    new_leads = []
    # Fetch a larger batch since we're filtering by keyword
    posts = _fetch_onshape_forum(limit=100, days_back=days_back)
    scanned = len(posts)
    for post in posts:
        lead = _process_post(post, "onshape_forum", db)
        if lead:
            new_leads.append(lead)

    db.commit()
    for lead in new_leads:
        db.refresh(lead)
    print(f"[Scanner] Onshape Forum: scanned {scanned} discussions. Created {len(new_leads)} leads.")
    return new_leads


def scan_all(db: Session, days_back: int = 30) -> list[Lead]:
    """Scan all sources: Reddit (if proxy/OAuth configured), Hacker News, Onshape Forum."""
    all_new = []
    # Reddit (only if we have access)
    if REDDIT_PROXY_URL or (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
        try:
            all_new.extend(scan_reddit(db, days_back=days_back))
        except Exception as e:
            print(f"[Scanner] Reddit scan failed: {e}")
    else:
        print("[Scanner] Skipping Reddit (no proxy or OAuth configured)")

    try:
        all_new.extend(scan_hackernews(db, days_back=days_back))
    except Exception as e:
        print(f"[Scanner] HN scan failed: {e}")

    try:
        all_new.extend(scan_onshape_forum(db, days_back=days_back))
    except Exception as e:
        print(f"[Scanner] Onshape Forum scan failed: {e}")

    print(f"[Scanner] Total new leads: {len(all_new)}")
    return all_new
