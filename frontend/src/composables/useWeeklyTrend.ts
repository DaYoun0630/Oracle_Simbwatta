import { ref } from "vue";
import { createTrendDataSource } from "@/data/trend/factory/createTrendDataSource";
import { createWeeklyTrendUseCase } from "@/domain/trend/usecases/getWeeklyTrend";
import type { TrendQuery, WeeklyTrendViewModel } from "@/domain/trend/contracts";
import { buildTrendQueryForRange } from "@/composables/useTrendRange";

const dataSource = createTrendDataSource();
const trendUseCase = createWeeklyTrendUseCase(dataSource);

const createDefaultQuery = (): TrendQuery => buildTrendQueryForRange("7d");

type PartialTrendQuery = Partial<TrendQuery>;

export function useWeeklyTrend() {
  const trend = ref<WeeklyTrendViewModel | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastQuery = ref<TrendQuery>(createDefaultQuery());

  const fetchWeeklyTrend = async (overrideQuery: PartialTrendQuery = {}) => {
    loading.value = true;
    error.value = null;
    try {
      const baseQuery = createDefaultQuery();
      const query = {
        ...baseQuery,
        ...overrideQuery,
      } as TrendQuery;
      lastQuery.value = query;
      trend.value = await trendUseCase.getWeeklyTrend(query);
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Failed to load trend data.";
    } finally {
      loading.value = false;
    }
  };

  return {
    trend,
    loading,
    error,
    lastQuery,
    fetchWeeklyTrend,
  };
}
