import React, { useCallback, useId, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronsUpDown,
  Columns,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ColumnDef<T> {
  key: string;
  header: string;
  sortable?: boolean;
  align?: "left" | "right" | "center";
  width?: string;
  hidden?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
  className?: string;
}

export interface SortState {
  key: string;
  direction: "asc" | "desc";
}

export interface BulkAction<T> {
  label: string;
  icon?: React.ElementType;
  variant?: "default" | "destructive";
  onClick: (selected: T[]) => void;
}

export interface DataTableProps<T extends Record<string, unknown>> {
  columns: ColumnDef<T>[];
  data: T[];
  getRowId?: (row: T) => string;
  // Controlled pagination
  total?: number;
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  // Controlled sort
  sort?: SortState;
  onSortChange?: (sort: SortState) => void;
  // Row features
  selectable?: boolean;
  bulkActions?: BulkAction<T>[];
  expandedRowContent?: (row: T) => React.ReactNode;
  rowClassName?: (row: T) => string;
  // Export
  exportable?: boolean;
  exportFilename?: string;
  // Display
  loading?: boolean;
  emptyState?: React.ReactNode;
  stickyHeader?: boolean;
  maxHeight?: string;
  className?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getValue<T>(row: T, key: string): unknown {
  return (row as Record<string, unknown>)[key];
}

function exportToCsv<T extends Record<string, unknown>>(
  columns: ColumnDef<T>[],
  data: T[],
  filename: string,
) {
  const visible = columns.filter((c) => !c.hidden);
  const header = visible.map((c) => `"${c.header}"`).join(",");
  const rows = data.map((row) =>
    visible
      .map((c) => {
        const v = getValue(row, c.key);
        const str = v == null ? "" : String(v).replace(/"/g, '""');
        return `"${str}"`;
      })
      .join(","),
  );
  const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportToJson<T extends Record<string, unknown>>(data: T[], filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SortIcon({ col, sort }: { col: ColumnDef<Record<string, unknown>>; sort?: SortState }) {
  if (!col.sortable) return null;
  if (sort?.key !== col.key)
    return <ChevronsUpDown className="w-3 h-3 text-muted-foreground/50 shrink-0" />;
  return sort.direction === "asc" ? (
    <ChevronUp className="w-3 h-3 text-brand-500 shrink-0" />
  ) : (
    <ChevronDown className="w-3 h-3 text-brand-500 shrink-0" />
  );
}

function SkeletonRows({ cols }: { cols: number }) {
  return (
    <>
      {[...Array(5)].map((_, i) => (
        <tr key={i} className="border-b border-border animate-pulse">
          {[...Array(cols)].map((__, j) => (
            <td key={j} className="px-3 py-2.5">
              <div className="h-4 rounded bg-muted" style={{ width: `${55 + ((i + j) % 4) * 10}%` }} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

function BulkActionsBar<T>({
  selected,
  actions,
  onClear,
}: {
  selected: T[];
  actions: BulkAction<T>[];
  onClear: () => void;
}) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-brand-50 dark:bg-brand-900/20 border-b border-brand-200 dark:border-brand-800 text-sm">
      <span className="font-medium text-brand-700 dark:text-brand-300">
        {selected.length} selected
      </span>
      {actions.map((a) => {
        const Icon = a.icon;
        return (
          <button
            key={a.label}
            onClick={() => a.onClick(selected)}
            className={cn(
              "inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors",
              a.variant === "destructive"
                ? "bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400"
                : "bg-white text-foreground hover:bg-muted border border-border dark:bg-card",
            )}
          >
            {Icon && <Icon className="w-3.5 h-3.5" />}
            {a.label}
          </button>
        );
      })}
      <button onClick={onClear} className="ml-auto text-xs text-muted-foreground hover:text-foreground">
        Clear
      </button>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  getRowId,
  total,
  page = 1,
  pageSize = 20,
  onPageChange,
  sort,
  onSortChange,
  selectable = false,
  bulkActions = [],
  expandedRowContent,
  rowClassName,
  exportable = false,
  exportFilename = "export",
  loading = false,
  emptyState,
  stickyHeader = false,
  maxHeight,
  className,
}: DataTableProps<T>) {
  const tableId = useId();
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(
    new Set(columns.filter((c) => c.hidden).map((c) => c.key)),
  );
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showColMenu, setShowColMenu] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const parentRef = useRef<HTMLDivElement>(null);

  const visibleCols = columns.filter((c) => !hiddenCols.has(c.key));
  const totalPages = total != null ? Math.ceil(total / pageSize) : 0;

  // Virtual scroll
  const rowVirtualizer = useVirtualizer({
    count: maxHeight ? data.length : 0,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 41,
    overscan: 8,
  });

  const rowId = useCallback(
    (row: T, i: number) => (getRowId ? getRowId(row) : String(i)),
    [getRowId],
  );

  function toggleSort(key: string) {
    if (!onSortChange) return;
    if (sort?.key === key) {
      onSortChange({ key, direction: sort.direction === "asc" ? "desc" : "asc" });
    } else {
      onSortChange({ key, direction: "asc" });
    }
  }

  function toggleAll() {
    if (selected.size === data.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(data.map((r, i) => rowId(r, i))));
    }
  }

  function toggleRow(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const selectedRows = data.filter((r, i) => selected.has(rowId(r, i)));
  const allSelected = data.length > 0 && selected.size === data.length;

  const renderRows = () => {
    if (loading) return <SkeletonRows cols={visibleCols.length + (selectable ? 1 : 0)} />;
    if (data.length === 0) {
      return (
        <tr>
          <td
            colSpan={visibleCols.length + (selectable ? 1 : 0)}
            className="px-4 py-12 text-center text-sm text-muted-foreground"
          >
            {emptyState ?? "No data."}
          </td>
        </tr>
      );
    }

    const items = maxHeight ? rowVirtualizer.getVirtualItems() : data.map((_, i) => ({ index: i, size: 41, start: i * 41 }));

    return (
      <>
        {maxHeight && rowVirtualizer.getTotalSize() > 0 && (
          <tr style={{ height: `${rowVirtualizer.getVirtualItems()[0]?.start ?? 0}px` }} />
        )}
        {items.map(({ index }) => {
          const row = data[index];
          const id = rowId(row, index);
          const isSelected = selected.has(id);
          const isExpanded = expanded.has(id);
          return (
            <React.Fragment key={id}>
              <tr
                className={cn(
                  "border-b border-border transition-colors hover:bg-muted/30",
                  isSelected && "bg-brand-50/50 dark:bg-brand-900/10",
                  rowClassName?.(row),
                )}
              >
                {selectable && (
                  <td className="px-3 py-2.5 w-9">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleRow(id)}
                      className="rounded border-border accent-brand-600 w-3.5 h-3.5"
                      aria-label={`Select row ${index + 1}`}
                    />
                  </td>
                )}
                {visibleCols.map((col) => {
                  const val = getValue(row, col.key);
                  return (
                    <td
                      key={col.key}
                      className={cn(
                        "px-3 py-2.5 text-sm",
                        col.align === "right" && "text-right",
                        col.align === "center" && "text-center",
                        col.className,
                      )}
                      style={col.width ? { width: col.width } : undefined}
                    >
                      {col.render ? col.render(val, row) : String(val ?? "—")}
                    </td>
                  );
                })}
                {expandedRowContent && (
                  <td className="px-2 py-2.5 w-8">
                    <button
                      onClick={() =>
                        setExpanded((prev) => {
                          const next = new Set(prev);
                          next.has(id) ? next.delete(id) : next.add(id);
                          return next;
                        })
                      }
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      aria-expanded={isExpanded}
                      aria-label="Expand row"
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                  </td>
                )}
              </tr>
              {isExpanded && expandedRowContent && (
                <tr className="border-b border-border bg-muted/20">
                  <td
                    colSpan={visibleCols.length + (selectable ? 1 : 0) + 1}
                    className="px-4 py-3"
                  >
                    {expandedRowContent(row)}
                  </td>
                </tr>
              )}
            </React.Fragment>
          );
        })}
        {maxHeight && rowVirtualizer.getTotalSize() > 0 && (
          <tr
            style={{
              height: `${
                rowVirtualizer.getTotalSize() -
                (rowVirtualizer.getVirtualItems().slice(-1)[0]?.end ?? 0)
              }px`,
            }}
          />
        )}
      </>
    );
  };

  return (
    <div className={cn("flex flex-col", className)} id={tableId}>
      {/* Toolbar */}
      <div className="flex items-center justify-end gap-2 pb-2">
        {exportable && (
          <div className="relative">
            <button
              onClick={() => setShowExportMenu((v) => !v)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs border border-border rounded-md hover:bg-accent transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
            {showExportMenu && (
              <div className="absolute right-0 top-8 z-20 bg-card border border-border rounded-md shadow-lg py-1 min-w-[120px]">
                <button
                  className="w-full px-3 py-1.5 text-xs text-left hover:bg-accent"
                  onClick={() => { exportToCsv(columns, data, exportFilename); setShowExportMenu(false); }}
                >
                  Export CSV
                </button>
                <button
                  className="w-full px-3 py-1.5 text-xs text-left hover:bg-accent"
                  onClick={() => { exportToJson(data, exportFilename); setShowExportMenu(false); }}
                >
                  Export JSON
                </button>
              </div>
            )}
          </div>
        )}
        {columns.length > 2 && (
          <div className="relative">
            <button
              onClick={() => setShowColMenu((v) => !v)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs border border-border rounded-md hover:bg-accent transition-colors"
            >
              <Columns className="w-3.5 h-3.5" />
              Columns
            </button>
            {showColMenu && (
              <div className="absolute right-0 top-8 z-20 bg-card border border-border rounded-md shadow-lg py-1 min-w-[150px]">
                {columns.map((col) => (
                  <label key={col.key} className="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-accent">
                    <input
                      type="checkbox"
                      checked={!hiddenCols.has(col.key)}
                      onChange={() =>
                        setHiddenCols((prev) => {
                          const next = new Set(prev);
                          next.has(col.key) ? next.delete(col.key) : next.add(col.key);
                          return next;
                        })
                      }
                      className="rounded accent-brand-600"
                    />
                    {col.header}
                  </label>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bulk actions */}
      {selectable && selected.size > 0 && bulkActions.length > 0 && (
        <BulkActionsBar
          selected={selectedRows}
          actions={bulkActions}
          onClear={() => setSelected(new Set())}
        />
      )}

      {/* Table */}
      <div
        ref={parentRef}
        className={cn("overflow-auto rounded-xl border border-border bg-card", maxHeight && "overflow-y-auto")}
        style={maxHeight ? { maxHeight } : undefined}
      >
        <table className="w-full text-sm min-w-max">
          <thead className={cn("bg-muted/40 text-xs text-muted-foreground uppercase tracking-wide", stickyHeader && "sticky top-0 z-10 bg-card")}>
            <tr>
              {selectable && (
                <th className="px-3 py-2.5 w-9">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    className="rounded border-border accent-brand-600 w-3.5 h-3.5"
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {visibleCols.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "px-3 py-2.5 font-medium text-left",
                    col.align === "right" && "text-right",
                    col.align === "center" && "text-center",
                    col.sortable && "cursor-pointer select-none hover:text-foreground",
                  )}
                  style={col.width ? { width: col.width } : undefined}
                  onClick={() => col.sortable && toggleSort(col.key)}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    <SortIcon col={col as ColumnDef<Record<string, unknown>>} sort={sort} />
                  </span>
                </th>
              ))}
              {expandedRowContent && <th className="w-8" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">{renderRows()}</tbody>
        </table>
      </div>

      {/* Pagination */}
      {total != null && totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 text-sm">
          <span className="text-muted-foreground text-xs">
            {((page - 1) * pageSize + 1).toLocaleString()}–
            {Math.min(page * pageSize, total).toLocaleString()} of {total.toLocaleString()}
          </span>
          <div className="flex items-center gap-1">
            <button
              disabled={page <= 1}
              onClick={() => onPageChange?.(page - 1)}
              className="p-1.5 rounded hover:bg-accent disabled:opacity-40 transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2 text-xs text-muted-foreground">
              {page} / {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => onPageChange?.(page + 1)}
              className="p-1.5 rounded hover:bg-accent disabled:opacity-40 transition-colors"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
