"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FileText,
  BarChart2,
  TrendingUp,
  Users,
  Calendar,
  Globe,
  GitBranch,
  Zap,
  Menu,
  X,
  LogOut,
  Settings,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Command Center", icon: LayoutDashboard },
  { href: "/content", label: "Content Studio", icon: FileText },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/stats", label: "Stats", icon: TrendingUp },
  { href: "/leads", label: "Leads & Outreach", icon: Users },
  { href: "/schedule", label: "Schedule", icon: Calendar },
  { href: "/market", label: "Market Intel", icon: Globe },
  { href: "/github", label: "GitHub Progress", icon: GitBranch },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => setMounted(true), []);

  // Close mobile menu on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  if (!mounted) {
    return (
      <>
        <aside className="fixed left-0 top-0 h-full w-60 bg-[var(--sidebar)] z-40 hidden lg:block" />
        <div className="h-14 lg:hidden" />
      </>
    );
  }

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="flex items-center justify-between px-5 h-14 lg:h-16 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-xl gradient-purple shadow-[0_0_16px_rgba(168,85,247,0.3)]">
            <Zap className="w-[18px] h-[18px] text-white" />
          </div>
          <div>
            <span className="text-[15px] font-bold tracking-tight text-white">
              Operator
            </span>
            <span className="block text-[11px] text-[var(--muted-foreground)] font-medium">
              Dashboard v1
            </span>
          </div>
        </div>
        {/* Close button — mobile only */}
        <button
          onClick={() => setMobileOpen(false)}
          className="lg:hidden p-1.5 rounded-lg hover:bg-white/[0.06] text-[var(--muted-foreground)]"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-[14px] font-medium transition-all group",
                active
                  ? "bg-gradient-to-r from-purple-500/20 to-pink-500/10 text-white border border-purple-500/20"
                  : "text-[var(--sidebar-foreground)] hover:bg-white/[0.04] hover:text-white"
              )}
            >
              <Icon
                className={cn(
                  "w-[18px] h-[18px] shrink-0 transition-colors",
                  active ? "text-purple-400" : "text-[#6E6E88] group-hover:text-purple-400/70"
                )}
              />
              <span className="truncate">{label}</span>
              {active && (
                <div className="ml-auto w-1.5 h-5 rounded-full gradient-purple" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-white/[0.06]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full gradient-cyan flex items-center justify-center text-[11px] font-bold text-white">
              {process.env.NEXT_PUBLIC_INITIALS || "OP"}
            </div>
            <div>
              <div className="text-[13px] font-semibold text-white">
                {process.env.NEXT_PUBLIC_DISPLAY_NAME || "Operator"}
              </div>
              <div className="text-[11px] text-[var(--muted-foreground)]">
                {process.env.NEXT_PUBLIC_TAGLINE || "solo founder mode"}
              </div>
            </div>
          </div>
          <button
            onClick={() => {
              document.cookie = "operator_token=; path=/; max-age=0";
              window.location.href = "/landing";
            }}
            className="p-2 rounded-lg hover:bg-white/[0.06] text-[var(--muted-foreground)] hover:text-white transition-colors"
            title="Log out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile top bar */}
      <div className="fixed top-0 left-0 right-0 h-14 bg-[var(--sidebar)] border-b border-white/[0.06] z-40 flex items-center px-4 lg:hidden">
        <button
          onClick={() => setMobileOpen(true)}
          className="p-2 rounded-lg hover:bg-white/[0.06] text-white"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2 ml-3">
          <div className="w-7 h-7 rounded-lg gradient-purple flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-[14px] font-bold text-white">Operator</span>
        </div>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/70 z-[70] lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar — desktop: always visible, mobile: slide in */}
      <aside
        className={cn(
          "fixed left-0 top-0 h-full w-64 flex flex-col border-r border-white/[0.06] bg-[var(--sidebar)] transition-transform duration-200",
          "lg:w-60 lg:translate-x-0 lg:z-40",
          mobileOpen ? "translate-x-0 z-[80]" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
