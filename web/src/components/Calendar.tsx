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

interface Props {
  days: DaySummary[];
  onDayClick: (date: string) => void;
}

function levelFromChecked(checked: number): 0 | 1 | 2 | 3 | 4 {
  if (checked === 0) return 0;
  if (checked <= 2) return 1;
  if (checked === 3) return 2;
  if (checked <= 5) return 3;
  return 4;
}

export function Calendar({ days, onDayClick }: Props) {
  const [month, setMonth] = useState(() => startOfMonth(new Date()));
  const byDate = new Map(days.map((d) => [d.date, d] as const));
  const today = new Date();

  const dark = isDarkScheme();
  const levelBg = dark
    ? ["#1f2937", "#0a4a3a", "#177a5d", "#1faf83", "#27d99b"]
    : ["#f1f5f9", "#9be9a8", "#40c463", "#30a14e", "#216e39"];
  const levelText = dark
    ? ["#9ca3af", "#e5e7eb", "#ffffff", "#ffffff", "#ffffff"]
    : ["#475569", "#0f172a", "#ffffff", "#ffffff", "#ffffff"];

  const firstDay = startOfMonth(month);
  const lastDay = endOfMonth(month);
  const daysInMonth = eachDayOfInterval({ start: firstDay, end: lastDay });
  // Mon=0..Sun=6
  const leadingBlanks = (getDay(firstDay) + 6) % 7;

  const canGoNext = !isFuture(addMonths(month, 1));

  return (
    <div>
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

      <div className="grid grid-cols-7 gap-1.5 mb-1.5 text-xs text-tg-hint text-center">
        {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((d) => (
          <div key={d}>{d}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1.5">
        {Array.from({ length: leadingBlanks }).map((_, i) => (
          <div key={`blank-${i}`} />
        ))}
        {daysInMonth.map((d) => {
          const iso = format(d, "yyyy-MM-dd");
          const summary = byDate.get(iso);
          const checked = summary?.checked_count ?? 0;
          const level = summary ? levelFromChecked(checked) : 0;
          const future = isFuture(d) && !isSameDay(d, today);
          const isToday_ = isToday(d);
          return (
            <button
              key={iso}
              type="button"
              onClick={() => !future && onDayClick(iso)}
              disabled={future}
              className={`aspect-square rounded-lg text-sm font-medium flex flex-col items-center justify-center transition ${
                future ? "opacity-30 cursor-default" : "hover:scale-105"
              } ${isToday_ ? "ring-2 ring-tg-button" : ""}`}
              style={{
                background: summary ? levelBg[level] : "transparent",
                color: summary ? levelText[level] : "var(--tg-hint)",
                border: summary ? "0" : "1px dashed var(--tg-hint)",
              }}
              aria-label={`${iso}, ${checked} из 6`}
            >
              <span className="leading-none">{format(d, "d")}</span>
              {summary && (
                <span className="text-[10px] opacity-70 mt-0.5 leading-none">
                  {checked}/{summary.total_habits}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
