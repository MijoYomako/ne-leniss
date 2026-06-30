interface TelegramWebApp {
  initData?: string;
  initDataUnsafe?: { user?: { id: number; first_name?: string; username?: string } };
  ready?: () => void;
  expand?: () => void;
  colorScheme?: "light" | "dark";
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

function webApp(): TelegramWebApp | undefined {
  return typeof window !== "undefined" ? window.Telegram?.WebApp : undefined;
}

let initialised = false;

export function initTelegram(): void {
  if (initialised) return;
  const wa = webApp();
  if (!wa) return;
  try {
    wa.ready?.();
    wa.expand?.();
    initialised = true;
  } catch {
    // noop
  }
}

export function getInitData(): string {
  return webApp()?.initData ?? "";
}

export function getTgUser(): { id: number; first_name?: string; username?: string } | null {
  return webApp()?.initDataUnsafe?.user ?? null;
}

export function isDarkScheme(): boolean {
  return webApp()?.colorScheme === "dark";
}
