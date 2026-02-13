<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

const props = defineProps<{
  originalImage?: string;
  originalNifti?: string;
  attentionMap?: string;
  loading?: boolean;
}>();

const niftiCanvasRef = ref<HTMLCanvasElement | null>(null);
const niftiLoading = ref(false);
const niftiError = ref('');

const hasOriginal = computed(() => !!props.originalImage);
const hasOriginalNifti = computed(() => !!props.originalNifti);
const hasAttention = computed(() => !!props.attentionMap);

const isGzip = (bytes: Uint8Array) => bytes.length >= 2 && bytes[0] === 0x1f && bytes[1] === 0x8b;

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const bytesPerVoxel = (datatype: number) => {
  switch (datatype) {
    case 2: // uint8
    case 256: // int8
      return 1;
    case 4: // int16
    case 512: // uint16
      return 2;
    case 8: // int32
    case 16: // float32
    case 768: // uint32
      return 4;
    case 64: // float64
      return 8;
    default:
      throw new Error(`지원하지 않는 NIfTI datatype: ${datatype}`);
  }
};

const readVoxelValue = (view: DataView, datatype: number, offset: number, littleEndian: boolean) => {
  switch (datatype) {
    case 2:
      return view.getUint8(offset);
    case 256:
      return view.getInt8(offset);
    case 4:
      return view.getInt16(offset, littleEndian);
    case 512:
      return view.getUint16(offset, littleEndian);
    case 8:
      return view.getInt32(offset, littleEndian);
    case 16:
      return view.getFloat32(offset, littleEndian);
    case 64:
      return view.getFloat64(offset, littleEndian);
    case 768:
      return view.getUint32(offset, littleEndian);
    default:
      throw new Error(`지원하지 않는 NIfTI datatype: ${datatype}`);
  }
};

const parseNiftiHeader = (buffer: ArrayBuffer) => {
  const view = new DataView(buffer);
  const sizeofHdrLe = view.getInt32(0, true);
  const sizeofHdrBe = view.getInt32(0, false);
  const littleEndian =
    sizeofHdrLe === 348 ? true : sizeofHdrBe === 348 ? false : null;

  if (littleEndian === null) {
    throw new Error('유효한 NIfTI 헤더가 아닙니다.');
  }

  const width = view.getInt16(42, littleEndian);
  const height = view.getInt16(44, littleEndian);
  const depth = view.getInt16(46, littleEndian);
  const datatype = view.getInt16(70, littleEndian);
  const voxOffset = Math.floor(view.getFloat32(108, littleEndian));

  if (width <= 0 || height <= 0 || depth <= 0) {
    throw new Error('NIfTI 볼륨 차원 정보가 유효하지 않습니다.');
  }

  return {
    littleEndian,
    width,
    height,
    depth,
    datatype,
    voxOffset
  };
};

const maybeGunzip = async (buffer: ArrayBuffer): Promise<ArrayBuffer> => {
  const bytes = new Uint8Array(buffer);
  if (!isGzip(bytes)) {
    return buffer;
  }

  if (typeof DecompressionStream === 'undefined') {
    throw new Error('브라우저에서 gzip 해제를 지원하지 않습니다.');
  }

  const decompressedStream = new Blob([bytes])
    .stream()
    .pipeThrough(new DecompressionStream('gzip'));
  return new Response(decompressedStream).arrayBuffer();
};

const renderMiddleSlice = (buffer: ArrayBuffer) => {
  const { littleEndian, width, height, depth, datatype, voxOffset } = parseNiftiHeader(buffer);
  const bytes = bytesPerVoxel(datatype);
  const volumeSize = width * height * depth;
  const requiredSize = voxOffset + volumeSize * bytes;
  if (requiredSize > buffer.byteLength) {
    throw new Error('NIfTI 데이터 길이가 헤더 정보와 일치하지 않습니다.');
  }

  const view = new DataView(buffer);
  const sliceIndex = Math.floor(depth / 2);
  const sliceSize = width * height;
  const values = new Float32Array(sliceSize);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const pixelIndex = y * width + x;
      const voxelIndex = sliceIndex * sliceSize + pixelIndex;
      const offset = voxOffset + voxelIndex * bytes;
      values[pixelIndex] = readVoxelValue(view, datatype, offset, littleEndian);
    }
  }

  const finiteValues = Array.from(values).filter((value) => Number.isFinite(value));
  if (finiteValues.length === 0) {
    throw new Error('NIfTI 슬라이스에 유효한 픽셀 값이 없습니다.');
  }

  finiteValues.sort((a, b) => a - b);
  const lowIndex = Math.floor((finiteValues.length - 1) * 0.02);
  const highIndex = Math.floor((finiteValues.length - 1) * 0.98);
  const low = finiteValues[lowIndex];
  const high = finiteValues[highIndex];
  const min = Number.isFinite(low) ? low : finiteValues[0];
  const max = Number.isFinite(high) && high > min ? high : finiteValues[finiteValues.length - 1];
  const range = max - min || 1;

  const canvas = niftiCanvasRef.value;
  if (!canvas) {
    throw new Error('NIfTI 캔버스를 찾을 수 없습니다.');
  }

  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('캔버스 2D 컨텍스트를 생성할 수 없습니다.');
  }

  const imageData = context.createImageData(width, height);
  for (let i = 0; i < values.length; i += 1) {
    const source = Number.isFinite(values[i]) ? values[i] : min;
    const gray = Math.round(clamp((source - min) / range, 0, 1) * 255);
    const offset = i * 4;
    imageData.data[offset] = gray;
    imageData.data[offset + 1] = gray;
    imageData.data[offset + 2] = gray;
    imageData.data[offset + 3] = 255;
  }
  context.putImageData(imageData, 0, 0);
};

