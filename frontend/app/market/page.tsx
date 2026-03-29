"use client";

import { useEffect, useState } from "react";
import {
  api,
  MarketGap,
  Competitor,
  CompetitorPost,
  NewsBriefing,
} from "@/lib/api";
import {
  Loader2,
  Radar,
  Eye,
  Users,
  Newspaper,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Sparkles,
  X,
  Rocket,
  TrendingUp,
  ThumbsUp,
  MessageSquare,
  Play,
  Music,
  Video,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function SectionHeader({
  title,
  action,
  glow,
}: {
  title: string;
  action?: React.ReactNode;
  glow?: boolean;
}) {
  return (
    <div className="flex items-center justify-between mb-5">
      <h2 className="text-label text-[var(--muted-foreground)] flex items-center gap-2">
        {glow && (
          <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse shadow-[0_0_8px_rgba(168,85,247,0.5)]" />
        )}
        {title}
      </h2>
      {action}
    </div>
  );
}

function sourceBadgeColor(source: string | null): string {
  switch (source?.toLowerCase()) {
    case "reddit":
      return "bg-orange-500/20 text-orange-400 border-orange-500/30";
    case "hackernews":
      return "bg-amber-500/20 text-amber-400 border-amber-500/30";
    case "twitter":
      return "bg-cyan-500/20 text-cyan-400 border-cyan-500/30";
    case "forum":
      return "bg-gray-500/20 text-gray-400 border-gray-500/30";
    default:
      return "bg-gray-500/20 text-gray-400 border-gray-500/30";
  }
}

function categoryBadgeColor(cat: string | null): string {
  switch (cat?.toLowerCase()) {
    case "product":
      return "bg-purple-500/20 text-purple-400 border-purple-500/30";
    case "content":
      return "bg-cyan-500/20 text-cyan-400 border-cyan-500/30";
    case "market":
      return "bg-pink-500/20 text-pink-400 border-pink-500/30";
    default:
      return "bg-gray-500/20 text-gray-400 border-gray-500/30";
  }
}

function scoreColor(score: number): string {
  if (score >= 0.8) return "from-emerald-500 to-green-600";
  if (score >= 0.6) return "from-amber-500 to-yellow-600";
  return "from-gray-500 to-gray-600";
}

function scoreTextColor(score: number): string {
  if (score >= 0.8) return "text-emerald-400";
  if (score >= 0.6) return "text-amber-400";
  return "text-gray-400";
}

function platformBorderColor(platform: string): string {
  switch (platform?.toLowerCase()) {
    case "youtube":
      return "border-l-red-500";
    case "tiktok":
      return "border-l-pink-500";
    case "twitter":
      return "border-l-cyan-500";
    case "github":
      return "border-l-gray-400";
    case "linkedin":
      return "border-l-blue-500";
    case "reddit":
      return "border-l-orange-500";
    default:
      return "border-l-purple-500";
  }
}

function platformBadge(platform: string): string {
  switch (platform?.toLowerCase()) {
    case "youtube":
      return "bg-red-500/20 text-red-400";
    case "tiktok":
      return "bg-pink-500/20 text-pink-400";
    case "twitter":
      return "bg-cyan-500/20 text-cyan-400";
    case "github":
      return "bg-gray-500/20 text-gray-300";
    case "linkedin":
      return "bg-blue-500/20 text-blue-400";
    case "reddit":
      return "bg-orange-500/20 text-orange-400";
    default:
      return "bg-purple-500/20 text-purple-400";
  }
}

function relevanceDot(score: number): string {
  if (score >= 0.8) return "bg-emerald-400";
  if (score >= 0.5) return "bg-amber-400";
  return "bg-gray-500";
}

/* ------------------------------------------------------------------ */
/*  Gap Card                                                          */
/* ------------------------------------------------------------------ */

function GapCard({
  gap,
  onDismiss,
  onAct,
}: {
  gap: MarketGap;
  onDismiss: (id: number) => void;
  onAct: (id: number) => void;
}) {
  return (
    <div className="elevated-card rounded-2xl p-5 space-y-4">
      {/* Top row: score + badges */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-gradient-to-r ${scoreColor(gap.opportunity_score)} text-white`}
          >
            <TrendingUp className="w-3 h-3" />
            {Math.round(gap.opportunity_score * 100)}%
          </span>
          {gap.source && (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${sourceBadgeColor(gap.source)}`}
            >
              {gap.source}
            </span>
          )}
          {gap.category && (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${categoryBadgeColor(gap.category)}`}
            >
              {gap.category}
            </span>
          )}
        </div>
        {gap.source_url && (
          <a
            href={gap.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--muted-foreground)] hover:text-purple-400 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>

      {/* Description */}
      <p className="text-body text-[var(--foreground)]">{gap.description}</p>

      {/* Suggested action */}
      {gap.suggested_action && (
        <div className="rounded-xl bg-purple-500/10 border border-purple-500/20 px-4 py-3">
          <p className="text-body-sm text-purple-300">
            <Sparkles className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />
            {gap.suggested_action}
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={() => onAct(gap.id)}
          className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold bg-gradient-to-r from-emerald-600 to-green-600 text-white hover:from-emerald-500 hover:to-green-500 transition-all"
        >
          <Rocket className="w-3.5 h-3.5" />
          Act on this
        </button>
        <button
          onClick={() => onDismiss(gap.id)}
          className="btn-pill btn-pill-outline text-xs flex items-center gap-1.5"
        >
          <X className="w-3.5 h-3.5" />
          Dismiss
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Competitor Card                                                   */
/* ------------------------------------------------------------------ */

function CompetitorCard({ competitor }: { competitor: Competitor }) {
  const [expanded, setExpanded] = useState(false);
  const [posts, setPosts] = useState<CompetitorPost[]>([]);
  const [loadingPosts, setLoadingPosts] = useState(false);

  const toggleExpand = async () => {
    if (!expanded && posts.length === 0) {
      setLoadingPosts(true);
      try {
        const data = await api.getCompetitorPosts(competitor.id);
        setPosts(data);
      } catch {
        /* silently fail */
      } finally {
        setLoadingPosts(false);
      }
    }
    setExpanded(!expanded);
  };

  return (
    <div
      className={`elevated-card rounded-2xl overflow-hidden border-l-4 ${platformBorderColor(competitor.platform)}`}
    >
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <h3 className="text-subtitle text-white font-semibold">
                {competitor.name}
              </h3>
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium ${platformBadge(competitor.platform)}`}
              >
                {competitor.platform}
              </span>
            </div>
            {competitor.handle && (
              <p className="text-caption text-[var(--muted-foreground)] font-mono">
                @{competitor.handle}
              </p>
            )}
            {competitor.description && (
              <p className="text-body-sm text-[var(--muted-foreground)] mt-1">
                {competitor.description}
              </p>
            )}
          </div>
          <button
            onClick={toggleExpand}
            className="text-[var(--muted-foreground)] hover:text-purple-400 transition-colors p-1"
          >
            {expanded ? (
              <ChevronUp className="w-5 h-5" />
            ) : (
              <ChevronDown className="w-5 h-5" />
            )}
          </button>
        </div>

        {competitor.last_checked && (
          <p className="text-caption text-[var(--muted-foreground)] mt-3">
            Last checked:{" "}
            {new Date(competitor.last_checked).toLocaleDateString()}
          </p>
        )}
      </div>

      {/* Expanded posts */}
      {expanded && (
        <div className="border-t border-[var(--border)] px-5 py-4 space-y-3">
          {loadingPosts ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
            </div>
          ) : posts.length === 0 ? (
            <p className="text-body-sm text-[var(--muted-foreground)] text-center py-3">
              No recent posts tracked.
            </p>
          ) : (
            posts.map((post) => (
              <div
                key={post.id}
                className="rounded-xl bg-[#111118] overflow-hidden"
              >
                {/* Thumbnail */}
                {post.thumbnail_url && (
                  <a
                    href={post.url || "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block"
                  >
                    <img
                      src={post.thumbnail_url}
                      alt={post.title || ""}
                      className="w-full object-cover"
                      style={{ height: 140 }}
                    />
                  </a>
                )}

                <div className="p-4 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-body-sm text-white font-medium line-clamp-2">
                      {post.title || "Untitled post"}
                    </p>
                    {post.url && (
                      <a
                        href={post.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--muted-foreground)] hover:text-purple-400 transition-colors shrink-0"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-caption text-[var(--muted-foreground)]">
                    <span className="flex items-center gap-1">
                      <Eye className="w-3 h-3" />
                      {post.views.toLocaleString()}
                    </span>
                    <span className="flex items-center gap-1">
                      <ThumbsUp className="w-3 h-3" />
                      {post.likes.toLocaleString()}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="w-3 h-3" />
                      {post.comments_count}
                    </span>
                    <span className={`font-semibold ${scoreTextColor(post.engagement)}`}>
                      {(post.engagement * 100).toFixed(1)}% eng
                    </span>
                  </div>
                  {post.ai_analysis && (
                    <p className="text-caption text-[var(--muted-foreground)] italic mt-1">
                      {post.ai_analysis}
                    </p>
                  )}
                  {post.posted_at && (
                    <p className="text-caption text-[var(--muted-foreground)]">
                      {new Date(post.posted_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  News Item                                                         */
/* ------------------------------------------------------------------ */

function NewsItem({ item }: { item: NewsBriefing }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-[var(--border)] last:border-b-0">
      <div
        className={`w-2 h-2 rounded-full mt-2 shrink-0 ${relevanceDot(item.relevance_score)}`}
      />
      <div className="min-w-0 space-y-1">
        <p className="text-body-sm text-white">{item.headline}</p>
        <div className="flex items-center gap-2">
          {item.category && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-[#1E1E2D] text-[var(--muted-foreground)] border border-[var(--border)]">
              {item.category}
            </span>
          )}
          {item.summary && (
            <span className="text-caption text-[var(--muted-foreground)] truncate">
              {item.summary}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                         */
/* ------------------------------------------------------------------ */

export default function MarketIntelligencePage() {
  const [gaps, setGaps] = useState<MarketGap[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [briefing, setBriefing] = useState<NewsBriefing[]>([]);
  const [similarContent, setSimilarContent] = useState<CompetitorPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [gapsData, competitorsData, ccData] = await Promise.all([
        api.getMarketGaps().catch(() => [] as MarketGap[]),
        api.getCompetitors().catch(() => [] as Competitor[]),
        api.commandCenter().catch(() => null),
      ]);
      setGaps(gapsData);
      setCompetitors(competitorsData);
      setBriefing(ccData?.briefing?.filter((b) => !b.dismissed) ?? []);

      // Fetch posts from all competitors for the "Similar Content" sidebar
      const allPosts: CompetitorPost[] = [];
      for (const comp of competitorsData) {
        try {
          const posts = await api.getCompetitorPosts(comp.id);
          allPosts.push(...posts);
        } catch { /* skip */ }
      }
      setSimilarContent(
        allPosts.sort((a, b) => b.views - a.views).slice(0, 8)
      );
    } catch {
      setError(
        "Cannot reach backend. Make sure FastAPI is running on port 8000."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      await api.scanMarket();
      // Reload after a delay to let the scan populate data
      setTimeout(async () => {
        await load();
        setScanning(false);
      }, 4000);
    } catch {
      setScanning(false);
    }
  };

  const handleDismiss = async (id: number) => {
    try {
      await api.dismissGap(id);
      setGaps((prev) => prev.filter((g) => g.id !== id));
    } catch {
      /* silently fail */
    }
  };

  const handleAct = async (id: number) => {
    try {
      await api.actOnGap(id);
      setGaps((prev) =>
        prev.map((g) => (g.id === id ? { ...g, status: "acted" } : g))
      );
    } catch {
      /* silently fail */
    }
  };

  /* Loading state */
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          <span className="text-body-sm text-[var(--muted-foreground)]">
            Loading market intelligence...
          </span>
        </div>
      </div>
    );
  }

  /* Error state */
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-5">
        <div className="text-subtitle text-pink-400">{error}</div>
        <button
          onClick={load}
          className="btn-pill btn-pill-primary flex items-center gap-2"
        >
          <Radar className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  const activeGaps = gaps.filter((g) => g.status === "active" || g.status === "new");

  return (
    <div className="p-8 lg:p-10 space-y-8 max-w-[1440px]">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-heading text-white">Market Intelligence</h1>
          <p className="text-body text-[var(--muted-foreground)] mt-1">
            Gaps, competitors, and industry signals
          </p>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="btn-pill btn-pill-primary flex items-center gap-2 disabled:opacity-50"
        >
          {scanning ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Radar className="w-4 h-4" />
          )}
          {scanning ? "Scanning..." : "Scan Market"}
        </button>
      </div>

      {/* Main layout */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-8">
        {/* LEFT — Market Gaps */}
        <div className="space-y-8">
          <section>
            <SectionHeader
              title={`Market Gaps (${activeGaps.length})`}
              glow
              action={
                <Eye className="w-4 h-4 text-purple-400 animate-pulse" />
              }
            />
            <div className="space-y-4">
              {activeGaps.length === 0 ? (
                <div className="py-12 text-center elevated-card rounded-2xl">
                  <Radar className="w-12 h-12 text-purple-400/30 mx-auto mb-4" />
                  <p className="text-body text-[var(--muted-foreground)]">
                    No market gaps detected. Click{" "}
                    <span className="text-purple-400 font-semibold">
                      Scan Market
                    </span>{" "}
                    to run analysis.
                  </p>
                </div>
              ) : (
                activeGaps.map((gap) => (
                  <GapCard
                    key={gap.id}
                    gap={gap}
                    onDismiss={handleDismiss}
                    onAct={handleAct}
                  />
                ))
              )}
            </div>
          </section>

          {/* Competitor Watch */}
          <section>
            <SectionHeader
              title="Competitor Watch"
              action={
                <Users className="w-4 h-4 text-[var(--muted-foreground)]" />
              }
            />
            <div className="space-y-4">
              {competitors.length === 0 ? (
                <div className="py-8 text-center elevated-card rounded-2xl">
                  <Users className="w-10 h-10 text-purple-400/30 mx-auto mb-3" />
                  <p className="text-body-sm text-[var(--muted-foreground)]">
                    No competitors tracked yet.
                  </p>
                </div>
              ) : (
                competitors.map((c) => (
                  <CompetitorCard key={c.id} competitor={c} />
                ))
              )}
            </div>
          </section>
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="space-y-8">
          {/* Similar / Competitor Content — with thumbnails */}
          <section>
            <SectionHeader
              title="Similar Content"
              action={
                <Video className="w-4 h-4 text-[var(--muted-foreground)]" />
              }
            />
            {similarContent.length === 0 ? (
              <div className="elevated-card rounded-2xl p-5">
                <p className="text-body-sm text-[var(--muted-foreground)] text-center py-4">
                  No competitor content tracked yet. Add competitors to see their content here.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {similarContent.map((c) => {
                  const pColor =
                    c.platform.toLowerCase() === "youtube"
                      ? "#EC4899"
                      : c.platform.toLowerCase() === "tiktok"
                        ? "#A855F7"
                        : c.platform.toLowerCase() === "twitter"
                          ? "#06B6D4"
                          : "#A855F7";
                  const PIcon =
                    c.platform.toLowerCase() === "youtube"
                      ? Play
                      : c.platform.toLowerCase() === "tiktok"
                        ? Music
                        : Video;
                  return (
                    <div
                      key={c.id}
                      className="elevated-card rounded-xl overflow-hidden hover:bg-white/[0.02] transition-colors"
                    >
                      {/* Thumbnail */}
                      {c.thumbnail_url ? (
                        <a
                          href={c.url || "#"}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block"
                        >
                          <img
                            src={c.thumbnail_url}
                            alt={c.title || ""}
                            className="w-full object-cover"
                            style={{ height: 120 }}
                          />
                        </a>
                      ) : c.url ? (
                        <a
                          href={c.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="w-full flex items-center justify-center"
                          style={{ height: 60, background: "#111118" }}
                        >
                          <PIcon className="w-6 h-6" style={{ color: pColor }} />
                        </a>
                      ) : null}
                      <div className="p-3 space-y-1.5">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-caption text-white font-medium line-clamp-2">
                            {c.title || "Untitled"}
                          </p>
                          <span
                            className="text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0"
                            style={{ background: `${pColor}20`, color: pColor }}
                          >
                            {c.platform}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-[var(--muted-foreground)]">
                          <span>
                            <Eye className="w-3 h-3 inline mr-0.5" />
                            {c.views >= 1000 ? `${(c.views / 1000).toFixed(1)}K` : c.views}
                          </span>
                          <span>
                            <ThumbsUp className="w-3 h-3 inline mr-0.5" />
                            {c.likes}
                          </span>
                          <span className={scoreTextColor(c.engagement)}>
                            {(c.engagement * 100).toFixed(1)}% eng
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Industry News */}
          <section>
            <SectionHeader
              title="Industry News"
              action={
                <Newspaper className="w-4 h-4 text-[var(--muted-foreground)]" />
              }
            />
            <div className="elevated-card rounded-2xl p-5">
              {briefing.length === 0 ? (
                <p className="text-body-sm text-[var(--muted-foreground)] text-center py-4">
                  No industry news available.
                </p>
              ) : (
                <div className="divide-y-0">
                  {briefing.map((item) => (
                    <NewsItem key={item.id} item={item} />
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
