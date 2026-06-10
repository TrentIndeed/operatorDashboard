/**
 * Cloudflare Worker: Reddit JSON Proxy
 *
 * Deploy this to Cloudflare Workers (free tier) to get a URL that proxies
 * Reddit JSON endpoints from Cloudflare's edge IPs (which Reddit doesn't
 * block like it blocks VPS/data center IPs).
 *
 * Usage after deploy:
 *   https://reddit-proxy.<your-subdomain>.workers.dev/r/onshape/new.json?limit=25
 *
 * Then set REDDIT_PROXY_URL in VPS .env to:
 *   REDDIT_PROXY_URL=https://reddit-proxy.<your-subdomain>.workers.dev
 *
 * Free tier: 100,000 requests/day — more than enough.
 *
 * ---
 * DEPLOY STEPS:
 *
 * 1. Go to https://dash.cloudflare.com/ (sign up if needed, free)
 * 2. Left sidebar: Workers & Pages → Create application → Create Worker
 * 3. Name it "reddit-proxy" → Deploy (it'll deploy a starter template)
 * 4. Click "Edit code" on the deployed worker
 * 5. Delete all the starter code and paste this entire file
 * 6. Click "Deploy" top right
 * 7. Copy the URL shown (like https://reddit-proxy.yourname.workers.dev)
 * 8. On VPS: echo "REDDIT_PROXY_URL=https://reddit-proxy.yourname.workers.dev" >> /opt/operatorDashboard/.env
 * 9. Restart: docker compose restart backend
 * 10. Test: curl -X POST https://api.dragonoperator.com/outreach/scan
 */

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const redditPath = url.pathname + url.search;

    if (request.method !== "GET") {
      return new Response("only GET allowed", { status: 405 });
    }
    if (!redditPath.includes(".json")) {
      return new Response("only .json endpoints allowed", { status: 400 });
    }

    // Try old.reddit.com first (less aggressive bot detection), then www fallback.
    const targets = [
      `https://old.reddit.com${redditPath}`,
      `https://www.reddit.com${redditPath}`,
    ];

    // Pretend to be a typical Reddit API client (they allow named bots)
    const botUA = "web:parameshai-leadscanner:v1.0 (by /u/TrentIndeed)";

    for (const target of targets) {
      try {
        const r = await fetch(target, {
          headers: {
            "User-Agent": botUA,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
          },
          redirect: "follow",
          cf: { cacheTtl: 180, cacheEverything: true },
        });

        const contentType = r.headers.get("content-type") || "";
        // Only accept JSON responses (Reddit sometimes serves HTML SPA instead)
        if (r.status === 200 && contentType.includes("json")) {
          const body = await r.text();
          return new Response(body, {
            status: 200,
            headers: {
              "Content-Type": "application/json",
              "Access-Control-Allow-Origin": "*",
              "X-Proxy-Source": target,
              "Cache-Control": "public, max-age=180",
            },
          });
        }
        // Otherwise fall through to next target
      } catch (err) {
        // try next
      }
    }

    return new Response(
      JSON.stringify({
        error: "Reddit returned non-JSON from all targets (bot detection or blocked)",
      }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  },
};
