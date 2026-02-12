<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as THREE from "three";

type VoiceState = "idle" | "listening" | "pause" | "processing" | "speaking";
type NormalizedState = "idle" | "listening" | "processing" | "speaking";
type OrbQuality = "high" | "medium" | "low" | "auto";

interface MotionPreset {
  breathPeriod: number;
  breathAmp: number;
  driftRateX: number;
  driftRateY: number;
  glow: number;
  highlight: number;
}

interface QualityPreset {
  dprCap: number;
  glowBoost: number;
}

const props = withDefaults(
  defineProps<{
    state: VoiceState;
    level?: number;
    reactive?: boolean;
    size?: number;
    quality?: OrbQuality;
    transparent?: boolean;
  }>(),
  {
    size: 280,
    quality: "auto",
    transparent: true,
    reactive: true,
  }
);

const normalizedState = computed<NormalizedState>(() =>
  props.state === "pause" ? "processing" : props.state
);

const orbStyle = computed(() => ({
  "--orb-size": `${props.size}px`,
}));

// Larger but still soft motion for audio-reactive "vibration" feel.
const MOTION_PRESETS: Record<NormalizedState, MotionPreset> = {
  idle: {
    breathPeriod: 6.2,
    breathAmp: 0.028,
    driftRateX: 0.13,
    driftRateY: 0.12,
    glow: 0.16,
    highlight: 0.36,
  },
  listening: {
    breathPeriod: 5.4,
    breathAmp: 0.046,
    driftRateX: 0.2,
    driftRateY: 0.18,
    glow: 0.22,
    highlight: 0.4,
  },
  processing: {
    breathPeriod: 5.1,
    breathAmp: 0.044,
    driftRateX: 0.18,
    driftRateY: 0.17,
    glow: 0.21,
    highlight: 0.39,
  },
  speaking: {
    breathPeriod: 4.5,
    breathAmp: 0.062,
    driftRateX: 0.27,
    driftRateY: 0.22,
    glow: 0.26,
    highlight: 0.44,
  },
};

const QUALITY_PRESETS: Record<Exclude<OrbQuality, "auto">, QualityPreset> = {
  high: { dprCap: 1.5, glowBoost: 1.0 },
  medium: { dprCap: 1.25, glowBoost: 0.9 },
  low: { dprCap: 1.0, glowBoost: 0.8 },
};

const BRAND_COLORS = {
  mint: "#4FD1C5",
  blue: "#3B82F6",
  cyan: "#67E8F9",
  white: "#FFFFFF",
};

const hostRef = ref<HTMLDivElement | null>(null);
const canvasRef = ref<HTMLDivElement | null>(null);
const hasRendererError = ref(false);

let scene: THREE.Scene | null = null;
let camera: THREE.OrthographicCamera | null = null;
let renderer: THREE.WebGLRenderer | null = null;
let material: THREE.ShaderMaterial | null = null;
let mesh: THREE.Mesh<THREE.PlaneGeometry, THREE.ShaderMaterial> | null = null;
let resizeObserver: ResizeObserver | null = null;
let cleanupReducedMotion: (() => void) | null = null;
let cleanupWindowResize: (() => void) | null = null;
let rafId = 0;
let startTime = 0;
let reducedMotion = false;
let smoothedLevel = 0;
let smoothedMotionMix = 0;
let smoothedListen = 0;
let smoothedProcess = 0;
let smoothedSpeak = 0;

const smoothedMotion: MotionPreset = { ...MOTION_PRESETS.idle };

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

const isProvidedLevel = computed(
  () => typeof props.level === "number" && Number.isFinite(props.level)
);

const detectAutoQuality = (): Exclude<OrbQuality, "auto"> => {
  if (typeof window === "undefined") return "medium";
  const nav = navigator as Navigator & { deviceMemory?: number };
  const cores = nav.hardwareConcurrency ?? 8;
  const memory = nav.deviceMemory ?? 8;

  if (memory <= 4 || cores <= 4) return "low";
  if (memory <= 8 || cores <= 8 || reducedMotion) return "medium";
  return "high";
};

