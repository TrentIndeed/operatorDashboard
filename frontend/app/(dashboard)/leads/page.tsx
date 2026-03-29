"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  api,
  Lead,
  CommentReply,
  WaitlistSignup,
  WaitlistStats,
} from "@/lib/api";
import {
  Users,
  MessageCircle,
  Mail,
  RefreshCw,
  Loader2,
  Send,
  CheckCircle,
  XCircle,
  Plus,
  TrendingUp,
  BarChart3,
  UserPlus,
  ArrowRight,
} from "lucide-react";

const CATEGORIES = ["all", "hot", "warm", "curious"] as const;

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

function CategoryBadge({ category }: { category: string }) {
  const styles: Record<string, string> = {
    hot: "bg-gradient-to-r from-red-600 to-red-500 text-white",
    warm: "bg-gradient-to-r from-amber-600 to-amber-500 text-white",
    curious: "bg-[var(--muted)] text-[var(--muted-foreground)]",
  };
  return (
    <span
      className={`text-caption px-2.5 py-0.5 rounded-full ${styles[category] || styles.curious}`}
    >
      {category}
    </span>
  );
}

function PlatformBadge({ platform }: { platform: string }) {
  const colors: Record<string, string> = {
    tiktok: "border-pink-500/40 text-pink-400",
    youtube: "border-red-500/40 text-red-400",
    twitter: "border-cyan-500/40 text-cyan-400",
    reddit: "border-orange-500/40 text-orange-400",
    linkedin: "border-blue-500/40 text-blue-400",
  };
  return (
    <span
      className={`text-caption px-2 py-0.5 rounded-full border ${colors[platform.toLowerCase()] || "border-[var(--border)] text-[var(--muted-foreground)]"}`}
    >
      {platform}
    </span>
  );
}

function SentimentDot({ sentiment }: { sentiment: string | null }) {
  const color =
    sentiment === "positive"
      ? "bg-emerald-400"
      : sentiment === "negative"
        ? "bg-red-400"
        : "bg-gray-400";
  return <div className={`w-2 h-2 rounded-full ${color}`} title={sentiment || "neutral"} />;
}

function SourceBadge({ source }: { source: string | null }) {
  const colors: Record<string, string> = {
    tiktok: "bg-pink-500/20 text-pink-400",
    youtube: "bg-red-500/20 text-red-400",
    twitter: "bg-cyan-500/20 text-cyan-400",
    direct: "bg-purple-500/20 text-purple-400",
    referral: "bg-emerald-500/20 text-emerald-400",
  };
  const s = (source || "direct").toLowerCase();
  return (
    <span className={`text-caption px-2 py-0.5 rounded-full ${colors[s] || "bg-[var(--muted)] text-[var(--muted-foreground)]"}`}>
      {source || "direct"}
    </span>
  );
}

