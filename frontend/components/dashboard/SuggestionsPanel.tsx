"use client";

import { useState } from "react";
import { AISuggestion, api } from "@/lib/api";
import { X, Sparkles, TrendingUp, Package, BarChart3 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

const CATEGORY_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string; glow: string; tagGradient: string }> = {
  content: { icon: <Sparkles className="w-3.5 h-3.5" />, label: "content", color: "text-purple-400", glow: "shadow-[inset_3px_0_0_#A855F7]", tagGradient: "from-purple-500 to-pink-400" },
  growth: { icon: <TrendingUp className="w-3.5 h-3.5" />, label: "growth", color: "text-emerald-400", glow: "shadow-[inset_3px_0_0_#10B981]", tagGradient: "from-emerald-500 to-teal-400" },
  product: { icon: <Package className="w-3.5 h-3.5" />, label: "product", color: "text-cyan-400", glow: "shadow-[inset_3px_0_0_#06B6D4]", tagGradient: "from-cyan-500 to-blue-400" },
  market: { icon: <BarChart3 className="w-3.5 h-3.5" />, label: "market", color: "text-amber-400", glow: "shadow-[inset_3px_0_0_#F59E0B]", tagGradient: "from-amber-500 to-orange-400" },
};

interface SuggestionsPanelProps {
  suggestions: AISuggestion[];
}

export function SuggestionsPanel({ suggestions: initial }: SuggestionsPanelProps) {
  const [suggestions, setSuggestions] = useState(initial);

  const dismiss = async (id: number) => {
    await api.dismissSuggestion(id);
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  };

  if (suggestions.length === 0) {
    return (
      <div className="py-12 text-center elevated-card rounded-2xl">
        <Sparkles className="w-12 h-12 text-purple-400/30 mx-auto mb-4" />
        <p className="text-body text-[var(--muted-foreground)]">
          No suggestions right now.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <AnimatePresence initial={false}>
        {suggestions.map((s) => {
          const config = CATEGORY_CONFIG[s.category ?? ""] ?? CATEGORY_CONFIG.content;
          return (
            <motion.div
              key={s.id}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className={cn(
                "group relative flex items-start gap-4 p-4 rounded-xl glass-card transition-all",
                config.glow
              )}
            >
              <button
                onClick={() => dismiss(s.id)}
                className="mt-1 shrink-0 w-5 h-5 rounded-full border-2 border-white/20 hover:border-pink-400 hover:bg-pink-400/20 flex items-center justify-center transition-all"
              >
                <X className="w-3 h-3 text-white/30 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>

              <div className="flex-1 min-w-0">
                <span className="text-[15px] font-semibold text-white leading-snug">
                  {s.body.includes("—")
                    ? s.body.split("—")[0].trim()
                    : s.body.includes(".")
                      ? s.body.split(".")[0].trim()
                      : s.body.slice(0, 60)}
                </span>

                <p className="text-body-sm text-[var(--muted-foreground)] mt-2 line-clamp-2">
                  {s.body.includes("—")
                    ? s.body.slice(s.body.indexOf("—") + 1).trim()
                    : s.body.includes(".")
                      ? s.body.slice(s.body.indexOf(".") + 1).trim()
                      : ""}
                </p>

                <div className="flex items-center gap-2.5 mt-3">
                  {s.category && (
                    <span
                      className={cn(
                        "text-caption font-bold px-3 py-1 rounded-full text-white bg-gradient-to-r",
                        config.tagGradient
                      )}
                    >
                      {config.label}
                    </span>
                  )}
                  <span className="text-caption font-bold text-purple-300 bg-purple-500/15 px-2.5 py-1 rounded-full">AI</span>
                </div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
