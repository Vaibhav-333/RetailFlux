import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { updateUserPrefsApi } from "@/features/prefs/api";

type Density = "comfortable" | "compact";

interface UserPrefs {
  density: Density;
}

interface PrefsContextValue {
  prefs: UserPrefs;
  setDensity: (d: Density) => void;
}

const PrefsContext = createContext<PrefsContextValue>({
  prefs: { density: "comfortable" },
  setDensity: () => {},
});

const STORAGE_KEY = "rf:prefs";

function loadPrefs(): UserPrefs {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<UserPrefs>;
      return { density: parsed.density ?? "comfortable" };
    }
  } catch {
    // ignore parse errors
  }
  return { density: "comfortable" };
}

function savePrefs(prefs: UserPrefs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // ignore storage errors
  }
}

export function PrefsProvider({ children }: { children: React.ReactNode }) {
  const [prefs, setPrefs] = useState<UserPrefs>(loadPrefs);

  // Apply/remove density-compact body class
  useEffect(() => {
    const body = document.body;
    if (prefs.density === "compact") {
      body.classList.add("density-compact");
    } else {
      body.classList.remove("density-compact");
    }
  }, [prefs.density]);

  const setDensity = useCallback(
    (density: Density) => {
      const next: UserPrefs = { ...prefs, density };
      setPrefs(next);
      savePrefs(next);
      // Sync to server fire-and-forget; non-blocking so UI stays instant
      void updateUserPrefsApi({ density }).catch(() => {});
    },
    [prefs]
  );

  return (
    <PrefsContext.Provider value={{ prefs, setDensity }}>
      {children}
    </PrefsContext.Provider>
  );
}

export function usePrefs() {
  return useContext(PrefsContext);
}
