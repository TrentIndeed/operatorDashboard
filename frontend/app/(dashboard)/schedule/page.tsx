"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { api, ScheduleItem, ContentDraft } from "@/lib/api";
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Calendar,
  Loader2,
  RefreshCw,
  X,
} from "lucide-react";

// --- Constants ---

const BLOCK_TYPES = [
  { value: "content", label: "Content", color: "#A855F7" },
  { value: "deep_work", label: "Deep Work", color: "#3B82F6" },
  { value: "business", label: "Business", color: "#F59E0B" },
  { value: "research", label: "Research", color: "#6B7280" },
] as const;

const PLATFORMS = [
  "tiktok",
  "youtube",
  "twitter",
  "linkedin",
  "instagram",
  "newsletter",
  "blog",
  "other",
];

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function getBlockColor(blockType: string): string {
  return BLOCK_TYPES.find((b) => b.value === blockType)?.color ?? "#6B7280";
}

// --- Helpers ---

function startOfMonth(year: number, month: number): Date {
  return new Date(year, month, 1);
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function formatDateISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function monthLabel(year: number, month: number): string {
  return new Date(year, month).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });
}

// --- Add Block Form ---

interface AddBlockFormProps {
  onSubmit: (item: Partial<ScheduleItem>) => Promise<void>;
  onClose: () => void;
  submitting: boolean;
}

