<script setup lang="ts">
import { computed } from "vue";
import type { TrendState } from "@/composables/useTrendBuckets";

type TrendValue = number | null;
type ChartPoint = {
  index: number;
  x: number;
  y: number | null;
  state: TrendState;
};
type DrawablePoint = { index: number; x: number; y: number };
type AxisTick = { index: number; label: string; left: number };
type YearMark = { year: number; left: number };

const props = withDefaults(
  defineProps<{
    data: TrendValue[];
    labels: string[];
    dates?: string[];
    states?: TrendState[];
    highlights?: number[];
    yStateLabels?: [string, string, string, string];
  }>(),
  {
    dates: () => [],
    states: () => [],
    highlights: () => [],
    yStateLabels: () => ["안정", "변화", "저하", "미참여"] as [string, string, string, string],
  }
);

const chartWidth = 420;
const chartHeight = 220;
const minPointCount = 7;
const paddingLeft = 52;
const paddingRight = 24;
const topY = 28;
const changeY = 86;
const bottomY = 144;
const baselineY = bottomY + 10;
const missingTrackY = 186;

const stateLevelMap: Record<Exclude<TrendState, "missing">, number> = {
  stable: topY,
  change: changeY,
  decline: bottomY,
};

const totalPoints = computed(() => Math.max(minPointCount, props.data.length || 0));
const xStep = computed(() =>
  totalPoints.value <= 1 ? 0 : (chartWidth - paddingLeft - paddingRight) / (totalPoints.value - 1)
);

const hasStateMode = computed(() => props.states.length === props.data.length && props.states.length > 0);

const points = computed<ChartPoint[]>(() =>
  Array.from({ length: totalPoints.value }, (_, index) => {
    const value = props.data[index] ?? null;
    const state = props.states[index] ?? (value === null ? "missing" : "change");
    const y = state === "missing" ? null : stateLevelMap[state];
    return {
      index,
      x: paddingLeft + xStep.value * index,
      y: hasStateMode.value ? y : null,
      state,
    };
  })
);

const trendPoints = computed<DrawablePoint[]>(() =>
  points.value
    .filter((point): point is ChartPoint & { y: number } => point.y !== null)
    .map((point) => ({ index: point.index, x: point.x, y: point.y }))
);

const segments = computed<DrawablePoint[][]>(() => {
  const result: DrawablePoint[][] = [];
  let currentSegment: DrawablePoint[] = [];

  points.value.forEach((point) => {
    if (point.y === null) {
      if (currentSegment.length > 0) {
        result.push(currentSegment);
        currentSegment = [];
      }
      return;
    }

    currentSegment.push({ index: point.index, x: point.x, y: point.y });
  });

  if (currentSegment.length > 0) {
    result.push(currentSegment);
  }

  return result;
});

const missingPoints = computed(() => points.value.filter((point) => point.state === "missing"));

const toLinePath = (segment: DrawablePoint[]) =>
  segment.reduce((path, point, index) => (index === 0 ? `M ${point.x},${point.y}` : `${path} L ${point.x},${point.y}`), "");

const toAreaPath = (segment: DrawablePoint[]) => {
  if (!segment.length) return "";
  const linePath = toLinePath(segment);
  const first = segment[0];
  const last = segment[segment.length - 1];
  return `${linePath} L ${last.x},${baselineY} L ${first.x},${baselineY} Z`;
};

const gridLines = [topY, changeY, bottomY];

const parsedDates = computed(() =>
  props.dates.map((value) => {
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : date;
  })
);

const axisTicks = computed<AxisTick[]>(() => {
  if (props.labels.length === 0) return [];
  return props.labels.map((label, index) => {
    const parsed = parsedDates.value[index];
    const tickLabel = parsed ? `${parsed.getMonth() + 1}.${parsed.getDate()}` : label;
    return {
      index,
      label: tickLabel,
      left: ((paddingLeft + xStep.value * index) / chartWidth) * 100,
    };
  });
});

const yearMarks = computed<YearMark[]>(() => {
  if (!props.dates.length || !axisTicks.value.length) return [];

  const marks: YearMark[] = [];
  let previousYear: number | null = null;

  axisTicks.value.forEach((tick) => {
    const parsed = parsedDates.value[tick.index];
    if (!parsed) return;
    const year = parsed.getFullYear();
    if (previousYear === null || previousYear !== year) {
      marks.push({ year, left: tick.left });
      previousYear = year;
    }
  });

  return marks;
});

const highlightSet = computed(() => new Set(props.highlights));
const isHighlight = (index: number) => highlightSet.value.has(index);

const gradientId = `trend-${Math.random().toString(36).slice(2, 9)}`;
</script>

