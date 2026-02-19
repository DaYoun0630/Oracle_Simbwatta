import type { TrendDataSource } from "@/domain/trend/ports";
import { trendSourceMode } from "@/config/env";
import { DummyTrendDataSource } from "../dummy/DummyTrendDataSource";
import { HttpTrendDataSource } from "../http/HttpTrendDataSource";

export const createTrendDataSource = (): TrendDataSource => {
  if (trendSourceMode === "http") {
    return new HttpTrendDataSource();
  }
  return new DummyTrendDataSource();
};
