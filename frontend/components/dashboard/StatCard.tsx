import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string;
  gradient: string;
  icon: LucideIcon;
  subtitle?: string;
}

export function StatCard({ label, value, gradient, icon: Icon, subtitle }: StatCardProps) {
  return (
    <div className={cn("relative overflow-hidden rounded-2xl p-6", gradient)}>
      <div className="relative z-10">
        <div className="flex items-center gap-2 mb-2">
          <Icon className="w-4 h-4 text-white/80" />
          <span className="text-label text-white/80">
            {label}
          </span>
        </div>
        <div className="text-display text-white" style={{ fontSize: "36px" }}>
          {value}
        </div>
        {subtitle && (
          <div className="text-body-sm text-white/70 mt-1">{subtitle}</div>
        )}
      </div>
      {/* Decorative glow */}
      <div className="absolute top-0 right-0 w-40 h-40 rounded-full bg-white/10 blur-3xl -translate-y-10 translate-x-10" />
    </div>
  );
}
