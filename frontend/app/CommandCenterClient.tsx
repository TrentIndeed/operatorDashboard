"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api, CommandCenterData, Task } from "@/lib/api";
import { TaskCard } from "@/components/dashboard/TaskCard";
import { ProjectCard } from "@/components/dashboard/ProjectCard";
import { GoalsPanel } from "@/components/dashboard/GoalsPanel";
import { SuggestionsPanel } from "@/components/dashboard/SuggestionsPanel";
import { BriefingPanel } from "@/components/dashboard/BriefingPanel";
import { StatCard } from "@/components/dashboard/StatCard";
import {
  Sparkles,
  RefreshCw,
  Loader2,
  Brain,
  Target,
  Clock,
  TrendingUp,
  AlertTriangle,
  Check,
  GitBranch,
  Radar,
  FileText,
  Calendar,
} from "lucide-react";

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
        {glow && <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse shadow-[0_0_8px_rgba(168,85,247,0.5)]" />}
        {title}
      </h2>
      {action}
    </div>
  );
}

type GenerateStep = {
  id: string;
  label: string;
  icon: React.ReactNode;
  status: "pending" | "running" | "done" | "error";
};

const GENERATE_STEPS: Omit<GenerateStep, "status">[] = [
  { id: "tasks", label: "Priority Tasks", icon: <Brain className="w-3.5 h-3.5" /> },
  { id: "suggestions", label: "AI Suggestions", icon: <Sparkles className="w-3.5 h-3.5" /> },
  { id: "draft_tiktok", label: "TikTok Draft", icon: <FileText className="w-3.5 h-3.5" /> },
  { id: "draft_youtube", label: "YouTube Draft", icon: <FileText className="w-3.5 h-3.5" /> },
  { id: "schedule", label: "Schedule", icon: <Calendar className="w-3.5 h-3.5" /> },
  { id: "briefing", label: "Briefing", icon: <FileText className="w-3.5 h-3.5" /> },
  { id: "market", label: "Market Scan", icon: <Radar className="w-3.5 h-3.5" /> },
  { id: "github", label: "GitHub Sync", icon: <GitBranch className="w-3.5 h-3.5" /> },
];

