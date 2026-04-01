"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Clock, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { api, Task } from "@/lib/api";

// Color cycle for project tags — auto-assigns by tag name
const TAG_GRADIENTS = [
  "from-blue-500 to-cyan-400",
  "from-emerald-500 to-teal-400",
  "from-purple-500 to-pink-400",
  "from-amber-500 to-orange-400",
  "from-orange-500 to-red-400",
  "from-pink-500 to-rose-400",
  "from-cyan-500 to-blue-400",
];

const tagColorCache: Record<string, string> = {};
function getTagGradient(tag: string): string {
  if (!tagColorCache[tag]) {
    const idx = Object.keys(tagColorCache).length % TAG_GRADIENTS.length;
    tagColorCache[tag] = TAG_GRADIENTS[idx];
  }
  return tagColorCache[tag];
}

const PRIORITY_GLOW: (score: number) => string = (score) => {
  if (score >= 8) return "shadow-[inset_3px_0_0_#EF4444]";
  if (score >= 6) return "shadow-[inset_3px_0_0_#F59E0B]";
  if (score >= 4) return "shadow-[inset_3px_0_0_#A855F7]";
  return "";
};

interface TaskCardProps {
  task: Task;
  onComplete: (id: number) => void;
}

export function TaskCard({ task, onComplete }: TaskCardProps) {
  const [completing, setCompleting] = useState(false);

  const handleComplete = async () => {
    setCompleting(true);
    try {
      await api.updateTask(task.id, { status: "done" });
      onComplete(task.id);
    } finally {
      setCompleting(false);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className={cn(
        "group relative flex items-start gap-4 p-4 rounded-xl glass-card transition-all cursor-default",
        PRIORITY_GLOW(task.priority_score)
      )}
    >
      <button
        onClick={handleComplete}
        disabled={completing}
        className="mt-1 shrink-0 w-5 h-5 rounded-full border-2 border-white/20 hover:border-purple-400 hover:bg-purple-400/20 flex items-center justify-center transition-all"
      >
        {completing ? (
          <Loader2 className="w-3 h-3 animate-spin text-purple-400" />
        ) : (
          <Check className="w-3 h-3 text-white/30 opacity-0 group-hover:opacity-100 transition-opacity" />
        )}
      </button>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3">
          <span className="text-[15px] font-semibold text-white leading-snug">
            {task.title}
          </span>
          <span className="shrink-0 text-caption font-bold text-white/80 bg-white/10 px-2.5 py-1 rounded-full">
            {task.priority_score.toFixed(1)}
          </span>
        </div>

        {task.why && (
          <p className="text-body-sm text-[var(--muted-foreground)] mt-2 line-clamp-2">
            {task.why}
          </p>
        )}

        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {task.project_tag && (
            <span
              className={cn(
                "text-caption font-bold px-2.5 py-0.5 rounded-full text-white bg-gradient-to-r truncate max-w-[140px]",
                getTagGradient(task.project_tag)
              )}
            >
              {task.project_tag}
            </span>
          )}
          <span className="flex items-center gap-1.5 text-body-sm text-[#8888A0]">
            <Clock className="w-3.5 h-3.5" />
            {task.estimated_minutes}m
          </span>
          {task.ai_generated && (
            <span className="text-caption font-bold text-purple-300 bg-purple-500/15 px-2.5 py-1 rounded-full">AI</span>
          )}
        </div>
      </div>
    </motion.div>
  );
}
