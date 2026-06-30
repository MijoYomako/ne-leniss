import { format, subDays, getDay } from "date-fns";

import type { DaySummary } from "../lib/api";
import { isDarkScheme } from "../lib/tg";

interface Props {
  days: DaySummary[];
  onDayClick: (date: string) => void;
  rangeDays?: number;
}

const MONTH_LABELS = [
  "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
  "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
];

function levelFromChecked(checked: number): 0 | 1 | 2 | 3 | 4 {
  if (checked === 0) return 0;
  if (checked <= 2) return 1;
  if (checked === 3) return 2;
  if (checked <= 5) return 3;
  return 4;
}

export function Calendar({ days, onDayClick, rangeDays = 89 }: Props) {
  const today = new Date();
  const byDate = new Map(days.map((d) => [d.date, d] as const));

  const dark = isDarkScheme();
  const levelColors = dark
    ? ["#2c2c2e", "#0a4a3a", "#177a5d", "#1faf83", "#27d99b"]
    : ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"];

  // Build a 7-row grid (Mon..Sun) of weekly columns.
  // Pad the leading cells so today aligns to the right.
  // Get today's weekday (Mon=0..Sun=6)
  const todayWd = (getDay(today) + 6) % 7;
  const totalCells = rangeDays + 1 + (6 - todayWd);
  const weeks = Math.ceil(totalCells / 7);
  const startOffset = 7 * weeks - 1 - (6 - todayWd); // days back from today to first column row 0

  type Cell = { date: string | null; level: 0 | 1 | 2 | 3 | 4; count: number };
  const grid: Cell[][] = [];
  for (let col = 0; col < weeks; col++) {
    const colCells: Cell[] = [];
    for (let row = 0; row < 7; row++) {
      const cellIndex = col * 7 + row;
      const daysBack = startOffset - cellIndex;
      if (daysBack < 0 || daysBack > rangeDays) {
        colCells.push({ date: null, level: 0, count: 0 });
        continue;
      }
      const d = subDays(today, daysBack);
      const iso = format(d, "yyyy-MM-dd");
      const summary = byDate.get(iso);
      const checked = summary?.checked_count ?? 0;
      colCells.push({ date: iso, level: levelFromChecked(checked), count: checked });
    }
    grid.push(colCells);
  }

  // Build month labels — show month label above first column where the month changes.
  const monthLabels: { col: number; label: string }[] = [];
  let lastMonth = -1;
  grid.forEach((col, idx) => {
    const firstDay = col.find((c) => c.date !== null);
    if (!firstDay || !firstDay.date) return;
    const month = parseInt(firstDay.date.split("-")[1], 10) - 1;
    if (month !== lastMonth) {
      monthLabels.push({ col: idx, label: MONTH_LABELS[month] });
      lastMonth = month;
    }
  });

  const cellSize = 12;
  const cellGap = 3;

  return (
    <div className="inline-block">
      {/* Month labels */}
      <div
        className="relative ml-7 mb-1 h-4 text-xs text-tg-hint"
        style={{ width: weeks * (cellSize + cellGap) }}
      >
        {monthLabels.map((m) => (
          <span
            key={m.col}
            className="absolute"
            style={{ left: m.col * (cellSize + cellGap) }}
          >
            {m.label}
          </span>
        ))}
      </div>

      <div className="flex gap-[3px]">
        {/* Weekday labels */}
        <div className="flex flex-col gap-[3px] mr-1 text-xs text-tg-hint" style={{ width: 20 }}>
          {["Пн", "", "Ср", "", "Пт", "", "Вс"].map((d, i) => (
            <div key={i} style={{ height: cellSize, lineHeight: `${cellSize}px` }}>
              {d}
            </div>
          ))}
        </div>

        {/* Grid */}
        <div className="flex gap-[3px]">
          {grid.map((col, ci) => (
            <div key={ci} className="flex flex-col gap-[3px]">
              {col.map((cell, ri) => (
                <button
                  key={ri}
                  type="button"
                  onClick={() => cell.date && onDayClick(cell.date)}
                  disabled={!cell.date}
                  title={cell.date ? `${cell.date}: ${cell.count}/6` : ""}
                  style={{
                    width: cellSize,
                    height: cellSize,
                    background: cell.date ? levelColors[cell.level] : "transparent",
                    borderRadius: 2,
                    border: 0,
                    padding: 0,
                    cursor: cell.date ? "pointer" : "default",
                  }}
                  aria-label={cell.date ? `${cell.date}, ${cell.count} из 6` : "empty"}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-1.5 mt-2 ml-7 text-xs text-tg-hint">
        <span>меньше</span>
        {levelColors.map((c, i) => (
          <span
            key={i}
            style={{ width: cellSize, height: cellSize, background: c, borderRadius: 2 }}
          />
        ))}
        <span>больше</span>
      </div>
    </div>
  );
}
