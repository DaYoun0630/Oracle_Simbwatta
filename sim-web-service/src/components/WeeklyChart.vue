<script setup lang="ts">
import { computed } from "vue";
import type { TrendState } from "@/composables/useTrendBuckets";

type TrendValue = number | null;
type ChartPoint = {
  index: number;
  x: number;
  y: number | null;
  value: TrendValue;
  state: TrendState;
};
type DrawablePoint = { index: number; x: number; y: number };
type AxisTick = { index: number; label: string; left: number; required: boolean };
type YearMark = { year: number; left: number };

const props = withDefaults(
  defineProps<{
    data: TrendValue[];
    labels: string[];
    dates?: string[];
    states?: TrendState[];
    highlights?: number[];
    activeIndex?: number | null;
    yStateLabels?: [string, string, string, string];
  }>(),
  {
    dates: () => [],
    states: () => [],
    highlights: () => [],
    activeIndex: null,
    yStateLabels: () => ["안정", "변화", "저하", "미참여"] as [string, string, string, string],
  }
);

const emit = defineEmits<{
  (e: "point-click", index: number): void;
}>();

const chartWidth = 420;
const chartHeight = 212;
const minPointCount = 7;
const paddingLeft = 52;
const paddingRight = 24;
const topY = 28;
const changeY = 87;
const bottomY = 146;
const missingY = 180;
const baselineY = bottomY + 10;
const missingMarkerY = missingY;

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

const validValues = computed(() =>
  props.data.filter((value): value is number => value !== null && Number.isFinite(value))
);

const domain = computed(() => {
  if (validValues.value.length === 0) {
    return { min: 0, max: 100 };
  }
  const min = Math.min(...validValues.value);
  const max = Math.max(...validValues.value);
  const range = Math.max(max - min, 1);
  const padding = Math.max(range * 0.24, 3);
  return {
    min: min - padding,
    max: max + padding,
  };
});

const valueToY = (value: number) => {
  const range = Math.max(domain.value.max - domain.value.min, 1);
  const ratio = (value - domain.value.min) / range;
  return bottomY - ratio * (bottomY - topY);
};

const stateToY = (state: TrendState) => {
  if (state === "missing") return null;
  return stateLevelMap[state];
};

const points = computed<ChartPoint[]>(() =>
  Array.from({ length: totalPoints.value }, (_, index) => {
    const value = props.data[index] ?? null;
    const state = props.states[index] ?? (value === null ? "missing" : "change");
    const y = hasStateMode.value ? stateToY(state) : value === null ? null : valueToY(value);
    return {
      index,
      x: paddingLeft + xStep.value * index,
      y,
      value,
      state,
    };
  })
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

    currentSegment.push({
      index: point.index,
      x: point.x,
      y: point.y,
    });
  });

  if (currentSegment.length > 0) {
    result.push(currentSegment);
  }

  return result;
});

const toLinePath = (segment: DrawablePoint[]) =>
  segment.reduce((path, point, index) => (index === 0 ? `M ${point.x},${point.y}` : `${path} L ${point.x},${point.y}`), "");

const toAreaPath = (segment: DrawablePoint[]) => {
  if (!segment.length) return "";
  const linePath = toLinePath(segment);
  const first = segment[0];
  const last = segment[segment.length - 1];
  return `${linePath} L ${last.x},${baselineY} L ${first.x},${baselineY} Z`;
};

const gridLines = computed(() => {
  if (hasStateMode.value) {
    return [topY, changeY, bottomY, missingY];
  }
  const lineCount = 4;
  const gap = (bottomY - topY) / (lineCount - 1);
  return Array.from({ length: lineCount }, (_, index) => topY + gap * index);
});

const parsedDates = computed(() =>
  props.dates.map((value) => {
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : date;
  })
);

const normalizedHighlightIndices = computed(() =>
  [...new Set(props.highlights)]
    .filter((index) => Number.isInteger(index))
    .filter((index) => index >= 0 && index < props.labels.length)
);

const requiredTickIndices = computed(() => {
  if (props.labels.length === 0) return [] as number[];
  const indices = new Set<number>([0, props.labels.length - 1, ...normalizedHighlightIndices.value]);
  if (props.activeIndex !== null && props.activeIndex >= 0 && props.activeIndex < props.labels.length) {
    indices.add(props.activeIndex);
  }
  return [...indices].sort((a, b) => a - b);
});