const resolveQuality = (): Exclude<OrbQuality, "auto"> => {
  if (props.quality === "auto") return detectAutoQuality();
  return props.quality;
};

const vertexShader = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const fragmentShader = `
precision highp float;

varying vec2 vUv;

uniform vec2 uResolution;
uniform float uTime;
uniform float uScale;
uniform float uGlow;
uniform float uHighlight;
uniform float uDriftX;
uniform float uDriftY;
uniform float uReducedMotion;
uniform float uLevel;
uniform float uGlowBoost;
uniform float uMotionMix;
uniform float uWobble;
uniform float uListen;
uniform float uProcess;
uniform float uSpeak;
uniform float uStatePulse;
uniform vec3 uMint;
uniform vec3 uBlue;
uniform vec3 uCyan;
uniform vec3 uWhite;

void main() {
  vec2 p = vUv * 2.0 - 1.0;
  float aspect = uResolution.x / max(uResolution.y, 1.0);
  p.x *= aspect;
  p /= max(uScale, 0.0001);

  float r = length(p);
  float sphereMask = 1.0 - smoothstep(0.965, 1.005, r);
  float rimLine = smoothstep(0.94, 0.995, r) * (1.0 - smoothstep(0.995, 1.02, r));
  float outerGlow = (1.0 - smoothstep(1.0, 1.11, r)) * smoothstep(0.96, 1.01, r);

  if (sphereMask + outerGlow < 0.001) {
    discard;
  }

  float motion = mix(0.06, 1.0, 1.0 - uReducedMotion) * uMotionMix;
  float t = uTime * motion;

  vec2 dir = normalize(p + vec2(0.0001, 0.0));
  float angle = atan(dir.y, dir.x);
  float wobbleWave = sin(angle * 3.2 + t * 2.4) + sin(angle * 5.1 - t * 1.7) * 0.55;
  vec2 wobbleOffset = dir * wobbleWave * 0.072 * uWobble;
  vec2 drift = vec2(
    sin(t * uDriftX + 0.5),
    sin(t * uDriftY + 2.1)
  ) * 0.42 * uMotionMix;

  vec2 q = p + drift + wobbleOffset;

  float axisA = dot(q, normalize(vec2(-0.45, 0.9))) * 0.5 + 0.5;
  float axisB = dot(q + vec2(0.12, -0.08), normalize(vec2(0.95, 0.2))) * 0.5 + 0.5;

  vec3 base = mix(uMint, uBlue, smoothstep(0.1, 0.92, axisA));
  base = mix(base, uCyan, smoothstep(0.22, 0.95, axisB) * 0.28);
  base = mix(base, mix(uMint, uCyan, 0.58), 0.13 * uListen);
  base = mix(base, mix(uBlue, uWhite, 0.32), 0.1 * uProcess);
  base = mix(base, mix(uBlue, uCyan, 0.36), 0.12 * uSpeak);

  float centerSoft = exp(-r * r * 1.8);
  base = mix(base, uWhite, 0.08 + centerSoft * 0.12);

  vec2 specPos = vec2(-0.25, 0.27) + drift * 0.24 + wobbleOffset * 0.25;
  float spec = exp(-dot(p - specPos, p - specPos) * 22.0);
  float softSpec = exp(-dot(p - vec2(-0.02, 0.04), p - vec2(-0.02, 0.04)) * 7.5);

  float level = clamp(uLevel, 0.0, 1.0);
  float rimLight = rimLine * (0.14 + uGlow * 0.65) * (0.78 + uMotionMix * 0.22) * uGlowBoost;
  rimLight *= (1.0 + uListen * 0.2 + uProcess * 0.28 + uSpeak * (0.42 + 0.22 * uStatePulse));
  float innerGlow = (1.0 - smoothstep(0.0, 0.96, r)) * (0.05 + uGlow * 0.14);
  float highlight = (spec * 0.24 + softSpec * 0.1) * uHighlight * (1.0 + level * 0.18);
  highlight *= (1.0 + uProcess * 0.2 + uSpeak * 0.24);

  float processBand = exp(-pow(r - 0.58, 2.0) * 120.0) * (0.35 + 0.65 * (0.5 + 0.5 * sin(uTime * 2.1)));
  float listenLift = smoothstep(-0.1, 0.85, p.y + 0.12);
  float speakingPulse = (0.5 + 0.5 * sin(uTime * 8.8)) * uSpeak;

  vec3 color = base;
  color += uWhite * highlight;
  color += uCyan * innerGlow;
  color += mix(uMint, uBlue, 0.4) * rimLight;
  color += uWhite * processBand * 0.11 * uProcess;
  color += uCyan * listenLift * 0.06 * uListen;
  color += mix(uMint, uBlue, 0.55) * rimLine * speakingPulse * 0.1;
  color = mix(color, vec3(1.0), rimLine * 0.1);

  float alpha = sphereMask;
  alpha += outerGlow * (0.015 + uGlow * 0.065) * uGlowBoost;
  alpha += outerGlow * speakingPulse * 0.035;
  alpha = clamp(alpha, 0.0, 1.0);

  gl_FragColor = vec4(color, alpha);
}
`;