function AddBlockForm({ onSubmit, onClose, submitting }: AddBlockFormProps) {
  const [title, setTitle] = useState("");
  const [platform, setPlatform] = useState("tiktok");
  const [date, setDate] = useState(formatDateISO(new Date()));
  const [blockType, setBlockType] = useState("content");

  const color = getBlockColor(blockType);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    await onSubmit({
      title: title.trim(),
      platform,
      scheduled_at: `${date}T09:00:00`,
      block_type: blockType,
      color,
      status: "scheduled",
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="text-caption text-[var(--muted-foreground)] block mb-1.5">
          Title
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Film TikTok on AI agents"
          className="w-full bg-[#111118] border border-white/[0.06] rounded-lg px-3 py-2 text-body-sm text-white placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-purple-500/50"
        />
      </div>

      <div>
        <label className="text-caption text-[var(--muted-foreground)] block mb-1.5">
          Block Type
        </label>
        <div className="flex flex-wrap gap-2">
          {BLOCK_TYPES.map((bt) => (
            <button
              key={bt.value}
              type="button"
              onClick={() => setBlockType(bt.value)}
              className="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all"
              style={{
                background:
                  blockType === bt.value
                    ? `${bt.color}30`
                    : "rgba(255,255,255,0.03)",
                border: `1px solid ${blockType === bt.value ? bt.color : "rgba(255,255,255,0.06)"}`,
                color: blockType === bt.value ? bt.color : "#9494AD",
              }}
            >
              {bt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-caption text-[var(--muted-foreground)] block mb-1.5">
            Platform
          </label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="w-full bg-[#111118] border border-white/[0.06] rounded-lg px-3 py-2 text-body-sm text-white focus:outline-none focus:border-purple-500/50"
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-caption text-[var(--muted-foreground)] block mb-1.5">
            Date
          </label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full bg-[#111118] border border-white/[0.06] rounded-lg px-3 py-2 text-body-sm text-white focus:outline-none focus:border-purple-500/50"
          />
        </div>
      </div>

      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={submitting || !title.trim()}
          className="btn-pill btn-pill-primary flex items-center gap-2 disabled:opacity-50"
        >
          {submitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Plus className="w-4 h-4" />
          )}
          {submitting ? "Adding..." : "Add Block"}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="btn-pill btn-pill-outline"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

// --- Event Pill ---

function EventPill({ item, needsApproval }: { item: ScheduleItem; needsApproval?: boolean }) {
  const color = item.color || getBlockColor(item.block_type);
  return (
    <div
      className="h-6 rounded-md flex items-center gap-1 px-1.5 text-[11px] font-medium truncate"
      style={{
        backgroundColor: needsApproval ? `${color}10` : `${color}20`,
        borderLeft: `2px solid ${color}`,
        color: color,
        borderStyle: needsApproval ? "dashed" : "solid",
        borderLeftStyle: needsApproval ? "dashed" : "solid",
      }}
      title={`${item.title} (${item.platform})${needsApproval ? " — Needs Approval" : ""}`}
    >
      <span className="truncate">{item.title}</span>
      {needsApproval && (
        <span className="flex-shrink-0 ml-0.5 text-[9px] px-1 py-0 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
          !
        </span>
      )}
    </div>
  );
}

// --- Main Page ---

export default function SchedulePage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [viewMode, setViewMode] = useState<"month" | "week" | "2week">("2week");
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [draftItems, setDraftItems] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [weeklyHours, setWeeklyHours] = useState<Record<string, number>>({
    mon: 2, tue: 2, wed: 2, thu: 2, fri: 2, sat: 0, sun: 0,
  });

  // IDs of draft-generated schedule items (to show "needs approval" badge)
  const draftItemIds = useMemo(() => new Set(draftItems.map((d) => d.id)), [draftItems]);

  // Map JS getDay() (0=Sun) to our day keys
  const getDayKey = (date: Date): string => {
    const keys = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
    return keys[date.getDay()];
  };

  const fetchItems = useCallback(async () => {
    try {
      const start = new Date(year, month - 1, 1);
      const end = new Date(year, month + 2, 0);
      const [data, drafts, sched] = await Promise.all([
        api.getSchedule(formatDateISO(start), formatDateISO(end)),
        api.getDrafts("draft"),
        fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/settings/schedule`).then((r) => r.json()).catch(() => null),
      ]);
      if (sched && typeof sched === "object") setWeeklyHours(sched);

      // Convert Content Studio drafts to virtual schedule items
      // Skip drafts that already have a real schedule item (to avoid duplicates)
      const scheduledDraftIds = new Set(data.filter((s) => s.draft_id).map((s) => s.draft_id));
      const draftScheduleItems: ScheduleItem[] = drafts
        .filter((d: ContentDraft) => !scheduledDraftIds.has(d.id))
        .map((d: ContentDraft, i: number) => {
          // Spread unscheduled drafts across upcoming days (1 per day)
          const schedDate = d.suggested_post_time
            ? d.suggested_post_time
            : (() => {
                const future = new Date();
                future.setDate(future.getDate() + i + 1);
                return `${formatDateISO(future)}T10:00:00`;
              })();
          return {
            id: -(d.id),
            draft_id: d.id,
            title: d.title,
            platform: d.platform,
            scheduled_at: schedDate,
            status: "scheduled",
            block_type: "content",
            color: "#F59E0B",
            created_at: d.created_at,
          } as ScheduleItem;
        });

      setItems(data);
      setDraftItems(draftScheduleItems);
      setError(null);
    } catch {
      setError(
        "Cannot reach backend. Make sure FastAPI is running on port 8000."
      );
    } finally {
      setLoading(false);
    }
  }, [year, month]);

  useEffect(() => {
    setLoading(true);
    fetchItems();
  }, [fetchItems]);

  const handlePrevMonth = () => {
    if (month === 0) {
      setYear((y) => y - 1);
      setMonth(11);
    } else {
      setMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (month === 11) {
      setYear((y) => y + 1);
      setMonth(0);
    } else {
      setMonth((m) => m + 1);
    }
  };

  const handleAddBlock = async (data: Partial<ScheduleItem>) => {
    setSubmitting(true);
    try {
      await api.createScheduleItem(data);
      await fetchItems();
      setShowForm(false);
    } catch {
      // silent
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteItem = async (id: number) => {
    try {
      await api.deleteScheduleItem(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch {
      // silent
    }
  };

  // --- Calendar grid computation ---

  const calendarDays = useMemo(() => {
    const firstDay = startOfMonth(year, month).getDay(); // 0=Sun
    const totalDays = daysInMonth(year, month);
    const cells: Array<{ date: Date; inMonth: boolean }> = [];

    // Padding days from previous month
    const prevMonthDays = daysInMonth(
      month === 0 ? year - 1 : year,
      month === 0 ? 11 : month - 1
    );
    for (let i = firstDay - 1; i >= 0; i--) {
      cells.push({
        date: new Date(
          month === 0 ? year - 1 : year,
          month === 0 ? 11 : month - 1,
          prevMonthDays - i
        ),
        inMonth: false,
      });
    }

    // Current month days
    for (let d = 1; d <= totalDays; d++) {
      cells.push({ date: new Date(year, month, d), inMonth: true });
    }

    // Padding days for next month to fill last row
    const remaining = 7 - (cells.length % 7);
    if (remaining < 7) {
      for (let d = 1; d <= remaining; d++) {
        cells.push({
          date: new Date(
            month === 11 ? year + 1 : year,
            month === 11 ? 0 : month + 1,
            d
          ),
          inMonth: false,
        });
      }
    }

    return cells;
  }, [year, month]);

  // For week view: find the week containing today (or first of month)
  const weekDays = useMemo(() => {
    const target =
      year === today.getFullYear() && month === today.getMonth()
        ? today
        : new Date(year, month, 1);
    const dayOfWeek = target.getDay();
    const weekStart = new Date(target);
    weekStart.setDate(target.getDate() - dayOfWeek);
    const days: Array<{ date: Date; inMonth: boolean }> = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(weekStart);
      d.setDate(weekStart.getDate() + i);
      days.push({ date: d, inMonth: d.getMonth() === month });
    }
    return days;
  }, [year, month]);

  // 2-week view: this week + next week (14 days starting from Sunday of current week)
  const twoWeekDays = useMemo(() => {
    const dayOfWeek = today.getDay();
    const weekStart = new Date(today);
    weekStart.setDate(today.getDate() - dayOfWeek);
    const days: Array<{ date: Date; inMonth: boolean }> = [];
    for (let i = 0; i < 14; i++) {
      const d = new Date(weekStart);
      d.setDate(weekStart.getDate() + i);
      days.push({ date: d, inMonth: true });
    }
    return days;
  }, []);

  const visibleDays =
    viewMode === "month" ? calendarDays :
    viewMode === "2week" ? twoWeekDays :
    weekDays;

  // All items including drafts
  const allItems = useMemo(() => [...items, ...draftItems], [items, draftItems]);

  // Events lookup by date string
  const eventsByDate = useMemo(() => {
    const map: Record<string, ScheduleItem[]> = {};
    for (const item of allItems) {
      const key = item.scheduled_at.slice(0, 10);
      if (!map[key]) map[key] = [];
      map[key].push(item);
    }
    return map;
  }, [allItems]);

  // Upcoming 7 days
  const upcoming = useMemo(() => {
    const result: Array<{ date: Date; items: ScheduleItem[] }> = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date();
      d.setDate(d.getDate() + i);
      const key = formatDateISO(d);
      const dayItems = eventsByDate[key] || [];
      result.push({ date: d, items: dayItems });
    }
    return result;
  }, [eventsByDate]);

  // --- Render ---

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          <span className="text-body-sm text-[var(--muted-foreground)]">
            Loading schedule...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-5">
        <div className="text-subtitle text-pink-400">{error}</div>
        <button
          onClick={() => {
            setError(null);
            setLoading(true);
            fetchItems();
          }}
          className="btn-pill btn-pill-primary flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-10 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Calendar className="w-6 h-6 text-purple-400" />
          <h1 className="text-heading text-white">Schedule</h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Month nav */}
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevMonth}
              className="w-8 h-8 rounded-lg flex items-center justify-center border border-white/[0.06] hover:bg-white/[0.04] transition-colors"
            >
              <ChevronLeft className="w-4 h-4 text-[var(--muted-foreground)]" />
            </button>
            <span className="text-subtitle text-white min-w-[160px] text-center">
              {monthLabel(year, month)}
            </span>
            <button
              onClick={handleNextMonth}
              className="w-8 h-8 rounded-lg flex items-center justify-center border border-white/[0.06] hover:bg-white/[0.04] transition-colors"
            >
              <ChevronRight className="w-4 h-4 text-[var(--muted-foreground)]" />
            </button>
          </div>

          {/* View toggle */}
          <div className="flex bg-[#111118] rounded-full p-0.5 border border-white/[0.06]">
            {(["2week", "week", "month"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`px-4 py-1.5 rounded-full text-[12px] font-medium transition-all ${
                  viewMode === mode
                    ? "bg-purple-500/20 text-purple-400"
                    : "text-[var(--muted-foreground)] hover:text-white"
                }`}
              >
                {mode === "2week" ? "2 Weeks" : mode === "week" ? "Week" : "Month"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main layout: calendar + sidebar */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-6">
        {/* Calendar Grid */}
        <div className="elevated-card rounded-2xl p-4 overflow-hidden flex flex-col" style={{ minHeight: "calc(100vh - 200px)" }}>
          {/* Day headers — only for month view (7-col) */}
          {viewMode === "month" && (
            <div className="grid grid-cols-7 mb-1">
              {DAY_NAMES.map((d) => (
                <div
                  key={d}
                  className="text-center text-caption text-[var(--muted-foreground)] py-2"
                >
                  {d}
                </div>
              ))}
            </div>
          )}

          {/* Day cells — responsive: 2 cols mobile, wider on desktop */}
          <div
            className={`flex-1 grid ${
              viewMode === "month"
                ? "grid-cols-4 sm:grid-cols-7"
                : viewMode === "2week"
                  ? "grid-cols-2 sm:grid-cols-3 lg:grid-cols-5"
                  : "grid-cols-2 sm:grid-cols-4 lg:grid-cols-7"
            }`}
            style={{ gridAutoRows: "1fr" }}
          >
            {visibleDays.map(({ date, inMonth }, idx) => {
              const key = formatDateISO(date);
              const dayEvents = eventsByDate[key] || [];
              const isToday = isSameDay(date, today);
              const showDayName = viewMode !== "month";
              const dayKey = getDayKey(date);
              const hoursAvail = weeklyHours[dayKey] ?? 0;
              const isDayOff = hoursAvail === 0;

              return (
                <div
                  key={idx}
                  className={`border border-white/[0.04] p-2 sm:p-2 transition-colors min-h-[80px] ${
                    isDayOff && inMonth ? "bg-red-500/[0.03]" : "hover:bg-white/[0.02]"
                  } ${isToday ? "border-purple-500/60" : ""} ${!inMonth ? "opacity-30" : ""}`}
                >
                  <div
                    className={`text-[13px] sm:text-[12px] font-semibold mb-1.5 flex items-center gap-1 ${
                      isToday
                        ? "text-purple-400"
                        : isDayOff
                          ? "text-red-400/60"
                          : "text-[var(--muted-foreground)]"
                    }`}
                  >
                    <span
                      className={
                        isToday
                          ? "bg-purple-500/20 rounded-full w-6 h-6 inline-flex items-center justify-center"
                          : ""
                      }
                    >
                      {date.getDate()}
                    </span>
                    {showDayName && (
                      <span className="text-[12px] sm:text-[11px]">
                        {date.toLocaleDateString("en-US", { weekday: "short" })}
                      </span>
                    )}
                    {/* Hours badge */}
                    {inMonth && !isDayOff && hoursAvail > 0 && (
                      <span className="text-[10px] sm:text-[9px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-300 ml-auto font-bold">
                        {hoursAvail}h
                      </span>
                    )}
                    {inMonth && isDayOff && (
                      <span className="text-[10px] sm:text-[9px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-400 ml-auto font-bold">
                        off
                      </span>
                    )}
                  </div>
                  <div className="space-y-1">
                    {dayEvents.slice(0, viewMode === "month" ? 3 : 6).map((item) => (
                      <EventPill key={item.id} item={item} needsApproval={item.id < 0 || draftItemIds.has(item.id)} />
                    ))}
                    {dayEvents.length > (viewMode === "month" ? 3 : 6) && (
                      <div className="text-[10px] text-[var(--muted-foreground)] px-1">
                        +{dayEvents.length - (viewMode === "month" ? 3 : 6)} more
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Empty state */}
          {allItems.length === 0 && (
            <div className="py-16 text-center">
              <Calendar className="w-12 h-12 text-purple-400/20 mx-auto mb-4" />
              <p className="text-body text-[var(--muted-foreground)]">
                No scheduled blocks yet.
              </p>
              <p className="text-body-sm text-[var(--muted-foreground)] mt-1">
                Add your first content block to get started.
              </p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-5">
          {/* Add Block */}
          <div className="elevated-card rounded-2xl p-4">
            {showForm ? (
              <>
                <h3 className="text-label text-[var(--muted-foreground)] mb-4">
                  Add Block
                </h3>
                <AddBlockForm
                  onSubmit={handleAddBlock}
                  onClose={() => setShowForm(false)}
                  submitting={submitting}
                />
              </>
            ) : (
              <button
                onClick={() => setShowForm(true)}
                className="btn-pill btn-pill-primary w-full flex items-center justify-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Block
              </button>
            )}
          </div>

          {/* Block type legend */}
          <div className="elevated-card rounded-2xl p-4">
            <h3 className="text-label text-[var(--muted-foreground)] mb-3">
              Block Types
            </h3>
            <div className="space-y-2">
              {BLOCK_TYPES.map((bt) => (
                <div key={bt.value} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-sm"
                    style={{ backgroundColor: bt.color }}
                  />
                  <span className="text-body-sm text-white">{bt.label}</span>
                </div>
              ))}
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-sm border border-dashed border-amber-400"
                  style={{ backgroundColor: "#F59E0B20" }}
                />
                <span className="text-body-sm text-amber-400">Needs Approval</span>
              </div>
            </div>
          </div>

          {/* Upcoming */}
          <div className="elevated-card rounded-2xl p-4">
            <h3 className="text-label text-[var(--muted-foreground)] mb-3">
              Upcoming 7 Days
            </h3>
            <div className="space-y-3">
              {upcoming.map(({ date: d, items: dayItems }, i) => {
                const label =
                  i === 0
                    ? "Today"
                    : i === 1
                      ? "Tomorrow"
                      : d.toLocaleDateString("en-US", {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                        });

                return (
                  <div key={i}>
                    <div className="text-caption text-[var(--muted-foreground)] mb-1">
                      {label}
                    </div>
                    {dayItems.length === 0 ? (
                      <div className="text-[11px] text-[var(--muted-foreground)]/50 italic pl-1">
                        No blocks
                      </div>
                    ) : (
                      <div className="space-y-1">
                        {dayItems.map((item) => (
                          <div
                            key={item.id}
                            className="flex items-center justify-between group"
                          >
                            <div className="flex-1 min-w-0">
                              <EventPill item={item} needsApproval={item.id < 0 || draftItemIds.has(item.id)} />
                            </div>
                            {item.id > 0 && (
                              <button
                                onClick={() => handleDeleteItem(item.id)}
                                className="opacity-0 group-hover:opacity-100 transition-opacity ml-1 p-0.5 rounded hover:bg-white/[0.06]"
                                title="Remove"
                              >
                                <X className="w-3 h-3 text-[var(--muted-foreground)]" />
                              </button>
                            )}
                            {item.id < 0 && (
                              <span className="text-[9px] text-amber-400 ml-1 flex-shrink-0">
                                Needs Approval
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
