import { getInitData } from "./tg";

const API_BASE = import.meta.env.VITE_API_URL || "";
const DEV_UID = import.meta.env.VITE_DEV_UID;

async function request<T>(path: string): Promise<T> {
  const initData = getInitData();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  let url = `${API_BASE}${path}`;
  if (initData) {
    headers["Authorization"] = `tma ${initData}`;
  } else if (DEV_UID && import.meta.env.DEV) {
    url += `${path.includes("?") ? "&" : "?"}uid=${DEV_UID}`;
  }
  const res = await fetch(url, { headers });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface MeResponse {
  tg_id: number;
  username: string | null;
  first_name: string | null;
  timezone: string;
}

export interface DaySummary {
  date: string;
  checked_count: number;
  total_habits: number;
  mood: string | null;
  has_plans: boolean;
  has_journal: boolean;
}

export interface DayDetail {
  date: string;
  mood: string | null;
  habits: { key: string; label: string; checked: boolean }[];
  plans: string[];
  journal: string[];
}

export interface Streak {
  key: string;
  label: string;
  current: number;
  best: number;
}

export const api = {
  me: () => request<MeResponse>("/api/me"),
  days: (from: string, to: string) =>
    request<DaySummary[]>(`/api/days?from=${from}&to=${to}`),
  dayDetail: (date: string) => request<DayDetail>(`/api/days/${date}`),
  streaks: () => request<Streak[]>("/api/streaks"),
};
