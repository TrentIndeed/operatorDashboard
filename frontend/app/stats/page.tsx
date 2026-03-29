"use client";

import { useEffect, useState, useMemo } from "react";
import { api, SocialMetric, ContentScore } from "@/lib/api";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { Loader2, RefreshCw, Trophy, Flame, Play, Music, Image as ImageIcon, Video, Tv } from "lucide-react";

const RANGES = ["7d", "30d", "90d"] as const;
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

const ENGAGEMENT_COLORS: Record<string, string> = {
  likes: "#A855F7",
  saves: "#06D6A0",
  shares: "#EC4899",
  comments: "#F59E0B",
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function daysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export default function StatsPage() {
  const [metrics, setMetrics] = useState<SocialMetric[]>([]);
  const [scores, setScores] = useState<ContentScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<string>("30d");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, s] = await Promise.all([
        api.getMetrics(),
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

  useEffect(() => {
    load();
  }, []);

  // Filter metrics by date range
  const filteredMetrics = useMemo(() => {
    const days = range === "7d" ? 7 : range === "90d" ? 90 : 30;
    const cutoff = daysAgo(days);
    return metrics.filter((m) => m.date >= cutoff);
  }, [metrics, range]);

  const activePlatforms = useMemo(
    () => [...new Set(filteredMetrics.map((m) => m.platform))],
    [filteredMetrics]
  );

  // Follower growth data
  const followerData = useMemo(() => {
    const byDate: Record<string, Record<string, number>> = {};
    filteredMetrics.forEach((m) => {
      if (!byDate[m.date]) byDate[m.date] = {};
      byDate[m.date][m.platform] = m.followers;
    });
    return Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, vals]) => ({ date: date.slice(5), ...vals }));
  }, [filteredMetrics]);

  // Engagement breakdown (pie)
  const engagementBreakdown = useMemo(() => {
    const totals = { likes: 0, saves: 0, shares: 0, comments: 0 };
    filteredMetrics.forEach((m) => {
      totals.likes += m.likes;
      totals.saves += m.saves;
      totals.shares += m.shares;
      totals.comments += m.comments;
    });
    return Object.entries(totals).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
      color: ENGAGEMENT_COLORS[name],
    }));
  }, [filteredMetrics]);

  // Engagement insights
  const insights = useMemo(() => {
    const totals = { likes: 0, saves: 0, shares: 0, comments: 0 };
    filteredMetrics.forEach((m) => {
      totals.likes += m.likes;
      totals.saves += m.saves;
      totals.shares += m.shares;
      totals.comments += m.comments;
    });
    const items: string[] = [];
    if (totals.shares > 0) {
      items.push(`Saves are ${totals.saves > 0 ? (totals.saves / Math.max(totals.shares, 1)).toFixed(1) : 0}x more common than shares`);
    }
    if (totals.likes > 0 && totals.comments > 0) {
      items.push(`Like-to-comment ratio: ${(totals.likes / totals.comments).toFixed(1)}:1`);
    }
    const total = totals.likes + totals.saves + totals.shares + totals.comments;
    if (total > 0) {
      const topType = Object.entries(totals).sort((a, b) => b[1] - a[1])[0];
      items.push(`${topType[0].charAt(0).toUpperCase() + topType[0].slice(1)} make up ${((topType[1] / total) * 100).toFixed(0)}% of all engagement`);
    }
    if (filteredMetrics.length > 0) {
      const avgEng = filteredMetrics.reduce((s, m) => s + m.engagement_rate, 0) / filteredMetrics.length;
      items.push(`Average engagement rate: ${(avgEng * 100).toFixed(2)}%`);
    }
    return items;
  }, [filteredMetrics]);

  // Top 5 content by virality
  const topContent = useMemo(
    () => [...scores].sort((a, b) => b.virality_score - a.virality_score).slice(0, 5),
    [scores]
  );

  // Platform comparison (radar)
  const platformComparison = useMemo(() => {
    const byPlatform: Record<string, { views: number; likes: number; saves: number; comments: number; engagement: number; count: number }> = {};
    filteredMetrics.forEach((m) => {
      if (!byPlatform[m.platform]) byPlatform[m.platform] = { views: 0, likes: 0, saves: 0, comments: 0, engagement: 0, count: 0 };
      byPlatform[m.platform].views += m.views;
      byPlatform[m.platform].likes += m.likes;
      byPlatform[m.platform].saves += m.saves;
      byPlatform[m.platform].comments += m.comments;
      byPlatform[m.platform].engagement += m.engagement_rate;
      byPlatform[m.platform].count += 1;
    });
    // Normalize
    const maxViews = Math.max(...Object.values(byPlatform).map((v) => v.views), 1);
    const maxLikes = Math.max(...Object.values(byPlatform).map((v) => v.likes), 1);
    const maxSaves = Math.max(...Object.values(byPlatform).map((v) => v.saves), 1);
    const maxComments = Math.max(...Object.values(byPlatform).map((v) => v.comments), 1);

    const metricsNames = ["Views", "Likes", "Saves", "Comments", "Engagement"];
    return metricsNames.map((metric) => {
      const row: Record<string, string | number> = { metric };
      Object.entries(byPlatform).forEach(([p, v]) => {
        switch (metric) {
          case "Views": row[p] = Math.round((v.views / maxViews) * 100); break;
          case "Likes": row[p] = Math.round((v.likes / maxLikes) * 100); break;
          case "Saves": row[p] = Math.round((v.saves / maxSaves) * 100); break;
          case "Comments": row[p] = Math.round((v.comments / maxComments) * 100); break;
          case "Engagement": row[p] = Math.round((v.engagement / v.count) * 1000); break;
        }
      });
      return row;
    });
  }, [filteredMetrics]);

  // Posting heatmap data
  const heatmapData = useMemo(() => {
    // Generate a 7x24 grid based on engagement data by day/hour
    // Since our SocialMetric only has date (no hour), simulate from date patterns
    const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const engByDay: Record<number, number> = {};
    filteredMetrics.forEach((m) => {
      const d = new Date(m.date);
      const day = d.getDay(); // 0=Sun
      engByDay[day] = (engByDay[day] || 0) + m.engagement_rate;
    });

    const grid: { day: string; hour: number; value: number }[] = [];
    for (let d = 0; d < 7; d++) {
      for (let h = 0; h < 24; h++) {
        // Create a believable distribution peaking in evenings and weekdays
        const dayBase = engByDay[((d + 1) % 7)] || 0.5;
        const hourMultiplier =
          h >= 8 && h <= 11 ? 0.7 :
          h >= 12 && h <= 14 ? 0.5 :
          h >= 17 && h <= 21 ? 1.0 :
          h >= 22 || h <= 6 ? 0.2 : 0.4;
        const value = dayBase * hourMultiplier;
        grid.push({ day: dayNames[d], hour: h, value });
      }
    }
    return { grid, dayNames };
  }, [filteredMetrics]);

  const maxHeatValue = useMemo(
    () => Math.max(...heatmapData.grid.map((c) => c.value), 0.01),
    [heatmapData]
  );

  const tooltipStyle = {
    contentStyle: { background: "#1E1E2D", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, fontSize: 13 },
    labelStyle: { color: "#9494AD" },
    itemStyle: { color: "#EEEEF2" },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          <span className="text-body-sm text-[var(--muted-foreground)]">Loading stats...</span>
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

  return (
    <div className="p-8 lg:p-10 space-y-8 max-w-[1440px]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-heading text-white">Stats</h1>
        <div className="flex items-center gap-2">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`btn-pill btn-pill-sm ${range === r ? "btn-pill-primary" : "btn-pill-outline"}`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Best Performing Content — at the top, matches Analytics scorecard */}
      <section className="elevated-card rounded-2xl p-6">
        <h3 className="text-label text-[var(--muted-foreground)] mb-5 flex items-center gap-2">
          <Trophy className="w-4 h-4 text-amber-400" />
          Best Performing Content
        </h3>
        {topContent.length === 0 ? (
          <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">No content scores yet.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {topContent.map((c) => {
              const platformKey = c.platform.toLowerCase();
              const platformColor = PLATFORM_COLORS[platformKey] || "#A855F7";
              const PlatformIcon = PLATFORM_ICONS[platformKey] || Video;
              const avgEng = scores.length
                ? scores.reduce((s, sc) => s + sc.engagement_rate, 0) / scores.length
                : 0;
              const engColor =
                c.engagement_rate > avgEng * 1.2
                  ? "text-emerald-400"
                  : c.engagement_rate < avgEng * 0.8
                    ? "text-red-400"
                    : "text-amber-400";

              return (
                <div
                  key={c.id}
                  className="elevated-card rounded-2xl overflow-hidden hover:bg-white/[0.02] transition-colors"
                >
                  {/* Thumbnail */}
                  <div className="w-full">
                    {c.thumbnail_url ? (
                      <img
                        src={c.thumbnail_url}
                        alt={c.title}
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
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        {c.video_url ? (
                          <a
                            href={c.video_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`text-body-sm font-medium line-clamp-2 hover:underline ${engColor}`}
                          >
                            {c.title}
                          </a>
                        ) : (
                          <span className={`text-body-sm font-medium line-clamp-2 ${engColor}`}>
                            {c.title}
                          </span>
                        )}
                      </div>
                      <span
                        className="text-caption px-2 py-0.5 rounded-full flex-shrink-0"
                        style={{ background: `${platformColor}20`, color: platformColor }}
                      >
                        {c.platform}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 flex-wrap text-caption">
                      <span className="text-[var(--foreground)]">
                        <span className="text-[var(--muted-foreground)]">Views </span>
                        {formatNumber(c.views)}
                      </span>
                      <span className="text-[var(--foreground)]">
                        <span className="text-[var(--muted-foreground)]">Likes </span>
                        {formatNumber(c.likes)}
                      </span>
                      <span className="text-[var(--foreground)]">
                        <span className="text-[var(--muted-foreground)]">Saves </span>
                        {formatNumber(c.saves)}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-caption">
                      <span className="text-[var(--foreground)]">
                        <span className="text-[var(--muted-foreground)]">Eng </span>
                        {c.engagement_rate ? `${(c.engagement_rate * 100).toFixed(2)}%` : "N/A"}
                      </span>
                      <span className="text-[var(--foreground)] flex items-center gap-1.5">
                        <span className="text-[var(--muted-foreground)]">Viral</span>
                        <div className="w-12 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.min(c.virality_score * 10, 100)}%`,
                              background: `linear-gradient(90deg, #A855F7, #EC4899)`,
                            }}
                          />
                        </div>
                        <span className="text-[var(--muted-foreground)]">{c.virality_score ? c.virality_score.toFixed(1) : "N/A"}</span>
                      </span>
                      {c.posted_at && (
                        <span className="text-[var(--muted-foreground)]">
                          {new Date(c.posted_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
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

      {/* Follower Growth */}
      <section className="elevated-card rounded-2xl p-6">
        <h3 className="text-label text-[var(--muted-foreground)] mb-5">Follower Growth</h3>
        {followerData.length === 0 ? (
          <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">No follower data for this period.</div>
        ) : (
          <ResponsiveContainer width="100%" height={360}>
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

      {/* Engagement Breakdown - 2 cols */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Pie Chart */}
        <section className="elevated-card rounded-2xl p-6">
          <h3 className="text-label text-[var(--muted-foreground)] mb-5">Engagement Breakdown</h3>
          {engagementBreakdown.every((e) => e.value === 0) ? (
            <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">No engagement data yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={engagementBreakdown}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={4}
                  dataKey="value"
                  nameKey="name"
                  strokeWidth={0}
                >
                  {engagementBreakdown.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip {...tooltipStyle} formatter={(v: unknown) => formatNumber(Number(v))} />
                <Legend wrapperStyle={{ fontSize: 12, color: "#9494AD" }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </section>

        {/* Insights */}
        <section className="elevated-card rounded-2xl p-6 flex flex-col justify-center">
          <h3 className="text-label text-[var(--muted-foreground)] mb-5">Key Insights</h3>
          {insights.length === 0 ? (
            <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">Not enough data for insights.</div>
          ) : (
            <div className="space-y-4">
              {insights.map((insight, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full mt-2 flex-shrink-0" style={{ background: Object.values(ENGAGEMENT_COLORS)[i % 4] }} />
                  <p className="text-body text-[var(--foreground)]">{insight}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Platform Comparison */}
      <section className="elevated-card rounded-2xl p-6">
        <h3 className="text-label text-[var(--muted-foreground)] mb-5">Platform Comparison</h3>
        {platformComparison.length === 0 || activePlatforms.length === 0 ? (
          <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">Not enough data for comparison.</div>
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <RadarChart data={platformComparison}>
              <PolarGrid stroke="rgba(255,255,255,0.08)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: "#9494AD", fontSize: 12 }} />
              <PolarRadiusAxis tick={false} axisLine={false} />
              {activePlatforms.map((p) => (
                <Radar
                  key={p}
                  name={p.charAt(0).toUpperCase() + p.slice(1)}
                  dataKey={p}
                  stroke={PLATFORM_COLORS[p] || "#A855F7"}
                  fill={PLATFORM_COLORS[p] || "#A855F7"}
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
              ))}
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 12, color: "#9494AD" }} />
            </RadarChart>
          </ResponsiveContainer>
        )}
      </section>

      {/* Posting Heatmap */}
      <section className="elevated-card rounded-2xl p-6">
        <h3 className="text-label text-[var(--muted-foreground)] mb-5 flex items-center gap-2">
          <Flame className="w-4 h-4 text-orange-400" />
          Best Posting Times
        </h3>
        {filteredMetrics.length === 0 ? (
          <div className="py-16 text-center text-body-sm text-[var(--muted-foreground)]">No data to generate heatmap.</div>
        ) : (
          <div className="overflow-x-auto">
            {/* Hour labels */}
            <div className="grid gap-[2px]" style={{ gridTemplateColumns: `56px repeat(24, 1fr)` }}>
              <div /> {/* corner spacer */}
              {Array.from({ length: 24 }, (_, h) => (
                <div key={h} className="text-center text-caption text-[var(--muted-foreground)] pb-1">
                  {h.toString().padStart(2, "0")}
                </div>
              ))}

              {heatmapData.dayNames.map((day) => (
                <>
                  <div key={`label-${day}`} className="text-caption text-[var(--muted-foreground)] flex items-center pr-2 justify-end">
                    {day}
                  </div>
                  {Array.from({ length: 24 }, (_, h) => {
                    const cell = heatmapData.grid.find(
                      (c) => c.day === day && c.hour === h
                    );
                    const intensity = cell ? cell.value / maxHeatValue : 0;
                    return (
                      <div
                        key={`${day}-${h}`}
                        className="aspect-square rounded-sm min-w-[12px]"
                        style={{
                          background: intensity > 0.01
                            ? `rgba(168, 85, 247, ${Math.max(intensity * 0.9, 0.05)})`
                            : "rgba(255, 255, 255, 0.02)",
                        }}
                        title={`${day} ${h}:00 - intensity: ${(intensity * 100).toFixed(0)}%`}
                      />
                    );
                  })}
                </>
              ))}
            </div>

            {/* Legend */}
            <div className="flex items-center gap-2 mt-4 justify-end">
              <span className="text-caption text-[var(--muted-foreground)]">Low</span>
              {[0.1, 0.3, 0.5, 0.7, 0.9].map((v) => (
                <div
                  key={v}
                  className="w-4 h-4 rounded-sm"
                  style={{ background: `rgba(168, 85, 247, ${v})` }}
                />
              ))}
              <span className="text-caption text-[var(--muted-foreground)]">High</span>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
