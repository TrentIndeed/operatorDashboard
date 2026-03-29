"use client";

import { useEffect, useState, useMemo } from "react";
import { api, SocialMetric, ContentScore } from "@/lib/api";
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import {
  Loader2, RefreshCw, Users, Eye, TrendingUp, Award,
  Play, Image as ImageIcon, Music, Video, Tv,
} from "lucide-react";

const PLATFORMS = ["All", "TikTok", "YouTube", "Instagram", "Twitter"] as const;
const PLATFORM_COLORS: Record<string, string> = {
  tiktok: "#A855F7",
  youtube: "#EC4899",
  instagram: "#F59E0B",
  twitter: "#06B6D4",
};

const PLATFORM_ICONS: Record<string, typeof Play> = {
  tiktok: Music,
  youtube: Play,
  instagram: ImageIcon,
  twitter: Tv,
};

function formatNumber(n: number | null | undefined): string {
  if (n == null) return "N/A";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function displayValue(val: number | null | undefined, suffix?: string): string {
  if (val == null || val === 0) return "N/A";
  if (suffix) return `${val}${suffix}`;
  return formatNumber(val);
}

function displayPercent(val: number | null | undefined): string {
  if (val == null || val === 0) return "N/A";
  return `${(val * 100).toFixed(1)}%`;
}

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<SocialMetric[]>([]);
  const [scores, setScores] = useState<ContentScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [platform, setPlatform] = useState<string>("All");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const pFilter = platform === "All" ? undefined : platform.toLowerCase();
      const [m, s] = await Promise.all([
        api.getMetrics(pFilter),
        api.getContentScores(),
      ]);
      setMetrics(m);
      setScores(s);
    } catch {
      setError("Cannot reach backend. Make sure FastAPI is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.syncSocial();
      await load();
    } catch {
      setError("Sync failed. Check your social media connections.");
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    load();
  }, [platform]);

  // Stat card calculations
  const totalFollowers = useMemo(() => {
    if (!metrics.length) return null;
    const latest: Record<string, number> = {};
    metrics.forEach((m) => {
      if (!latest[m.platform] || m.date > (latest[m.platform] as unknown as string)) {
        latest[m.platform] = m.followers;
      }
    });
    const sum = Object.values(latest).reduce((a, b) => a + b, 0);
    return sum || null;
  }, [metrics]);

  const totalViews = useMemo(() => {
    if (!metrics.length) return null;
    const sum = metrics.reduce((s, m) => s + m.views, 0);
    return sum || null;
  }, [metrics]);

  const avgEngagement = useMemo(() => {
    if (!metrics.length) return null;
    const avg = metrics.reduce((sum, m) => sum + m.engagement_rate, 0) / metrics.length;
    return avg || null;
  }, [metrics]);

  const bestPlatform = useMemo(() => {
    if (!metrics.length) return "N/A";
    const platformEng: Record<string, { sum: number; count: number }> = {};
    metrics.forEach((m) => {
      if (!platformEng[m.platform]) platformEng[m.platform] = { sum: 0, count: 0 };
      platformEng[m.platform].sum += m.engagement_rate;
      platformEng[m.platform].count += 1;
    });
    let best = "";
    let bestAvg = 0;
    Object.entries(platformEng).forEach(([p, v]) => {
      const avg = v.sum / v.count;
      if (avg > bestAvg) { bestAvg = avg; best = p; }
    });
    return best ? best.charAt(0).toUpperCase() + best.slice(1) : "N/A";
  }, [metrics]);

  // Engagement trend data (grouped by date, one series per platform)
  const trendData = useMemo(() => {
    const byDate: Record<string, Record<string, number>> = {};
    metrics.forEach((m) => {
      if (!byDate[m.date]) byDate[m.date] = {};
      byDate[m.date][m.platform] = m.engagement_rate;
    });
    return Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, vals]) => ({ date: date.slice(5), ...vals }));
  }, [metrics]);

  // Follower growth data
  const followerData = useMemo(() => {
    const byDate: Record<string, Record<string, number>> = {};
    metrics.forEach((m) => {
      if (!byDate[m.date]) byDate[m.date] = {};
      byDate[m.date][m.platform] = m.followers;
    });
    return Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, vals]) => ({ date: date.slice(5), ...vals }));
  }, [metrics]);

  // Views by platform
  const viewsByPlatform = useMemo(() => {
    const totals: Record<string, number> = {};
    metrics.forEach((m) => {
      totals[m.platform] = (totals[m.platform] || 0) + m.views;
    });
    return Object.entries(totals).map(([p, v]) => ({
      platform: p.charAt(0).toUpperCase() + p.slice(1),
      views: v,
      fill: PLATFORM_COLORS[p] || "#A855F7",
    }));
  }, [metrics]);

  // Unique platforms in data
  const activePlatforms = useMemo(() => {
    return [...new Set(metrics.map((m) => m.platform))];
  }, [metrics]);

  // Sorted content scores — filter out private/unlisted videos (title contains "Private" or 0 views with no engagement)
  const sortedScores = useMemo(() => {
    return [...scores]
      .filter((s) => {
        // Filter out private YouTube videos: title starts with "Private video" or has no views/engagement
        if (s.platform.toLowerCase() === "youtube") {
          if (s.title?.toLowerCase().startsWith("private video")) return false;
        }
        return true;
      })
      .sort((a, b) => b.virality_score - a.virality_score);
  }, [scores]);

  const filteredScores = useMemo(() => {
    if (platform === "All") return sortedScores;
    return sortedScores.filter((s) => s.platform.toLowerCase() === platform.toLowerCase());
  }, [sortedScores, platform]);

  const avgContentEng = scores.length
    ? scores.reduce((s, c) => s + c.engagement_rate, 0) / scores.length
    : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          <span className="text-body-sm text-[var(--muted-foreground)]">Loading analytics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-5">
        <div className="text-subtitle text-pink-400">{error}</div>
        <button onClick={load} className="btn-pill btn-pill-primary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  const tooltipStyle = {
    contentStyle: { background: "#1E1E2D", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, fontSize: 13 },
    labelStyle: { color: "#9494AD" },
    itemStyle: { color: "#EEEEF2" },
  };

  return (
    <div className="p-8 lg:p-10 space-y-8 max-w-[1440px]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-heading text-white">Analytics</h1>
        <div className="flex items-center gap-2 flex-wrap">
          {PLATFORMS.map((p) => (
            <button
              key={p}
              onClick={() => setPlatform(p)}
              className={`btn-pill btn-pill-sm ${
                platform === p ? "btn-pill-primary" : "btn-pill-outline"
              }`}
            >
              {p}
            </button>
          ))}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-pill btn-pill-outline flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Syncing..." : "Sync Social"}
          </button>
        </div>
      </div>

      {/* Content Scorecard — always visible, above charts */}
      <section className="elevated-card rounded-2xl p-6">
        <h3 className="text-label text-[var(--muted-foreground)] mb-5">Content Scorecard</h3>
        {filteredScores.length === 0 ? (
          <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">
            No content scores yet. Sync your social media accounts to see performance data.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {filteredScores.map((s) => {
              const engColor =
                s.engagement_rate > avgContentEng * 1.2
                  ? "text-emerald-400"
                  : s.engagement_rate < avgContentEng * 0.8
                    ? "text-red-400"
                    : "text-amber-400";
              const platformKey = s.platform.toLowerCase();
              const platformColor = PLATFORM_COLORS[platformKey] || "#A855F7";
              const PlatformIcon = PLATFORM_ICONS[platformKey] || Video;

              return (
                <div
                  key={s.id}
                  className="elevated-card rounded-2xl overflow-hidden hover:bg-white/[0.02] transition-colors"
                >
                  {/* Thumbnail — large, full width */}
                  <div className="w-full">
                    {s.thumbnail_url ? (
                      <img
                        src={s.thumbnail_url}
                        alt={s.title}
                        className="w-full object-cover"
                        style={{ height: 200 }}
                      />
                    ) : (
                      <div
                        className="w-full flex items-center justify-center"
                        style={{ height: 200, background: "#1E1E2D" }}
                      >
                        <PlatformIcon className="w-14 h-14" style={{ color: platformColor }} />
                      </div>
                    )}
                  </div>

                  {/* Stats below thumbnail */}
                  <div className="p-4 space-y-2">
                    {/* Title + Platform */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        {s.video_url ? (
                          <a
                            href={s.video_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`text-body-sm font-medium line-clamp-2 hover:underline ${engColor}`}
                          >
                            {s.title}
                          </a>
                        ) : (
                          <span className={`text-body-sm font-medium line-clamp-2 ${engColor}`}>
                            {s.title}
                          </span>
                        )}
                      </div>
                      <span
                        className="text-caption px-2 py-0.5 rounded-full flex-shrink-0"
                        style={{ background: `${platformColor}20`, color: platformColor }}
                      >
                        {s.platform}
                      </span>
                    </div>

                    {/* Stats row */}
                    <div className="flex items-center gap-3 flex-wrap text-caption">
                      <span className="text-[var(--foreground)]">
                        <span className="text-[var(--muted-foreground)]">Views </span>
                        {displayValue(s.views)}
                      </span>
                      <span className="text-[var(--foreground)]">
                        <span className="text-[var(--muted-foreground)]">Likes </span>
                        {displayValue(s.likes)}
                      </span>
                      <span className="text-[var(--foreground)]">
                        <span className="text-[var(--muted-foreground)]">Saves </span>
                        {displayValue(s.saves)}
                      </span>
                    </div>

                    {/* Engagement + Virality + Date */}
                    <div className="flex items-center gap-3 text-caption">
                      <span className="text-[var(--foreground)]">
                        <span className="text-[var(--muted-foreground)]">Eng </span>
                        {s.engagement_rate ? `${(s.engagement_rate * 100).toFixed(2)}%` : <span className="text-[var(--muted-foreground)]">N/A</span>}
                      </span>
                      <span className="text-[var(--foreground)] flex items-center gap-1.5">
                        <span className="text-[var(--muted-foreground)]">Viral</span>
                        <div className="w-12 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.min(s.virality_score * 10, 100)}%`,
                              background: `linear-gradient(90deg, #A855F7, #EC4899)`,
                            }}
                          />
                        </div>
                        <span className="text-[var(--muted-foreground)]">{s.virality_score ? s.virality_score.toFixed(1) : "N/A"}</span>
                      </span>
                      {s.posted_at && (
                        <span className="text-[var(--muted-foreground)]">
                          {new Date(s.posted_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Empty metrics state */}
      {metrics.length === 0 ? (
        <div className="elevated-card rounded-2xl p-12 text-center">
          <p className="text-body-sm text-[var(--muted-foreground)] mb-4">
            No analytics data yet. Click Sync Social to pull data from your connected platforms.
          </p>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-pill btn-pill-primary flex items-center gap-2 mx-auto"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Syncing..." : "Sync Now"}
          </button>
        </div>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              {
                label: "Total Followers",
                value: totalFollowers != null ? formatNumber(totalFollowers) : "N/A",
                gradient: "bg-gradient-to-br from-purple-600 via-purple-700 to-violet-800",
                icon: Users,
                subtitle: "across platforms",
              },
              {
                label: "Total Views (30d)",
                value: totalViews != null ? formatNumber(totalViews) : "N/A",
                gradient: "bg-gradient-to-br from-cyan-600 via-cyan-700 to-blue-800",
                icon: Eye,
                subtitle: "combined views",
              },
              {
                label: "Avg Engagement",
                value: avgEngagement != null ? displayPercent(avgEngagement) : "N/A",
                gradient: "bg-gradient-to-br from-pink-600 via-pink-700 to-rose-800",
                icon: TrendingUp,
                subtitle: "engagement rate",
              },
              {
                label: "Best Platform",
                value: bestPlatform,
                gradient: "bg-gradient-to-br from-amber-600 via-amber-700 to-orange-800",
                icon: Award,
                subtitle: "highest engagement",
              },
            ].map((card) => (
              <div key={card.label} className={`relative overflow-hidden rounded-2xl p-6 ${card.gradient}`}>
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-2">
                    <card.icon className="w-4 h-4 text-white/80" />
                    <span className="text-label text-white/80">{card.label}</span>
                  </div>
                  <div
                    className={`font-extrabold ${card.value === "N/A" ? "text-white/50" : "text-white"}`}
                    style={{ fontSize: 36, lineHeight: 1.1, letterSpacing: "-0.02em" }}
                  >
                    {card.value}
                  </div>
                  <div className="text-body-sm text-white/70 mt-1">{card.subtitle}</div>
                </div>
                <div className="absolute top-0 right-0 w-40 h-40 rounded-full bg-white/10 blur-3xl -translate-y-10 translate-x-10" />
              </div>
            ))}
          </div>

          {/* Engagement Trend Chart */}
          <section className="elevated-card rounded-2xl p-6">
            <h3 className="text-label text-[var(--muted-foreground)] mb-5">Engagement Trend</h3>
            {trendData.length === 0 ? (
              <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">
                No engagement data available for this time period.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={trendData}>
                  <defs>
                    {activePlatforms.map((p) => (
                      <linearGradient key={p} id={`grad-${p}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={PLATFORM_COLORS[p] || "#A855F7"} stopOpacity={0.4} />
                        <stop offset="100%" stopColor={PLATFORM_COLORS[p] || "#A855F7"} stopOpacity={0} />
                      </linearGradient>
                    ))}
                  </defs>
                  <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fill: "#6A6A80", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#6A6A80", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
                  <Tooltip {...tooltipStyle} formatter={(v: unknown) => `${(Number(v) * 100).toFixed(2)}%`} />
                  <Legend wrapperStyle={{ fontSize: 12, color: "#9494AD" }} />
                  {activePlatforms.map((p) => (
                    <Area
                      key={p}
                      type="monotone"
                      dataKey={p}
                      stroke={PLATFORM_COLORS[p] || "#A855F7"}
                      fill={`url(#grad-${p})`}
                      strokeWidth={2}
                      dot={false}
                      name={p.charAt(0).toUpperCase() + p.slice(1)}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            )}
          </section>

          {/* Two-col: Followers Growth + Views by Platform */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Followers Growth */}
            <section className="elevated-card rounded-2xl p-6">
              <h3 className="text-label text-[var(--muted-foreground)] mb-5">Followers Growth</h3>
              {followerData.length === 0 ? (
                <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">
                  No follower data available. Sync your social accounts to track growth.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={followerData}>
                    <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fill: "#6A6A80", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#6A6A80", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => formatNumber(v)} />
                    <Tooltip {...tooltipStyle} formatter={(v: unknown) => formatNumber(Number(v))} />
                    <Legend wrapperStyle={{ fontSize: 12, color: "#9494AD" }} />
                    {activePlatforms.map((p) => (
                      <Line
                        key={p}
                        type="monotone"
                        dataKey={p}
                        stroke={PLATFORM_COLORS[p] || "#A855F7"}
                        strokeWidth={2}
                        dot={false}
                        name={p.charAt(0).toUpperCase() + p.slice(1)}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </section>

            {/* Views by Platform */}
            <section className="elevated-card rounded-2xl p-6">
              <h3 className="text-label text-[var(--muted-foreground)] mb-5">Views by Platform</h3>
              {viewsByPlatform.length === 0 ? (
                <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">
                  No views data available. Sync your social accounts to see platform breakdown.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={viewsByPlatform}>
                    <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
                    <XAxis dataKey="platform" tick={{ fill: "#6A6A80", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#6A6A80", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => formatNumber(v)} />
                    <Tooltip {...tooltipStyle} formatter={(v: unknown) => formatNumber(Number(v))} />
                    <Bar dataKey="views" radius={[8, 8, 0, 0]}>
                      {viewsByPlatform.map((entry, i) => (
                        <rect key={i} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
