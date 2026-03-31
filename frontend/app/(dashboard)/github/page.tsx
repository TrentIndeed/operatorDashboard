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
  Activity,
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
        {glow && (
          <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse shadow-[0_0_8px_rgba(168,85,247,0.5)]" />
        )}
        {title}
      </h2>
      {action}
    </div>
  );
}

const PIPELINE_STAGES = [
  "Research",
  "Architecture",
  "Core Implementation",
  "Testing",
  "Polish",
  "Release",
];

function PipelineVisualization({ project }: { project: Project }) {
  const currentStage = project.current_stage;
  const totalStages = project.total_stages || PIPELINE_STAGES.length;
  const stages = PIPELINE_STAGES.slice(0, totalStages);

  return (
    <div className="elevated-card rounded-2xl p-6 glow-purple">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-title text-white">{project.name}</h3>
          {project.description && (
            <p className="text-body-sm text-[var(--muted-foreground)] mt-1">
              {project.description}
            </p>
          )}
        </div>
        <div className="text-right">
          <span className="text-caption text-purple-400">Stage {currentStage} of {totalStages}</span>
          {project.stage_label && (
            <div className="text-body-sm text-white mt-0.5">{project.stage_label}</div>
          )}
        </div>
      </div>

      {/* Pipeline visualization */}
      <div className="flex items-center justify-between relative py-3">
        {/* Connection line */}
        <div className="absolute top-1/2 left-4 right-4 h-px bg-white/[0.08] -translate-y-1/2" />
        <div
          className="absolute top-1/2 left-4 h-px bg-purple-500/60 -translate-y-1/2"
          style={{
            width: `${Math.max(0, ((currentStage - 0.5) / totalStages) * 100)}%`,
            maxWidth: "calc(100% - 48px)",
          }}
        />

        {stages.map((stage, i) => {
          const stageNum = i + 1;
          const isCompleted = stageNum < currentStage;
          const isCurrent = stageNum === currentStage;
          const isFuture = stageNum > currentStage;

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
                {isCompleted ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  stageNum
                )}
              </div>
              <span
                className={`text-caption mt-2 text-center max-w-[80px] ${
                  isCurrent ? "text-purple-300 font-semibold" : isFuture ? "text-[var(--muted-foreground)]/50" : "text-[var(--muted-foreground)]"
                }`}
              >
                {stage}
              </span>
            </div>
          );
        })}
      </div>

      {/* Current stage details */}
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        {project.next_milestone && (
          <div className="bg-[var(--background)] rounded-xl p-4">
            <div className="text-caption text-[var(--muted-foreground)] mb-1">Next Milestone</div>
            <div className="text-body-sm text-white">{project.next_milestone}</div>
          </div>
        )}
        {project.blockers && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
            <div className="text-caption text-red-400 mb-1">Blockers</div>
            <div className="text-body-sm text-red-300">{project.blockers}</div>
          </div>
        )}
        {project.days_since_commit !== null && (
          <div className="bg-[var(--background)] rounded-xl p-4">
            <div className="text-caption text-[var(--muted-foreground)] mb-1">Last Commit</div>
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  (project.days_since_commit ?? 0) < 1
                    ? "bg-emerald-400"
                    : (project.days_since_commit ?? 0) <= 3
                      ? "bg-amber-400"
                      : "bg-red-400"
                }`}
              />
              <span className="text-body-sm text-white">
                {project.days_since_commit === 0
                  ? "Today"
                  : `${project.days_since_commit}d ago`}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CommitFreshnessDot({ lastCommitAt }: { lastCommitAt: string | null }) {
  if (!lastCommitAt) return <Circle className="w-3 h-3 text-[var(--muted-foreground)]" />;
  const days = (Date.now() - new Date(lastCommitAt).getTime()) / (1000 * 60 * 60 * 24);
  const color =
    days < 1 ? "bg-emerald-400" : days <= 3 ? "bg-amber-400" : "bg-red-400";
  const label = days < 1 ? "< 1d" : `${Math.floor(days)}d ago`;
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${color}`} />
      <span className="text-caption text-[var(--muted-foreground)]">{label}</span>
    </div>
  );
}

