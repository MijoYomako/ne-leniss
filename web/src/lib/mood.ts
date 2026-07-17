// Mood color palettes for calendar tile + modal accent.
// Palette choices:
//   Good        → grass green (light, warm)
//   Productive  → emerald / darker green (energetic, distinct from Good)
//   Normal      → neutral slate (deliberately unremarkable)
//   Could be better → amber (clearly not red)
//   Bad         → red
//   Relaxing    → sky blue (soft, restful)

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
    bgDark: "#166534",
    accent: "#22c55e",
    emoji: "😊",
    label: "Хороший",
  },
  Productive: {
    bgLight: "#a7f3d0",
    bgDark: "#047857",
    accent: "#10b981",
    emoji: "⚡",
    label: "Продуктивный",
  },
  Normal: {
    bgLight: "#e2e8f0",
    bgDark: "#334155",
    accent: "#64748b",
    emoji: "✅",
    label: "Обычный",
  },
  "Could be better": {
    bgLight: "#fde68a",
    bgDark: "#78350f",
    accent: "#eab308",
    emoji: "😕",
    label: "Могло бы быть лучше",
  },
  Bad: {
    bgLight: "#fecaca",
    bgDark: "#991b1b",
    accent: "#ef4444",
    emoji: "😞",
    label: "Плохой",
  },
  Relaxing: {
    bgLight: "#bae6fd",
    bgDark: "#075985",
    accent: "#0ea5e9",
    emoji: "🌿",
    label: "Расслабленный",
  },
};

export function moodVisual(mood: string | null): MoodVisual | null {
  if (!mood) return null;
  return MOOD[mood] ?? null;
}