<template>
  <div class="chart-wrapper">
    <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="chart-svg" role="presentation">
      <defs>
        <linearGradient :id="`${gradientId}-line`" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#c8ecec" />
          <stop offset="50%" stop-color="#58bcbc" />
          <stop offset="100%" stop-color="#85d6d6" />
        </linearGradient>
        <linearGradient :id="`${gradientId}-area`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(88, 188, 188, 0.26)" />
          <stop offset="100%" stop-color="rgba(88, 188, 188, 0)" />
        </linearGradient>
      </defs>

      <g class="grid">
        <line v-for="line in gridLines" :key="line" :x1="paddingLeft - 4" :y1="line" :x2="chartWidth - 6" :y2="line" />
      </g>

      <g v-if="hasStateMode" class="state-y-labels">
        <text :x="4" :y="topY + 3">{{ yStateLabels[0] }}</text>
        <text :x="4" :y="changeY + 3">{{ yStateLabels[1] }}</text>
        <text :x="4" :y="bottomY + 3">{{ yStateLabels[2] }}</text>
      </g>

      <g class="missing-track">
        <line :x1="paddingLeft - 4" :y1="missingTrackY" :x2="chartWidth - 6" :y2="missingTrackY" />
        <text :x="4" :y="missingTrackY + 3">{{ yStateLabels[3] }}</text>
      </g>

      <template v-for="(segment, segmentIndex) in segments" :key="`segment-${segmentIndex}`">
        <path :d="toAreaPath(segment)" :fill="`url(#${gradientId}-area)`" />
        <path
          :d="toLinePath(segment)"
          :stroke="`url(#${gradientId}-line)`"
          stroke-width="5"
          stroke-linecap="round"
          fill="none"
        />
      </template>

      <g
        v-for="point in trendPoints"
        :key="`trend-${point.index}`"
        class="point"
        :class="{
          highlight: isHighlight(point.index),
          stable: points[point.index]?.state === 'stable',
          change: points[point.index]?.state === 'change',
          decline: points[point.index]?.state === 'decline'
        }"
      >
        <circle class="point-core" :cx="point.x" :cy="point.y" r="7.5" />
        <circle v-if="isHighlight(point.index)" class="point-ring" :cx="point.x" :cy="point.y" r="13" />
      </g>

      <g v-for="point in missingPoints" :key="`missing-${point.index}`" class="missing-point">
        <rect :x="point.x - 5.4" :y="missingTrackY - 5.4" width="10.8" height="10.8" rx="2.5" />
        <line :x1="point.x - 3.5" :y1="missingTrackY + 3.5" :x2="point.x + 3.5" :y2="missingTrackY - 3.5" />
      </g>
    </svg>

    <div v-if="yearMarks.length" class="x-year-axis">
      <span
        v-for="mark in yearMarks"
        :key="`${mark.year}-${mark.left}`"
        class="year-label"
        :style="{ left: `${mark.left}%` }"
      >
        {{ mark.year }}
      </span>
    </div>

    <div class="x-axis">
      <span
        v-for="tick in axisTicks"
        :key="tick.index"
        class="axis-label"
        :style="{ left: `${tick.left}%` }"
      >
        {{ tick.label }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.chart-wrapper {
  width: 100%;
  padding: 8px 0 0;
}

.chart-svg {
  width: 100%;
  height: auto;
  overflow: visible;
}

.grid line {
  stroke: rgba(160, 170, 180, 0.34);
  stroke-width: 1.9;
}

.state-y-labels text,
.missing-track text {
  font-size: 11px;
  font-weight: 700;
  fill: #8c98a1;
}

.missing-track line {
  stroke: rgba(160, 170, 180, 0.3);
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.point-core {
  fill: #58bcbc;
}

.point.change .point-core {
  fill: #89b9cf;
}

.point.decline .point-core {
  fill: #f0a39a;
}

.point-ring {
  fill: rgba(240, 163, 154, 0.18);
  stroke: #f0a39a;
  stroke-width: 2;
}

.missing-point rect {
  fill: #f9d7d2;
  stroke: #e9897f;
  stroke-width: 1.6;
}

.missing-point line {
  stroke: #cf756b;
  stroke-width: 1.6;
  stroke-linecap: round;
}

.x-year-axis {
  position: relative;
  height: 12px;
  margin-top: 2px;
}

.year-label {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  font-size: 0.56rem;
  font-weight: 700;
  color: #95a1aa;
  white-space: nowrap;
}

.x-axis {
  position: relative;
  height: 22px;
  margin-top: 4px;
}

.axis-label {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  font-size: 0.72rem;
  font-weight: 700;
  color: #5e6b74;
  white-space: nowrap;
}

@media (max-width: 560px) {
  .axis-label {
    font-size: 0.68rem;
  }
}
</style>
