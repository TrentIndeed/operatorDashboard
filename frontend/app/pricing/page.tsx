"use client";

import Link from "next/link";
import { Zap, Check, ArrowRight, Server, Laptop } from "lucide-react";

const PLANS = [
  {
    id: "local",
    name: "Local",
    price: "Free",
    period: "forever",
    description: "Self-hosted on your own machine",
    icon: Laptop,
    features: [
      "Full source code access",
      "Unlimited AI Generate",
      "All dashboard features",
      "No usage limits",
      "You manage hosting",
    ],
    cta: "Get Started",
    href: "/signup?plan=local",
    gradient: "from-gray-700 to-gray-800",
    border: "border-white/10",
    popular: false,
  },
  {
    id: "starter",
    name: "Starter",
    price: "$9",
    period: "/month",
    description: "Cloud-hosted, we manage everything",
    icon: Server,
    features: [
      "Cloud-hosted dashboard",
      "AI Generate (50 calls/mo)",
      "Daily email briefing",
      "1 project",
      "Auto HTTPS + domain",
    ],
    cta: "Start Free Trial",
    href: "/signup?plan=starter",
    gradient: "from-purple-600 to-pink-600",
    border: "border-purple-500/30",
    popular: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: "$29",
    period: "/month",
    description: "Dedicated VPS, unlimited everything",
    icon: Zap,
    features: [
      "Dedicated VPS (4GB RAM)",
      "Unlimited AI Generate",
      "Email + WhatsApp briefing",
      "Unlimited projects",
      "Custom domain",
      "Priority support",
    ],
    cta: "Go Pro",
    href: "/signup?plan=pro",
    gradient: "from-cyan-600 to-blue-600",
    border: "border-cyan-500/30",
    popular: false,
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 sm:px-10 py-5 max-w-6xl mx-auto">
        <Link href="/landing" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl gradient-purple shadow-[0_0_20px_rgba(168,85,247,0.3)] flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight">Operator</span>
        </Link>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm text-[var(--muted-foreground)] hover:text-white px-4 py-2">
            Log in
          </Link>
        </div>
      </nav>

      {/* Header */}
      <section className="px-6 sm:px-10 pt-12 pb-16 max-w-6xl mx-auto text-center">
        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight mb-4">
          Simple pricing
        </h1>
        <p className="text-lg text-[#9494AD] max-w-lg mx-auto">
          Run it yourself for free, or let us host it for you.
        </p>
      </section>

      {/* Plans */}
      <section className="px-6 sm:px-10 pb-24 max-w-5xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`relative rounded-2xl border ${plan.border} bg-[#111118] p-7 flex flex-col ${
                plan.popular ? "ring-2 ring-purple-500/50" : ""
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 text-xs font-bold">
                  Most Popular
                </div>
              )}

              <div className="flex items-center gap-3 mb-4">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${plan.gradient} flex items-center justify-center`}>
                  <plan.icon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">{plan.name}</h3>
                  <p className="text-xs text-[#9494AD]">{plan.description}</p>
                </div>
              </div>

              <div className="mb-6">
                <span className="text-4xl font-extrabold">{plan.price}</span>
                <span className="text-[#9494AD] text-sm">{plan.period}</span>
              </div>

              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-[#9494AD]">
                    <Check className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>

              <Link
                href={plan.href}
                className={`flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all ${
                  plan.popular
                    ? "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white"
                    : "border border-white/10 hover:border-white/20 text-white hover:bg-white/[0.04]"
                }`}
              >
                {plan.cta}
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