const applyQualityPreset = () => {
  if (!renderer || !material) return;
  const preset = QUALITY_PRESETS[resolveQuality()];
  const dpr = Math.min(window.devicePixelRatio || 1, preset.dprCap);

  renderer.setPixelRatio(dpr);
  material.uniforms.uGlowBoost.value = preset.glowBoost;
};

const resizeRenderer = () => {
  if (!renderer || !material || !hostRef.value) return;
  const width = Math.max(1, Math.floor(hostRef.value.clientWidth));
  const height = Math.max(1, Math.floor(hostRef.value.clientHeight));
  renderer.setSize(width, height, false);
  material.uniforms.uResolution.value.set(width, height);
};

const animate = (time: number) => {
  if (!renderer || !scene || !camera || !material) return;
  if (!startTime) startTime = time;
  const elapsed = (time - startTime) * 0.001;

  const target = MOTION_PRESETS[normalizedState.value];
  const transition = reducedMotion ? 0.04 : 0.075;

  smoothedMotion.breathPeriod = THREE.MathUtils.lerp(
    smoothedMotion.breathPeriod,
    target.breathPeriod,
    transition
  );
  smoothedMotion.breathAmp = THREE.MathUtils.lerp(
    smoothedMotion.breathAmp,
    target.breathAmp * (reducedMotion ? 0.4 : 1.0),
    transition
  );
  smoothedMotion.driftRateX = THREE.MathUtils.lerp(
    smoothedMotion.driftRateX,
    target.driftRateX * (reducedMotion ? 0.35 : 1.0),
    transition
  );
  smoothedMotion.driftRateY = THREE.MathUtils.lerp(
    smoothedMotion.driftRateY,
    target.driftRateY * (reducedMotion ? 0.35 : 1.0),
    transition
  );
  smoothedMotion.glow = THREE.MathUtils.lerp(smoothedMotion.glow, target.glow, transition);
  smoothedMotion.highlight = THREE.MathUtils.lerp(smoothedMotion.highlight, target.highlight, transition);

  const sourceLevel = isProvidedLevel.value ? clamp01(props.level as number) : 0;
  const ema = reducedMotion ? 0.05 : 0.14;
  smoothedLevel += (sourceLevel - smoothedLevel) * ema;
  const level = clamp01(smoothedLevel);

  const listenTarget = normalizedState.value === "listening" ? 1 : 0;
  const processTarget = normalizedState.value === "processing" ? 1 : 0;
  const speakTarget = normalizedState.value === "speaking" ? 1 : 0;
  const stateBlend = reducedMotion ? 0.06 : 0.12;
  smoothedListen += (listenTarget - smoothedListen) * stateBlend;
  smoothedProcess += (processTarget - smoothedProcess) * stateBlend;
  smoothedSpeak += (speakTarget - smoothedSpeak) * stateBlend;

  const motionTarget = props.reactive ? 1 : 0;
  const motionBlend = reducedMotion ? 0.09 : 0.2;
  smoothedMotionMix += (motionTarget - smoothedMotionMix) * motionBlend;
  const motionMix = clamp01(smoothedMotionMix);

  const breathFrequency = (Math.PI * 2) / Math.max(0.001, smoothedMotion.breathPeriod);
  const breath = Math.sin(elapsed * breathFrequency) * smoothedMotion.breathAmp * motionMix;
  const vibration = Math.sin(elapsed * 14.5) * 0.014 * motionMix * (0.45 + level * 0.85);
  const amplitudeScale = level * 0.075 * motionMix;
  const scale = 1 + breath + vibration + amplitudeScale;
  const statePulse = 0.5 + 0.5 * Math.sin(elapsed * (7.2 + level * 3.0));

  material.uniforms.uTime.value = elapsed;
  material.uniforms.uScale.value = THREE.MathUtils.clamp(scale, 0.9, 1.22);
  material.uniforms.uGlow.value = smoothedMotion.glow + level * 0.14;
  material.uniforms.uHighlight.value = smoothedMotion.highlight + level * 0.09;
  material.uniforms.uDriftX.value = smoothedMotion.driftRateX * motionMix;
  material.uniforms.uDriftY.value = smoothedMotion.driftRateY * motionMix;
  material.uniforms.uReducedMotion.value = reducedMotion ? 1 : 0;
  material.uniforms.uLevel.value = level;
  material.uniforms.uMotionMix.value = motionMix;
  material.uniforms.uWobble.value = (0.9 + level * 1.9) * motionMix;
  material.uniforms.uListen.value = smoothedListen;
  material.uniforms.uProcess.value = smoothedProcess;
  material.uniforms.uSpeak.value = smoothedSpeak;
  material.uniforms.uStatePulse.value = statePulse;

  renderer.render(scene, camera);
  rafId = window.requestAnimationFrame(animate);
};

