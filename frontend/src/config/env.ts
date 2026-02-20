export type TrendSourceMode = "dummy" | "http";

const readTrendSource = (): TrendSourceMode => {
  const value = (import.meta.env.VITE_TREND_SOURCE || "dummy").toLowerCase();
  return value === "http" ? "http" : "dummy";
};

export const trendSourceMode = readTrendSource();
