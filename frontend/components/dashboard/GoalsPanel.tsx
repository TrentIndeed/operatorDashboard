"use client";

import { useState } from "react";
import { Goal, api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface GoalsPanelProps {
  week: Goal[];
  month: Goal[];
  quarter: Goal[];
}

type Tab = "week" | "month" | "quarter";

const TAB_LABELS: Record<Tab, string> = {
  week: "This Week",
  month: "This Month",
  quarter: "Quarter",
};

export function GoalsPanel({ week, month, quarter }: GoalsPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("week");
  const [goals, setGoals] = useState({ week, month, quarter });

  const currentGoals = goals[activeTab];

  const handleComplete = async (goalId: number) => {
    await api.updateGoal(goalId, { status: "completed" });
    setGoals((prev) => ({
      ...prev,
      [activeTab]: prev[activeTab].filter((g) => g.id !== goalId),
    }));
  };

  const handleProgressClick = async (goal: Goal) => {
    const newProgress = Math.min(1, goal.progress + 0.1);
    await api.updateGoal(goal.id, { progress: parseFloat(newProgress.toFixed(1)) });
    setGoals((prev) => ({
      ...prev,
      [activeTab]: prev[activeTab].map((g) =>
        g.id === goal.id ? { ...g, progress: newProgress } : g
      ),
    }));
  };

  return (
    <div>
      {/* Tab row - pill buttons */}
      <div className="flex items-center gap-2 mb-5">
        {(["week", "month", "quarter"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "btn-pill btn-pill-sm transition-all",
              activeTab === tab
                ? "btn-pill-primary"
                : "btn-pill-outline"
            )}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* Goals list */}
      <div className="space-y-3">
        {currentGoals.length === 0 && (
          <p className="text-body-sm text-[var(--muted-foreground)] py-4">
            No active goals for this period.
          </p>
        )}
        {currentGoals.map((goal) => {
          const pct = Math.round(goal.progress * 100);
          return (
            <div
              key={goal.id}
              className="flex items-center gap-3 p-4 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.04] transition-all group"
            >
              <button
                onClick={() => handleComplete(goal.id)}
                className="shrink-0 w-5 h-5 rounded-full border-2 border-white/15 hover:border-purple-400 hover:bg-purple-400/20 flex items-center justify-center transition-all"
              >
                <Check className="w-2.5 h-2.5 text-white/30 opacity-0 group-hover:opacity-100" />
              </button>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-3 mb-2">
                  <span className="text-[14px] font-medium text-[#D0D0E0] truncate">{goal.title}</span>
                  <span className="shrink-0 text-caption font-bold text-white/70">
                    {pct}%
                  </span>
                </div>
                <button
                  onClick={() => handleProgressClick(goal)}
                  className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden group/bar cursor-pointer"
                  title="Click to +10% progress"
                >
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all group-hover/bar:opacity-80"
                    style={{ width: `${pct}%` }}
                  />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
