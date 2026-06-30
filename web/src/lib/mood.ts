// Mood color palettes for calendar tile + modal accent.
// Each entry: [light_bg, dark_bg, accent_border]

export interface MoodVisual {
  bgLight: string;
  bgDark: string;
  accent: string;
  emoji: string;
  label: string;
}

export const MOOD: Record<string, MoodVisual> = {
  Good: {
    bgLight: "#bbf7d0",
    bgDark: "#15803d",
    accent: "#22c55e",
    emoji: "😊",
    label: "Хороший",
  },
  Productive: {
    bgLight: "#fde68a",
    bgDark: "#b45309",
    accent: "#f59e0b",
    emoji: "⚡",
    label: "Продуктивный",
  },
  "Could be better": {
    bgLight: "#fed7aa",
    bgDark: "#9a3412",
    accent: "#fb923c",
    emoji: "🤔",
    label: "Так себе",
  },
  Bad: {
    bgLight: "#fecaca",
    bgDark: "#991b1b",
    accent: "#ef4444",
    emoji: "😞",
    label: "Плохой",
  },
  Relaxing: {
    bgLight: "#c7d2fe",
    bgDark: "#3730a3",
    accent: "#6366f1",
    emoji: "🌿",
    label: "Расслабленный",
  },
};

export function moodVisual(mood: string | null): MoodVisual | null {
  if (!mood) return null;
  return MOOD[mood] ?? null;
}
