<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  originalImage?: string;
  attentionMap?: string;
  loading?: boolean;
}>();

const hasOriginal = computed(() => !!props.originalImage);
const hasAttention = computed(() => !!props.attentionMap);
</script>

<template>
  <div class="mri-image-display">
    <div class="image-grid">
      <!-- 원본 MRI -->
      <div class="image-card">
        <h4 class="image-label">원본 MRI</h4>
        <div class="image-container">
          <div v-if="loading" class="image-placeholder loading">
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
          <div v-else class="image-placeholder">
            <span>MRI 이미지가 없습니다</span>
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