const setupReducedMotion = () => {
  if (typeof window === "undefined" || !window.matchMedia) return;
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  reducedMotion = media.matches;

  const onChange = (event: MediaQueryListEvent) => {
    reducedMotion = event.matches;
    applyQualityPreset();
  };

  const modernMedia = media as MediaQueryList & {
    addEventListener?: (type: "change", listener: (event: MediaQueryListEvent) => void) => void;
    removeEventListener?: (type: "change", listener: (event: MediaQueryListEvent) => void) => void;
  };
  const legacyMedia = media as MediaQueryList & {
    addListener?: (listener: (event: MediaQueryListEvent) => void) => void;
    removeListener?: (listener: (event: MediaQueryListEvent) => void) => void;
  };

  if (typeof modernMedia.addEventListener === "function") {
    modernMedia.addEventListener("change", onChange);
    cleanupReducedMotion = () => modernMedia.removeEventListener?.("change", onChange);
    return;
  }

  if (typeof legacyMedia.addListener === "function") {
    legacyMedia.addListener(onChange);
    cleanupReducedMotion = () => legacyMedia.removeListener?.(onChange);
    return;
  }

  cleanupReducedMotion = null;
};

const setupRenderer = () => {
  if (!hostRef.value || !canvasRef.value) return;

  try {
    scene = new THREE.Scene();
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10);
    camera.position.z = 1;

    material = new THREE.ShaderMaterial({
      uniforms: {
        uResolution: { value: new THREE.Vector2(1, 1) },
        uTime: { value: 0 },
        uScale: { value: 1 },
        uGlow: { value: MOTION_PRESETS.idle.glow },
        uHighlight: { value: MOTION_PRESETS.idle.highlight },
        uDriftX: { value: MOTION_PRESETS.idle.driftRateX },
        uDriftY: { value: MOTION_PRESETS.idle.driftRateY },
        uReducedMotion: { value: 0 },
        uLevel: { value: 0 },
        uGlowBoost: { value: QUALITY_PRESETS.high.glowBoost },
        uMotionMix: { value: 0 },
        uWobble: { value: 0 },
        uListen: { value: 0 },
        uProcess: { value: 0 },
        uSpeak: { value: 0 },
        uStatePulse: { value: 0.5 },
        uMint: { value: new THREE.Color(BRAND_COLORS.mint) },
        uBlue: { value: new THREE.Color(BRAND_COLORS.blue) },
        uCyan: { value: new THREE.Color(BRAND_COLORS.cyan) },
        uWhite: { value: new THREE.Color(BRAND_COLORS.white) },
      },
      vertexShader,
      fragmentShader,
      transparent: true,
      depthWrite: false,
      depthTest: false,
      dithering: true,
    });

    mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
    scene.add(mesh);

    renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      premultipliedAlpha: true,
      powerPreference: "high-performance",
    });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x000000, props.transparent ? 0 : 1);
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    renderer.domElement.style.borderRadius = "50%";

    canvasRef.value.innerHTML = "";
    canvasRef.value.appendChild(renderer.domElement);

    resizeRenderer();
    applyQualityPreset();

    resizeObserver = new ResizeObserver(() => resizeRenderer());
    resizeObserver.observe(hostRef.value);

    const onWindowResize = () => resizeRenderer();
    window.addEventListener("resize", onWindowResize, { passive: true });
    cleanupWindowResize = () => window.removeEventListener("resize", onWindowResize);

    rafId = window.requestAnimationFrame(animate);
    hasRendererError.value = false;
  } catch (error) {
    console.error("VoiceOrb renderer init failed:", error);
    hasRendererError.value = true;
  }
};