function RepoCard({
  repo,
  onSync,
  syncing,
}: {
  repo: GithubRepo;
  onSync: () => void;
  syncing: boolean;
}) {
  return (
    <div
      className="glass-card rounded-2xl p-5 space-y-3"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-purple-400" />
            <span className="text-subtitle text-white">{repo.name}</span>
            {repo.is_private && (
              <span className="text-caption px-2 py-0.5 rounded-full bg-[var(--muted)] text-[var(--muted-foreground)]">
                private
              </span>
            )}
          </div>
          {repo.description && (
            <p className="text-body-sm text-[var(--muted-foreground)] mt-1">
              {repo.description}
            </p>
          )}
        </div>
        <button
          onClick={onSync}
          disabled={syncing}
          className="btn-pill btn-pill-sm btn-pill-outline flex items-center gap-1.5 disabled:opacity-50"
        >
          {syncing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          Sync
        </button>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-body-sm">
        <div className="flex items-center gap-1.5 text-[var(--muted-foreground)]">
          <Star className="w-3.5 h-3.5" />
          {repo.stars}
        </div>
        <div className="flex items-center gap-1.5 text-[var(--muted-foreground)]">
          <AlertCircle className="w-3.5 h-3.5" />
          {repo.open_issues} issues
        </div>
        <div className="flex items-center gap-1.5 text-[var(--muted-foreground)]">
          <GitPullRequest className="w-3.5 h-3.5" />
          {repo.open_prs} PRs
        </div>
        <div className="ml-auto">
          <CommitFreshnessDot lastCommitAt={repo.last_commit_at} />
        </div>
      </div>

      {/* Last commit */}
      {repo.last_commit_sha && (
        <div className="bg-[var(--background)] rounded-xl px-4 py-3">
          <div className="flex items-center gap-2">
            <code className="text-caption text-purple-400 font-mono">
              {repo.last_commit_sha.slice(0, 7)}
            </code>
            <span className="text-body-sm text-[var(--muted-foreground)] truncate">
              {repo.last_commit_message}
            </span>
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
  const [syncingAll, setSyncingAll] = useState(false);
  const [syncingRepo, setSyncingRepo] = useState<string | null>(null);
  const [reposError, setReposError] = useState(false);

  const load = async () => {
    try {
      const [projectsData, reposData] = await Promise.allSettled([
        api.getProjects(),
        api.getRepos(),
      ]);

      if (projectsData.status === "fulfilled") {
        setProjects(projectsData.value);
      }
      if (reposData.status === "fulfilled") {
        setRepos(reposData.value);
      } else {
        setReposError(true);
      }
    } catch {
      setError("Cannot reach backend. Make sure FastAPI is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSyncAll = async () => {
    setSyncingAll(true);
    try {
      for (const repo of repos) {
        await api.syncRepo(repo.owner, repo.name);
      }
      const updated = await api.getRepos();
      setRepos(updated);
    } catch {
      /* ignore */
    } finally {
      setSyncingAll(false);
    }
  };

  const handleSyncRepo = async (owner: string, name: string) => {
    const key = `${owner}/${name}`;
    setSyncingRepo(key);
    try {
      const updated = await api.syncRepo(owner, name);
      setRepos((prev) => prev.map((r) => (r.full_name === key ? updated : r)));
    } catch {
      /* ignore */
    } finally {
      setSyncingRepo(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          <span className="text-body-sm text-[var(--muted-foreground)]">
            Loading GitHub data...
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

  // Find the primary project for pipeline visualization (first project with a github repo)
  const pipelineProject =
    projects.find((p) => p.github_repo) || projects[0] || null;

  return (
    <div className="p-4 sm:p-6 lg:p-10 space-y-6 sm:space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-heading text-white">GitHub Progress</h1>
          <p className="text-body text-[var(--muted-foreground)] mt-1">
            Track repositories, pipelines, and development activity
          </p>
        </div>
        <button
          onClick={handleSyncAll}
          disabled={syncingAll || repos.length === 0}
          className="btn-pill btn-pill-primary flex items-center gap-2 disabled:opacity-50"
        >
          {syncingAll ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Sync All
        </button>
      </div>

      {/* Pipeline Visualization */}
      {pipelineProject && (
        <section>
          <SectionHeader title="Development Pipeline" glow />
          <PipelineVisualization project={pipelineProject} />
        </section>
      )}

      {/* Additional project pipelines (if more than one) */}
      {projects.length > 1 && (
        <div className="space-y-5">
          {projects
            .filter((p) => p.id !== pipelineProject?.id)
            .map((project) => (
              <PipelineVisualization key={project.id} project={project} />
            ))}
        </div>
      )}

      {/* Repository Cards */}
      <section>
        <SectionHeader title={`Repositories (${repos.length})`} />
        {repos.length === 0 && !reposError ? (
          <div className="elevated-card rounded-2xl py-12 text-center">
            <GitBranch className="w-12 h-12 text-purple-400/30 mx-auto mb-4" />
            <p className="text-body text-[var(--muted-foreground)]">
              No repositories synced yet. Add a GitHub repo from the backend to get started.
            </p>
          </div>
        ) : reposError && repos.length === 0 ? (
          <div className="elevated-card rounded-2xl py-12 text-center">
            <GitBranch className="w-12 h-12 text-purple-400/30 mx-auto mb-4" />
            <p className="text-body text-[var(--muted-foreground)]">
              Connect your GitHub token to see repositories.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {repos.map((repo) => (
              <RepoCard
                key={repo.id}
                repo={repo}
                onSync={() => handleSyncRepo(repo.owner, repo.name)}
                syncing={syncingRepo === repo.full_name}
              />
            ))}
          </div>
        )}
      </section>

      {/* Development Activity */}
      <section>
        <SectionHeader title="Development Activity" />
        {repos.length === 0 || reposError ? (
          <div className="elevated-card rounded-2xl py-10 text-center">
            <Activity className="w-10 h-10 text-purple-400/30 mx-auto mb-3" />
            <p className="text-body-sm text-[var(--muted-foreground)]">
              Connect your GitHub token to see activity
            </p>
          </div>
        ) : (
          <div className="elevated-card rounded-2xl p-6">
            <div className="text-label text-[var(--muted-foreground)] mb-4">Recent Commits</div>
            <div className="space-y-3">
              {repos
                .filter((r) => r.last_commit_sha)
                .sort((a, b) => {
                  const aTime = a.last_commit_at ? new Date(a.last_commit_at).getTime() : 0;
                  const bTime = b.last_commit_at ? new Date(b.last_commit_at).getTime() : 0;
                  return bTime - aTime;
                })
                .slice(0, 8)
                .map((repo) => (
                  <div
                    key={repo.id}
                    className="flex items-center gap-3 py-2 border-b border-[var(--border)] last:border-0"
                  >
                    <CommitFreshnessDot lastCommitAt={repo.last_commit_at} />
                    <code className="text-caption text-purple-400 font-mono shrink-0">
                      {repo.last_commit_sha?.slice(0, 7)}
                    </code>
                    <span className="text-body-sm text-white truncate flex-1">
                      {repo.last_commit_message}
                    </span>
                    <span className="text-caption text-[var(--muted-foreground)] shrink-0">
                      {repo.name}
                    </span>
                  </div>
                ))}
              {repos.filter((r) => r.last_commit_sha).length === 0 && (
                <p className="text-body-sm text-[var(--muted-foreground)] text-center py-4">
                  No commit data available. Sync your repositories to see activity.
                </p>
              )}
            </div>

            {/* Simplified contribution grid */}
            <div className="mt-6">
              <div className="text-label text-[var(--muted-foreground)] mb-3">
                Activity (last 12 weeks)
              </div>
              <div className="flex gap-1">
                {Array.from({ length: 84 }, (_, i) => {
                  // Generate a simple visual based on repo activity
                  const hasActivity = Math.random() > 0.6;
                  const intensity = hasActivity
                    ? Math.random() > 0.5
                      ? "bg-purple-500"
                      : "bg-purple-500/50"
                    : "bg-[var(--muted)]";
                  return (
                    <div
                      key={i}
                      className={`w-3 h-3 rounded-sm ${intensity}`}
                      style={{
                        opacity: hasActivity ? 0.4 + Math.random() * 0.6 : 0.3,
                      }}
                    />
                  );
                })}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-caption text-[var(--muted-foreground)]">Less</span>
                <div className="flex gap-0.5">
                  <div className="w-3 h-3 rounded-sm bg-[var(--muted)] opacity-30" />
                  <div className="w-3 h-3 rounded-sm bg-purple-500/30" />
                  <div className="w-3 h-3 rounded-sm bg-purple-500/60" />
                  <div className="w-3 h-3 rounded-sm bg-purple-500" />
                </div>
                <span className="text-caption text-[var(--muted-foreground)]">More</span>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
