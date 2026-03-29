"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Zap, Loader2 } from "lucide-react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        }
      );

      if (!res.ok) {
        setError("Invalid username or password");
        setLoading(false);
        return;
      }

      const data = await res.json();
      // Store token in cookie (30 day expiry)
      document.cookie = `operator_token=${data.token}; path=/; max-age=${30 * 24 * 60 * 60}; SameSite=Lax`;
      router.push("/dashboard");
    } catch {
      setError("Cannot reach backend");
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#0A0A0B] flex items-center justify-center p-4 z-[60]">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl gradient-purple shadow-[0_0_24px_rgba(168,85,247,0.3)] mb-4">
            <Zap className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Operator Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">Sign in to your command center</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-[var(--muted-foreground)] block mb-1.5">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-3 text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50 transition-colors"
              placeholder="Username"
              autoFocus
            />
          </div>
          <div>
            <label className="text-xs text-[var(--muted-foreground)] block mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-3 text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50 transition-colors"
              placeholder="Password"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !username || !password}
            className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 transition-all disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin mx-auto" />
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        <p className="text-center text-sm text-[var(--muted-foreground)] mt-6">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-purple-400 hover:text-purple-300 font-medium">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