const disposeRenderer = () => {
  if (rafId) {
    window.cancelAnimationFrame(rafId);
    rafId = 0;
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  cleanupWindowResize?.();
  cleanupWindowResize = null;

  if (mesh) {
    mesh.geometry.dispose();
    mesh.material.dispose();
    scene?.remove(mesh);
    mesh = null;
  }

  material = null;
  camera = null;
  scene = null;

  if (renderer) {
    renderer.dispose();
    renderer.forceContextLoss();
    if (renderer.domElement.parentNode) {
      renderer.domElement.parentNode.removeChild(renderer.domElement);
    }
    renderer = null;
  }

  startTime = 0;
};

watch(
  () => props.quality,
  () => applyQualityPreset()
);

watch(
  () => props.transparent,
  () => {
    if (!renderer) return;
    renderer.setClearColor(0x000000, props.transparent ? 0 : 1);
  }
);

watch(
  () => props.size,
  () => resizeRenderer()
);

onMounted(() => {
  setupReducedMotion();
  setupRenderer();
});

onBeforeUnmount(() => {
  cleanupReducedMotion?.();
  cleanupReducedMotion = null;
  disposeRenderer();
});
</script>

<template>
  <div ref="hostRef" class="voice-orb" :style="orbStyle" aria-hidden="true">
    <div ref="canvasRef" class="voice-orb__canvas"></div>
    <div v-if="hasRendererError" class="voice-orb__fallback"></div>
  </div>
</template>

<style scoped>
.voice-orb {
  position: relative;
  width: min(var(--orb-size), 70vw);
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  overflow: visible;
  display: grid;
  place-items: center;
  contain: layout size paint;
}

.voice-orb__canvas {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  overflow: hidden;
}

.voice-orb__canvas :deep(canvas) {
  width: 100% !important;
  height: 100% !important;
  display: block;
  border-radius: 50%;
}

.voice-orb__fallback {
  position: absolute;
  inset: 7%;
  border-radius: 50%;
  background: linear-gradient(140deg, #67e8f9, #4fd1c5 42%, #3b82f6 100%);
  box-shadow: inset 0 10px 24px rgba(255, 255, 255, 0.42), 0 10px 24px rgba(59, 130, 246, 0.14);
}
</style>
