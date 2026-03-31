"use client";

import { useEffect, useState } from "react";
import { api, Project, GithubRepo } from "@/lib/api";
import {
  GitBranch,
  RefreshCw,
  Loader2,
  Star,
  AlertCircle,
  GitPullRequest,
  CheckCircle2,
  Circle,
  Clock,
} from "lucide-react";

function SectionHeader({
  title,
  glow,
  action,
}: {
  title: string;
  glow?: boolean;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-5">
      <h2 className="text-label text-[var(--muted-foreground)] flex items-center gap-2">
        {glow && (
          <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
        )}
        {title}
      </h2>
      {action}
    </div>
  );
}

function PipelineVisualization({ project }: { project: Project }) {
  const totalStages = project.total_stages || 6;
  const currentStage = project.current_stage || 0;

  const stages = Array.from({ length: totalStages }, (_, i) => `Stage ${i + 1}`);

  return (
    <div className="elevated-card rounded-2xl p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-subtitle text-white">{project.name}</h3>
          {project.description && (
            <p className="text-body-sm text-[var(--muted-foreground)] mt-1">
              {project.description}
            </p>
          )}
        </div>
        <div className="text-right">
          <span className="text-caption text-purple-400">
            Stage {currentStage} of {totalStages}
          </span>
          {project.stage_label && (
            <div className="text-body-sm text-white mt-0.5">
              {project.stage_label}
            </div>
          )}
        </div>
      </div>

      {/* Pipeline */}
      <div className="flex items-center justify-between relative py-3">
        <div className="absolute top-1/2 left-4 right-4 h-px bg-white/[0.08] -translate-y-1/2" />
        <div
          className="absolute top-1/2 left-4 h-px bg-purple-500/60 -translate-y-1/2"
          style={{
            width: `${Math.max(0, ((currentStage - 0.5) / totalStages) * 100)}%`,
            maxWidth: "calc(100% - 32px)",
          }}
        />
        {stages.map((stage, i) => {
          const stageNum = i + 1;
          const isCompleted = stageNum < currentStage;
          const isCurrent = stageNum === currentStage;
          return (
            <div key={stage} className="relative z-10 flex flex-col items-center" style={{ flex: 1 }}>
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold ${
                  isCompleted
                    ? "bg-emerald-500 text-white"
                    : isCurrent
                      ? "bg-purple-500 text-white"
                      : "bg-white/[0.08] text-[var(--muted-foreground)]"
                }`}
              >
                {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5" /> : stageNum}
              </div>
            </div>
          );
        })}
      </div>

      {/* Blockers / Next milestone */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
        {project.blockers && (
          <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-3">
            <div className="text-caption text-red-400 mb-1">Blockers</div>
            <div className="text-body-sm text-red-300">{project.blockers}</div>
          </div>
        )}
        {project.next_milestone && (
          <div className="bg-purple-500/5 border border-purple-500/10 rounded-xl p-3">
            <div className="text-caption text-purple-400 mb-1">Next Milestone</div>
            <div className="text-body-sm text-white">{project.next_milestone}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function RepoCard({ repo }: { repo: GithubRepo }) {
  const daysAgo = repo.last_commit_at
    ? Math.round((Date.now() - new Date(repo.last_commit_at).getTime()) / 86400000)
    : null;

  const freshness =
    daysAgo === null ? "text-[var(--muted-foreground)]"
    : daysAgo < 1 ? "text-emerald-400"
    : daysAgo <= 3 ? "text-amber-400"
    : daysAgo <= 7 ? "text-orange-400"
    : "text-red-400";

  const dotColor =
    daysAgo === null ? "bg-[var(--muted-foreground)]"
    : daysAgo < 1 ? "bg-emerald-400"
    : daysAgo <= 3 ? "bg-amber-400"
    : daysAgo <= 7 ? "bg-orange-400"
    : "bg-red-400";

  return (
    <div className="glass-card rounded-2xl p-5 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-purple-400" />
            <span className="text-subtitle text-white">{repo.name}</span>
            {repo.is_private && (
              <span className="text-caption px-2 py-0.5 rounded-full bg-white/[0.06] text-[var(--muted-foreground)]">
                private
              </span>
            )}
          </div>
          {repo.description && (
            <p className="text-body-sm text-[var(--muted-foreground)] mt-1 line-clamp-1">
              {repo.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${dotColor}`} />
          <span className={`text-caption ${freshness}`}>
            {daysAgo === null ? "—" : daysAgo === 0 ? "today" : `${daysAgo}d`}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-body-sm text-[var(--muted-foreground)]">
        <span className="flex items-center gap-1"><Star className="w-3 h-3" />{repo.stars}</span>
        <span className="flex items-center gap-1"><AlertCircle className="w-3 h-3" />{repo.open_issues}</span>
        <span className="flex items-center gap-1"><GitPullRequest className="w-3 h-3" />{repo.open_prs}</span>
      </div>

      {repo.last_commit_sha && (
        <div className="bg-[var(--background)] rounded-xl px-4 py-2.5">
          <div className="flex items-center gap-2">
            <code className="text-caption text-purple-400 font-mono">{repo.last_commit_sha.slice(0, 7)}</code>
            <span className="text-body-sm text-[var(--muted-foreground)] truncate">{repo.last_commit_message}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Page() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [repos, setRepos] = useState<GithubRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const load = async () => {
    try {
      const [projectsData, reposData] = await Promise.allSettled([
        api.getProjects(),
        api.getRepos(),
      ]);
      if (projectsData.status === "fulfilled") setProjects(projectsData.value);
      if (reposData.status === "fulfilled") setRepos(reposData.value);
    } catch {
      setError("Cannot reach backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.syncAllRepos();
      // Wait a bit for sync to complete then refresh
      setTimeout(async () => {
        await load();
        setSyncing(false);
      }, 5000);
    } catch {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
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

  // Split repos: active (committed in last 14 days) vs inactive
  const activeRepos = repos
    .filter((r) => {
      if (!r.last_commit_at) return false;
      const days = (Date.now() - new Date(r.last_commit_at).getTime()) / 86400000;
      return days <= 14;
    })
    .sort((a, b) => new Date(b.last_commit_at!).getTime() - new Date(a.last_commit_at!).getTime());

  const inactiveRepos = repos
    .filter((r) => {
      if (!r.last_commit_at) return true;
      const days = (Date.now() - new Date(r.last_commit_at).getTime()) / 86400000;
      return days > 14;
    });

  // Projects with github repos get pipeline visualization
  const linkedProjects = projects.filter((p) => p.github_repo && repos.some((r) => r.name === p.github_repo));

  return (
    <div className="p-4 sm:p-6 lg:p-10 space-y-6 sm:space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h1 className="text-heading text-white">GitHub Progress</h1>
          <p className="text-body text-[var(--muted-foreground)] mt-1">
            {activeRepos.length} active repos · {repos.length} total
          </p>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-pill btn-pill-outline flex items-center gap-2 disabled:opacity-50"
        >
          {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {syncing ? "Syncing..." : "Sync All"}
        </button>
      </div>

      {/* Project Pipelines */}
      {linkedProjects.length > 0 && (
        <section>
          <SectionHeader title="Project Pipelines" glow />
          <div className="space-y-5">
            {linkedProjects.map((p) => (
              <PipelineVisualization key={p.id} project={p} />
            ))}
          </div>
        </section>
      )}

      {/* Active Repos */}
      <section>
        <SectionHeader
          title={`Active (${activeRepos.length})`}
          action={
            <span className="text-caption text-[var(--muted-foreground)]">committed in last 14 days</span>
          }
        />
        {activeRepos.length === 0 ? (
          <div className="elevated-card rounded-2xl py-12 text-center">
            <Clock className="w-10 h-10 text-purple-400/30 mx-auto mb-3" />
            <p className="text-body text-[var(--muted-foreground)]">
              No recent activity. Push some code!
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {activeRepos.map((r) => (
              <RepoCard key={r.id} repo={r} />
            ))}
          </div>
        )}
      </section>

      {/* Inactive Repos */}
      {inactiveRepos.length > 0 && (
        <section>
          <SectionHeader title={`Inactive (${inactiveRepos.length})`} />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            {inactiveRepos.map((r) => (
              <div key={r.id} className="glass-card rounded-xl p-4 opacity-50">
                <div className="flex items-center gap-2">
                  <GitBranch className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                  <span className="text-body-sm text-[var(--muted-foreground)]">{r.name}</span>
                  {r.last_commit_at && (
                    <span className="text-caption text-[var(--muted-foreground)] ml-auto">
                      {Math.round((Date.now() - new Date(r.last_commit_at).getTime()) / 86400000)}d ago
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
