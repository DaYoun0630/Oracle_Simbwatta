<script setup lang="ts">
import { computed } from "vue";
import type { TrendState } from "@/composables/useTrendBuckets";

type TrendValue = number | null;
type PointNode = {
  index: number;
  x: number;
  y: number | null;
  state: TrendState;
};
type DrawablePoint = { index: number; x: number; y: number };
type AxisTick = { index: number; label: string; leftPct: number };

const props = withDefaults(
  defineProps<{
    data: TrendValue[];
    labels: string[];
    dates?: string[];
    states?: TrendState[];
    highlights?: number[];
    activeIndex?: number | null;
    yStateLabels?: [string, string, string, string];
    chartWidthPx?: number;
    paddingLeftPx?: number;
    paddingRightPx?: number;
  }>(),
  {
    dates: () => [],
    states: () => [],
    highlights: () => [],
    activeIndex: null,
    yStateLabels: () => ["안정", "변화", "저하", "미측정"] as [string, string, string, string],
    chartWidthPx: 700,
    paddingLeftPx: 66,
    paddingRightPx: 28,
  }
);

const emit = defineEmits<{
  (e: "point-click", index: number): void;
}>();

const chartWidth = computed(() => Math.max(700, props.chartWidthPx));
const chartHeight = 286;
const paddingLeft = computed(() => props.paddingLeftPx);
const paddingRight = computed(() => props.paddingRightPx);

const topY = 46;
const midY = 124;
const lowY = 202;
const missingY = 246;
const baselineY = lowY + 10;

const levelYMap: Record<Exclude<TrendState, "missing">, number> = {
  stable: topY,
  change: midY,
  decline: lowY,
};

const totalPoints = computed(() => Math.max(2, props.data.length || 0));
const xStep = computed(() =>
  totalPoints.value <= 1
    ? 0
    : (chartWidth.value - paddingLeft.value - paddingRight.value) / (totalPoints.value - 1)
);
const xAt = (index: number) => paddingLeft.value + xStep.value * index;

const points = computed<PointNode[]>(() =>
  Array.from({ length: totalPoints.value }, (_, index) => {
    const value = props.data[index] ?? null;
    const state = props.states[index] ?? (value === null ? "missing" : "change");
    const y = state === "missing" ? null : levelYMap[state];
    return {
      index,
      x: xAt(index),
      y,
      state,
    };
  })
);

const segments = computed<DrawablePoint[][]>(() => {
  const result: DrawablePoint[][] = [];
  let current: DrawablePoint[] = [];

  for (const point of points.value) {
    if (point.y === null) {
      if (current.length > 0) {
        result.push(current);
        current = [];
      }
      continue;
    }
    current.push({ index: point.index, x: point.x, y: point.y });
  }

  if (current.length > 0) {
    result.push(current);
  }

  return result;
});

const toLinePath = (segment: DrawablePoint[]) =>
  segment.reduce((path, point, index) => (index === 0 ? `M ${point.x},${point.y}` : `${path} L ${point.x},${point.y}`), "");

const toAreaPath = (segment: DrawablePoint[]) => {
  if (!segment.length) return "";
  const first = segment[0];
  const last = segment[segment.length - 1];
  return `${toLinePath(segment)} L ${last.x},${baselineY} L ${first.x},${baselineY} Z`;
};

