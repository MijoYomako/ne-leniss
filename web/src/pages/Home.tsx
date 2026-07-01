import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, subDays } from "date-fns";

import { api } from "../lib/api";
import { Calendar } from "../components/Calendar";
import { DayModal } from "../components/DayModal";
import { StreakCard } from "../components/StreakCard";

export function Home() {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const today = useMemo(() => new Date(), []);
  const from = format(subDays(today, 89), "yyyy-MM-dd");
  const to = format(today, "yyyy-MM-dd");
  const todayIso = format(today, "yyyy-MM-dd");

  const meQ = useQuery({ queryKey: ["me"], queryFn: api.me });
  const daysQ = useQuery({
    queryKey: ["days", from, to],
    queryFn: () => api.days(from, to),
  });
  const streaksQ = useQuery({ queryKey: ["streaks"], queryFn: api.streaks });
  const todayDetailQ = useQuery({
    queryKey: ["day", todayIso],
    queryFn: () => api.dayDetail(todayIso),
  });

  const todayPlans = (todayDetailQ.data?.plans ?? [])
    .flatMap((p) => p.split("\n"))
    .map((l) => l.trim())
    .filter(Boolean);

  return (
    <div className="min-h-screen px-4 py-5 max-w-2xl mx-auto">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">
          Салют, {meQ.data?.first_name ?? "друг"} 👋
        </h1>
        <div className="mt-3">
          <div className="text-xs uppercase text-tg-hint tracking-wider font-semibold mb-1.5">
            Планы на сегодня
          </div>
          {todayPlans.length > 0 ? (
            <ul className="space-y-1">
              {todayPlans.map((line, i) => (
                <li key={i} className="flex gap-2 text-sm leading-relaxed">
                  <span className="text-tg-hint mt-0.5">•</span>
                  <span className="flex-1">{line}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-tg-hint">
              Пока пусто. Запиши план через /plan в чате бота.
            </p>
          )}
        </div>
      </header>

      <section className="mb-8">
        {daysQ.isLoading && <p className="text-tg-hint">Загрузка календаря…</p>}
        {daysQ.error && <p className="text-red-500 text-sm">Не удалось загрузить календарь</p>}
        {daysQ.data && (
          <Calendar days={daysQ.data} onDayClick={(d) => setSelectedDate(d)} />
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Стрики</h2>
        {streaksQ.isLoading && <p className="text-tg-hint">Загрузка…</p>}
        {streaksQ.data && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {streaksQ.data.map((s) => (
              <StreakCard key={s.key} streak={s} />
            ))}
          </div>
        )}
      </section>

      {selectedDate && (
        <DayModal date={selectedDate} onClose={() => setSelectedDate(null)} />
      )}
    </div>
  );
}
