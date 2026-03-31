"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Zap,
  Loader2,
  Plus,
  X,
  ArrowRight,
  Sparkles,
  Target,
  Layers,
  Brain,
} from "lucide-react";

interface ProjectInput {
  name: string;
  description: string;
  github_repo: string;
  color: string;
}

interface GoalInput {
  title: string;
  timeframe: "week" | "month" | "quarter";
}

const PROJECT_COLORS = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ec4899", "#06b6d4"];

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<"intro" | "projects" | "goals" | "llm" | "done">("intro");
  const [projects, setProjects] = useState<ProjectInput[]>([
    { name: "", description: "", github_repo: "", color: PROJECT_COLORS[0] },
  ]);
  const [goals, setGoals] = useState<GoalInput[]>([
    { title: "", timeframe: "week" },
  ]);
  const [llmPaste, setLlmPaste] = useState("");
  const [llmParsing, setLlmParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const addProject = () => {
    setProjects([
      ...projects,
      { name: "", description: "", github_repo: "", color: PROJECT_COLORS[projects.length % PROJECT_COLORS.length] },
    ]);
  };

  const removeProject = (i: number) => {
    setProjects(projects.filter((_, idx) => idx !== i));
  };

  const updateProject = (i: number, field: keyof ProjectInput, value: string) => {
    const updated = [...projects];
    updated[i] = { ...updated[i], [field]: value };
    setProjects(updated);
  };

  const addGoal = () => {
    setGoals([...goals, { title: "", timeframe: "week" }]);
  };

  const removeGoal = (i: number) => {
    setGoals(goals.filter((_, idx) => idx !== i));
  };

  const updateGoal = (i: number, field: keyof GoalInput, value: string) => {
    const updated = [...goals];
    updated[i] = { ...updated[i], [field]: value };
    setGoals(updated);
  };

  const parseLLMPaste = async () => {
    if (!llmPaste.trim()) return;
    setLlmParsing(true);
    setError("");

    try {
      const res = await fetch(`${API}/onboarding/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: llmPaste }),
      });

      if (!res.ok) throw new Error("Failed to parse");

      const data = await res.json();

      if (data.projects?.length) {
        setProjects(data.projects.map((p: any, i: number) => ({
          name: p.name || "",
          description: p.description || "",
          github_repo: p.github_repo || "",
          color: PROJECT_COLORS[i % PROJECT_COLORS.length],
        })));
      }

      if (data.goals?.length) {
        setGoals(data.goals.map((g: any) => ({
          title: g.title || "",
          timeframe: g.timeframe || "week",
        })));
      }

      setStep("projects");
    } catch (e) {
      setError("Couldn't parse the text. Try adding projects manually.");
    } finally {
      setLlmParsing(false);
    }
  };

  const handleFinish = async () => {
    setSaving(true);
    setError("");

    try {
      // Create projects
      const validProjects = projects.filter((p) => p.name.trim());
      for (const p of validProjects) {
        const slug = p.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        await fetch(`${API}/projects/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: p.name,
            slug,
            description: p.description,
            github_repo: p.github_repo || "",
            color: p.color,
            current_stage: 0,
            total_stages: 5,
            stage_label: "Getting started",
            next_milestone: "",
          }),
        });
      }

      // Create goals
      const validGoals = goals.filter((g) => g.title.trim());
      for (const g of validGoals) {
        const projectSlug = validProjects[0]
          ? validProjects[0].name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")
          : "";
        await fetch(`${API}/goals/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: g.title,
            timeframe: g.timeframe,
            progress: 0.0,
            project_slug: projectSlug,
          }),
        });
      }

      setStep("done");

      // Trigger AI Generate to populate tasks/suggestions/briefing
      fetch(`${API}/ai/generate-all`, { method: "POST" }).catch(() => {});

      setTimeout(() => router.push("/dashboard"), 2000);
    } catch (e) {
      setError("Failed to save. Check your connection.");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#0A0A0B] overflow-y-auto z-[60]">
      <div className="max-w-2xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl gradient-purple shadow-[0_0_24px_rgba(168,85,247,0.3)] mb-4">
            <Zap className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Set Up Your Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Tell us what you're building so Claude can prioritize your day.
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-10">
          {["intro", "projects", "goals"].map((s, i) => (
            <div
              key={s}
              className={`h-1.5 rounded-full transition-all ${
                ["intro", "projects", "goals", "llm", "done"].indexOf(step) >= i
                  ? "w-10 bg-purple-500"
                  : "w-6 bg-white/10"
              }`}
            />
          ))}
        </div>

        {/* Intro step */}
        {step === "intro" && (
          <div className="space-y-6">
            <div className="elevated-card rounded-2xl p-8 text-center">
              <Brain className="w-12 h-12 text-purple-400/50 mx-auto mb-4" />
              <h2 className="text-lg font-semibold text-white mb-2">How would you like to start?</h2>
              <p className="text-sm text-[var(--muted-foreground)] mb-8">
                Add your projects and goals manually, or paste context from another AI conversation.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button
                  onClick={() => setStep("projects")}
                  className="p-6 rounded-xl border border-white/10 hover:border-purple-500/40 hover:bg-purple-500/5 transition-all text-left"
                >
                  <Layers className="w-8 h-8 text-purple-400 mb-3" />
                  <h3 className="text-sm font-semibold text-white mb-1">Add Manually</h3>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Type in your projects and goals one by one.
                  </p>
                </button>

                <button
                  onClick={() => setStep("llm")}
                  className="p-6 rounded-xl border border-white/10 hover:border-cyan-500/40 hover:bg-cyan-500/5 transition-all text-left"
                >
                  <Sparkles className="w-8 h-8 text-cyan-400 mb-3" />
                  <h3 className="text-sm font-semibold text-white mb-1">Paste from AI</h3>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Paste a ChatGPT/Claude conversation about your projects. We'll extract the details.
                  </p>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* LLM paste step */}
        {step === "llm" && (
          <div className="space-y-6">
            <div className="elevated-card rounded-2xl p-6">
              <h2 className="text-lg font-semibold text-white mb-2">Paste Your Context</h2>
              <p className="text-sm text-[var(--muted-foreground)] mb-4">
                Paste any text that describes your projects, goals, timeline, or strategy.
                Claude will extract the structured data.
              </p>
              <textarea
                value={llmPaste}
                onChange={(e) => setLlmPaste(e.target.value)}
                placeholder={"Example:\n\nI'm building mesh2param, a mesh-to-parametric CAD SaaS. Currently in stage 3 (surface segmentation). My main blocker is edge classification on curved surfaces.\n\nI'm also making AI automation content on TikTok. Goal is to reach 10K followers this quarter.\n\nThis week I need to finish the prototype and film 3 short videos..."}
                className="w-full h-48 bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-white placeholder:text-[var(--muted-foreground)]/50 focus:outline-none focus:border-purple-500/50 resize-none"
              />
              {error && <p className="text-sm text-red-400 mt-2">{error}</p>}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep("intro")}
                className="px-6 py-3 rounded-xl border border-white/10 text-[var(--muted-foreground)] hover:text-white transition-colors text-sm"
              >
                Back
              </button>
              <button
                onClick={parseLLMPaste}
                disabled={llmParsing || !llmPaste.trim()}
                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 transition-all disabled:opacity-50 text-sm"
              >
                {llmParsing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                {llmParsing ? "Parsing..." : "Extract Projects & Goals"}
              </button>
            </div>
          </div>
        )}

        {/* Projects step */}
        {step === "projects" && (
          <div className="space-y-6">
            <div className="elevated-card rounded-2xl p-6">
              <h2 className="text-lg font-semibold text-white mb-1">Your Projects</h2>
              <p className="text-sm text-[var(--muted-foreground)] mb-6">
                What are you building? Claude uses this to generate relevant tasks and content.
              </p>

              <div className="space-y-4">
                {projects.map((p, i) => (
                  <div key={i} className="rounded-xl bg-[#111118] border border-white/[0.06] p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: p.color }}
                        />
                        <span className="text-xs text-[var(--muted-foreground)]">Project {i + 1}</span>
                      </div>
                      {projects.length > 1 && (
                        <button onClick={() => removeProject(i)} className="text-[var(--muted-foreground)] hover:text-red-400">
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                    <input
                      type="text"
                      value={p.name}
                      onChange={(e) => updateProject(i, "name", e.target.value)}
                      placeholder="Project name (e.g. mesh2param)"
                      className="w-full bg-transparent border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
                    />
                    <input
                      type="text"
                      value={p.description}
                      onChange={(e) => updateProject(i, "description", e.target.value)}
                      placeholder="Short description (e.g. Mesh-to-CAD reverse engineering SaaS)"
                      className="w-full bg-transparent border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
                    />
                    <input
                      type="text"
                      value={p.github_repo}
                      onChange={(e) => updateProject(i, "github_repo", e.target.value)}
                      placeholder="GitHub repo name (optional)"
                      className="w-full bg-transparent border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
                    />
                  </div>
                ))}
              </div>

              <button
                onClick={addProject}
                className="flex items-center gap-2 mt-4 text-sm text-purple-400 hover:text-purple-300"
              >
                <Plus className="w-4 h-4" /> Add another project
              </button>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep("intro")}
                className="px-6 py-3 rounded-xl border border-white/10 text-[var(--muted-foreground)] hover:text-white transition-colors text-sm"
              >
                Back
              </button>
              <button
                onClick={() => setStep("goals")}
                disabled={!projects.some((p) => p.name.trim())}
                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 transition-all disabled:opacity-50 text-sm"
              >
                Next: Goals
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Goals step */}
        {step === "goals" && (
          <div className="space-y-6">
            <div className="elevated-card rounded-2xl p-6">
              <h2 className="text-lg font-semibold text-white mb-1">Your Goals</h2>
              <p className="text-sm text-[var(--muted-foreground)] mb-6">
                What do you want to achieve? These drive your AI-generated priorities.
              </p>

              <div className="space-y-3">
                {goals.map((g, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Target className="w-4 h-4 text-pink-400 shrink-0" />
                    <input
                      type="text"
                      value={g.title}
                      onChange={(e) => updateGoal(i, "title", e.target.value)}
                      placeholder="e.g. Reach 1,000 waitlist signups"
                      className="flex-1 bg-[#111118] border border-white/[0.06] rounded-lg px-3 py-2.5 text-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
                    />
                    <select
                      value={g.timeframe}
                      onChange={(e) => updateGoal(i, "timeframe", e.target.value)}
                      className="bg-[#111118] border border-white/[0.06] rounded-lg px-2 py-2.5 text-xs text-white focus:outline-none"
                    >
                      <option value="week">This Week</option>
                      <option value="month">This Month</option>
                      <option value="quarter">This Quarter</option>
                    </select>
                    {goals.length > 1 && (
                      <button onClick={() => removeGoal(i)} className="text-[var(--muted-foreground)] hover:text-red-400">
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <button
                onClick={addGoal}
                className="flex items-center gap-2 mt-4 text-sm text-purple-400 hover:text-purple-300"
              >
                <Plus className="w-4 h-4" /> Add another goal
              </button>
            </div>

            {error && <p className="text-sm text-red-400 text-center">{error}</p>}

            <div className="flex gap-3">
              <button
                onClick={() => setStep("projects")}
                className="px-6 py-3 rounded-xl border border-white/10 text-[var(--muted-foreground)] hover:text-white transition-colors text-sm"
              >
                Back
              </button>
              <button
                onClick={handleFinish}
                disabled={saving}
                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 transition-all disabled:opacity-50 text-sm"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                {saving ? "Setting up..." : "Launch Dashboard"}
              </button>
            </div>
          </div>
        )}

        {/* Done step */}
        {step === "done" && (
          <div className="elevated-card rounded-2xl p-12 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-8 h-8 text-emerald-400" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">You're all set!</h2>
            <p className="text-sm text-[var(--muted-foreground)]">
              Claude is generating your first tasks, content drafts, and daily briefing...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
