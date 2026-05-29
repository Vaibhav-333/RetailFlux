import { useState, useCallback } from "react";
import type { SortState } from "@/components/ui/DataTable";

interface UseDataTableOptions {
  defaultPage?: number;
  defaultPageSize?: number;
  defaultSort?: SortState;
}

/**
 * Manages server-driven DataTable state: pagination, sort, and filter params
 * for use with API query keys and onPageChange/onSortChange callbacks.
 */
export function useDataTable({
  defaultPage = 1,
  defaultPageSize = 20,
  defaultSort,
}: UseDataTableOptions = {}) {
  const [page, setPage] = useState(defaultPage);
  const [pageSize] = useState(defaultPageSize);
  const [sort, setSort] = useState<SortState | undefined>(defaultSort);
  const [filters, setFilters] = useState<Record<string, string>>({});

  const onPageChange = useCallback((next: number) => setPage(next), []);
  const onSortChange = useCallback((next: SortState) => {
    setSort(next);
    setPage(1);
  }, []);
  const setFilter = useCallback((key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  }, []);
  const clearFilter = useCallback((key: string) => {
    setFilters((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
    setPage(1);
  }, []);
  const resetAll = useCallback(() => {
    setPage(defaultPage);
    setSort(defaultSort);
    setFilters({});
  }, [defaultPage, defaultSort]);

  const sortParam = sort ? `${sort.key}:${sort.direction}` : undefined;

  return {
    page,
    pageSize,
    sort,
    filters,
    sortParam,
    onPageChange,
    onSortChange,
    setFilter,
    clearFilter,
    resetAll,
  };
}
