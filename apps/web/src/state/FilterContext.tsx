import {
  createContext,
  useContext,
  useState,
  useMemo,
  useCallback,
  type ReactNode,
} from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
export type Preset = "7d" | "28d" | "qtd" | "ytd" | "custom";
export type CompareTo = "" | "previous_period" | "previous_year";

export interface ParsedDim {
  key: string;
  value: string;
  raw: string;
}

// ─── Date math ────────────────────────────────────────────────────────────────
function isoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function presetToDates(preset: Preset): { dateFrom: string; dateTo: string } {
  const today = new Date();
  const dateTo = isoDate(today);

  if (preset === "7d") {
    const d = new Date(today);
    d.setDate(d.getDate() - 7);
    return { dateFrom: isoDate(d), dateTo };
  }
  if (preset === "28d") {
    const d = new Date(today);
    d.setDate(d.getDate() - 28);
    return { dateFrom: isoDate(d), dateTo };
  }
  if (preset === "qtd") {
    const q = Math.floor(today.getMonth() / 3);
    return { dateFrom: isoDate(new Date(today.getFullYear(), q * 3, 1)), dateTo };
  }
  if (preset === "ytd") {
    return { dateFrom: isoDate(new Date(today.getFullYear(), 0, 1)), dateTo };
  }
  // custom — defaults to last 28 days until user changes manually
  const d = new Date(today);
  d.setDate(d.getDate() - 28);
  return { dateFrom: isoDate(d), dateTo };
}

// ─── Dim helpers ──────────────────────────────────────────────────────────────
export function parseDims(dims: string): ParsedDim[] {
  return dims
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((raw) => {
      const eq = raw.indexOf("=");
      if (eq < 0) return { key: raw, value: "", raw };
      return { key: raw.slice(0, eq).trim(), value: raw.slice(eq + 1).trim(), raw };
    });
}

function setDim(dims: string, key: string, value: string): string {
  const parts = parseDims(dims).filter((d) => d.key !== key);
  parts.push({ key, value, raw: `${key}=${value}` });
  return parts.map((d) => d.raw).join(",");
}

function removeDimFromStr(dims: string, key: string): string {
  return parseDims(dims)
    .filter((d) => d.key !== key)
    .map((d) => d.raw)
    .join(",");
}

// ─── Context definition ───────────────────────────────────────────────────────
interface FilterContextValue {
  preset: Preset;
  dateFrom: string;
  dateTo: string;
  compareTo: CompareTo;
  dims: string;
  parsedDims: ParsedDim[];

  setPreset: (p: Preset) => void;
  setDateFrom: (v: string) => void;
  setDateTo: (v: string) => void;
  setCompareTo: (v: CompareTo) => void;
  setDims: (v: string) => void;
  /** Add or update a single dim key=value */
  addDim: (key: string, value: string) => void;
  /** Remove a dim by key */
  removeDim: (key: string) => void;
}

const FilterContext = createContext<FilterContextValue | null>(null);

// ─── Provider ─────────────────────────────────────────────────────────────────
const DEFAULT_PRESET: Preset = "28d";

export function FilterProvider({ children }: { children: ReactNode }) {
  const initial = presetToDates(DEFAULT_PRESET);

  const [preset, setPresetState] = useState<Preset>(DEFAULT_PRESET);
  const [dateFrom, setDateFromState] = useState(initial.dateFrom);
  const [dateTo, setDateToState] = useState(initial.dateTo);
  const [compareTo, setCompareTo] = useState<CompareTo>("");
  const [dims, setDimsState] = useState("");

  const setPreset = useCallback((p: Preset) => {
    setPresetState(p);
    if (p !== "custom") {
      const { dateFrom: f, dateTo: t } = presetToDates(p);
      setDateFromState(f);
      setDateToState(t);
    }
  }, []);

  const setDateFrom = useCallback((v: string) => {
    setDateFromState(v);
    setPresetState("custom");
  }, []);

  const setDateTo = useCallback((v: string) => {
    setDateToState(v);
    setPresetState("custom");
  }, []);

  const setDims = useCallback((v: string) => {
    setDimsState(v);
  }, []);

  const addDim = useCallback((key: string, value: string) => {
    setDimsState((prev) => setDim(prev, key, value));
  }, []);

  const removeDim = useCallback((key: string) => {
    setDimsState((prev) => removeDimFromStr(prev, key));
  }, []);

  const parsedDims = useMemo(() => parseDims(dims), [dims]);

  const value = useMemo<FilterContextValue>(
    () => ({
      preset,
      dateFrom,
      dateTo,
      compareTo,
      dims,
      parsedDims,
      setPreset,
      setDateFrom,
      setDateTo,
      setCompareTo,
      setDims,
      addDim,
      removeDim,
    }),
    [
      preset,
      dateFrom,
      dateTo,
      compareTo,
      dims,
      parsedDims,
      setPreset,
      setDateFrom,
      setDateTo,
      setCompareTo,
      setDims,
      addDim,
      removeDim,
    ]
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────
export function useFilters(): FilterContextValue {
  const ctx = useContext(FilterContext);
  if (!ctx) throw new Error("useFilters must be used within <FilterProvider>");
  return ctx;
}
