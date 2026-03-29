"use client";

import Link from "next/link";
import {
  Zap,
  Brain,
  Calendar,
  BarChart2,
  Globe,
  FileText,
  ArrowRight,
  CheckCircle,
} from "lucide-react";

const FEATURES = [
  {
    icon: Brain,
    title: "AI-Powered Tasks",
    desc: "Claude generates your daily priorities based on your projects, goals, and deadlines.",
  },
  {
    icon: FileText,
    title: "Content Studio",
    desc: "Auto-generate content drafts with hooks, scripts, and CTAs for any platform.",
  },
  {
    icon: Calendar,
    title: "Smart Schedule",
    desc: "Content blocks auto-scheduled across your calendar with approval workflows.",
  },
  {
    icon: BarChart2,
    title: "Analytics",
    desc: "YouTube, TikTok, and Twitter stats synced with content performance scoring.",
  },
  {
    icon: Globe,
    title: "Market Intelligence",
    desc: "AI scans for market gaps, competitor moves, and opportunities in your niche.",
  },
  {
    icon: Zap,
    title: "Daily Briefing",
    desc: "Morning email with your focus tasks, drafts to review, and industry news.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-white overflow-x-hidden">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 sm:px-10 py-5 max-w-6xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl gradient-purple shadow-[0_0_20px_rgba(168,85,247,0.3)] flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight">Operator</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm font-medium text-[var(--muted-foreground)] hover:text-white transition-colors px-4 py-2"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="text-sm font-semibold px-5 py-2.5 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 transition-all"
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-6 sm:px-10 pt-16 sm:pt-24 pb-20 max-w-6xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-300 text-sm font-medium mb-8">
          <Zap className="w-3.5 h-3.5" />
          Powered by Claude AI
        </div>
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold leading-[1.1] tracking-tight mb-6">
          Your AI-powered
          <br />
          <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400 bg-clip-text text-transparent">
            command center
          </span>
        </h1>
        <p className="text-lg sm:text-xl text-[#9494AD] max-w-2xl mx-auto mb-10 leading-relaxed">
          The solo founder dashboard that thinks for you. AI generates your tasks,
          drafts your content, scans your market, and briefs you every morning.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/signup"
            className="flex items-center gap-2 px-8 py-3.5 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold text-base transition-all shadow-[0_0_30px_rgba(168,85,247,0.25)]"
          >
            Get Started Free
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/pricing"
            className="flex items-center gap-2 px-8 py-3.5 rounded-full border border-white/10 hover:border-white/20 text-[#9494AD] hover:text-white font-medium text-base transition-all"
          >
            See Pricing
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 sm:px-10 py-20 max-w-6xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold text-center mb-4">
          Everything you need to operate solo
        </h2>
        <p className="text-[#9494AD] text-center max-w-lg mx-auto mb-14">
          One dashboard. One AI. Every morning you wake up to a prioritized day.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-white/[0.06] bg-[#111118] p-6 hover:border-purple-500/30 transition-colors"
            >
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center mb-4">
                <f.icon className="w-5 h-5 text-purple-400" />
              </div>
              <h3 className="text-base font-semibold mb-2">{f.title}</h3>
              <p className="text-sm text-[#9494AD] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="px-6 sm:px-10 py-20 max-w-4xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold text-center mb-14">
          How it works
        </h2>
        <div className="space-y-8">
          {[
            { step: "1", title: "Add your projects", desc: "Tell the dashboard what you're building — your SaaS, content, open-source tools." },
            { step: "2", title: "Hit AI Generate", desc: "Claude analyzes your projects, goals, and market — then generates tasks, content drafts, and a daily briefing." },
            { step: "3", title: "Review and execute", desc: "Approve content, check off tasks, and track progress. The dashboard updates in real time." },
            { step: "4", title: "Wake up to a plan", desc: "Every morning, n8n triggers AI Generate and emails you your focus for the day." },
          ].map((item) => (
            <div key={item.step} className="flex gap-5 items-start">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center text-sm font-bold shrink-0">
                {item.step}
              </div>
              <div>
                <h3 className="text-base font-semibold mb-1">{item.title}</h3>
                <p className="text-sm text-[#9494AD]">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 sm:px-10 py-20 max-w-4xl mx-auto text-center">
        <div className="rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20 p-10 sm:p-16">
          <h2 className="text-2xl sm:text-3xl font-bold mb-4">Ready to operate?</h2>
          <p className="text-[#9494AD] mb-8 max-w-md mx-auto">
            Set up in 5 minutes. No credit card. Just Claude and your ambition.
          </p>
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold transition-all shadow-[0_0_30px_rgba(168,85,247,0.25)]"
          >
            Create Account
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 sm:px-10 py-8 border-t border-white/[0.06] max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-[#6A6A80]">
            <Zap className="w-4 h-4 text-purple-400" />
            Operator Dashboard
          </div>
          <div className="text-sm text-[#6A6A80]">
            Built with Claude AI
          </div>
        </div>
      </footer>
    </div>
  );
}
