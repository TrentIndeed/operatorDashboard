"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api, Lead, OutreachStats } from "@/lib/api";
import {
  Users, RefreshCw, Loader2, Send, CheckCircle, XCircle, Plus,
  TrendingUp, Search, ExternalLink, Copy, Sparkles, Clock,
  MessageCircle, Target, UserCheck, Star, Filter,
} from "lucide-react";

// --- Helpers ---

function TierBadge({ tier }: { tier: number | null }) {
  if (!tier) return null;
  const styles: Record<number, string> = {
    1: "bg-gradient-to-r from-amber-500 to-yellow-400 text-black font-semibold",
    2: "bg-gradient-to-r from-blue-600 to-blue-500 text-white",
    3: "bg-[var(--muted)] text-[var(--muted-foreground)]",
  };
  return (
    <span className={`text-caption px-2 py-0.5 rounded-full ${styles[tier] || styles[3]}`}>
      Tier {tier}
    </span>
  );
}

function PlatformBadge({ platform }: { platform: string }) {
  const label = platform.replace("reddit_", "r/");
  const colors: Record<string, string> = {
    reddit: "border-orange-500/40 text-orange-400",
    linkedin: "border-blue-500/40 text-blue-400",
    fiverr: "border-green-500/40 text-green-400",
    upwork: "border-emerald-500/40 text-emerald-400",
    forum: "border-purple-500/40 text-purple-400",
  };
  const key = Object.keys(colors).find((k) => platform.toLowerCase().includes(k)) || "";
  return (
    <span className={`text-caption px-2 py-0.5 rounded-full border ${colors[key] || "border-[var(--border)] text-[var(--muted-foreground)]"}`}>
      {label}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    new: "bg-white/10 text-white",
    contacted: "bg-blue-500/20 text-blue-400",
    responded: "bg-cyan-500/20 text-cyan-400",
    interested: "bg-emerald-500/20 text-emerald-400",
    beta_user: "bg-purple-500/20 text-purple-400",
    paying: "bg-amber-500/20 text-amber-400",
    not_interested: "bg-red-500/20 text-red-400",
    no_response: "bg-gray-500/20 text-gray-400",
    skip: "bg-gray-500/20 text-gray-400",
  };
  return (
    <span className={`text-caption px-2 py-0.5 rounded-full ${styles[status] || styles.new}`}>
      {status.replace("_", " ")}
    </span>
  );
}

function timeAgo(dateStr: string | null) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number | string; icon: any; color: string }) {
  return (
    <div className="flex items-center gap-3 p-3">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <div className="text-subtitle text-white">{value}</div>
        <div className="text-caption text-[var(--muted-foreground)]">{label}</div>
      </div>
    </div>
  );
}

// --- Main Page ---

