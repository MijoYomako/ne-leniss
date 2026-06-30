import type { Streak } from "../lib/api";

interface Props {
  streak: Streak;
}

export function StreakCard({ streak }: Props) {
  const hot = streak.current >= 3;
  return (
    <div className="bg-tg-secondary rounded-xl p-3 flex items-center justify-between">
      <div>
        <div className="font-medium">{streak.label}</div>
        <div className="text-xs text-tg-hint mt-0.5">
          Рекорд: {streak.best}
        </div>
      </div>
      <div className="text-right">
        <div className="text-2xl font-bold leading-none">
          {streak.current}
          {hot ? " 🔥" : ""}
        </div>
        <div className="text-xs text-tg-hint mt-1">
          {streak.current === 1 ? "день" : "дней"}
        </div>
      </div>
    </div>
  );
}
