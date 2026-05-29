import { useQuery } from "@tanstack/react-query";
import { listFeatureFlagsApi } from "@/features/featureFlags/api";

/**
 * Returns true if the given feature flag key is enabled for the current company.
 * Falls back to false while loading, on error, or if the key is not found.
 *
 * Data is cached in TanStack Query with a 60-second stale time to match the
 * server-side Redis cache TTL.
 *
 * Usage:
 *   const scenariosEnabled = useFeatureFlag('scenarios');
 *   if (!scenariosEnabled) return <ComingSoon />;
 */
export function useFeatureFlag(key: string): boolean {
  const { data } = useQuery({
    queryKey: ["feature-flags"],
    queryFn: listFeatureFlagsApi,
    staleTime: 60_000,
    // Don't throw — caller gets false on any failure
    throwOnError: false,
  });

  if (!data) return false;
  const flag = data.flags.find((f) => f.key === key);
  return flag?.enabled ?? false;
}
