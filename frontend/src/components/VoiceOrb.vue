<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as THREE from "three";

type VoiceState = "idle" | "listening" | "pause" | "processing" | "speaking" | "cooldown";
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
  props.state === "pause" || props.state === "cooldown" ? "processing" : props.state
);

const orbStyle = computed(() => ({
  "--orb-size": `${props.size}px`,
}));

const AUDIO_ACTIVE_LEVEL = 0.026;

const currentLevel = computed(() =>
  isProvidedLevel.value ? clamp01(props.level as number) : 0
);

const isAudioReactive = computed(
  () => Boolean(props.reactive) && currentLevel.value > AUDIO_ACTIVE_LEVEL
);

const orbClasses = computed(() => [
  `state--${normalizedState.value}`,
  isAudioReactive.value ? "is-audio-reactive" : "is-silent",
]);

// Stronger state contrast + larger audio-reactive breathing.
const MOTION_PRESETS: Record<NormalizedState, MotionPreset> = {
  idle: {
    breathPeriod: 6.4,
    breathAmp: 0.02,
    driftRateX: 0.11,
    driftRateY: 0.1,
    glow: 0.14,
    highlight: 0.33,
  },
  listening: {
    breathPeriod: 4.6,
    breathAmp: 0.052,
    driftRateX: 0.2,
    driftRateY: 0.18,
    glow: 0.26,
    highlight: 0.42,
  },
  processing: {
    breathPeriod: 6.2,
    breathAmp: 0.04,
    driftRateX: 0.11,
    driftRateY: 0.09,
    glow: 0.3,
    highlight: 0.48,
  },
  speaking: {
    breathPeriod: 3.8,
    breathAmp: 0.07,
    driftRateX: 0.24,
    driftRateY: 0.2,
    glow: 0.35,
    highlight: 0.52,
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
  base = mix(base, mix(uMint, uCyan, 0.66), 0.24 * uListen);
  base = mix(base, mix(uBlue, uWhite, 0.48), 0.3 * uProcess);
  base = mix(base, mix(uBlue, uCyan, 0.44), 0.34 * uSpeak);

  float centerSoft = exp(-r * r * 1.8);
  base = mix(base, uWhite, 0.08 + centerSoft * 0.12);

  vec2 specPos = vec2(-0.25, 0.27) + drift * 0.24 + wobbleOffset * 0.25;
  float spec = exp(-dot(p - specPos, p - specPos) * 22.0);
  float softSpec = exp(-dot(p - vec2(-0.02, 0.04), p - vec2(-0.02, 0.04)) * 7.5);

  float level = clamp(uLevel, 0.0, 1.0);
  float rimLight = rimLine * (0.18 + uGlow * 0.74) * (0.72 + uMotionMix * 0.4) * uGlowBoost;
  rimLight *= (1.0 + uListen * 0.34 + uProcess * 0.48 + uSpeak * (0.86 + 0.42 * uStatePulse));
  float innerGlow = (1.0 - smoothstep(0.0, 0.96, r)) * (0.05 + uGlow * 0.14);
  float highlight = (spec * 0.24 + softSpec * 0.1) * uHighlight * (1.0 + level * 0.36);
  highlight *= (1.0 + uProcess * 0.3 + uSpeak * 0.5);

  float motionPulse = smoothstep(0.04, 0.34, uMotionMix);
  float processBand = exp(-pow(r - 0.58, 2.0) * 120.0) * (0.3 + 0.7 * (0.5 + 0.5 * sin(uTime * 2.8))) * motionPulse;
  float listenLift = smoothstep(-0.1, 0.85, p.y + 0.12);
  float listeningRing = exp(-pow(r - 0.78, 2.0) * 95.0) * uListen * (0.55 + level * 0.85);
  float processingCore = exp(-r * r * 3.2) * uProcess * (0.35 + 0.65 * (0.5 + 0.5 * sin(uTime * 3.3))) * motionPulse;
  float speakingPulse = (0.5 + 0.5 * sin(uTime * 10.6)) * uSpeak * motionPulse;
  float speakingBand = exp(-pow(r - 0.66, 2.0) * 92.0) * uSpeak * (0.28 + level * 0.58 + speakingPulse * 0.55) * motionPulse;

  vec3 color = base;
  color += uWhite * highlight;
  color += uCyan * innerGlow;
  color += mix(uMint, uBlue, 0.4) * rimLight;
  color += uWhite * processBand * 0.2 * uProcess;
  color += uCyan * listenLift * 0.11 * uListen;
  color += uCyan * listeningRing * 0.14;
  color += mix(uBlue, uWhite, 0.4) * processingCore * 0.2;
  color += mix(uMint, uWhite, 0.35) * speakingBand * 0.28;
  color += mix(uMint, uBlue, 0.55) * rimLine * speakingPulse * 0.2;
  color = mix(color, vec3(1.0), rimLine * (0.12 + 0.06 * uSpeak));

  float alpha = sphereMask;
  alpha += outerGlow * (0.025 + uGlow * 0.085) * uGlowBoost;
  alpha += outerGlow * speakingPulse * 0.06;
  alpha += outerGlow * (listeningRing * 0.04 + processingCore * 0.03 + speakingBand * 0.05);
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
  const transition = reducedMotion ? 0.04 : 0.055;

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

  const sourceLevel = currentLevel.value;
  const ema = reducedMotion ? 0.05 : 0.11;
  smoothedLevel += (sourceLevel - smoothedLevel) * ema;
  const level = clamp01(smoothedLevel);
  const boostedLevel = reducedMotion ? level : clamp01(Math.pow(level, 0.9) * 1.02);

  const listenTarget = normalizedState.value === "listening" ? 1 : 0;
  const processTarget = normalizedState.value === "processing" ? 1 : 0;
  const speakTarget = normalizedState.value === "speaking" ? 1 : 0;
  const stateBlend = reducedMotion ? 0.06 : 0.12;
  smoothedListen += (listenTarget - smoothedListen) * stateBlend;
  smoothedProcess += (processTarget - smoothedProcess) * stateBlend;
  smoothedSpeak += (speakTarget - smoothedSpeak) * stateBlend;

  const motionTargetRaw = isAudioReactive.value ? 1 : 0;
  const motionTarget = reducedMotion ? Math.min(0.3, motionTargetRaw) : motionTargetRaw;
  const motionBlend = reducedMotion ? 0.07 : 0.14;
  smoothedMotionMix += (motionTarget - smoothedMotionMix) * motionBlend;
  const motionMix = clamp01(smoothedMotionMix);

  const breathFrequency = (Math.PI * 2) / Math.max(0.001, smoothedMotion.breathPeriod);
  const stateMotionBoost = 1 + smoothedListen * 0.1 + smoothedProcess * 0.08 + smoothedSpeak * 0.16;
  const breath = Math.sin(elapsed * breathFrequency) * smoothedMotion.breathAmp * motionMix * stateMotionBoost;
  const vibration =
    Math.sin(elapsed * 11.2) *
    0.011 *
    motionMix *
    (0.34 + boostedLevel * 0.72 + smoothedSpeak * 0.14);
  const audioBounce =
    Math.sin(elapsed * (12 + boostedLevel * 6)) *
    (0.004 + boostedLevel * 0.018) *
    motionMix *
    (0.66 + smoothedListen * 0.1 + smoothedSpeak * 0.18);
  const amplitudeScale =
    boostedLevel * (0.048 + smoothedListen * 0.01 + smoothedSpeak * 0.02) * motionMix;
  const scale = 1 + breath + vibration + audioBounce + amplitudeScale;
  const statePulse =
    motionMix > 0.02 ? 0.5 + 0.5 * Math.sin(elapsed * (6.3 + boostedLevel * 2.1)) : 0.5;

  material.uniforms.uTime.value = elapsed;
  material.uniforms.uScale.value = THREE.MathUtils.clamp(scale, 0.94, 1.16);
  material.uniforms.uGlow.value = smoothedMotion.glow + boostedLevel * 0.1 + smoothedSpeak * 0.03;
  material.uniforms.uHighlight.value =
    smoothedMotion.highlight + boostedLevel * 0.07 + smoothedProcess * 0.025;
  material.uniforms.uDriftX.value = smoothedMotion.driftRateX * motionMix;
  material.uniforms.uDriftY.value = smoothedMotion.driftRateY * motionMix;
  material.uniforms.uReducedMotion.value = reducedMotion ? 1 : 0;
  material.uniforms.uLevel.value = boostedLevel;
  material.uniforms.uMotionMix.value = motionMix;
  material.uniforms.uWobble.value = (0.78 + boostedLevel * 1.2 + smoothedSpeak * 0.28) * motionMix;
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
  <div ref="hostRef" class="voice-orb" :class="orbClasses" :style="orbStyle" aria-hidden="true">
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

.voice-orb::before,
.voice-orb::after {
  content: "";
  position: absolute;
  inset: -2%;
  border-radius: 50%;
  pointer-events: none;
  opacity: 0;
  transform: scale(0.96);
  z-index: 0;
  transition: opacity 220ms ease, transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
}

.voice-orb.state--idle::before {
  opacity: 0.42;
  transform: scale(0.98);
  box-shadow: 0 0 0 1px rgba(103, 232, 249, 0.26), 0 0 18px rgba(79, 209, 197, 0.18);
}

.voice-orb.state--listening::before {
  opacity: 0.52;
  transform: scale(0.99);
  box-shadow:
    0 0 0 1px rgba(103, 232, 249, 0.35),
    0 0 18px rgba(103, 232, 249, 0.22),
    inset 0 0 12px rgba(79, 209, 197, 0.12);
}

.voice-orb.state--processing::before {
  opacity: 0.6;
  inset: -3%;
  border: 2px dashed rgba(59, 130, 246, 0.24);
  box-shadow: 0 0 16px rgba(59, 130, 246, 0.18);
}

.voice-orb.state--processing::after {
  opacity: 0.45;
  transform: scale(0.96);
  box-shadow: 0 0 24px rgba(59, 130, 246, 0.16), inset 0 0 12px rgba(255, 255, 255, 0.2);
}

.voice-orb.state--speaking::before {
  opacity: 0.66;
  inset: -4%;
  transform: scale(0.99);
  box-shadow:
    0 0 0 1px rgba(79, 209, 197, 0.4),
    0 0 24px rgba(79, 209, 197, 0.25),
    0 0 38px rgba(59, 130, 246, 0.18);
}

.voice-orb.state--speaking::after {
  opacity: 0;
  inset: -3%;
  border: 2px solid rgba(103, 232, 249, 0.32);
}

.voice-orb.is-audio-reactive.state--listening::before {
  opacity: 0.86;
  transform: scale(1);
  box-shadow:
    0 0 0 2px rgba(103, 232, 249, 0.48),
    0 0 26px rgba(103, 232, 249, 0.38),
    inset 0 0 18px rgba(79, 209, 197, 0.16);
  animation: orbListeningHalo 1.55s ease-in-out infinite;
}

.voice-orb.is-audio-reactive.state--processing::before {
  opacity: 0.82;
  border-color: rgba(59, 130, 246, 0.34);
  box-shadow: 0 0 22px rgba(59, 130, 246, 0.24);
  animation: orbProcessingOrbit 2.6s linear infinite;
}

.voice-orb.is-audio-reactive.state--processing::after {
  opacity: 0.64;
  animation: orbProcessingPulse 2.8s ease-in-out infinite;
}

.voice-orb.is-audio-reactive.state--speaking::before {
  opacity: 0.92;
  transform: scale(1);
  box-shadow:
    0 0 0 2px rgba(79, 209, 197, 0.48),
    0 0 32px rgba(79, 209, 197, 0.38),
    0 0 54px rgba(59, 130, 246, 0.24);
  animation: orbSpeakingHalo 1.15s cubic-bezier(0.2, 0.8, 0.2, 1) infinite;
}

.voice-orb.is-audio-reactive.state--speaking::after {
  opacity: 0.74;
  animation: orbSpeakingRing 1.35s ease-out infinite;
}

.voice-orb.is-silent::before,
.voice-orb.is-silent::after {
  animation: none !important;
}

.voice-orb__canvas {
  position: relative;
  z-index: 1;
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
  z-index: 1;
  border-radius: 50%;
  background: linear-gradient(140deg, #67e8f9, #4fd1c5 42%, #3b82f6 100%);
  box-shadow: inset 0 10px 24px rgba(255, 255, 255, 0.42), 0 10px 24px rgba(59, 130, 246, 0.14);
}

@keyframes orbListeningHalo {
  0% {
    transform: scale(0.98);
    box-shadow:
      0 0 0 2px rgba(103, 232, 249, 0.26),
      0 0 16px rgba(103, 232, 249, 0.24),
      inset 0 0 12px rgba(79, 209, 197, 0.14);
  }
  55% {
    transform: scale(1.03);
    box-shadow:
      0 0 0 3px rgba(103, 232, 249, 0.46),
      0 0 28px rgba(103, 232, 249, 0.4),
      inset 0 0 18px rgba(79, 209, 197, 0.2);
  }
  100% {
    transform: scale(0.99);
    box-shadow:
      0 0 0 2px rgba(103, 232, 249, 0.32),
      0 0 20px rgba(103, 232, 249, 0.28),
      inset 0 0 14px rgba(79, 209, 197, 0.16);
  }
}

@keyframes orbProcessingOrbit {
  0% {
    transform: rotate(0deg) scale(0.98);
  }
  50% {
    transform: rotate(180deg) scale(1.01);
  }
  100% {
    transform: rotate(360deg) scale(0.98);
  }
}

@keyframes orbProcessingPulse {
  0% {
    transform: scale(0.96);
    opacity: 0.48;
  }
  50% {
    transform: scale(1);
    opacity: 0.68;
  }
  100% {
    transform: scale(0.97);
    opacity: 0.5;
  }
}

@keyframes orbSpeakingHalo {
  0% {
    transform: scale(0.97);
    filter: brightness(0.99);
  }
  50% {
    transform: scale(1.05);
    filter: brightness(1.04);
  }
  100% {
    transform: scale(0.98);
    filter: brightness(1.01);
  }
}

@keyframes orbSpeakingRing {
  0% {
    transform: scale(0.96);
    opacity: 0.64;
  }
  100% {
    transform: scale(1.14);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .voice-orb::before,
  .voice-orb::after {
    animation: none !important;
    transition: none !important;
    filter: none !important;
    transform: scale(1) !important;
  }
}
</style>