const parsedDates = computed(() =>
  props.dates.map((value) => {
    const parsed = new Date(`${value}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  })
);

const formatDateLabel = (index: number) => {
  const parsed = parsedDates.value[index];
  if (parsed) return `${parsed.getMonth() + 1}.${parsed.getDate()}`;
  return props.labels[index] ?? `${index + 1}`;
};

const axisTicks = computed<AxisTick[]>(() =>
  Array.from({ length: totalPoints.value }, (_, index) => ({
    index,
    label: formatDateLabel(index),
    leftPct: (xAt(index) / chartWidth.value) * 100,
  }))
);

const activeGuideX = computed(() => {
  if (props.activeIndex === null || props.activeIndex < 0 || props.activeIndex >= totalPoints.value) return null;
  return xAt(props.activeIndex);
});

const isHighlighted = (index: number) => props.highlights.includes(index);
const isActive = (index: number) => props.activeIndex === index;
const isMissing = (index: number) => points.value[index]?.state === "missing";

const gradientId = `trend-${Math.random().toString(36).slice(2, 9)}`;

const onPointClick = (index: number) => {
  emit("point-click", index);
};
</script>

<template>
  <div class="chart-wrapper">
    <svg
      :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
      preserveAspectRatio="none"
      class="chart-svg"
      role="presentation"
    >
      <defs>
        <linearGradient :id="`${gradientId}-line`" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#8fd1d1" />
          <stop offset="100%" stop-color="#4cb7b7" />
        </linearGradient>
        <linearGradient :id="`${gradientId}-area`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(76, 183, 183, 0.24)" />
          <stop offset="100%" stop-color="rgba(76, 183, 183, 0)" />
        </linearGradient>
      </defs>

      <g class="x-guides">
        <line
          v-for="tick in axisTicks"
          :key="`guide-${tick.index}`"
          :x1="(tick.leftPct / 100) * chartWidth"
          :y1="topY"
          :x2="(tick.leftPct / 100) * chartWidth"
          :y2="missingY + 4"
        />
      </g>

      <line
        v-if="activeGuideX !== null"
        class="active-guide"
        :x1="activeGuideX"
        :y1="topY"
        :x2="activeGuideX"
        :y2="missingY + 4"
      />

      <g class="grid">
        <line :x1="paddingLeft - 2" :y1="topY" :x2="chartWidth - 2" :y2="topY" />
        <line :x1="paddingLeft - 2" :y1="midY" :x2="chartWidth - 2" :y2="midY" />
        <line :x1="paddingLeft - 2" :y1="lowY" :x2="chartWidth - 2" :y2="lowY" />
      </g>

      <g class="y-axis">
        <text :x="2" :y="topY + 4">{{ yStateLabels[0] }}</text>
        <text :x="2" :y="midY + 4">{{ yStateLabels[1] }}</text>
        <text :x="2" :y="lowY + 4">{{ yStateLabels[2] }}</text>
        <text class="missing-label" :x="2" :y="missingY + 4">{{ yStateLabels[3] }}</text>
      </g>

      <g class="missing-lane">
        <line :x1="paddingLeft - 2" :y1="missingY" :x2="chartWidth - 2" :y2="missingY" />
      </g>

      <template v-for="(segment, segmentIndex) in segments" :key="`segment-${segmentIndex}`">
        <path :d="toAreaPath(segment)" :fill="`url(#${gradientId}-area)`" />
        <path :d="toLinePath(segment)" :stroke="`url(#${gradientId}-line)`" stroke-width="3.6" stroke-linecap="round" fill="none" />
      </template>

      <g v-for="point in points" :key="point.index" class="point-group" @click="onPointClick(point.index)">
        <circle
          v-if="point.y !== null"
          class="point-hit"
          :cx="point.x"
          :cy="point.y"
          r="15"
        />
        <circle
          v-if="point.y !== null"
          class="point-core"
          :class="[point.state, { active: isActive(point.index) }]"
          :cx="point.x"
          :cy="point.y"
          :r="isActive(point.index) ? 8.6 : 6.8"
        />
        <circle
          v-if="point.y !== null && isHighlighted(point.index)"
          class="point-alert-ring"
          :cx="point.x"
          :cy="point.y"
          r="12.5"
        />

        <template v-if="isMissing(point.index)">
          <rect
            class="missing-marker"
            :class="{ active: isActive(point.index) }"
            :x="point.x - 9"
            :y="missingY - 9"
            width="18"
            height="18"
            rx="2.6"
          />
          <line class="missing-cross" :x1="point.x - 5.2" :y1="missingY - 5.2" :x2="point.x + 5.2" :y2="missingY + 5.2" />
          <line class="missing-cross" :x1="point.x - 5.2" :y1="missingY + 5.2" :x2="point.x + 5.2" :y2="missingY - 5.2" />
        </template>
      </g>
    </svg>

    <div class="x-axis">
      <span
        v-for="tick in axisTicks"
        :key="tick.index"
        class="axis-label"
        :class="{ active: isActive(tick.index), missing: isMissing(tick.index) }"
        :style="{ left: `${tick.leftPct}%` }"
      >
        {{ tick.label }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.chart-wrapper {
  width: 100%;
  position: relative;
  padding-top: 4px;
}

.chart-svg {
  width: 100%;
  height: 140px;
  display: block;
}

.x-guides line {
  stroke: rgba(169, 183, 194, 0.24);
  stroke-width: 1.2;
}

.active-guide {
  stroke: rgba(44, 66, 82, 0.42);
  stroke-width: 1.6;
  stroke-dasharray: 3 2;
}

.grid line {
  stroke: rgba(145, 162, 173, 0.44);
  stroke-width: 1.5;
}

.y-axis text {
  font-size: 13px;
  font-weight: 800;
  fill: #6d7e89;
}

.y-axis .missing-label {
  fill: #b04e47;
}

.missing-lane line {
  stroke: rgba(189, 85, 78, 0.84);
  stroke-width: 2.8;
  stroke-dasharray: 5 2;
}

.point-group {
  cursor: pointer;
}

.point-hit {
  fill: transparent;
}

.point-core {
  stroke-width: 1.4;
}

.point-core.stable {
  fill: #4cb7b7;
  stroke: #2f8f8f;
}

.point-core.change {
  fill: #ffb74d;
  stroke: #c88625;
}

.point-core.decline {
  fill: #ff8a80;
  stroke: #ce5c54;
}

.point-core.active {
  stroke: #2c4252;
  stroke-width: 2.7;
}

.point-alert-ring {
  fill: none;
  stroke: #ce5c54;
  stroke-width: 2.2;
}

.missing-marker {
  fill: #ffb8b0;
  stroke: #b9403a;
  stroke-width: 2.6;
}

.missing-marker.active {
  fill: #ff9f94;
  stroke-width: 3.2;
}

.missing-cross {
  stroke: #8b211c;
  stroke-width: 2.2;
  stroke-linecap: round;
}

.x-axis {
  position: relative;
  height: 28px;
  margin-top: 6px;
}

.axis-label {
  position: absolute;
  transform: translateX(-50%);
  top: 0;
  font-size: clamp(12px, 0.95vw, 14px);
  font-weight: 700;
  color: #4f616c;
  white-space: nowrap;
}

.axis-label.active {
  color: #243f50;
  font-weight: 900;
}

.axis-label.missing {
  color: #b04e47;
}

</style>
