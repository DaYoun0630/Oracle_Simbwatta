<script setup lang="ts">
import { computed } from "vue";

type VoiceState = "idle" | "listening" | "pause" | "processing" | "speaking";

const props = withDefaults(
  defineProps<{
    state: VoiceState;
    size?: number;
  }>(),
  {
    size: 280,
  }
);

const normalizedState = computed(() =>
  props.state === "pause" ? "processing" : props.state
);
const orbStyle = computed(() => ({
  "--orb-size": `${props.size}px`,
}));
const gradientId = `waveGradient-${Math.random().toString(36).slice(2, 9)}`;
</script>

<template>
  <div class="voice-orb" :data-state="normalizedState" :style="orbStyle" aria-hidden="true">
    <div class="orb-glow"></div>
    <div class="orb-halo"></div>
    <div class="orb-color color-1"></div>
    <div class="orb-color color-2"></div>
    <div class="orb-core"></div>
    <div class="orb-ring ring-1"></div>
    <div class="orb-ring ring-2"></div>
    <div class="orb-ring ring-3"></div>
    <svg class="orb-wave" viewBox="0 0 260 120">
      <defs>
        <linearGradient :id="gradientId" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#4cb7b7" />
          <stop offset="50%" stop-color="#7fd4d4" />
          <stop offset="100%" stop-color="#4cb7b7" />
        </linearGradient>
      </defs>
      <path
        class="wave wave-1"
        :stroke="`url(#${gradientId})`"
        d="M10 60c20-20 40-20 60 0s40 20 60 0 40-20 60 0 40 20 60 0"
      />
      <path
        class="wave wave-2"
        :stroke="`url(#${gradientId})`"
        d="M10 80c18-18 36-18 54 0s36 18 54 0 36-18 54 0 36 18 54 0"
      />
    </svg>
  </div>
</template>

<style scoped>
.voice-orb {
  position: relative;
  width: min(var(--orb-size), 70vw);
  height: min(var(--orb-size), 70vw);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.4s ease;
}

.orb-glow {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(76, 183, 183, 0.35) 0%, rgba(76, 183, 183, 0) 65%);
  filter: blur(2px);
}

.orb-halo {
  position: absolute;
  width: 92%;
  height: 92%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.65), rgba(255, 255, 255, 0) 70%);
  filter: blur(6px);
  opacity: 0.6;
}

.orb-color {
  position: absolute;
  width: 78%;
  height: 78%;
  border-radius: 50%;
  mix-blend-mode: screen;
  opacity: 0.65;
  filter: blur(8px);
  animation: colorDrift 6s ease-in-out infinite;
}

.orb-color.color-1 {
  background: radial-gradient(circle at 30% 30%, rgba(127, 212, 212, 0.9), rgba(76, 183, 183, 0.2));
}

.orb-color.color-2 {
  width: 68%;
  height: 68%;
  background: radial-gradient(circle at 70% 40%, rgba(122, 159, 255, 0.6), rgba(76, 183, 183, 0.15));
  animation-delay: 1.8s;
}

.orb-core {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #dff6f6, #4cb7b7 60%, #2d6f6f 100%);
  box-shadow: inset 0 6px 12px rgba(255, 255, 255, 0.4), 0 18px 40px rgba(76, 183, 183, 0.4);
  transition: background 0.4s ease, transform 0.4s ease;
}

.orb-ring {
  position: absolute;
  border: 2px solid rgba(76, 183, 183, 0.35);
  border-radius: 50%;
  opacity: 0.6;
}

.ring-1 { width: 180px; height: 180px; }
.ring-2 { width: 220px; height: 220px; }
.ring-3 { width: 260px; height: 260px; }

.orb-wave {
  position: absolute;
  width: 220px;
  height: 120px;
  opacity: 0;
}

.wave {
  fill: none;
  stroke-width: 5;
  stroke-linecap: round;
  stroke-dasharray: 14 16;
}

.voice-orb[data-state="idle"] .orb-core {
  animation: idleBreath 4s ease-in-out infinite;
}

.voice-orb[data-state="idle"] .orb-ring {
  animation: idleRing 5s ease-in-out infinite;
}

.voice-orb[data-state="listening"] .orb-core {
  background: radial-gradient(circle at 30% 30%, #e8fffe, #4cb7b7 60%, #1f5f5f 100%);
  transform: scale(1.03);
}

.voice-orb[data-state="listening"] .orb-color {
  opacity: 0.85;
  animation-duration: 3.6s;
}

.voice-orb[data-state="listening"] .orb-wave {
  opacity: 1;
}

.voice-orb[data-state="listening"] .wave {
  animation: waveFlow 1.6s ease-in-out infinite;
}

.voice-orb[data-state="processing"] .orb-core {
  background: radial-gradient(circle at 40% 40%, #f3f7ff, #7fd4d4 60%, #2d6f6f 100%);
  animation: processingPulse 1.4s ease-in-out infinite;
}

.voice-orb[data-state="processing"] .orb-ring {
  animation: spin 2.2s linear infinite;
  opacity: 0.8;
}

.voice-orb[data-state="processing"] .orb-color {
  animation: spin 4s linear infinite;
  opacity: 0.7;
}

.voice-orb[data-state="speaking"] .orb-core {
  background: radial-gradient(circle at 30% 30%, #ffffff, #70cfcf 60%, #2d6f6f 100%);
}

.voice-orb[data-state="speaking"] .orb-ring {
  animation: speakPulse 2.4s ease-out infinite;
}

.voice-orb[data-state="speaking"] .orb-wave {
  opacity: 0.9;
}

.voice-orb[data-state="speaking"] .wave {
  animation: waveFlow 2.2s ease-in-out infinite;
}

@keyframes idleBreath {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes idleRing {
  0% { transform: scale(0.96); opacity: 0.5; }
  50% { transform: scale(1.05); opacity: 0.25; }
  100% { transform: scale(0.96); opacity: 0.5; }
}

@keyframes colorDrift {
  0% { transform: translate(-6px, -4px) scale(1); opacity: 0.6; }
  50% { transform: translate(6px, 4px) scale(1.05); opacity: 0.85; }
  100% { transform: translate(-6px, -4px) scale(1); opacity: 0.6; }
}

@keyframes waveFlow {
  0% { stroke-dashoffset: 120; opacity: 0.5; }
  50% { opacity: 1; }
  100% { stroke-dashoffset: 0; opacity: 0.6; }
}

@keyframes processingPulse {
  0%, 100% { transform: scale(0.95); }
  50% { transform: scale(1.08); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes speakPulse {
  0% { transform: scale(0.9); opacity: 0.4; }
  70% { opacity: 0; }
  100% { transform: scale(1.2); opacity: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .voice-orb * {
    animation: none !important;
    transition: none !important;
  }
}
</style>
