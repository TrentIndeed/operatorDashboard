"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  api,
  ContentDraft,
  HookVariation,
} from "@/lib/api";
import {
  Loader2,
  RefreshCw,
  Sparkles,
  PenTool,
  Check,
  X,
  Shuffle,
  ChevronDown,
  ChevronUp,
  Hash,
  FileText,
  Wand2,
  Send,
  Film,
  Zap,
} from "lucide-react";

// --- Helpers ---

const PLATFORMS = ["tiktok", "youtube", "twitter", "instagram", "blog"] as const;
const CONTENT_TYPES = ["short-form", "long-form", "thread", "reel", "blog-post", "script"] as const;
const PROJECT_TAGS = ["ai-automation", "operator-dashboard", "content-engine", "personal-brand", "side-project"] as const;

const STATUS_FILTERS = ["all", "draft", "approved", "declined"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

const platformColor: Record<string, string> = {
  tiktok: "gradient-pink",
  youtube: "bg-gradient-to-r from-red-500 to-rose-600 text-white",
  twitter: "gradient-cyan",
  instagram: "gradient-amber",
  blog: "gradient-purple",
};

const statusBadge: Record<string, string> = {
  draft: "border border-purple-500/40 text-purple-300",
  approved: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  declined: "bg-red-500/10 text-red-400/70 border border-red-500/20",
  scheduled: "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30",
};

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

// --- Draft Card ---

function DraftCard({
  draft,
  onApprove,
  onDecline,
  onRemix,
}: {
  draft: ContentDraft;
  onApprove: (id: number) => void;
  onDecline: (id: number) => void;
  onRemix: (id: number, feedback: string) => void;
}) {
  const [remixOpen, setRemixOpen] = useState(false);
  const [remixFeedback, setRemixFeedback] = useState("");
  const [expanded, setExpanded] = useState(false);

  const hashtags = draft.hashtags
    ? draft.hashtags.split(",").map((h) => h.trim()).filter(Boolean)
    : [];

  const bodyPreview =
    draft.body.length > 200 && !expanded
      ? draft.body.slice(0, 200) + "..."
      : draft.body;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.25 }}
      className="elevated-card rounded-2xl p-5 flex flex-col gap-3"
    >
      {/* Top row: platform + status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`text-caption font-semibold px-2.5 py-0.5 rounded-full ${
              platformColor[draft.platform] || "gradient-purple"
            }`}
          >
            {draft.platform}
          </span>
          {draft.project_tag && (
            <span className="text-caption px-2 py-0.5 rounded-full border border-white/10 text-[var(--muted-foreground)]">
              {draft.project_tag}
            </span>
          )}
        </div>
        <span
          className={`text-caption px-2 py-0.5 rounded-full ${
            statusBadge[draft.status] || statusBadge.draft
          }`}
        >
          {draft.status}
        </span>
      </div>

      {/* Title */}
      <h3 className="text-subtitle text-white leading-snug">{draft.title}</h3>

      {/* Hook */}
      {draft.hook && (
        <p className="text-body-sm italic text-purple-300">{draft.hook}</p>
      )}

      {/* Body preview */}
      <p className="text-body-sm text-[var(--muted-foreground)] whitespace-pre-line">
        {bodyPreview}
      </p>
      {draft.body.length > 200 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-caption text-purple-400 hover:text-purple-300 flex items-center gap-1 self-start"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? "Show less" : "Read more"}
        </button>
      )}

      {/* Hashtags */}
      {hashtags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {hashtags.map((tag) => (
            <span
              key={tag}
              className="text-caption px-2 py-0.5 rounded-full bg-white/5 text-[var(--muted-foreground)] border border-white/5"
            >
              <Hash className="w-3 h-3 inline mr-0.5 opacity-50" />
              {tag.replace(/^#/, "")}
            </span>
          ))}
        </div>
      )}

      {/* Hook score */}
      {draft.hook_score != null && (
        <div className="flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-caption text-amber-300 font-medium">
            Hook score: {Math.round(draft.hook_score * 100)}%
          </span>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-white/5 mt-auto">
        {draft.status === "draft" && (
          <>
            <button
              onClick={() => onApprove(draft.id)}
              className="btn-pill text-xs flex items-center gap-1.5 bg-gradient-to-r from-emerald-500 to-green-600 text-white hover:brightness-110 transition"
            >
              <Check className="w-3.5 h-3.5" /> Approve
            </button>
            <button
              onClick={() => onDecline(draft.id)}
              className="btn-pill btn-pill-outline text-xs flex items-center gap-1.5"
            >
              <X className="w-3.5 h-3.5" /> Decline
            </button>
            <button
              onClick={() => setRemixOpen(!remixOpen)}
              className="btn-pill text-xs flex items-center gap-1.5 border border-purple-500/40 text-purple-300 hover:bg-purple-500/10 transition"
            >
              <Shuffle className="w-3.5 h-3.5" /> Remix
            </button>
          </>
        )}
        {draft.status !== "draft" && (
          <span className="text-caption text-[var(--muted-foreground)]">
            {draft.status === "approved" ? "Approved" : draft.status === "declined" ? "Declined" : draft.status}
          </span>
        )}
      </div>

      {/* Remix feedback input */}
      <AnimatePresence>
        {remixOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="flex gap-2 pt-2">
              <input
                type="text"
                placeholder="Remix feedback (e.g. make it punchier)..."
                value={remixFeedback}
                onChange={(e) => setRemixFeedback(e.target.value)}
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-body-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
              />
              <button
                onClick={() => {
                  if (remixFeedback.trim()) {
                    onRemix(draft.id, remixFeedback);
                    setRemixFeedback("");
                    setRemixOpen(false);
                  }
                }}
                className="btn-pill btn-pill-primary text-xs"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// --- Hook Result Card ---

function HookResultCard({ variation, index }: { variation: HookVariation; index: number }) {
  const [scriptOpen, setScriptOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="elevated-card rounded-xl p-4 space-y-3"
    >
      <div className="flex items-center justify-between">
        <span className="text-label text-[var(--muted-foreground)]">Variation {index + 1}</span>
        <span className="text-caption font-semibold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/20">
          <Zap className="w-3 h-3 inline mr-1" />
          {Math.round(variation.score * 100)}%
        </span>
      </div>
      <p className="text-body text-white font-medium leading-snug">&ldquo;{variation.hook}&rdquo;</p>

      {/* Expandable script */}
      <button
        onClick={() => setScriptOpen(!scriptOpen)}
        className="text-caption text-purple-400 hover:text-purple-300 flex items-center gap-1"
      >
        <FileText className="w-3 h-3" />
        {scriptOpen ? "Hide script" : "Show full script"}
        {scriptOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      <AnimatePresence>
        {scriptOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <p className="text-body-sm text-[var(--muted-foreground)] whitespace-pre-line bg-white/[0.03] rounded-lg p-3 border border-white/5">
              {variation.full_script}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* CTA */}
      {variation.cta && (
        <div className="text-caption text-cyan-300 flex items-center gap-1.5">
          <Sparkles className="w-3 h-3" />
          CTA: {variation.cta}
        </div>
      )}
    </motion.div>
  );
}

// --- Main Page ---

export default function ContentStudioPage() {
  // Data
  const [drafts, setDrafts] = useState<ContentDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [activeFilter, setActiveFilter] = useState<StatusFilter>("all");

  // Generate draft modal
  const [showGenerate, setShowGenerate] = useState(false);
  const [genTopic, setGenTopic] = useState("");
  const [genPlatform, setGenPlatform] = useState<string>("tiktok");
  const [genType, setGenType] = useState<string>("short-form");
  const [genProject, setGenProject] = useState<string>("ai-automation");
  const [generating, setGenerating] = useState(false);

  // Hook generator
  const [hookTopic, setHookTopic] = useState("");
  const [hookPlatform, setHookPlatform] = useState<string>("tiktok");
  const [hookProject, setHookProject] = useState<string>("ai-automation");
  const [hookResults, setHookResults] = useState<HookVariation[]>([]);
  const [hookLoading, setHookLoading] = useState(false);

  // Actions loading
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const loadDrafts = async () => {
    try {
      const status = activeFilter === "all" ? undefined : activeFilter;
      const d = await api.getDrafts(status);
      // Keep only the best 8 drafts, sorted by hook_score (highest first)
      const sorted = [...d].sort((a, b) => (b.hook_score ?? 0) - (a.hook_score ?? 0));
      setDrafts(sorted.slice(0, 8));
    } catch (e) {
      setError("Cannot reach backend. Make sure FastAPI is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    loadDrafts();
  }, [activeFilter]);

  // --- Actions ---

  const handleApprove = async (id: number) => {
    setActionLoading(id);
    try {
      const updated = await api.approveDraft(id);
      setDrafts((prev) => prev.map((d) => (d.id === id ? updated : d)));
    } catch {
      // silent
    } finally {
      setActionLoading(null);
    }
  };

  const handleDecline = async (id: number) => {
    setActionLoading(id);
    try {
      const updated = await api.declineDraft(id);
      setDrafts((prev) => prev.map((d) => (d.id === id ? updated : d)));
    } catch {
      // silent
    } finally {
      setActionLoading(null);
    }
  };

  const handleRemix = async (id: number, feedback: string) => {
    setActionLoading(id);
    try {
      const newDraft = await api.remixDraft(id, feedback);
      setDrafts((prev) => [newDraft, ...prev]);
    } catch {
      // silent
    } finally {
      setActionLoading(null);
    }
  };

  const handleGenerate = async () => {
    if (!genTopic.trim()) return;
    setGenerating(true);
    try {
      const newDraft = await api.generateDraft(genTopic, genPlatform, genType, genProject);
      setDrafts((prev) => [newDraft, ...prev]);
      setShowGenerate(false);
      setGenTopic("");
    } catch {
      // silent
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateHooks = async () => {
    if (!hookTopic.trim()) return;
    setHookLoading(true);
    try {
      const res = await api.generateHooks(hookTopic, hookPlatform, hookProject);
      setHookResults(res.variations);
    } catch {
      // silent
    } finally {
      setHookLoading(false);
    }
  };

  // --- Render ---

  if (loading && drafts.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          <span className="text-body-sm text-[var(--muted-foreground)]">
            Loading Content Studio...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-5">
        <div className="text-subtitle text-pink-400">{error}</div>
        <button
          onClick={() => {
            setError(null);
            setLoading(true);
            loadDrafts();
          }}
          className="btn-pill btn-pill-primary flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-10 space-y-6 sm:space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-heading text-white">Content Studio</h1>
          <p className="text-body text-[var(--muted-foreground)] mt-1">
            Generate, review, and manage content drafts
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => loadDrafts()}
            className="btn-pill btn-pill-outline flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
          <button
            onClick={() => setShowGenerate(!showGenerate)}
            className="btn-pill btn-pill-primary flex items-center gap-2"
          >
            <Wand2 className="w-4 h-4" /> Generate Draft
          </button>
        </div>
      </div>

      {/* Generate Draft Panel */}
      <AnimatePresence>
        {showGenerate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="elevated-card rounded-2xl p-6 space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-5 h-5 text-purple-400" />
                <h3 className="text-subtitle text-white">Generate with Claude</h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="space-y-1.5">
                  <label className="text-caption text-[var(--muted-foreground)]">Topic</label>
                  <input
                    type="text"
                    placeholder="e.g. Why AI agents are the future..."
                    value={genTopic}
                    onChange={(e) => setGenTopic(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-body-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-caption text-[var(--muted-foreground)]">Platform</label>
                  <select
                    value={genPlatform}
                    onChange={(e) => setGenPlatform(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-body-sm text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {PLATFORMS.map((p) => (
                      <option key={p} value={p} className="bg-[#0A0A0B]">
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-caption text-[var(--muted-foreground)]">Content Type</label>
                  <select
                    value={genType}
                    onChange={(e) => setGenType(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-body-sm text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {CONTENT_TYPES.map((t) => (
                      <option key={t} value={t} className="bg-[#0A0A0B]">
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-caption text-[var(--muted-foreground)]">Project</label>
                  <select
                    value={genProject}
                    onChange={(e) => setGenProject(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-body-sm text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {PROJECT_TAGS.map((p) => (
                      <option key={p} value={p} className="bg-[#0A0A0B]">
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={handleGenerate}
                  disabled={generating || !genTopic.trim()}
                  className="btn-pill btn-pill-primary flex items-center gap-2 disabled:opacity-50"
                >
                  {generating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Wand2 className="w-4 h-4" />
                  )}
                  {generating ? "Generating..." : "Generate"}
                </button>
                <button
                  onClick={() => setShowGenerate(false)}
                  className="btn-pill btn-pill-outline text-xs"
                >
                  Cancel
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Filter Pills */}
      <div className="flex items-center gap-2">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter}
            onClick={() => setActiveFilter(filter)}
            className={`btn-pill text-xs capitalize transition ${
              activeFilter === filter
                ? "btn-pill-primary"
                : "btn-pill-outline"
            }`}
          >
            {filter === "all" ? "All" : filter}
            {filter !== "all" && activeFilter === filter && (
              <span className="ml-1.5 bg-white/20 rounded-full px-1.5 text-[10px]">
                {drafts.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Main Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-8">
        {/* Drafts Grid */}
        <section>
          <SectionHeader
            title={`Content Drafts (${drafts.length})`}
            glow
          />
          {drafts.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="py-16 text-center elevated-card rounded-2xl"
            >
              <PenTool className="w-12 h-12 text-purple-400/30 mx-auto mb-4" />
              <p className="text-body text-[var(--muted-foreground)]">
                No drafts{activeFilter !== "all" ? ` with status "${activeFilter}"` : ""}.
              </p>
              <p className="text-body-sm text-[var(--muted-foreground)] mt-1">
                Hit{" "}
                <span className="text-purple-400 font-semibold">Generate Draft</span>{" "}
                to create content with Claude.
              </p>
            </motion.div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <AnimatePresence mode="popLayout">
                {drafts.map((draft) => (
                  <DraftCard
                    key={draft.id}
                    draft={draft}
                    onApprove={handleApprove}
                    onDecline={handleDecline}
                    onRemix={handleRemix}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </section>

        {/* Hook & Script Generator Sidebar */}
        <section>
          <SectionHeader
            title="Hook & Script Generator"
            action={<Film className="w-4 h-4 text-purple-400 animate-pulse" />}
          />
          <div className="elevated-card rounded-2xl p-5 space-y-4">
            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-caption text-[var(--muted-foreground)]">Topic</label>
                <input
                  type="text"
                  placeholder="e.g. Building in public with AI..."
                  value={hookTopic}
                  onChange={(e) => setHookTopic(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-body-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-caption text-[var(--muted-foreground)]">Platform</label>
                  <select
                    value={hookPlatform}
                    onChange={(e) => setHookPlatform(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-body-sm text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {PLATFORMS.map((p) => (
                      <option key={p} value={p} className="bg-[#0A0A0B]">
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-caption text-[var(--muted-foreground)]">Project</label>
                  <select
                    value={hookProject}
                    onChange={(e) => setHookProject(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-body-sm text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {PROJECT_TAGS.map((p) => (
                      <option key={p} value={p} className="bg-[#0A0A0B]">
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                onClick={handleGenerateHooks}
                disabled={hookLoading || !hookTopic.trim()}
                className="btn-pill btn-pill-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {hookLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                {hookLoading ? "Generating Hooks..." : "Generate Hooks"}
              </button>
            </div>

            {/* Hook Results */}
            {hookResults.length > 0 && (
              <div className="space-y-3 pt-3 border-t border-white/5">
                <span className="text-label text-[var(--muted-foreground)]">
                  {hookResults.length} Variations
                </span>
                {hookResults.map((v, i) => (
                  <HookResultCard key={i} variation={v} index={i} />
                ))}
              </div>
            )}

            {/* Empty state for hooks */}
            {hookResults.length === 0 && !hookLoading && (
              <div className="text-center py-6">
                <Sparkles className="w-8 h-8 text-purple-400/20 mx-auto mb-2" />
                <p className="text-caption text-[var(--muted-foreground)]">
                  Enter a topic and generate hook variations with scores, scripts, and CTAs.
                </p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