export default function OutreachPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<OutreachStats | null>(null);
  const [followUps, setFollowUps] = useState<Lead[]>([]);
  const [selected, setSelected] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterTier, setFilterTier] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [newLead, setNewLead] = useState({ username: "", platform: "linkedin", post_url: "", post_text: "", profile_url: "", notes: "" });
  const [editDm, setEditDm] = useState("");
  const [editReply, setEditReply] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const params: any = {};
      if (filterTier) params.tier = filterTier;
      if (filterStatus !== "all") params.status = filterStatus;
      if (searchQuery) params.search = searchQuery;
      const [leadsData, statsData, followUpData] = await Promise.all([
        api.outreachLeads(params),
        api.outreachStats(),
        api.outreachFollowUps(),
      ]);
      setLeads(leadsData);
      setStats(statsData);
      setFollowUps(followUpData);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterTier, searchQuery]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (selected) {
      setEditDm(selected.draft_dm || selected.dm_draft || "");
      setEditReply(selected.draft_public_reply || "");
    }
  }, [selected]);

  const handleScan = async () => {
    setScanning(true);
    try {
      await api.scanSignals();
      // Poll for results after 15 seconds
      setTimeout(() => { load(); setScanning(false); }, 15000);
    } catch {
      setScanning(false);
    }
  };

  const handleDraft = async (id: number) => {
    setDrafting(true);
    try {
      await api.draftMessages(id);
      setTimeout(async () => {
        const updated = await api.outreachLead(id);
        setLeads((prev) => prev.map((l) => (l.id === id ? updated : l)));
        if (selected?.id === id) setSelected(updated);
        setDrafting(false);
      }, 10000);
    } catch {
      setDrafting(false);
    }
  };

  const handleStatus = async (id: number, status: string) => {
    try {
      if (status === "contacted") {
        // Save current DM text before marking contacted
        if (editDm) {
          await api.updateOutreachLead(id, { draft_dm: editDm } as any);
        }
        const updated = await api.markContacted(id);
        setLeads((prev) => prev.map((l) => (l.id === id ? updated : l)));
        if (selected?.id === id) setSelected(updated);
      } else {
        const updated = await api.updateOutreachLead(id, { status } as any);
        setLeads((prev) => prev.map((l) => (l.id === id ? updated : l)));
        if (selected?.id === id) setSelected(updated);
      }
      if (stats) {
        const s = await api.outreachStats();
        setStats(s);
      }
    } catch { /* ignore */ }
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleAddLead = async () => {
    if (!newLead.username || !newLead.post_url || !newLead.post_text) return;
    try {
      const created = await api.createOutreachLead(newLead);
      setLeads((prev) => [created, ...prev]);
      setShowAddForm(false);
      setNewLead({ username: "", platform: "linkedin", post_url: "", post_text: "", profile_url: "", notes: "" });
    } catch { /* ignore */ }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-56px)] lg:h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[var(--border)]">
        <div>
          <h1 className="text-heading text-white">Outreach Command Center</h1>
          <p className="text-body-sm text-[var(--muted-foreground)]">
            Find leads, draft messages, track conversations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="btn-pill btn-pill-sm btn-pill-outline flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> Add Lead
          </button>
          <button
            onClick={handleScan}
            disabled={scanning}
            className="btn-pill btn-pill-sm btn-pill-primary flex items-center gap-1.5 disabled:opacity-50"
          >
            {scanning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            {scanning ? "Scanning..." : "Scan Reddit"}
          </button>
          <button onClick={load} className="btn-pill btn-pill-sm btn-pill-outline">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Manual Add Form */}
      <AnimatePresence>
        {showAddForm && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden border-b border-[var(--border)]">
            <div className="p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <input value={newLead.username} onChange={(e) => setNewLead({ ...newLead, username: e.target.value })}
                className="bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-body-sm text-white outline-none focus:border-purple-500"
                placeholder="Username *" />
              <select value={newLead.platform} onChange={(e) => setNewLead({ ...newLead, platform: e.target.value })}
                className="bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-body-sm text-white outline-none focus:border-purple-500">
                <option value="linkedin">LinkedIn</option>
                <option value="fiverr">Fiverr</option>
                <option value="upwork">Upwork</option>
                <option value="reddit">Reddit</option>
                <option value="onshape_forum">Onshape Forum</option>
              </select>
              <input value={newLead.post_url} onChange={(e) => setNewLead({ ...newLead, post_url: e.target.value })}
                className="bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-body-sm text-white outline-none focus:border-purple-500"
                placeholder="Post URL *" />
              <textarea value={newLead.post_text} onChange={(e) => setNewLead({ ...newLead, post_text: e.target.value })}
                className="sm:col-span-2 bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-body-sm text-white outline-none focus:border-purple-500 resize-none"
                rows={2} placeholder="Paste their post text *" />
              <div className="flex items-end gap-2">
                <input value={newLead.profile_url} onChange={(e) => setNewLead({ ...newLead, profile_url: e.target.value })}
                  className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-body-sm text-white outline-none focus:border-purple-500"
                  placeholder="Profile URL" />
                <button onClick={handleAddLead} className="btn-pill btn-pill-primary flex items-center gap-1.5 whitespace-nowrap">
                  <Plus className="w-3.5 h-3.5" /> Add
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Three-panel layout */}
      <div className="grid grid-cols-1 xl:grid-cols-[320px_1fr_300px] flex-1 overflow-hidden">

        {/* LEFT: Signal Feed */}
        <div className="border-r border-[var(--border)] flex flex-col overflow-hidden">
          {/* Filters */}
          <div className="p-3 border-b border-[var(--border)] space-y-2">
            <div className="flex gap-1.5 flex-wrap">
              {["all", "new", "contacted", "responded", "interested"].map((s) => (
                <button key={s} onClick={() => setFilterStatus(s)}
                  className={`text-caption px-2 py-0.5 rounded-full capitalize ${filterStatus === s ? "bg-purple-500/30 text-purple-300 border border-purple-500/40" : "bg-[var(--muted)] text-[var(--muted-foreground)] border border-transparent"}`}>
                  {s}
                </button>
              ))}
            </div>
            <div className="flex gap-1.5">
              {[null, 1, 2, 3].map((t) => (
                <button key={String(t)} onClick={() => setFilterTier(t)}
                  className={`text-caption px-2 py-0.5 rounded-full ${filterTier === t ? "bg-purple-500/30 text-purple-300 border border-purple-500/40" : "bg-[var(--muted)] text-[var(--muted-foreground)] border border-transparent"}`}>
                  {t === null ? "All tiers" : `Tier ${t}`}
                </button>
              ))}
            </div>
          </div>

          {/* Lead list */}
          <div className="flex-1 overflow-y-auto">
            {leads.length === 0 ? (
              <div className="p-8 text-center">
                <Users className="w-10 h-10 text-purple-400/30 mx-auto mb-3" />
                <p className="text-body-sm text-[var(--muted-foreground)]">
                  No leads yet. Click &quot;Scan Reddit&quot; to find people.
                </p>
              </div>
            ) : (
              leads.map((lead) => (
                <button key={lead.id} onClick={() => setSelected(lead)}
                  className={`w-full text-left p-3 border-b border-[var(--border)] hover:bg-white/[0.03] transition-colors ${selected?.id === lead.id ? "bg-purple-500/10 border-l-2 border-l-purple-500" : ""}`}>
                  <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                    <TierBadge tier={lead.tier} />
                    <PlatformBadge platform={lead.platform} />
                    <StatusBadge status={lead.status} />
                  </div>
                  <div className="text-body-sm text-white font-medium truncate">
                    @{lead.username}
                  </div>
                  <p className="text-caption text-[var(--muted-foreground)] line-clamp-2 mt-0.5">
                    {lead.post_text || lead.message || "No post text"}
                  </p>
                  <span className="text-caption text-[var(--muted-foreground)] opacity-60">
                    {timeAgo(lead.post_date || lead.created_at)}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* CENTER: Lead Detail */}
        <div className="overflow-y-auto">
          {!selected ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-8">
              <Target className="w-16 h-16 text-purple-400/20 mb-4" />
              <p className="text-body text-[var(--muted-foreground)]">
                Select a lead from the list to see details
              </p>
            </div>
          ) : (
            <div className="p-5 space-y-5">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <TierBadge tier={selected.tier} />
                    <PlatformBadge platform={selected.platform} />
                    <StatusBadge status={selected.status} />
                  </div>
                  <h2 className="text-subtitle text-white">@{selected.username}</h2>
                  {selected.tier_reason && (
                    <p className="text-caption text-[var(--muted-foreground)] mt-0.5">{selected.tier_reason}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {selected.post_url && (
                    <a href={selected.post_url} target="_blank" rel="noopener noreferrer"
                      className="btn-pill btn-pill-sm btn-pill-outline flex items-center gap-1.5">
                      <ExternalLink className="w-3.5 h-3.5" /> View Post
                    </a>
                  )}
                  {selected.profile_url && (
                    <a href={selected.profile_url} target="_blank" rel="noopener noreferrer"
                      className="btn-pill btn-pill-sm btn-pill-outline flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5" /> Profile
                    </a>
                  )}
                </div>
              </div>

              {/* Post text */}
              <div className="glass-card rounded-xl p-4">
                <div className="text-caption text-[var(--muted-foreground)] mb-2">Original Post</div>
                <p className="text-body-sm text-white whitespace-pre-wrap">
                  {selected.post_text || selected.message || "No post text available"}
                </p>
              </div>

              {/* Account summary */}
              {selected.account_summary && (
                <div className="elevated-card rounded-xl p-4">
                  <div className="text-caption text-purple-400 mb-2">About This Person</div>
                  <p className="text-body-sm text-[var(--muted-foreground)] whitespace-pre-wrap">
                    {selected.account_summary}
                  </p>
                </div>
              )}

              {/* Demo video recommendation */}
              {selected.include_demo_video && (
                <div className={`rounded-xl p-3 text-body-sm ${selected.include_demo_video.toLowerCase().startsWith("yes") ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-300" : "bg-[var(--muted)] text-[var(--muted-foreground)]"}`}>
                  Include demo video: {selected.include_demo_video}
                </div>
              )}

              {/* DM Draft */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-caption text-purple-400">Draft DM</span>
                  <div className="flex gap-1.5">
                    <button onClick={() => handleDraft(selected.id)} disabled={drafting}
                      className="text-caption text-purple-400 hover:text-purple-300 flex items-center gap-1">
                      {drafting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                      {drafting ? "Generating..." : "Regenerate"}
                    </button>
                    <button onClick={() => handleCopy(editDm, "dm")}
                      className="text-caption text-[var(--muted-foreground)] hover:text-white flex items-center gap-1">
                      <Copy className="w-3 h-3" />
                      {copied === "dm" ? "Copied!" : "Copy"}
                    </button>
                  </div>
                </div>
                <textarea
                  value={editDm}
                  onChange={(e) => setEditDm(e.target.value)}
                  onBlur={() => {
                    if (selected && editDm !== (selected.draft_dm || "")) {
                      api.updateOutreachLead(selected.id, { draft_dm: editDm } as any);
                    }
                  }}
                  className="w-full bg-purple-500/5 border border-purple-500/20 rounded-xl p-3 text-body-sm text-white resize-none outline-none focus:border-purple-500/40"
                  rows={4}
                  placeholder="No DM draft yet. Click Regenerate to create one."
                />
              </div>

              {/* Public Reply Draft */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-caption text-cyan-400">Draft Public Reply</span>
                  <button onClick={() => handleCopy(editReply, "reply")}
                    className="text-caption text-[var(--muted-foreground)] hover:text-white flex items-center gap-1">
                    <Copy className="w-3 h-3" />
                    {copied === "reply" ? "Copied!" : "Copy"}
                  </button>
                </div>
                <textarea
                  value={editReply}
                  onChange={(e) => setEditReply(e.target.value)}
                  onBlur={() => {
                    if (selected && editReply !== (selected.draft_public_reply || "")) {
                      api.updateOutreachLead(selected.id, { draft_public_reply: editReply } as any);
                    }
                  }}
                  className="w-full bg-cyan-500/5 border border-cyan-500/20 rounded-xl p-3 text-body-sm text-white resize-none outline-none focus:border-cyan-500/40"
                  rows={4}
                  placeholder="No public reply draft yet."
                />
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <span className="text-caption text-[var(--muted-foreground)]">Notes</span>
                <textarea
                  defaultValue={selected.notes || ""}
                  onBlur={(e) => api.updateOutreachLead(selected.id, { notes: e.target.value } as any)}
                  className="w-full bg-[var(--background)] border border-[var(--border)] rounded-xl p-3 text-body-sm text-white resize-none outline-none focus:border-purple-500/40"
                  rows={2}
                  placeholder="Personal notes about this lead..."
                />
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-[var(--border)]">
                {selected.status === "new" && (
                  <>
                    <button onClick={() => handleStatus(selected.id, "contacted")}
                      className="btn-pill btn-pill-sm flex items-center gap-1.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30">
                      <CheckCircle className="w-3.5 h-3.5" /> Mark Contacted
                    </button>
                    <button onClick={() => handleStatus(selected.id, "skip")}
                      className="btn-pill btn-pill-sm flex items-center gap-1.5 border border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]">
                      <XCircle className="w-3.5 h-3.5" /> Skip
                    </button>
                  </>
                )}
                {selected.status === "contacted" && (
                  <>
                    <button onClick={() => handleStatus(selected.id, "responded")}
                      className="btn-pill btn-pill-sm flex items-center gap-1.5 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30">
                      <MessageCircle className="w-3.5 h-3.5" /> Responded
                    </button>
                    <button onClick={() => handleStatus(selected.id, "no_response")}
                      className="btn-pill btn-pill-sm flex items-center gap-1.5 border border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]">
                      No Response
                    </button>
                  </>
                )}
                {selected.status === "responded" && (
                  <button onClick={() => handleStatus(selected.id, "interested")}
                    className="btn-pill btn-pill-sm flex items-center gap-1.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30">
                    <Star className="w-3.5 h-3.5" /> Interested
                  </button>
                )}
                {selected.status === "interested" && (
                  <button onClick={() => handleStatus(selected.id, "beta_user")}
                    className="btn-pill btn-pill-sm flex items-center gap-1.5 bg-purple-500/20 text-purple-400 border border-purple-500/30 hover:bg-purple-500/30">
                    <UserCheck className="w-3.5 h-3.5" /> Add to Beta
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: Stats & Follow-ups */}
        <div className="border-l border-[var(--border)] overflow-y-auto hidden xl:block">
          {stats && (
            <div className="border-b border-[var(--border)]">
              <div className="p-3 text-caption text-[var(--muted-foreground)] font-semibold uppercase tracking-wider">
                Pipeline
              </div>
              <div className="grid grid-cols-2 gap-0">
                <StatCard label="Total" value={stats.total_leads} icon={Users} color="bg-purple-500/20 text-purple-400" />
                <StatCard label="Tier 1" value={stats.tier1_count} icon={Star} color="bg-amber-500/20 text-amber-400" />
                <StatCard label="New" value={stats.new_count} icon={Target} color="bg-white/10 text-white" />
                <StatCard label="Contacted" value={stats.contacted_count} icon={Send} color="bg-blue-500/20 text-blue-400" />
                <StatCard label="Responded" value={stats.responded_count} icon={MessageCircle} color="bg-cyan-500/20 text-cyan-400" />
                <StatCard label="Interested" value={stats.interested_count} icon={TrendingUp} color="bg-emerald-500/20 text-emerald-400" />
                <StatCard label="Beta" value={stats.beta_count} icon={UserCheck} color="bg-purple-500/20 text-purple-400" />
                <StatCard label="Paying" value={stats.paying_count} icon={Star} color="bg-amber-500/20 text-amber-400" />
              </div>
              {stats.follow_ups_due > 0 && (
                <div className="px-3 pb-3">
                  <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-2 text-center">
                    <span className="text-caption text-amber-400">
                      {stats.follow_ups_due} follow-up{stats.follow_ups_due > 1 ? "s" : ""} due
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Follow-up queue */}
          <div className="p-3">
            <div className="text-caption text-[var(--muted-foreground)] font-semibold uppercase tracking-wider mb-3">
              Follow-up Queue
            </div>
            {followUps.length === 0 ? (
              <p className="text-caption text-[var(--muted-foreground)] text-center py-4">
                No follow-ups due
              </p>
            ) : (
              <div className="space-y-2">
                {followUps.map((lead) => (
                  <button key={lead.id} onClick={() => setSelected(lead)}
                    className="w-full text-left p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 hover:bg-amber-500/10 transition-colors">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <Clock className="w-3 h-3 text-amber-400" />
                      <span className="text-caption text-white">@{lead.username}</span>
                      <PlatformBadge platform={lead.platform} />
                    </div>
                    <p className="text-caption text-[var(--muted-foreground)]">
                      Contacted {timeAgo(lead.contacted_at)}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
