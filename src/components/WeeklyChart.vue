<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    data: number[];
    labels: string[];
    highlights?: number[];
    activeIndex?: number | null;
  }>(),
  {
    highlights: () => [],
    activeIndex: null,
  }
);

const emit = defineEmits<{
  (e: "point-click", index: number): void;
}>();

const baseline = 160;
const points = computed(() => props.data.map((val, i) => ({
  x: i * 55 + 30,
  y: baseline - (val * 1.2),
})));

const linePath = computed(() => {
  return points.value.reduce((acc, point, index, array) => {
    if (index === 0) return `M ${point.x},${point.y}`;
    const prev = array[index - 1];
    const cp1x = prev.x + (point.x - prev.x) / 2;
    return `${acc} C ${cp1x},${prev.y} ${cp1x},${point.y} ${point.x},${point.y}`;
  }, "");
});

const areaPath = computed(() => {
  if (!points.value.length) return "";
  const first = points.value[0];
  const last = points.value[points.value.length - 1];
  return `${linePath.value} L ${last.x},${baseline} L ${first.x},${baseline} Z`;
});

const highlightSet = computed(() => new Set(props.highlights));
const isHighlight = (index: number) => highlightSet.value.has(index);

const gridLines = [40, 80, 120, baseline];
const gradientId = `trend-${Math.random().toString(36).slice(2, 9)}`;

const handlePointClick = (index: number) => {
  emit("point-click", index);
};
</script>

<template>
  <div class="chart-wrapper">
    <svg viewBox="0 0 400 180" class="chart-svg" role="presentation">
      <defs>
        <linearGradient :id="`${gradientId}-line`" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#bfe9e9" />
          <stop offset="50%" stop-color="#4cb7b7" />
          <stop offset="100%" stop-color="#7fd4d4" />
        </linearGradient>
        <linearGradient :id="`${gradientId}-area`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(76, 183, 183, 0.42)" />
          <stop offset="100%" stop-color="rgba(76, 183, 183, 0)" />
        </linearGradient>
      </defs>

      <g class="grid">
        <line v-for="line in gridLines" :key="line" x1="0" :y1="line" x2="400" :y2="line" />
      </g>

      <path :d="areaPath" :fill="`url(#${gradientId}-area)`" />
      <path :d="linePath" :stroke="`url(#${gradientId}-line)`" stroke-width="7" stroke-linecap="round" fill="none" />

      <g
        v-for="(point, index) in points"
        :key="index"
        class="point"
        :class="{ highlight: isHighlight(index), active: index === activeIndex }"
        @click="handlePointClick(index)"
      >
        <circle class="point-hit" :cx="point.x" :cy="point.y" r="14" />
        <circle class="point-core" :cx="point.x" :cy="point.y" r="8" />
        <circle v-if="isHighlight(index)" class="point-ring" :cx="point.x" :cy="point.y" r="14" />
      </g>
    </svg>

    <div class="x-axis">
      <span v-for="label in labels" :key="label" class="axis-label">{{ label }}</span>
    </div>
  </div>
</template>

<style scoped>
.chart-wrapper {
  width: 100%;
  padding: 10px 4px 0;
}

.chart-svg {
  width: 100%;
  height: auto;
  overflow: visible;
}

.grid line {
  stroke: rgba(160, 170, 180, 0.35);
  stroke-width: 2;
}

.point {
  cursor: pointer;
}

.point-hit {
  fill: transparent;
}

.point-core {
  fill: #4cb7b7;
}

.point-ring {
  fill: rgba(76, 183, 183, 0.2);
  stroke: #4cb7b7;
  stroke-width: 2;
}

.point.highlight .point-core {
  fill: #ff8a80;
  animation: pulseHighlight 2s ease-in-out infinite;
  transform-origin: center;
  transform-box: fill-box;
}

.point.highlight .point-ring {
  stroke: #ff8a80;
  fill: rgba(255, 138, 128, 0.2);
  animation: pulseRing 2s ease-in-out infinite;
  transform-origin: center;
  transform-box: fill-box;
}

@keyframes pulseHighlight {
  0%, 100% {
    transform: scale(1);
    filter: drop-shadow(0 0 0 rgba(255, 138, 128, 0));
  }
  50% {
    transform: scale(1.15);
    filter: drop-shadow(0 0 8px rgba(255, 138, 128, 0.6));
  }
}

@keyframes pulseRing {
  0%, 100% {
    opacity: 0.6;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.3);
  }
}

@media (prefers-reduced-motion: reduce) {
  .point.highlight .point-core,
  .point.highlight .point-ring {
    animation: none !important;
  }
}

.point.active .point-core {
  fill: #1f5f5f;
}

.x-axis {
  display: flex;
  justify-content: space-between;
  padding: 14px 6px 0;
}

.axis-label {
  font-size: 1.125rem;
  font-weight: 800;
  color: #555;
}

.axis-label:last-child {
  color: #4cb7b7;
}
</style>
