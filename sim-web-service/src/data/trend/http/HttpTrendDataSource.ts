import type { TrendDataSource } from "@/domain/trend/ports";
import type { TrendQuery, TrendResponse } from "@/domain/trend/contracts";

const DEFAULT_PATH = "/api/caregiver/weekly-trend";

const createUrl = (path: string, query: TrendQuery) => {
  const url = new URL(path, window.location.origin);
  url.searchParams.set("subjectId", query.subjectId);
  url.searchParams.set("startDate", query.startDate);
  url.searchParams.set("endDate", query.endDate);
  if (query.timezone) {
    url.searchParams.set("timezone", query.timezone);
  }
  return url.toString();
};

export class HttpTrendDataSource implements TrendDataSource {
  constructor(private readonly path: string = DEFAULT_PATH) {}

  async fetchWeeklyTrend(query: TrendQuery): Promise<TrendResponse> {
    const url = createUrl(this.path, query);
    const response = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch weekly trend: ${response.status}`);
    }

    return (await response.json()) as TrendResponse;
  }
}
