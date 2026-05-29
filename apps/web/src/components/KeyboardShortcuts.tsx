import { useEffect, useState } from "react";
import { Keyboard, X } from "lucide-react";

interface Shortcut {
  keys: string[];
  description: string;
  group: string;
}

const SHORTCUTS: Shortcut[] = [
  // Navigation
  { group: "Navigation", keys: ["⌘", "K"], description: "Open command palette" },
  { group: "Navigation", keys: ["⌘", "P"], description: "Go to a page" },
  { group: "Navigation", keys: ["⌘", "."], description: "Run a command" },
  { group: "Navigation", keys: ["⌘", "/"], description: "Ask AI (inline)" },
  { group: "Navigation", keys: ["]"], description: "Toggle context rail" },
  // AI
  { group: "AI", keys: ["⌘", "J"], description: "Toggle AI Copilot dock" },
  // Display
  { group: "Display", keys: ["?"], description: "Show keyboard shortcuts" },
  { group: "Display", keys: ["Esc"], description: "Close panel / clear selection" },
];

const GROUPS = [...new Set(SHORTCUTS.map((s) => s.group))];

function Kbd({ children }: { children: string }) {
  return (
    <kbd className="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-1.5 rounded border border-border bg-muted text-[10px] font-mono font-semibold text-muted-foreground shadow-sm">
      {children}
    </kbd>
  );
}

interface KeyboardShortcutsProps {
  open: boolean;
  onClose: () => void;
}

export function KeyboardShortcuts({ open, onClose }: KeyboardShortcutsProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Keyboard shortcuts"
        className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-card border border-border rounded-xl shadow-2xl overflow-hidden animate-in fade-in-0 zoom-in-95"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Keyboard className="w-4 h-4 text-brand-500" />
            <span className="text-sm font-semibold text-foreground">Keyboard Shortcuts</span>
          </div>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 rounded outline-none"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5 max-h-[60vh] overflow-y-auto">
          {GROUPS.map((group) => (
            <div key={group}>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">
                {group}
              </p>
              <div className="space-y-1.5">
                {SHORTCUTS.filter((s) => s.group === group).map((shortcut) => (
                  <div
                    key={shortcut.description}
                    className="flex items-center justify-between gap-4"
                  >
                    <span className="text-sm text-foreground">{shortcut.description}</span>
                    <div className="flex items-center gap-1 shrink-0">
                      {shortcut.keys.map((k, i) => (
                        <span key={i} className="flex items-center gap-1">
                          <Kbd>{k}</Kbd>
                          {i < shortcut.keys.length - 1 && (
                            <span className="text-muted-foreground text-xs">+</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="px-5 py-3 border-t border-border bg-muted/30">
          <p className="text-xs text-muted-foreground text-center">
            Press <Kbd>?</Kbd> to toggle this panel
          </p>
        </div>
      </div>
    </>
  );
}

/** Global hook: press ? to open, Escape to close. */
export function useKeyboardShortcuts() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement).isContentEditable) return;
      if (e.key === "?" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return { open, setOpen };
}