const tickBaseLabels = computed(() =>
  props.labels.map((label, index) => {
    const parsed = parsedDates.value[index];
    if (!parsed) return label;
    return `${parsed.getMonth() + 1}.${parsed.getDate()}`;
  })
);

const getMaxTickCount = (length: number) => {
  if (length <= 4) return length;
  if (length <= 7) return 4;
  if (length <= 12) return 5;
  if (length <= 20) return 6;
  return 7;
};

const buildTickIndices = (length: number, maxTicks: number) => {
  if (length <= 0) return [] as number[];
  if (length === 1) return [0];

  const lastIndex = length - 1;
  const step = Math.max(1, Math.ceil(lastIndex / Math.max(maxTicks - 1, 1)));
  const indices: number[] = [];

  for (let index = 0; index <= lastIndex; index += step) {
    indices.push(index);
  }
  if (indices[indices.length - 1] !== lastIndex) {
    indices.push(lastIndex);
  }

  return indices;
};

const MIN_TICK_GAP_PERCENT = 15;

const compactTicksByGap = (ticks: AxisTick[]) => {
  if (ticks.length <= 2) return ticks;

  const compacted: AxisTick[] = [];

  for (let i = 0; i < ticks.length; i += 1) {
    const current = ticks[i];
    if (!compacted.length) {
      compacted.push(current);
      continue;
    }

    const prevKept = compacted[compacted.length - 1];
    const gapFromPrev = current.left - prevKept.left;

    if (gapFromPrev >= MIN_TICK_GAP_PERCENT) {
      compacted.push(current);
      continue;
    }

    if (!current.required) continue;
    if (!prevKept.required) {
      compacted[compacted.length - 1] = current;
      continue;
    }

    compacted.push(current);
  }

  return compacted;
};

const axisTicks = computed<AxisTick[]>(() => {
  if (props.labels.length === 0) return [];

  const maxTickCount = getMaxTickCount(props.labels.length);
  const autoIndices = buildTickIndices(props.labels.length, maxTickCount);
  const mergedIndices = [...new Set([...autoIndices, ...requiredTickIndices.value])].sort((a, b) => a - b);
  const requiredSet = new Set(requiredTickIndices.value);
  const baseTicks = mergedIndices.map((index) => ({
    index,
    label: tickBaseLabels.value[index] ?? "",
    left: ((paddingLeft + xStep.value * index) / chartWidth) * 100,
    required: requiredSet.has(index),
  }));

  return compactTicksByGap(baseTicks);
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

const handlePointClick = (index: number) => {
  emit("point-click", index);
};
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
        <text :x="4" :y="missingY + 3">{{ yStateLabels[3] }}</text>
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
        v-for="point in points"
        :key="point.index"
        class="point"
        :class="{
          highlight: isHighlight(point.index),
          active: point.index === activeIndex,
          missing: point.state === 'missing',
          stable: point.state === 'stable',
          change: point.state === 'change',
          decline: point.state === 'decline'
        }"
        @click="handlePointClick(point.index)"
      >
        <template v-if="point.y !== null">
          <circle class="point-hit" :cx="point.x" :cy="point.y" r="16" />
          <circle class="point-core" :cx="point.x" :cy="point.y" r="7.5" />
          <circle v-if="isHighlight(point.index)" class="point-ring" :cx="point.x" :cy="point.y" r="13" />
        </template>
        <template v-else>
          <circle class="point-hit" :cx="point.x" :cy="missingMarkerY" r="16" />
          <circle class="point-missing" :cx="point.x" :cy="missingMarkerY" r="5.6" />
          <circle v-if="isHighlight(point.index)" class="point-missing-ring" :cx="point.x" :cy="missingMarkerY" r="12.5" />
        </template>
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

.state-y-labels text {
  font-size: 11px;
  font-weight: 700;
  fill: #8c98a1;
}

.point {
  cursor: pointer;
}

.point-hit {
  fill: transparent;
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

.point.active .point-core {
  stroke: #356b6b;
  stroke-width: 2.4;
}

.point-missing {
  fill: #f6c3bd;
  stroke: #e9897f;
  stroke-width: 1.8;
}

.point-missing-ring {
  fill: rgba(240, 163, 154, 0.18);
  stroke: #f0a39a;
  stroke-width: 2.2;
}

.point.active .point-missing {
  stroke: #c76a62;
  stroke-width: 2.4;
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
