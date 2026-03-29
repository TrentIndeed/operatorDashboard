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
    <div className={cn("relative overflow-hidden rounded-xl sm:rounded-2xl p-4 sm:p-6", gradient)}>
      <div className="relative z-10">
        <div className="flex items-center gap-1.5 sm:gap-2 mb-1 sm:mb-2">
          <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white/80" />
          <span className="text-[10px] sm:text-[11px] uppercase tracking-wider font-semibold text-white/80 truncate">
            {label}
          </span>
        </div>
        <div className="text-white font-extrabold text-2xl sm:text-4xl leading-none">
          {value}
        </div>
        {subtitle && (
          <div className="text-[11px] sm:text-[13px] text-white/70 mt-1 line-clamp-2">{subtitle}</div>
        )}
      </div>
      <div className="absolute top-0 right-0 w-40 h-40 rounded-full bg-white/10 blur-3xl -translate-y-10 translate-x-10" />
    </div>
  );
}
