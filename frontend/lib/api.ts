const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_USER = process.env.NEXT_PUBLIC_API_USER || "";
const API_PASS = process.env.NEXT_PUBLIC_API_PASS || "";

function authHeaders(): Record<string, string> {
  if (API_USER && API_PASS) {
    const encoded = typeof btoa !== "undefined"
      ? btoa(`${API_USER}:${API_PASS}`)
      : Buffer.from(`${API_USER}:${API_PASS}`).toString("base64");
    return { Authorization: `Basic ${encoded}` };
  }
  return {};
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

// --- Types ---

export interface Task {
  id: number;
  title: string;
  why: string | null;
  estimated_minutes: number;
  project_tag: string | null;
  priority_score: number;
  status: string;
  ai_generated: boolean;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  current_stage: number;
  total_stages: number;
  stage_label: string | null;
  blockers: string | null;
  next_milestone: string | null;
  github_repo: string | null;
  last_commit_at: string | null;
  days_since_commit: number | null;
  color: string;
}

export interface Goal {
  id: number;
  title: string;
  timeframe: string;
  progress: number;
  project_slug: string | null;
  status: string;
  created_at: string;
}

export interface AISuggestion {
  id: number;
  body: string;
  category: string | null;
  dismissed: boolean;
  created_at: string;
}

export interface NewsBriefing {
  id: number;
  headline: string;
  summary: string | null;
  category: string | null;
  relevance_score: number;
  suggested_action: string | null;
  dismissed: boolean;
  briefing_date: string | null;
  created_at: string;
}

export interface CommandCenterData {
  tasks: Task[];
  projects: Project[];
  goals_week: Goal[];
  goals_month: Goal[];
  goals_quarter: Goal[];
  suggestions: AISuggestion[];
  briefing: NewsBriefing[];
}

export interface GithubRepo {
  id: number;
  owner: string;
  name: string;
  full_name: string;
  description: string | null;
  stars: number;
  open_issues: number;
  open_prs: number;
  last_commit_sha: string | null;
  last_commit_message: string | null;
  last_commit_at: string | null;
  is_private: boolean;
  synced_at: string;
}

// --- Content Types ---

export interface ContentDraft {
  id: number;
  title: string;
  body: string;
  platform: string;
  content_type: string;
  hook: string | null;
  cta: string | null;
  hashtags: string | null;
  suggested_post_time: string | null;
  status: string;
  ai_generated: boolean;
  remix_of_id: number | null;
  feedback: string | null;
  project_tag: string | null;
  hook_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface ScheduleItem {
  id: number;
  draft_id: number | null;
  title: string;
  platform: string;
  scheduled_at: string;
  status: string;
  block_type: string;
  color: string;
  created_at: string;
}

export interface HookVariation {
  hook: string;
  score: number;
  full_script: string;
  cta: string;
}

// --- Market Intelligence Types ---

export interface MarketGap {
  id: number;
  description: string;
  source: string | null;
  source_url: string | null;
  opportunity_score: number;
  suggested_action: string | null;
  category: string | null;
  status: string;
  created_at: string;
}

export interface Competitor {
  id: number;
  name: string;
  platform: string;
  handle: string | null;
  url: string | null;
  description: string | null;
  last_checked: string | null;
}

export interface CompetitorPost {
  id: number;
  competitor_id: number;
  title: string | null;
  url: string | null;
  platform: string;
  thumbnail_url: string | null;
  views: number;
  likes: number;
  comments_count: number;
  engagement: number;
  ai_analysis: string | null;
  posted_at: string | null;
}

// --- Analytics Types ---

export interface SocialMetric {
  id: number; platform: string; date: string;
  views: number; likes: number; comments: number; shares: number; saves: number;
  followers: number; engagement_rate: number;
}

export interface ContentScore {
  id: number; draft_id: number | null; title: string; platform: string;
  views: number; likes: number; saves: number; shares: number;
  comments_count: number; engagement_rate: number; virality_score: number;
  content_type: string | null; topic: string | null; posted_at: string | null;
  thumbnail_url?: string | null; video_url?: string | null; external_id?: string | null;
}

// --- Leads & Outreach Types ---

export interface Lead {
  id: number; username: string; platform: string; message: string | null;
  source_url: string | null; sentiment: string | null; category: string;
  status: string; suggested_action: string | null; dm_draft: string | null;
  created_at: string;
}
export interface CommentReply {
  id: number; original_comment: string; username: string | null;
  platform: string; source_url: string | null; reply_draft: string | null;
  status: string; created_at: string;
}
export interface WaitlistSignup {
  id: number; email: string; name: string | null; source: string | null;
  source_detail: string | null; status: string; signed_up_at: string;
}
export interface WaitlistStats {
  total: number; by_source: Record<string, number>;
  active: number; converted: number;
}

// --- API Functions ---

export const api = {
  // Command Center
  commandCenter: () => apiFetch<CommandCenterData>("/command-center/"),

  // Tasks
  getTasks: (status?: string) =>
    apiFetch<Task[]>(`/tasks/${status ? `?status=${status}` : ""}`),
  createTask: (data: Partial<Task>) =>
    apiFetch<Task>("/tasks/", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (id: number, data: Partial<Task>) =>
    apiFetch<Task>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTask: (id: number) =>
    apiFetch<{ ok: boolean }>(`/tasks/${id}`, { method: "DELETE" }),

  // Goals
  getGoals: (timeframe?: string) =>
    apiFetch<Goal[]>(`/goals/${timeframe ? `?timeframe=${timeframe}` : ""}`),
  updateGoal: (id: number, data: Partial<Goal>) =>
    apiFetch<Goal>(`/goals/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // Suggestions
  dismissSuggestion: (id: number) =>
    apiFetch<{ ok: boolean }>(`/suggestions/${id}/dismiss`, { method: "PATCH" }),

  // Briefing
  dismissBriefingItem: (id: number) =>
    apiFetch<{ ok: boolean }>(`/briefing/${id}/dismiss`, { method: "PATCH" }),

  // Projects
  getProjects: () => apiFetch<Project[]>("/projects/"),

  // GitHub
  getRepos: () => apiFetch<GithubRepo[]>("/github/repos"),
  syncRepo: (owner: string, repo: string) =>
    apiFetch<GithubRepo>(`/github/sync/${owner}/${repo}`, { method: "POST" }),

  // Content Drafts
  getDrafts: (status?: string, platform?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (platform) params.set("platform", platform);
    const qs = params.toString();
    return apiFetch<ContentDraft[]>(`/content/drafts/${qs ? `?${qs}` : ""}`);
  },
  createDraft: (data: Partial<ContentDraft>) =>
    apiFetch<ContentDraft>("/content/drafts/", { method: "POST", body: JSON.stringify(data) }),
  updateDraft: (id: number, data: Partial<ContentDraft>) =>
    apiFetch<ContentDraft>(`/content/drafts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  approveDraft: (id: number, scheduledAt?: string) =>
    apiFetch<ContentDraft>(`/content/drafts/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ scheduled_at: scheduledAt }),
    }),
  declineDraft: (id: number, feedback?: string) =>
    apiFetch<ContentDraft>(`/content/drafts/${id}/decline`, {
      method: "POST",
      body: JSON.stringify({ feedback }),
    }),
  remixDraft: (id: number, feedback: string) =>
    apiFetch<ContentDraft>(`/content/drafts/${id}/remix`, {
      method: "POST",
      body: JSON.stringify({ feedback }),
    }),
  deleteDraft: (id: number) =>
    apiFetch<{ ok: boolean }>(`/content/drafts/${id}`, { method: "DELETE" }),

  // Content Schedule
  getSchedule: (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    const qs = params.toString();
    return apiFetch<ScheduleItem[]>(`/content/schedule/${qs ? `?${qs}` : ""}`);
  },
  createScheduleItem: (data: Partial<ScheduleItem>) =>
    apiFetch<ScheduleItem>("/content/schedule/", { method: "POST", body: JSON.stringify(data) }),
  deleteScheduleItem: (id: number) =>
    apiFetch<{ ok: boolean }>(`/content/schedule/${id}`, { method: "DELETE" }),

  // Hook Generator
  generateHooks: (topic: string, platform: string = "tiktok", projectTag: string = "ai-automation") =>
    apiFetch<{ variations: HookVariation[] }>("/content/generate-hooks", {
      method: "POST",
      body: JSON.stringify({ topic, platform, project_tag: projectTag }),
    }),

  // Analytics
  getMetrics: (platform?: string) => {
    const qs = platform ? `?platform=${platform}` : "";
    return apiFetch<SocialMetric[]>(`/analytics/metrics${qs}`);
  },
  getContentScores: () => apiFetch<ContentScore[]>("/analytics/content-scores"),
  getEngagementTrend: (platform?: string) => {
    const qs = platform ? `?platform=${platform}` : "";
    return apiFetch<SocialMetric[]>(`/analytics/engagement-trend${qs}`);
  },

  // Market Intel
  getMarketGaps: () => apiFetch<MarketGap[]>("/market/gaps"),
  dismissGap: (id: number) => apiFetch<{ ok: boolean }>(`/market/gaps/${id}/dismiss`, { method: "POST" }),
  actOnGap: (id: number) => apiFetch<{ ok: boolean }>(`/market/gaps/${id}/act`, { method: "POST" }),
  getCompetitors: () => apiFetch<Competitor[]>("/market/competitors"),
  getCompetitorPosts: (id: number) => apiFetch<CompetitorPost[]>(`/market/competitors/${id}/posts`),
  scanMarket: () => apiFetch<{ status: string }>("/market/scan", { method: "POST" }),

  // Leads & Outreach
  getLeads: (category?: string) => {
    const qs = category ? `?category=${category}` : "";
    return apiFetch<Lead[]>(`/leads/${qs}`);
  },
  updateLead: (id: number, data: Partial<Lead>) =>
    apiFetch<Lead>(`/leads/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  generateDM: (id: number) =>
    apiFetch<Lead>(`/leads/${id}/generate-dm`, { method: "POST" }),
  getCommentReplies: () => apiFetch<CommentReply[]>("/leads/comment-replies"),
  updateCommentReply: (id: number, data: Partial<CommentReply>) =>
    apiFetch<CommentReply>(`/leads/comment-replies/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  generateReply: (id: number) =>
    apiFetch<CommentReply>(`/leads/comment-replies/${id}/generate`, { method: "POST" }),
  getWaitlist: () => apiFetch<WaitlistSignup[]>("/leads/waitlist"),
  getWaitlistStats: () => apiFetch<WaitlistStats>("/leads/waitlist/stats"),
  addWaitlistSignup: (data: { email: string; name?: string; source?: string }) =>
    apiFetch<WaitlistSignup>("/leads/waitlist", { method: "POST", body: JSON.stringify(data) }),

  // Social Sync
  syncSocial: () => apiFetch<{ synced: string[]; errors: string[] }>("/social/sync", { method: "POST" }),
  getSocialStatus: () => apiFetch<Record<string, boolean>>("/social/status"),

  // AI Actions
  generateTasks: () =>
    apiFetch<{ status: string; message: string }>("/ai/generate-tasks", { method: "POST" }),
  generateSuggestions: () =>
    apiFetch<{ status: string; message: string }>("/ai/generate-suggestions", { method: "POST" }),
  generateDraft: (topic: string, platform: string, contentType: string, projectTag: string) =>
    apiFetch<ContentDraft>(`/ai/generate-draft?topic=${encodeURIComponent(topic)}&platform=${platform}&content_type=${contentType}&project_tag=${projectTag}`, {
      method: "POST",
    }),
  generateAll: () =>
    apiFetch<{ status: string; message: string; queued: string[] }>("/ai/generate-all", { method: "POST" }),

  // GitHub
  syncAllRepos: () =>
    apiFetch<{ status: string; message: string }>("/github/sync-all", { method: "POST" }),
};
