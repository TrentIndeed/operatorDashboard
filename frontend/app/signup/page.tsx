"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Zap, Loader2, Laptop, Server } from "lucide-react";

export default function SignupPage() {
  return (
    <Suspense>
      <SignupForm />
    </Suspense>
  );
}

function SignupForm() {
  const searchParams = useSearchParams();
  const planParam = searchParams.get("plan") || "local";

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [plan, setPlan] = useState(planParam);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    if (password.length < 3) {
      setError("Password must be at least 3 characters");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/signup`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email, password, plan }),
        }
      );

      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Signup failed");
        setLoading(false);
        return;
      }

      const data = await res.json();
      document.cookie = `operator_token=${data.token}; path=/; max-age=${30 * 24 * 60 * 60}; SameSite=Lax`;

      // Cloud plans → redirect to Stripe checkout
      if (plan !== "local" && data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        router.push("/dashboard");
      }
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
          <h1 className="text-2xl font-bold text-white">Create Account</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">Set up your operator dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Plan toggle */}
          <div>
            <label className="text-xs text-[var(--muted-foreground)] block mb-2">Hosting</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setPlan("local")}
                className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  plan === "local"
                    ? "bg-purple-500/20 border border-purple-500/40 text-white"
                    : "bg-[#111118] border border-white/[0.08] text-[var(--muted-foreground)] hover:border-white/20"
                }`}
              >
                <Laptop className="w-4 h-4" />
                Local (Free)
              </button>
              <button
                type="button"
                onClick={() => setPlan("starter")}
                className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  plan !== "local"
                    ? "bg-purple-500/20 border border-purple-500/40 text-white"
                    : "bg-[#111118] border border-white/[0.08] text-[var(--muted-foreground)] hover:border-white/20"
                }`}
              >
                <Server className="w-4 h-4" />
                Cloud
              </button>
            </div>
            {plan === "local" && (
              <p className="text-[11px] text-[var(--muted-foreground)] mt-2">
                Run on your own machine. Full source code access, no limits.
              </p>
            )}
            {plan !== "local" && (
              <p className="text-[11px] text-purple-300 mt-2">
                We host it for you. Starting at $9/mo.{" "}
                <Link href="/pricing" className="underline">See plans</Link>
              </p>
            )}
          </div>

          <div>
            <label className="text-xs text-[var(--muted-foreground)] block mb-1.5">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-3 text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50 transition-colors"
              placeholder="Choose a username"
              autoFocus
            />
          </div>

          {plan !== "local" && (
            <div>
              <label className="text-xs text-[var(--muted-foreground)] block mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-3 text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50 transition-colors"
                placeholder="you@example.com"
              />
            </div>
          )}

          <div>
            <label className="text-xs text-[var(--muted-foreground)] block mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-3 text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50 transition-colors"
              placeholder="Create a password"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--muted-foreground)] block mb-1.5">Confirm Password</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full bg-[#111118] border border-white/[0.08] rounded-xl px-4 py-3 text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50 transition-colors"
              placeholder="Confirm password"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !username || !password || !confirm}
            className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 transition-all disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin mx-auto" />
            ) : (
              "Create Account"
            )}
          </button>
        </form>

        <p className="text-center text-sm text-[var(--muted-foreground)] mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-purple-400 hover:text-purple-300 font-medium">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
