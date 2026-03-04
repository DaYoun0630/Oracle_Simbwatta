import type { TrendQuery, TrendResponse } from "./contracts";

export interface TrendDataSource {
  fetchWeeklyTrend(query: TrendQuery): Promise<TrendResponse>;
}
