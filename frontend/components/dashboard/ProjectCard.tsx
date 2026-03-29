import { Project } from "@/lib/api";
import { GitBranch, AlertTriangle, ArrowRight } from "lucide-react";

const COLOR_TO_GRADIENT: Record<string, string> = {
  "#3b82f6": "from-blue-500 to-cyan-400",
  "#8b5cf6": "from-purple-500 to-pink-400",
  "#10b981": "from-emerald-500 to-teal-400",
  "#f59e0b": "from-amber-500 to-orange-400",
};

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  // A project is "connected" only if it has a repo AND that repo has been synced (has commit data)
  const isConnected = !!project.github_repo && project.last_commit_at != null;
  const progressPct = isConnected ? Math.round((project.current_stage / project.total_stages) * 100) : null;
  const gradient = COLOR_TO_GRADIENT[project.color] ?? "from-purple-500 to-pink-400";

  return (
    <div className="group p-5 rounded-2xl glass-card transition-all">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-3.5 h-3.5 rounded-full bg-gradient-to-r ${gradient} shrink-0 shadow-[0_0_8px_rgba(168,85,247,0.3)]`} />
          <div>
            <span className="text-subtitle text-white" style={{ fontSize: "16px" }}>
              {project.name}
            </span>
            {project.description && (
              <p className="text-body-sm text-[var(--muted-foreground)] mt-0.5 line-clamp-1">
                {project.description}
              </p>
            )}
          </div>
        </div>
        {isConnected ? (
          <span className="shrink-0 text-caption font-bold text-white/70 bg-white/[0.06] px-3 py-1.5 rounded-full">
            {project.current_stage}/{project.total_stages}
          </span>
        ) : (
          <span className="shrink-0 text-caption font-medium text-white/40 bg-white/[0.04] px-3 py-1.5 rounded-full">
            N/A
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        {progressPct != null ? (
          <>
            <div className="flex items-center justify-between mb-2">
              <span className="text-body-sm text-[var(--muted-foreground)] truncate">
                {project.stage_label ?? `Stage ${project.current_stage}`}
              </span>
              <span className="text-body-sm font-bold text-white shrink-0 ml-2">
                {progressPct}%
              </span>
            </div>
            <div className="h-2.5 bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-all`}
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <div className="flex items-center gap-1.5 mt-3">
              {Array.from({ length: project.total_stages }).map((_, i) => (
                <div
                  key={i}
                  className={`h-1.5 flex-1 rounded-full transition-colors ${
                    i < project.current_stage
                      ? `bg-gradient-to-r ${gradient}`
                      : "bg-white/[0.06]"
                  }`}
                />
              ))}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-between">
            <span className="text-body-sm text-[var(--muted-foreground)]">Progress</span>
            <span className="text-body-sm text-white/50 font-medium">N/A</span>
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="space-y-2">
        {project.next_milestone && (
          <div className="flex items-start gap-2 text-body-sm text-[var(--muted-foreground)]">
            <ArrowRight className="w-4 h-4 mt-0.5 shrink-0 text-purple-400" />
            <span className="line-clamp-1">{project.next_milestone}</span>
          </div>
        )}
        {project.blockers && (
          <div className="flex items-start gap-2 text-body-sm text-amber-400">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span className="line-clamp-1">{project.blockers}</span>
          </div>
        )}
        {project.days_since_commit != null && (
          <div className="flex items-center gap-2 text-caption text-[#7A7A95]">
            <GitBranch className="w-3.5 h-3.5 shrink-0" />
            <span>
              {project.days_since_commit === 0
                ? "committed today"
                : `${project.days_since_commit}d since last commit`}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
