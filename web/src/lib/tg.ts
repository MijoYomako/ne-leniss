import WebApp from "@twa-dev/sdk";

let initialised = false;

export function initTelegram(): void {
  if (initialised) return;
  try {
    WebApp.ready();
    WebApp.expand();
    initialised = true;
  } catch {
    // Running in browser dev mode — TG WebApp not present
  }
}

export function getInitData(): string {
  try {
    return WebApp.initData ?? "";
  } catch {
    return "";
  }
}

export function getTgUser(): { id: number; first_name?: string; username?: string } | null {
  try {
    return WebApp.initDataUnsafe?.user ?? null;
  } catch {
    return null;
  }
}

export function isDarkScheme(): boolean {
  try {
    return WebApp.colorScheme === "dark";
  } catch {
    return false;
  }
}
