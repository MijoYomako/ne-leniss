import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { ru } from "date-fns/locale";

import { api } from "../lib/api";
import { isDarkScheme } from "../lib/tg";
import { moodVisual } from "../lib/mood";

interface Props {
  date: string;
  onClose: () => void;
}

export function DayModal({ date, onClose }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["day", date],
    queryFn: () => api.dayDetail(date),
  });

  const dateObj = parseISO(date);
  const dark = isDarkScheme();
  const isEmpty =
    data &&
    !data.mood &&
    data.plans.length === 0 &&
    data.journal.length === 0 &&
    !data.habits.some((h) => h.checked);
  const mv = data ? moodVisual(data.mood) : null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-tg-bg w-full sm:max-w-lg sm:rounded-2xl rounded-t-2xl max-h-[88vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-tg-bg z-10 px-5 pt-5 pb-3 border-b border-tg-hint/20 flex items-start justify-between">
          <div>
            <div className="text-xs text-tg-hint uppercase tracking-wide">
              {format(dateObj, "EEEE", { locale: ru })}
            </div>
            <div className="text-2xl font-bold mt-0.5">
              {format(dateObj, "d MMMM yyyy", { locale: ru })}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-tg-hint hover:text-tg-text text-3xl leading-none -mt-1"
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>

        <div className="px-5 py-4 space-y-5">
          {isLoading && <p className="text-tg-hint">Загрузка…</p>}
          {error && <p className="text-red-500 text-sm">Ошибка загрузки</p>}

          {isEmpty && (
            <div className="text-center py-6 text-tg-hint text-sm">
              <div className="text-4xl mb-2">📭</div>
              <div>В этот день ничего не отмечено</div>
            </div>
          )}

          {data && !isEmpty && (
            <>
              {/* Habits */}
              <section>
                <h3 className="text-xs uppercase text-tg-hint mb-2 tracking-wider font-semibold">
                  Привычки
                </h3>
                <div className="flex flex-wrap gap-2">
                  {data.habits.map((h) => (
                    <div
                      key={h.key}
                      className={`px-3 py-1.5 rounded-full text-sm flex items-center gap-1.5 transition ${
                        h.checked
                          ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-500/40"
                          : "bg-tg-secondary text-tg-hint"
                      }`}
                    >
                      <span>{h.checked ? "✓" : "○"}</span>
                      <span>{h.label}</span>
                    </div>
                  ))}
                </div>
              </section>

              {/* День был */}
              {mv && (
                <section>
                  <h3 className="text-xs uppercase text-tg-hint mb-2 tracking-wider font-semibold">
                    День был
                  </h3>
                  <div
                    className="rounded-xl p-4 flex items-center gap-3 ring-1"
                    style={{
                      background: dark ? mv.bgDark : mv.bgLight,
                      color: dark ? "#fff" : "#0f172a",
                      borderColor: mv.accent,
                    }}
                  >
                    <div className="text-4xl">{mv.emoji}</div>
                    <div className="font-semibold text-lg">{mv.label}</div>
                  </div>
                </section>
              )}

              {/* Plans (bulleted, line-by-line) */}
              {data.plans.length > 0 && (
                <section>
                  <h3 className="text-xs uppercase text-tg-hint mb-2 tracking-wider font-semibold">
                    Планы
                  </h3>
                  <ul className="space-y-1.5">
                    {data.plans
                      .flatMap((p) => p.split("\n"))
                      .map((l) => l.trim())
                      .filter(Boolean)
                      .map((line, i) => (
                        <li key={i} className="flex gap-2 text-sm leading-relaxed">
                          <span className="text-tg-hint mt-0.5">•</span>
                          <span className="flex-1">{line}</span>
                        </li>
                      ))}
                  </ul>
                </section>
              )}

              {/* Journal */}
              {data.journal.length > 0 && (
                <section>
                  <h3 className="text-xs uppercase text-tg-hint mb-2 tracking-wider font-semibold">
                    Журнал
                  </h3>
                  <div className="space-y-2">
                    {data.journal.map((j, i) => (
                      <div
                        key={i}
                        className="bg-tg-secondary rounded-xl p-3 whitespace-pre-wrap text-sm leading-relaxed"
                      >
                        {j}
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
