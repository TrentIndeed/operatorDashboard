"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Settings,
  Key,
  Trash2,
  Lock,
  GitBranch,
  Play,
  Music,
  Tv,
  Mail,
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle,
  Clock,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DAYS = [
  { key: "mon", label: "Monday" },
  { key: "tue", label: "Tuesday" },
  { key: "wed", label: "Wednesday" },
  { key: "thu", label: "Thursday" },
  { key: "fri", label: "Friday" },
  { key: "sat", label: "Saturday" },
  { key: "sun", label: "Sunday" },
];

interface Config {
  github_owner: string;
  github_connected: boolean;
  youtube_connected: boolean;
  tiktok_connected: boolean;
  twitter_connected: boolean;
  email_to: string;
  display_name: string;
  n8n_configured: boolean;
  stripe_configured: boolean;
}

function ConnectionBadge({ connected, label }: { connected: boolean; label: string }) {
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${
      connected
        ? "border-emerald-500/30 bg-emerald-500/10"
        : "border-white/[0.06] bg-white/[0.02]"
    }`}>
      {connected ? (
        <CheckCircle className="w-4 h-4 text-emerald-400" />
      ) : (
        <XCircle className="w-4 h-4 text-[var(--muted-foreground)]" />
      )}
      <span className={`text-sm ${connected ? "text-emerald-300" : "text-[var(--muted-foreground)]"}`}>
        {label}
      </span>
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);

  // Weekly schedule
  const [schedule, setSchedule] = useState<Record<string, number>>({
    mon: 2, tue: 2, wed: 2, thu: 0, fri: 5, sat: 5, sun: 5,
  });
  const [schedLoading, setSchedLoading] = useState(false);
  const [schedSaved, setSchedSaved] = useState(false);

  // Change password
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwLoading, setPwLoading] = useState(false);
  const [pwMessage, setPwMessage] = useState("");
  const [pwError, setPwError] = useState("");

  // Delete account
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deletePw, setDeletePw] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  // Get username from cookie token (simplified — in production use JWT)
  const getUsername = () => {
    // For now, prompt or use stored value
    return "123"; // TODO: store username in cookie alongside token
  };

  useEffect(() => {
    Promise.all([
      fetch(`${API}/settings/config`).then((r) => r.json()).then(setConfig).catch(() => {}),
      fetch(`${API}/settings/schedule`).then((r) => r.json()).then(setSchedule).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const handleSaveSchedule = async () => {
    setSchedLoading(true);
    setSchedSaved(false);
    try {
      await fetch(`${API}/settings/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(schedule),
      });
      setSchedSaved(true);
      setTimeout(() => setSchedSaved(false), 3000);
    } catch {}
    setSchedLoading(false);
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwMessage("");
    setPwError("");

    if (newPw !== confirmPw) {
      setPwError("Passwords don't match");
      return;
    }

    setPwLoading(true);
    try {
      const username = prompt("Enter your username:");
      if (!username) return;

      const res = await fetch(`${API}/settings/change-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          current_password: currentPw,
          new_password: newPw,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        setPwError(data.detail || "Failed to change password");
      } else {
        setPwMessage("Password changed successfully");
        setCurrentPw("");
        setNewPw("");
        setConfirmPw("");
      }
    } catch {
      setPwError("Cannot reach server");
    } finally {
      setPwLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleteError("");
    setDeleteLoading(true);

    try {
      const username = prompt("Enter your username to confirm deletion:");
      if (!username) {
        setDeleteLoading(false);
        return;
      }

      const res = await fetch(`${API}/settings/delete-account`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password: deletePw }),
      });

      if (!res.ok) {
        const data = await res.json();
        setDeleteError(data.detail || "Failed to delete account");
      } else {
        document.cookie = "operator_token=; path=/; max-age=0";
        router.push("/landing");
      }
    } catch {
      setDeleteError("Cannot reach server");
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-10 space-y-8 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-heading text-white flex items-center gap-3">
          <Settings className="w-7 h-7 text-purple-400" />
          Settings
        </h1>
        <p className="text-body text-[var(--muted-foreground)] mt-1">
          Manage your account and connections
        </p>
      </div>

      {/* Connections Status */}
      <section className="elevated-card rounded-2xl p-6">
        <h2 className="text-subtitle text-white mb-4">Connections</h2>
        <p className="text-body-sm text-[var(--muted-foreground)] mb-4">
          Configure these in your <code className="text-purple-300 bg-purple-500/10 px-1.5 py-0.5 rounded">.env</code> file and restart the backend.
        </p>
        {loading ? (
          <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
        ) : config ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <ConnectionBadge connected={config.github_connected} label={`GitHub ${config.github_owner ? `(@${config.github_owner})` : ""}`} />
            <ConnectionBadge connected={config.youtube_connected} label="YouTube" />
            <ConnectionBadge connected={config.tiktok_connected} label="TikTok" />
            <ConnectionBadge connected={config.twitter_connected} label="Twitter/X" />
            <ConnectionBadge connected={config.n8n_configured} label="n8n Automation" />
            <ConnectionBadge connected={config.stripe_configured} label="Stripe Billing" />
            <ConnectionBadge connected={!!config.email_to} label={`Email ${config.email_to ? `(${config.email_to})` : ""}`} />
          </div>
        ) : (
          <p className="text-body-sm text-red-400">Cannot load config</p>
        )}
      </section>

      {/* Weekly Availability */}
      <section className="elevated-card rounded-2xl p-6">
        <h2 className="text-subtitle text-white mb-2 flex items-center gap-2">
          <Clock className="w-5 h-5 text-purple-400" />
          Weekly Availability
        </h2>
        <p className="text-body-sm text-[var(--muted-foreground)] mb-5">
          Set how many hours you can work each day. AI Generate will create tasks that fit your schedule.
          Set 0 for days off.
        </p>

        <div className="space-y-3">
          {DAYS.map(({ key, label }) => (
            <div key={key} className="flex items-center gap-4">
              <span className="text-body-sm text-white w-24">{label}</span>
              <div className="flex items-center gap-2 flex-1">
                <input
                  type="range"
                  min={0}
                  max={12}
                  step={0.5}
                  value={schedule[key] || 0}
                  onChange={(e) => setSchedule({ ...schedule, [key]: parseFloat(e.target.value) })}
                  className="flex-1 accent-purple-500 h-1.5"
                />
                <span className={`text-body-sm font-bold w-12 text-right ${
                  schedule[key] === 0 ? "text-red-400" : schedule[key] <= 2 ? "text-amber-400" : "text-emerald-400"
                }`}>
                  {schedule[key]}h
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3 mt-5 pt-4 border-t border-white/[0.06]">
          <div className="text-body-sm text-[var(--muted-foreground)]">
            Total: <span className="text-white font-semibold">
              {Object.values(schedule).reduce((a, b) => a + b, 0)}h/week
            </span>
          </div>
          <div className="ml-auto flex items-center gap-3">
            {schedSaved && <span className="text-caption text-emerald-400">Saved!</span>}
            <button
              onClick={handleSaveSchedule}
              disabled={schedLoading}
              className="px-5 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 transition-all"
            >
              {schedLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save Schedule"}
            </button>
          </div>
        </div>
      </section>

      {/* Environment Variables Guide */}
      <section className="elevated-card rounded-2xl p-6">
        <h2 className="text-subtitle text-white mb-4">Environment Variables</h2>
        <p className="text-body-sm text-[var(--muted-foreground)] mb-4">
          Edit your <code className="text-purple-300 bg-purple-500/10 px-1.5 py-0.5 rounded">.env</code> file to configure integrations. Restart the backend after changes.
        </p>

        <div className="space-y-3">
          {[
            { section: "GitHub", vars: ["GITHUB_TOKEN", "GITHUB_OWNER"], icon: GitBranch, desc: "GitHub personal access token with repo scope" },
            { section: "YouTube", vars: ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"], icon: Play, desc: "Google OAuth credentials — run /auth/google/login to get refresh token" },
            { section: "TikTok", vars: ["TIKTOK_SESSION_ID"], icon: Music, desc: "Session cookie from browser DevTools" },
            { section: "Twitter", vars: ["TWITTER_CONSUMER_KEY", "TWITTER_CONSUMER_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"], icon: Tv, desc: "Twitter API v2 credentials" },
            { section: "Email", vars: ["EMAIL_TO"], icon: Mail, desc: "Email address for daily briefing" },
            { section: "Auth", vars: ["AUTH_SECRET", "DASHBOARD_USER", "DASHBOARD_PASS"], icon: Lock, desc: "AUTH_SECRET must be persistent (set once, never change)" },
          ].map((group) => (
            <div key={group.section} className="rounded-xl bg-[#111118] border border-white/[0.06] p-4">
              <div className="flex items-center gap-2 mb-2">
                <group.icon className="w-4 h-4 text-purple-400" />
                <span className="text-body-sm font-semibold text-white">{group.section}</span>
              </div>
              <p className="text-caption text-[var(--muted-foreground)] mb-2">{group.desc}</p>
              <div className="flex flex-wrap gap-1.5">
                {group.vars.map((v) => (
                  <code key={v} className="text-[11px] px-2 py-0.5 rounded bg-white/[0.04] text-[var(--muted-foreground)] border border-white/[0.06]">
                    {v}
                  </code>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Change Password */}
      <section className="elevated-card rounded-2xl p-6">
        <h2 className="text-subtitle text-white mb-4 flex items-center gap-2">
          <Key className="w-5 h-5 text-purple-400" />
          Change Password
        </h2>
        <form onSubmit={handleChangePassword} className="space-y-3 max-w-sm">
          <input
            type="password"
            value={currentPw}
            onChange={(e) => setCurrentPw(e.target.value)}
            placeholder="Current password"
            className="w-full bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
          />
          <input
            type="password"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            placeholder="New password"
            className="w-full bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
          />
          <input
            type="password"
            value={confirmPw}
            onChange={(e) => setConfirmPw(e.target.value)}
            placeholder="Confirm new password"
            className="w-full bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
          />
          {pwError && <p className="text-sm text-red-400">{pwError}</p>}
          {pwMessage && <p className="text-sm text-emerald-400">{pwMessage}</p>}
          <button
            type="submit"
            disabled={pwLoading || !currentPw || !newPw || !confirmPw}
            className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 transition-all"
          >
            {pwLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Change Password"}
          </button>
        </form>
      </section>

      {/* Danger Zone */}
      <section className="elevated-card rounded-2xl p-6 border border-red-500/20">
        <h2 className="text-subtitle text-red-400 mb-2 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          Danger Zone
        </h2>
        <p className="text-body-sm text-[var(--muted-foreground)] mb-4">
          This permanently deletes your account and all data (projects, tasks, goals, drafts, analytics). This cannot be undone.
        </p>

        {!deleteConfirm ? (
          <button
            onClick={() => setDeleteConfirm(true)}
            className="px-6 py-2.5 rounded-xl text-sm font-semibold text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-all"
          >
            <Trash2 className="w-4 h-4 inline mr-2" />
            Delete Account
          </button>
        ) : (
          <div className="space-y-3 max-w-sm">
            <p className="text-sm text-red-300 font-medium">
              Type your password to confirm deletion:
            </p>
            <input
              type="password"
              value={deletePw}
              onChange={(e) => setDeletePw(e.target.value)}
              placeholder="Your password"
              className="w-full bg-[#111118] border border-red-500/30 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-red-500/50"
            />
            {deleteError && <p className="text-sm text-red-400">{deleteError}</p>}
            <div className="flex gap-3">
              <button
                onClick={handleDeleteAccount}
                disabled={deleteLoading || !deletePw}
                className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-red-600 hover:bg-red-500 disabled:opacity-50 transition-all"
              >
                {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Permanently Delete"}
              </button>
              <button
                onClick={() => { setDeleteConfirm(false); setDeletePw(""); setDeleteError(""); }}
                className="px-6 py-2.5 rounded-xl text-sm text-[var(--muted-foreground)] border border-white/10 hover:text-white transition-all"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