export function CommandCenterClient() {
  const [data, setData] = useState<CommandCenterData | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genSteps, setGenSteps] = useState<GenerateStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [draftCount, setDraftCount] = useState(0);
  const [scheduledCount, setScheduledCount] = useState(0);

  const load = async () => {
    try {
      const d = await api.commandCenter();
      setData(d);
      setTasks(d.tasks);
    } catch (e) {
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

  // Content pipeline: count drafts and scheduled items
  useEffect(() => {
    api.getDrafts("draft").then((d) => setDraftCount(d.length)).catch(() => {});
    api.getSchedule().then((s) => setScheduledCount(s.length)).catch(() => {});
  }, [data]);

  const updateStep = (id: string, status: GenerateStep["status"]) => {
    setGenSteps((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status } : s))
    );
  };

  const handleGenerateTasks = async () => {
    // Initialize steps
    setGenSteps(GENERATE_STEPS.map((s) => ({ ...s, status: "pending" as const })));
    setGenerating(true);

    try {
      // Fire off generate-all (all tasks run in background on backend)
      updateStep("tasks", "running");
      await api.generateAll();

      // Simulate steps by marking them running sequentially, then polling
      // The backend runs them in parallel, but we show progress as we detect results
      updateStep("suggestions", "running");
      updateStep("draft_tiktok", "running");
      updateStep("draft_youtube", "running");
      updateStep("briefing", "running");
      updateStep("market", "running");
      updateStep("github", "running");

      // Poll and check which results have appeared
      const startTaskCount = tasks.length;
      for (let attempt = 0; attempt < 20; attempt++) {
        await new Promise((r) => setTimeout(r, 3000));

        try {
          // Check tasks
          const taskResp = await api.getTasks();
          const aiTasks = taskResp.filter((t) => t.ai_generated && t.status === "pending");
          if (aiTasks.length > 0) updateStep("tasks", "done");

          // Check suggestions
          const ccData = await api.commandCenter();
          if (ccData.suggestions.length > 4) updateStep("suggestions", "done");

          // Check drafts
          const drafts = await api.getDrafts();
          const aiDrafts = drafts.filter((d) => d.ai_generated);
          const hasTiktok = aiDrafts.some((d) => d.platform === "tiktok");
          const hasYoutube = aiDrafts.some((d) => d.platform === "youtube");
          if (hasTiktok) updateStep("draft_tiktok", "done");
          if (hasYoutube) updateStep("draft_youtube", "done");

          // Check schedule
          const schedule = await api.getSchedule();
          if (schedule.length > 0) updateStep("schedule", "done");

          // Check briefing
          if (ccData.briefing && ccData.briefing.length > 0) updateStep("briefing", "done");

          // Check market gaps
          const gaps = await api.getMarketGaps();
          if (gaps.length > 0) updateStep("market", "done");

          // Check github
          const repos = await api.getRepos();
          if (repos.length > 0 && repos.some((r) => r.last_commit_sha)) {
            updateStep("github", "done");
          }

          // Update command center data
          setData(ccData);
          setTasks(ccData.tasks);

          // Check if everything is done
          const currentSteps = await new Promise<GenerateStep[]>((resolve) => {
            setGenSteps((prev) => { resolve(prev); return prev; });
          });
          const allDone = currentSteps.every((s) => s.status === "done");
          if (allDone) break;
        } catch {
          // keep polling
        }
      }

      // Mark any remaining running steps as done (timeout)
      setGenSteps((prev) =>
        prev.map((s) => s.status === "running" || s.status === "pending" ? { ...s, status: "done" } : s)
      );

      // Final refresh
      try {
        const d = await api.commandCenter();
        setData(d);
        setTasks(d.tasks);
      } catch { /* silent */ }

      // Keep the bar visible for a moment, then hide
      setTimeout(() => {
        setGenerating(false);
        setGenSteps([]);
      }, 2000);
    } catch {
      setGenSteps((prev) =>
        prev.map((s) => s.status !== "done" ? { ...s, status: "error" } : s)
      );
      setTimeout(() => {
        setGenerating(false);
        setGenSteps([]);
      }, 3000);
    }
  };

  const handleTaskComplete = (id: number) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  };

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          <span className="text-body-sm text-[var(--muted-foreground)]">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-5">
        <div className="text-subtitle text-pink-400">{error}</div>
        <button
          onClick={load}
          className="btn-pill btn-pill-primary flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  // --- Compute useful stats ---

  // Focus time: total estimated hours across active tasks
  const totalMinutes = tasks.reduce((sum, t) => sum + (t.estimated_minutes || 0), 0);
  const focusHours = totalMinutes >= 60
    ? `${(totalMinutes / 60).toFixed(1)}h`
    : `${totalMinutes}m`;
  // Weekly goal progress: how many weekly goals are >=50% done
  const weekOnTrack = data.goals_week.filter((g) => g.progress >= 0.5).length;
  const weekTotal = data.goals_week.length;
  const weekPct = weekTotal > 0
    ? Math.round(data.goals_week.reduce((s, g) => s + g.progress, 0) / weekTotal * 100)
    : 0;

  // Blockers: count projects with active blockers
  const blockedProjects = data.projects.filter((p) => p.blockers);
  const firstBlocker = blockedProjects[0];

  return (
    <div className="p-4 sm:p-6 lg:p-10 space-y-6 sm:space-y-8">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h1 className="text-heading text-white">
            Command Center
          </h1>
          <p className="text-body text-[var(--muted-foreground)] mt-1">{today}</p>
        </div>
        <button
          onClick={load}
          className="btn-pill btn-pill-outline flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-5">
        <StatCard
          label="Focus Time"
          value={tasks.length > 0 ? focusHours : "—"}
          gradient="bg-gradient-to-br from-purple-600 via-purple-700 to-violet-800"
          icon={Clock}
          subtitle={tasks.length > 0 ? `${tasks.length} tasks queued` : "No tasks yet — hit AI Generate"}
        />
        <StatCard
          label="Content Pipeline"
          value={String(draftCount + scheduledCount)}
          gradient="bg-gradient-to-br from-cyan-600 via-cyan-700 to-blue-800"
          icon={FileText}
          subtitle={`${draftCount} drafts to review · ${scheduledCount} scheduled`}
        />
        <StatCard
          label="Weekly Goals"
          value={weekTotal > 0 ? `${weekPct}%` : "—"}
          gradient="bg-gradient-to-br from-pink-600 via-pink-700 to-rose-800"
          icon={Target}
          subtitle={weekTotal > 0 ? `${weekOnTrack} of ${weekTotal} on track` : "No weekly goals set"}
        />
        <StatCard
          label="Blockers"
          value={String(blockedProjects.length)}
          gradient={blockedProjects.length > 0
            ? "bg-gradient-to-br from-amber-600 via-amber-700 to-orange-800"
            : "bg-gradient-to-br from-emerald-600 via-emerald-700 to-green-800"}
          icon={AlertTriangle}
          subtitle={firstBlocker
            ? `${firstBlocker.name}: ${firstBlocker.blockers!.slice(0, 38)}${firstBlocker.blockers!.length > 38 ? "…" : ""}`
            : "All clear — no blockers"}
        />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* LEFT */}
        <div className="space-y-8">
          {/* Tasks */}
          <section>
            <SectionHeader
              title={`Priority Tasks (${tasks.length})`}
              glow
              action={
                <button
                  onClick={handleGenerateTasks}
                  disabled={generating}
                  className="btn-pill btn-pill-primary flex items-center gap-2 disabled:opacity-50"
                >
                  {generating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Brain className="w-4 h-4" />
                  )}
                  {generating ? "Generating..." : "AI Generate"}
                </button>
              }
            />
            <div className="space-y-3">
              <AnimatePresence initial={false}>
                {tasks.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="py-12 text-center elevated-card rounded-2xl"
                  >
                    <Brain className="w-12 h-12 text-purple-400/30 mx-auto mb-4" />
                    <p className="text-body text-[var(--muted-foreground)]">
                      All clear. Hit{" "}
                      <span className="text-purple-400 font-semibold">AI Generate</span> to get
                      Claude to prioritize your day.
                    </p>
                  </motion.div>
                ) : (
                  tasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onComplete={handleTaskComplete}
                    />
                  ))
                )}
              </AnimatePresence>
            </div>
          </section>

          {/* Goals */}
          <section>
            <SectionHeader title="Goals" />
            <div className="elevated-card rounded-2xl p-6">
              <GoalsPanel
                week={data.goals_week}
                month={data.goals_month}
                quarter={data.goals_quarter}
              />
            </div>
          </section>

          {/* Projects */}
          <section>
            <SectionHeader title="Projects" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {data.projects.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>
          </section>
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="space-y-8">
          <section>
            <SectionHeader
              title="AI Suggestions"
              action={
                <Sparkles className="w-4 h-4 text-purple-400 animate-pulse" />
              }
            />
            <SuggestionsPanel suggestions={data.suggestions} />
          </section>

          <section>
            <SectionHeader title="Today's Briefing" />
            <BriefingPanel items={data.briefing} />
          </section>
        </div>
      </div>

      {/* AI Generate progress bar — fixed bottom */}
      <AnimatePresence>
        {generating && genSteps.length > 0 && (
          <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed bottom-0 left-0 right-0 z-50"
          >
            <div className="mx-auto max-w-[900px] mb-6 px-4">
              <div className="rounded-2xl bg-[#111118]/95 backdrop-blur-xl border border-white/[0.08] shadow-2xl shadow-purple-500/10 p-4">
                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                    <span className="text-body-sm font-semibold text-white">
                      AI Generate
                    </span>
                  </div>
                  <span className="text-caption text-[var(--muted-foreground)]">
                    {genSteps.filter((s) => s.status === "done").length}/{genSteps.length} complete
                  </span>
                </div>

                {/* Progress bar */}
                <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden mb-3">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500"
                    initial={{ width: "0%" }}
                    animate={{
                      width: `${(genSteps.filter((s) => s.status === "done").length / genSteps.length) * 100}%`,
                    }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                  />
                </div>

                {/* Steps */}
                <div className="flex items-center gap-1 flex-wrap">
                  {genSteps.map((step) => (
                    <div
                      key={step.id}
                      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
                        step.status === "done"
                          ? "bg-emerald-500/15 text-emerald-400"
                          : step.status === "running"
                            ? "bg-purple-500/15 text-purple-300"
                            : step.status === "error"
                              ? "bg-red-500/15 text-red-400"
                              : "bg-white/[0.03] text-[var(--muted-foreground)]"
                      }`}
                    >
                      {step.status === "done" ? (
                        <Check className="w-3 h-3" />
                      ) : step.status === "running" ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        step.icon
                      )}
                      {step.label}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
