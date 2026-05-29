/**
 * ChartCursorContext — global shared cursor position for the Bloomberg-style
 * synced crosshair across sibling charts on the same page.
 *
 * Usage:
 *   // In a chart's onMouseMove:
 *   const { setActiveX } = useChartCursor();
 *   // In SmartChart render props, pass activeX to Recharts' syncId charts
 *   // or use it to render a custom reference line.
 *
 * The context is provided at AppShell level so all charts in any dashboard share
 * the same cursor state.  Charts that don't interact simply ignore it.
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

interface ChartCursorContextValue {
  /** The currently hovered X value (date string or numeric index), or null. */
  activeX: string | number | null;
  /** Call from onMouseMove / onMouseEnter to broadcast the cursor position. */
  setActiveX: (x: string | number | null) => void;
}

const ChartCursorContext = createContext<ChartCursorContextValue>({
  activeX: null,
  setActiveX: () => undefined,
});

export function ChartCursorProvider({ children }: { children: ReactNode }) {
  const [activeX, setActiveXState] = useState<string | number | null>(null);

  const setActiveX = useCallback((x: string | number | null) => {
    setActiveXState(x);
  }, []);

  const value = useMemo(() => ({ activeX, setActiveX }), [activeX, setActiveX]);

  return (
    <ChartCursorContext.Provider value={value}>
      {children}
    </ChartCursorContext.Provider>
  );
}

export function useChartCursor(): ChartCursorContextValue {
  return useContext(ChartCursorContext);
}
