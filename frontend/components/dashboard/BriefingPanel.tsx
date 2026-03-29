"use client";

import { useState } from "react";
import { NewsBriefing, api } from "@/lib/api";
import { X, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

const CATEGORY_COLORS: Record<string, string> = {
  ai: "bg-cyan-400",
  competitor: "bg-pink-400",
  marketing: "bg-purple-400",
  cad: "bg-amber-400",
};

const RELEVANCE_DOT = (score: number) => {
  if (score >= 0.8) return "bg-pink-400 shadow-[0_0_6px_rgba(236,72,153,0.5)]";
  if (score >= 0.6) return "bg-amber-400 shadow-[0_0_6px_rgba(245,158,11,0.5)]";
  return "bg-white/20";
};

interface BriefingPanelProps {
  items: NewsBriefing[];
}

export function BriefingPanel({ items: initial }: BriefingPanelProps) {
  const [items, setItems] = useState(initial);
  const [expanded, setExpanded] = useState<number | null>(null);

  const dismiss = async (id: number) => {
    await api.dismissBriefingItem(id);
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  if (items.length === 0) {
    return (
      <div className="text-sm text-[#6A6A80] py-6 text-center">
        No briefing items today. Run the seed script to populate.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.id}
          className="group rounded-xl glass-card hover:bg-white/[0.04] transition-all overflow-hidden"
        >
          <div
            className="flex items-start gap-3 p-3.5 cursor-pointer"
            onClick={() => setExpanded(expanded === item.id ? null : item.id)}
          >
            <div
              className={cn(
                "shrink-0 mt-1.5 w-2 h-2 rounded-full",
                RELEVANCE_DOT(item.relevance_score)
              )}
            />
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium text-white leading-snug block">{item.headline}</span>
              {item.category && (
                <span className="inline-flex items-center gap-1.5 mt-1">
                  <div className={cn("w-1.5 h-1.5 rounded-full", CATEGORY_COLORS[item.category] ?? "bg-white/30")} />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#6A6A80]">
                    {item.category}
                  </span>
                </span>
              )}
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); dismiss(item.id); }}
              className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-white/30 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {expanded === item.id && (
            <div className="px-3.5 pb-3.5 border-t border-white/5 pt-3 space-y-2">
              {item.summary && (
                <p className="text-xs text-[#8A8AA0] leading-relaxed">{item.summary}</p>
              )}
              {item.suggested_action && (
                <div className="flex items-start gap-2 bg-purple-500/10 rounded-lg p-2.5">
                  <Plus className="w-3.5 h-3.5 shrink-0 mt-0.5 text-purple-400" />
                  <p className="text-xs font-medium text-purple-300">{item.suggested_action}</p>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
