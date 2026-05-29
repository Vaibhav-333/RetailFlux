import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface SheetProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  side?: "bottom" | "right";
  className?: string;
}

export function Sheet({
  open,
  onClose,
  title,
  children,
  side = "bottom",
  className,
}: SheetProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    if (open && panelRef.current) {
      const first = panelRef.current.querySelector<HTMLElement>(
        'button, [href], input, [tabindex]:not([tabindex="-1"])'
      );
      first?.focus();
    }
  }, [open]);

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[2px] animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          "fixed z-50 flex flex-col bg-[hsl(var(--surface-2))] shadow-2xl",
          side === "bottom"
            ? "inset-x-0 bottom-0 max-h-[85vh] rounded-t-xl border-t border-border animate-slide-up"
            : "top-0 right-0 bottom-0 w-full max-w-sm border-l border-border animate-slide-in-right",
          className
        )}
      >
        {/* Pull handle — bottom sheet only */}
        {side === "bottom" && (
          <div className="flex justify-center pt-3 pb-0 shrink-0" aria-hidden>
            <div className="w-8 h-1 rounded-full bg-border" />
          </div>
        )}

        {title && (
          <div className="flex items-center justify-between px-5 py-3 border-b border-border shrink-0">
            <h2 className="text-sm font-semibold text-foreground">{title}</h2>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              aria-label="Close sheet"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {children}
        </div>
      </div>
    </>
  );
}