export default function Page() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [replies, setReplies] = useState<CommentReply[]>([]);
  const [waitlist, setWaitlist] = useState<WaitlistSignup[]>([]);
  const [waitlistStats, setWaitlistStats] = useState<WaitlistStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<string>("all");
  const [generatingDM, setGeneratingDM] = useState<number | null>(null);
  const [generatingReply, setGeneratingReply] = useState<number | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newSignup, setNewSignup] = useState({ email: "", name: "", source: "" });

  const load = async () => {
    try {
      const cat = category === "all" ? undefined : category;
      const [leadsData, repliesData, waitlistData, statsData] = await Promise.all([
        api.getLeads(cat),
        api.getCommentReplies(),
        api.getWaitlist(),
        api.getWaitlistStats(),
      ]);
      setLeads(leadsData);
      setReplies(repliesData);
      setWaitlist(waitlistData);
      setWaitlistStats(statsData);
    } catch {
      setError("Cannot reach backend. Make sure FastAPI is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [category]);

  const handleGenerateDM = async (id: number) => {
    setGeneratingDM(id);
    try {
      const updated = await api.generateDM(id);
      setLeads((prev) => prev.map((l) => (l.id === id ? updated : l)));
    } catch {
      /* ignore */
    } finally {
      setGeneratingDM(null);
    }
  };

  const handleUpdateLead = async (id: number, data: Partial<Lead>) => {
    try {
      const updated = await api.updateLead(id, data);
      if (data.status === "dismissed") {
        setLeads((prev) => prev.filter((l) => l.id !== id));
      } else {
        setLeads((prev) => prev.map((l) => (l.id === id ? updated : l)));
      }
    } catch {
      /* ignore */
    }
  };

  const handleGenerateReply = async (id: number) => {
    setGeneratingReply(id);
    try {
      const updated = await api.generateReply(id);
      setReplies((prev) => prev.map((r) => (r.id === id ? updated : r)));
    } catch {
      /* ignore */
    } finally {
      setGeneratingReply(null);
    }
  };

  const handleUpdateReply = async (id: number, data: Partial<CommentReply>) => {
    try {
      const updated = await api.updateCommentReply(id, data);
      if (data.status === "skipped" || data.status === "approved") {
        setReplies((prev) => prev.filter((r) => r.id !== id));
      } else {
        setReplies((prev) => prev.map((r) => (r.id === id ? updated : r)));
      }
    } catch {
      /* ignore */
    }
  };

  const handleAddSignup = async () => {
    if (!newSignup.email) return;
    try {
      const signup = await api.addWaitlistSignup({
        email: newSignup.email,
        name: newSignup.name || undefined,
        source: newSignup.source || undefined,
      });
      setWaitlist((prev) => [signup, ...prev]);
      setWaitlistStats((prev) =>
        prev ? { ...prev, total: prev.total + 1, active: prev.active + 1 } : prev
      );
      setNewSignup({ email: "", name: "", source: "" });
      setShowAddForm(false);
    } catch {
      /* ignore */
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          <span className="text-body-sm text-[var(--muted-foreground)]">
            Loading leads...
          </span>
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

  const conversionRate =
    waitlistStats && waitlistStats.total > 0
      ? ((waitlistStats.converted / waitlistStats.total) * 100).toFixed(1)
      : "0";

  return (
    <div className="p-4 sm:p-6 lg:p-10 space-y-6 sm:space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-heading text-white">Leads & Outreach</h1>
          <p className="text-body text-[var(--muted-foreground)] mt-1">
            Detect, engage, and convert your audience
          </p>
        </div>
        <button onClick={load} className="btn-pill btn-pill-outline flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Category filter pills */}
      <div className="flex gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`btn-pill btn-pill-sm capitalize ${
              category === cat ? "btn-pill-primary" : "btn-pill-outline"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Waitlist Stats Bar */}
      {waitlistStats && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="relative overflow-hidden rounded-2xl p-6 bg-gradient-to-br from-purple-600 via-purple-700 to-violet-800">
            <div className="relative z-10">
              <div className="flex items-center gap-2 mb-2">
                <UserPlus className="w-4 h-4 text-white/80" />
                <span className="text-label text-white/80">Total Signups</span>
              </div>
              <div className="text-display text-white" style={{ fontSize: "36px" }}>
                {waitlistStats.total}
              </div>
              <div className="text-body-sm text-white/70 mt-1">
                {waitlistStats.active} active
              </div>
            </div>
            <div className="absolute top-0 right-0 w-40 h-40 rounded-full bg-white/10 blur-3xl -translate-y-10 translate-x-10" />
          </div>

          <div className="elevated-card rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 className="w-4 h-4 text-purple-400" />
              <span className="text-label text-[var(--muted-foreground)]">Sources</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(waitlistStats.by_source).map(([source, count]) => (
                <div key={source} className="flex items-center gap-1.5">
                  <SourceBadge source={source} />
                  <span className="text-body-sm text-white font-semibold">{count}</span>
                </div>
              ))}
              {Object.keys(waitlistStats.by_source).length === 0 && (
                <span className="text-body-sm text-[var(--muted-foreground)]">No data yet</span>
              )}
            </div>
          </div>

          <div className="elevated-card rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span className="text-label text-[var(--muted-foreground)]">Conversion Rate</span>
            </div>
            <div className="text-display text-white" style={{ fontSize: "36px" }}>
              {conversionRate}%
            </div>
            <div className="text-body-sm text-[var(--muted-foreground)] mt-1">
              {waitlistStats.converted} converted
            </div>
          </div>
        </div>
      )}

      {/* Main content grid */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-8">
        {/* Left: Lead Detection Queue */}
        <section>
          <SectionHeader
            title={`Lead Detection Queue (${leads.length})`}
            glow
          />
          <div className="space-y-4">
            <AnimatePresence initial={false}>
              {leads.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="py-12 text-center elevated-card rounded-2xl"
                >
                  <Users className="w-12 h-12 text-purple-400/30 mx-auto mb-4" />
                  <p className="text-body text-[var(--muted-foreground)]">
                    No leads detected yet. They will appear here as your audience grows.
                  </p>
                </motion.div>
              ) : (
                leads.map((lead) => (
                  <motion.div
                    key={lead.id}
                    layout
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="glass-card rounded-2xl p-5 space-y-3"
                  >
                    {/* Top row: badges */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <CategoryBadge category={lead.category} />
                      <PlatformBadge platform={lead.platform} />
                      <SentimentDot sentiment={lead.sentiment} />
                      <span className="text-body-sm text-white font-medium ml-1">
                        @{lead.username}
                      </span>
                      <span className="text-caption text-[var(--muted-foreground)] ml-auto">
                        {new Date(lead.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    {/* Message */}
                    {lead.message && (
                      <p className="text-body-sm text-[var(--muted-foreground)] italic border-l-2 border-purple-500/30 pl-3">
                        &ldquo;{lead.message}&rdquo;
                      </p>
                    )}

                    {/* Suggested action */}
                    {lead.suggested_action && (
                      <div className="flex items-center gap-2">
                        <ArrowRight className="w-3.5 h-3.5 text-purple-400" />
                        <span className="text-body-sm text-purple-300">{lead.suggested_action}</span>
                      </div>
                    )}

                    {/* DM Draft */}
                    {lead.dm_draft && (
                      <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-3">
                        <div className="text-caption text-purple-400 mb-1.5">DM Draft</div>
                        <textarea
                          className="w-full bg-transparent text-body-sm text-white resize-none outline-none"
                          rows={3}
                          defaultValue={lead.dm_draft}
                          onBlur={(e) =>
                            handleUpdateLead(lead.id, { dm_draft: e.target.value })
                          }
                        />
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-1">
                      <button
                        onClick={() => handleGenerateDM(lead.id)}
                        disabled={generatingDM === lead.id}
                        className="btn-pill btn-pill-sm btn-pill-primary flex items-center gap-1.5 disabled:opacity-50"
                      >
                        {generatingDM === lead.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Send className="w-3.5 h-3.5" />
                        )}
                        Generate DM
                      </button>
                      <button
                        onClick={() => handleUpdateLead(lead.id, { status: "contacted" })}
                        className="btn-pill btn-pill-sm flex items-center gap-1.5 border border-emerald-500/40 text-emerald-400 bg-transparent hover:bg-emerald-500/10"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        Mark Contacted
                      </button>
                      <button
                        onClick={() => handleUpdateLead(lead.id, { status: "dismissed" })}
                        className="btn-pill btn-pill-sm flex items-center gap-1.5 border border-[var(--border)] text-[var(--muted-foreground)] bg-transparent hover:bg-[var(--muted)]"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        Dismiss
                      </button>
                    </div>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>
        </section>

        {/* Right: Comment Replies */}
        <section>
          <SectionHeader title={`Pending Replies (${replies.length})`} />
          <div className="space-y-4">
            <AnimatePresence initial={false}>
              {replies.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="py-10 text-center elevated-card rounded-2xl"
                >
                  <MessageCircle className="w-10 h-10 text-purple-400/30 mx-auto mb-3" />
                  <p className="text-body-sm text-[var(--muted-foreground)]">
                    No pending replies.
                  </p>
                </motion.div>
              ) : (
                replies.map((reply) => (
                  <motion.div
                    key={reply.id}
                    layout
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    className="glass-card rounded-2xl p-4 space-y-3"
                  >
                    <div className="flex items-center gap-2">
                      <PlatformBadge platform={reply.platform} />
                      {reply.username && (
                        <span className="text-body-sm text-white/70">@{reply.username}</span>
                      )}
                    </div>

                    <p className="text-body-sm text-[var(--muted-foreground)] italic border-l-2 border-[var(--border)] pl-3">
                      &ldquo;{reply.original_comment}&rdquo;
                    </p>

                    {reply.reply_draft ? (
                      <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-3">
                        <div className="text-caption text-purple-400 mb-1.5">Reply Draft</div>
                        <textarea
                          className="w-full bg-transparent text-body-sm text-white resize-none outline-none"
                          rows={2}
                          defaultValue={reply.reply_draft}
                          onBlur={(e) =>
                            handleUpdateReply(reply.id, { reply_draft: e.target.value })
                          }
                        />
                      </div>
                    ) : (
                      <button
                        onClick={() => handleGenerateReply(reply.id)}
                        disabled={generatingReply === reply.id}
                        className="btn-pill btn-pill-sm btn-pill-primary flex items-center gap-1.5 disabled:opacity-50"
                      >
                        {generatingReply === reply.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Send className="w-3.5 h-3.5" />
                        )}
                        Generate Reply
                      </button>
                    )}

                    {reply.reply_draft && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleUpdateReply(reply.id, { status: "approved" })}
                          className="btn-pill btn-pill-sm flex items-center gap-1.5 border border-emerald-500/40 text-emerald-400 bg-transparent hover:bg-emerald-500/10"
                        >
                          <CheckCircle className="w-3.5 h-3.5" />
                          Approve
                        </button>
                        <button
                          onClick={() => handleUpdateReply(reply.id, { status: "skipped" })}
                          className="btn-pill btn-pill-sm flex items-center gap-1.5 border border-[var(--border)] text-[var(--muted-foreground)] bg-transparent hover:bg-[var(--muted)]"
                        >
                          Skip
                        </button>
                      </div>
                    )}
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>
        </section>
      </div>

      {/* Waitlist Management */}
      <section>
        <SectionHeader
          title="Waitlist"
          action={
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="btn-pill btn-pill-sm btn-pill-primary flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Signup
            </button>
          }
        />

        {/* Add signup form */}
        <AnimatePresence>
          {showAddForm && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="elevated-card rounded-2xl p-5 mb-5 flex flex-wrap items-end gap-4">
                <div className="flex-1 min-w-[200px]">
                  <label className="text-caption text-[var(--muted-foreground)] mb-1 block">
                    Email *
                  </label>
                  <input
                    type="email"
                    value={newSignup.email}
                    onChange={(e) => setNewSignup({ ...newSignup, email: e.target.value })}
                    className="w-full bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-body-sm text-white outline-none focus:border-purple-500"
                    placeholder="user@example.com"
                  />
                </div>
                <div className="flex-1 min-w-[160px]">
                  <label className="text-caption text-[var(--muted-foreground)] mb-1 block">
                    Name
                  </label>
                  <input
                    type="text"
                    value={newSignup.name}
                    onChange={(e) => setNewSignup({ ...newSignup, name: e.target.value })}
                    className="w-full bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-body-sm text-white outline-none focus:border-purple-500"
                    placeholder="Jane Doe"
                  />
                </div>
                <div className="flex-1 min-w-[140px]">
                  <label className="text-caption text-[var(--muted-foreground)] mb-1 block">
                    Source
                  </label>
                  <input
                    type="text"
                    value={newSignup.source}
                    onChange={(e) => setNewSignup({ ...newSignup, source: e.target.value })}
                    className="w-full bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-body-sm text-white outline-none focus:border-purple-500"
                    placeholder="tiktok, twitter..."
                  />
                </div>
                <button
                  onClick={handleAddSignup}
                  disabled={!newSignup.email}
                  className="btn-pill btn-pill-primary flex items-center gap-1.5 disabled:opacity-40"
                >
                  <Mail className="w-4 h-4" />
                  Add
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Waitlist table */}
        <div className="elevated-card rounded-2xl overflow-hidden">
          {waitlist.length === 0 ? (
            <div className="py-12 text-center">
              <Mail className="w-10 h-10 text-purple-400/30 mx-auto mb-3" />
              <p className="text-body-sm text-[var(--muted-foreground)]">
                No waitlist signups yet.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-[var(--border)]">
                    <th className="text-caption text-[var(--muted-foreground)] px-5 py-3">
                      Email
                    </th>
                    <th className="text-caption text-[var(--muted-foreground)] px-5 py-3">
                      Name
                    </th>
                    <th className="text-caption text-[var(--muted-foreground)] px-5 py-3">
                      Source
                    </th>
                    <th className="text-caption text-[var(--muted-foreground)] px-5 py-3">
                      Date
                    </th>
                    <th className="text-caption text-[var(--muted-foreground)] px-5 py-3">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {waitlist.map((signup) => (
                    <tr
                      key={signup.id}
                      className="border-b border-[var(--border)] last:border-0 hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="text-body-sm text-white px-5 py-3 font-mono">
                        {signup.email}
                      </td>
                      <td className="text-body-sm text-[var(--muted-foreground)] px-5 py-3">
                        {signup.name || "-"}
                      </td>
                      <td className="px-5 py-3">
                        <SourceBadge source={signup.source} />
                      </td>
                      <td className="text-body-sm text-[var(--muted-foreground)] px-5 py-3">
                        {new Date(signup.signed_up_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`text-caption px-2 py-0.5 rounded-full ${
                            signup.status === "active"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : signup.status === "converted"
                                ? "bg-purple-500/20 text-purple-400"
                                : "bg-[var(--muted)] text-[var(--muted-foreground)]"
                          }`}
                        >
                          {signup.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