const loadNifti = async () => {
  if (!props.originalNifti || props.originalImage) {
    return;
  }

  niftiLoading.value = true;
  niftiError.value = '';
  try {
    const response = await fetch(props.originalNifti);
    if (!response.ok) {
      throw new Error(`NIfTI 요청 실패 (${response.status})`);
    }
    const compressedBuffer = await response.arrayBuffer();
    const decompressedBuffer = await maybeGunzip(compressedBuffer);
    // loading placeholder를 먼저 내린 뒤 canvas가 마운트되면 그린다.
    niftiLoading.value = false;
    await nextTick();
    renderMiddleSlice(decompressedBuffer);
  } catch (error) {
    console.error(error);
    niftiError.value = 'NIfTI 원본 이미지를 표시할 수 없습니다.';
  } finally {
    if (niftiLoading.value) {
      niftiLoading.value = false;
    }
  }
};

watch(
  () => [props.originalImage, props.originalNifti],
  () => {
    if (props.originalImage || !props.originalNifti) {
      niftiLoading.value = false;
      niftiError.value = '';
      return;
    }
    void loadNifti();
  },
  { immediate: true }
);
</script>

<template>
  <div class="mri-image-display">
    <div class="image-grid">
      <!-- 원본 MRI -->
      <div class="image-card">
        <h4 class="image-label">원본 MRI</h4>
        <div class="image-container">
          <div v-if="loading || niftiLoading" class="image-placeholder loading">
            <div class="spinner"></div>
            <span>MRI 이미지 로딩 중...</span>
          </div>
          <template v-else-if="hasOriginal">
            <img
              :src="originalImage"
              alt="Original MRI"
              loading="lazy"
              @error="($event.target as HTMLImageElement).src = ''"
            />
          </template>
          <template v-else-if="hasOriginalNifti && !niftiError">
            <canvas
              ref="niftiCanvasRef"
              class="nifti-canvas"
              aria-label="Original MRI NIfTI middle slice"
            />
          </template>
          <div v-else class="image-placeholder">
            <span>{{ niftiError || 'MRI 이미지가 없습니다' }}</span>
          </div>
        </div>
      </div>

      <!-- Attention Map -->
      <div class="image-card">
        <h4 class="image-label">Attention Map</h4>
        <div class="image-container">
          <div v-if="loading" class="image-placeholder loading">
            <div class="spinner"></div>
            <span>Attention Map 로딩 중...</span>
          </div>
          <template v-else-if="hasAttention">
            <img
              :src="attentionMap"
              alt="Attention Map"
              loading="lazy"
              @error="($event.target as HTMLImageElement).src = ''"
            />
          </template>
          <div v-else class="image-placeholder">
            <span>Attention Map이 없습니다</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mri-image-display {
  width: 100%;
}

.image-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.image-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 16px;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.image-label {
  font-size: 16px;
  font-weight: 800;
  color: #777;
  margin: 0;
}

.image-container {
  aspect-ratio: 1 / 1;
  border-radius: 16px;
  overflow: hidden;
  background: #1f2428;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-container img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.nifti-canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  background: #000;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: #e5e7eb;
  color: #666;
  font-weight: 700;
  font-size: 15px;
  text-align: center;
  padding: 20px;
}

.image-placeholder.loading {
  background: #f0f3f6;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #4cb7b7;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 반응형 - 모바일에서는 세로 스택 */
@media (max-width: 768px) {
  .image-grid {
    grid-template-columns: 1fr;
  }
}
</style>
