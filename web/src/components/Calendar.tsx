import { useState } from "react";
import {
  addMonths,
  format,
  getDay,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameDay,
  isFuture,
  isToday,
} from "date-fns";
import { ru } from "date-fns/locale";

import type { DaySummary } from "../lib/api";
import { isDarkScheme } from "../lib/tg";
import { moodVisual } from "../lib/mood";

interface Props {
  days: DaySummary[];
  onDayClick: (date: string) => void;
}

type Mode = "habits" | "mood";

function levelFromChecked(checked: number, total: number): 0 | 1 | 2 | 3 | 4 {
  if (total === 0 || checked === 0) return 0;
  const ratio = checked / total;
  if (ratio <= 0.25) return 1;
  if (ratio <= 0.5) return 2;
  if (ratio <= 0.85) return 3;
  return 4;
}

export function Calendar({ days, onDayClick }: Props) {
  const [month, setMonth] = useState(() => startOfMonth(new Date()));
  const [mode, setMode] = useState<Mode>("habits");
  const byDate = new Map(days.map((d) => [d.date, d] as const));
  const today = new Date();
  const dark = isDarkScheme();

  const habitLevels = dark
    ? ["#1f2937", "#0a4a3a", "#177a5d", "#1faf83", "#27d99b"]
    : ["#f1f5f9", "#bbf7d0", "#86efac", "#22c55e", "#15803d"];
  const habitText = dark
    ? ["#9ca3af", "#e5e7eb", "#ffffff", "#ffffff", "#ffffff"]
    : ["#475569", "#0f172a", "#0f172a", "#ffffff", "#ffffff"];

  const firstDay = startOfMonth(month);
  const lastDay = endOfMonth(month);
  const daysInMonth = eachDayOfInterval({ start: firstDay, end: lastDay });
  const leadingBlanks = (getDay(firstDay) + 6) % 7;
  const canGoNext = !isFuture(addMonths(month, 1));

  function cellBg(summary: DaySummary | undefined): { bg: string; color: string } {
    if (!summary) return { bg: "transparent", color: "var(--tg-hint)" };
    if (mode === "habits") {
      const lvl = levelFromChecked(summary.checked_count, summary.total_habits);
      return { bg: habitLevels[lvl], color: habitText[lvl] };
    }
    const mv = moodVisual(summary.mood);
    if (!mv) return { bg: dark ? "#1f2937" : "#f1f5f9", color: "var(--tg-hint)" };
    return { bg: dark ? mv.bgDark : mv.bgLight, color: dark ? "#fff" : "#0f172a" };
  }

  return (
    <div>
      {/* Month nav */}
      <div className="flex items-center justify-between mb-3">
        <button
          type="button"
          onClick={() => setMonth(addMonths(month, -1))}
          className="px-3 py-1.5 rounded-lg bg-tg-secondary hover:opacity-80 text-base"
          aria-label="Предыдущий месяц"
        >
          ‹
        </button>
        <div className="text-lg font-semibold capitalize">
          {format(month, "LLLL yyyy", { locale: ru })}
        </div>
        <button
          type="button"
          onClick={() => canGoNext && setMonth(addMonths(month, 1))}
          disabled={!canGoNext}
          className="px-3 py-1.5 rounded-lg bg-tg-secondary hover:opacity-80 text-base disabled:opacity-30"
          aria-label="Следующий месяц"
        >
          ›
        </button>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 gap-1.5 mb-1.5 text-xs text-tg-hint text-center">
        {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((d) => (
          <div key={d}>{d}</div>
        ))}
      </div>

      {/* Cells */}
      <div className="grid grid-cols-7 gap-1.5">
        {Array.from({ length: leadingBlanks }).map((_, i) => (
          <div key={`blank-${i}`} />
        ))}
        {daysInMonth.map((d) => {
          const iso = format(d, "yyyy-MM-dd");
          const summary = byDate.get(iso);
          const future = isFuture(d) && !isSameDay(d, today);
          const isTodayCell = isToday(d);
          const style = cellBg(summary);
          return (
            <button
              key={iso}
              type="button"
              onClick={() => !future && onDayClick(iso)}
              disabled={future}
              className={`aspect-square rounded-lg text-sm font-medium flex flex-col items-center justify-center transition ${
                future ? "opacity-30 cursor-default" : "hover:scale-105"
              } ${isTodayCell ? "ring-2 ring-tg-button" : ""}`}
              style={{
                background: style.bg,
                color: style.color,
                border: summary ? "0" : "1px dashed var(--tg-hint)",
              }}
              aria-label={iso}
            >
              <span className="leading-none">{format(d, "d")}</span>
              {summary && mode === "habits" && (
                <span className="text-[10px] opacity-70 mt-0.5 leading-none">
                  {summary.checked_count}/{summary.total_habits}
                </span>
              )}
              {summary && mode === "mood" && summary.mood && (
                <span className="text-[10px] mt-0.5 leading-none">
                  {moodVisual(summary.mood)?.emoji}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Mode toggle */}
      <div className="mt-4 flex justify-center gap-1 bg-tg-secondary rounded-xl p-1">
        <button
          type="button"
          onClick={() => setMode("habits")}
          className={`flex-1 py-1.5 px-3 rounded-lg text-sm font-medium transition ${
            mode === "habits"
              ? "bg-tg-bg shadow-sm"
              : "text-tg-hint hover:text-tg-text"
          }`}
        >
          По чекбоксам
        </button>
        <button
          type="button"
          onClick={() => setMode("mood")}
          className={`flex-1 py-1.5 px-3 rounded-lg text-sm font-medium transition ${
            mode === "mood"
              ? "bg-tg-bg shadow-sm"
              : "text-tg-hint hover:text-tg-text"
          }`}
        >
          По настроению
        </button>
      </div>
    </div>
  );
}
