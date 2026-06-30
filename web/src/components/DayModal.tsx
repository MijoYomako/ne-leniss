import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";

import { api } from "../lib/api";

interface Props {
  date: string;
  onClose: () => void;
}

const MOOD_EMOJI: Record<string, string> = {
  Good: "😊",
  Productive: "⚡",
  "Could be better": "🤔",
  Bad: "😞",
  Relaxing: "🌿",
};

export function DayModal({ date, onClose }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["day", date],
    queryFn: () => api.dayDetail(date),
  });

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-tg-bg w-full sm:max-w-md sm:rounded-2xl rounded-t-2xl p-5 max-h-[85vh] overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">
            {format(parseISO(date), "d MMM yyyy")}
          </h2>
          <button
            onClick={onClose}
            className="text-tg-hint hover:text-tg-text text-2xl leading-none"
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>

        {isLoading && <p className="text-tg-hint">Загрузка…</p>}
        {error && <p className="text-red-500 text-sm">Ошибка загрузки</p>}

        {data && (
          <>
            <section className="mb-5">
              <h3 className="text-sm uppercase text-tg-hint mb-2 tracking-wide">
                Привычки
              </h3>
              <ul className="space-y-1.5">
                {data.habits.map((h) => (
                  <li key={h.key} className="flex items-center gap-2">
                    <span className={h.checked ? "" : "opacity-30"}>
                      {h.checked ? "☑" : "☐"}
                    </span>
                    <span className={h.checked ? "" : "text-tg-hint"}>{h.label}</span>
                  </li>
                ))}
              </ul>
            </section>

            {data.mood && (
              <section className="mb-5">
                <h3 className="text-sm uppercase text-tg-hint mb-2 tracking-wide">
                  Настроение
                </h3>
                <p>
                  {MOOD_EMOJI[data.mood] ?? "•"} {data.mood}
                </p>
              </section>
            )}

            {data.plans.length > 0 && (
              <section className="mb-5">
                <h3 className="text-sm uppercase text-tg-hint mb-2 tracking-wide">
                  Планы
                </h3>
                <ul className="space-y-2">
                  {data.plans.map((p, i) => (
                    <li key={i} className="whitespace-pre-wrap">{p}</li>
                  ))}
                </ul>
              </section>
            )}

            {data.journal.length > 0 && (
              <section className="mb-2">
                <h3 className="text-sm uppercase text-tg-hint mb-2 tracking-wide">
                  Журнал
                </h3>
                <ul className="space-y-2">
                  {data.journal.map((j, i) => (
                    <li key={i} className="whitespace-pre-wrap">{j}</li>
                  ))}
                </ul>
              </section>
            )}

            {!data.mood && data.plans.length === 0 && data.journal.length === 0 && (
              <p className="text-tg-hint text-sm">Этот день пустой.</p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
