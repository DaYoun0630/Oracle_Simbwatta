<script setup lang="ts">
import { computed } from 'vue';

type EmptyStateType = 'info' | 'warning' | 'success' | 'no-data' | 'partial-data' | 'not-applicable';

const props = withDefaults(
  defineProps<{
    type?: EmptyStateType;
    icon?: string;
    title: string;
    description: string;
    benefits?: string[];
    actionText?: string;
    note?: string;
  }>(),
  {
    type: 'info',
    benefits: () => []
  }
);

const emit = defineEmits<{
  (e: 'action'): void;
}>();

// 타입별 기본 아이콘
const defaultIcon = computed(() => {
  switch (props.type) {
    case 'no-data':
    case 'info':
      return 'clipboard';
    case 'warning':
      return 'alert';
    case 'success':
      return 'check';
    case 'partial-data':
      return 'chart';
    case 'not-applicable':
      return 'info';
    default:
      return 'clipboard';
  }
});

const iconType = computed(() => props.icon || defaultIcon.value);

const handleAction = () => {
  emit('action');
};
</script>

<template>
  <div class="empty-state" :class="`empty-state--${type}`" role="status" aria-live="polite">
    <!-- 아이콘 영역 -->
    <div class="empty-state__icon-wrapper">
      <div class="empty-state__icon">
        <slot name="icon">
          <!-- Clipboard Icon (default for no-data, info) -->
          <svg v-if="iconType === 'clipboard'" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
            <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
          </svg>
          <!-- Alert Icon (warning) -->
          <svg v-else-if="iconType === 'alert'" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          <!-- Check Icon (success) -->
          <svg v-else-if="iconType === 'check'" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <!-- Chart Icon (partial-data) -->
          <svg v-else-if="iconType === 'chart'" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
          <!-- Info Icon (not-applicable) -->
          <svg v-else-if="iconType === 'info'" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          <!-- Brain Icon (for MRI/cognitive) -->
          <svg v-else-if="iconType === 'brain'" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"></path>
            <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"></path>
          </svg>
          <!-- Microphone Icon (for voice) -->
          <svg v-else-if="iconType === 'microphone'" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
        </slot>
      </div>
    </div>

    <!-- 타이틀 -->
    <h3 class="empty-state__title">{{ title }}</h3>

    <!-- 설명 -->
    <p class="empty-state__description">{{ description }}</p>

    <!-- 이점 목록 -->
    <ul v-if="benefits.length > 0" class="empty-state__benefits">
      <li v-for="benefit in benefits" :key="benefit">{{ benefit }}</li>
    </ul>

    <!-- 액션 버튼 -->
    <button
      v-if="actionText"
      class="empty-state__action"
      type="button"
      @click="handleAction"
    >
      {{ actionText }}
    </button>

    <!-- 부가 설명 (노트) -->
    <p v-if="note" class="empty-state__note">{{ note }}</p>

    <!-- 커스텀 슬롯 -->
    <slot></slot>
  </div>
</template>

<style scoped>
.empty-state {
  background: #f5f6f7;
  border-radius: 26px;
  padding: 40px 32px;
  box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

/* 아이콘 래퍼 */
.empty-state__icon-wrapper {
  width: 88px;
  height: 88px;
  border-radius: 24px;
  background: #ffffff;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.empty-state__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4cb7b7;
}

/* 타입별 아이콘 색상 */
.empty-state--warning .empty-state__icon {
  color: #ffb74d;
}

.empty-state--success .empty-state__icon {
  color: #66bb6a;
}

.empty-state--no-data .empty-state__icon,
.empty-state--partial-data .empty-state__icon {
  color: #4cb7b7;
}

.empty-state--not-applicable .empty-state__icon {
  color: #9ca3af;
}

/* 타이틀 */
.empty-state__title {
  font-size: 20px;
  font-weight: 800;
  color: #2e2e2e;
  margin: 0;
  line-height: 1.4;
}

/* 설명 */
.empty-state__description {
  font-size: 15px;
  font-weight: 700;
  color: #777;
  line-height: 1.6;
  max-width: 340px;
  margin: 0;
}

/* 이점 목록 */
.empty-state__benefits {
  list-style: none;
  padding: 0;
  margin: 12px 0;
  text-align: left;
  width: 100%;
  max-width: 320px;
}

.empty-state__benefits li {
  padding: 10px 0 10px 28px;
  position: relative;
  font-size: 14px;
  font-weight: 700;
  color: #555;
  line-height: 1.5;
}

.empty-state__benefits li::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4cb7b7;
}

.empty-state--warning .empty-state__benefits li::before {
  background: #ffb74d;
}

/* 액션 버튼 */
.empty-state__action {
  padding: 14px 28px;
  border-radius: 16px;
  border: none;
  background: #4cb7b7;
  color: #ffffff;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
  transition: all 0.2s ease;
  margin-top: 8px;
}

.empty-state__action:hover {
  background: #3da5a5;
  transform: translateY(-2px);
  box-shadow: 8px 8px 16px #d1d9e6, -8px -8px 16px #ffffff;
}

.empty-state__action:active {
  transform: translateY(0);
  box-shadow: inset 4px 4px 8px rgba(0, 0, 0, 0.1);
}

/* 부가 설명 */
.empty-state__note {
  font-size: 13px;
  font-weight: 700;
  color: #888;
  line-height: 1.5;
  margin: 8px 0 0;
  max-width: 320px;
}

/* 반응형 - 모바일 */
@media (max-width: 520px) {
  .empty-state {
    padding: 32px 20px;
    border-radius: 20px;
  }

  .empty-state__icon-wrapper {
    width: 72px;
    height: 72px;
    border-radius: 20px;
  }

  .empty-state__icon svg {
    width: 32px;
    height: 32px;
  }

  .empty-state__title {
    font-size: 18px;
  }

  .empty-state__description {
    font-size: 14px;
  }

  .empty-state__benefits {
    max-width: 100%;
  }

  .empty-state__action {
    width: 100%;
    padding: 14px 20px;
  }
}
</style>
