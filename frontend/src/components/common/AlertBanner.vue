<script setup lang="ts">
import { ref } from 'vue';

type AlertType = 'info' | 'warning' | 'error' | 'success';

const props = withDefaults(
  defineProps<{
    type?: AlertType;
    message: string;
    actionRequired?: boolean;
    dismissible?: boolean;
    actionText?: string;
    compact?: boolean;
  }>(),
  {
    type: 'info',
    actionRequired: false,
    dismissible: true,
    compact: false
  }
);

const emit = defineEmits<{
  (e: 'action'): void;
  (e: 'dismiss'): void;
}>();

const dismissed = ref(false);

const handleAction = () => {
  emit('action');
};

const handleDismiss = () => {
  dismissed.value = true;
  emit('dismiss');
};
</script>

<template>
  <Transition name="alert-slide">
    <div
      v-if="!dismissed"
      class="alert-banner"
      :class="[
        `alert-banner--${type}`,
        { 'alert-banner--compact': compact },
        { 'alert-banner--action-required': actionRequired }
      ]"
      role="alert"
      :aria-live="type === 'error' ? 'assertive' : 'polite'"
    >
      <!-- 아이콘 -->
      <div class="alert-banner__icon">
        <!-- Info Icon -->
        <svg v-if="type === 'info'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
        <!-- Warning Icon -->
        <svg v-else-if="type === 'warning'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <!-- Error Icon -->
        <svg v-else-if="type === 'error'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        <!-- Success Icon -->
        <svg v-else-if="type === 'success'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
      </div>

      <!-- 메시지 영역 -->
      <div class="alert-banner__content">
        <p class="alert-banner__message">{{ message }}</p>
        <button
          v-if="actionText"
          class="alert-banner__action"
          type="button"
          @click="handleAction"
        >
          {{ actionText }}
        </button>
      </div>

      <!-- 닫기 버튼 -->
      <button
        v-if="dismissible"
        class="alert-banner__dismiss"
        type="button"
        @click="handleDismiss"
        aria-label="닫기"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.alert-banner {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
  border-left: 4px solid;
  transition: all 0.2s ease;
}

/* 타입별 스타일 */
.alert-banner--info {
  border-left-color: #4cb7b7;
  background: rgba(76, 183, 183, 0.06);
}

.alert-banner--info .alert-banner__icon {
  color: #4cb7b7;
}

.alert-banner--warning {
  border-left-color: #f5a623;
  background: rgba(245, 166, 35, 0.12);
}

.alert-banner--warning .alert-banner__icon {
  color: #f5a623;
}

.alert-banner--error {
  border-left-color: #ff8a80;
  background: rgba(255, 138, 128, 0.12);
}

.alert-banner--error .alert-banner__icon {
  color: #ff8a80;
}

.alert-banner--success {
  border-left-color: #66bb6a;
  background: rgba(102, 187, 106, 0.08);
}

.alert-banner--success .alert-banner__icon {
  color: #43a047;
}

/* 액션 필요 상태 강조 */
.alert-banner--action-required {
  animation: pulse-border 2s infinite;
}

@keyframes pulse-border {
  0%, 100% {
    box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
  }
  50% {
    box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff, 0 0 0 3px rgba(245, 166, 35, 0.3);
  }
}

/* 아이콘 */
.alert-banner__icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 2px;
}

/* 콘텐츠 영역 */
.alert-banner__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-banner__message {
  font-size: 15px;
  font-weight: 700;
  color: #2e2e2e;
  margin: 0;
  line-height: 1.5;
}

/* 액션 버튼 */
.alert-banner__action {
  align-self: flex-start;
  padding: 8px 16px;
  border-radius: 10px;
  border: none;
  background: rgba(0, 0, 0, 0.08);
  color: #2e2e2e;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}

.alert-banner__action:hover {
  background: rgba(0, 0, 0, 0.12);
}

.alert-banner--info .alert-banner__action {
  background: rgba(76, 183, 183, 0.15);
  color: #2e7d7d;
}

.alert-banner--info .alert-banner__action:hover {
  background: rgba(76, 183, 183, 0.25);
}

.alert-banner--warning .alert-banner__action {
  background: rgba(245, 166, 35, 0.2);
  color: #e65100;
}

.alert-banner--warning .alert-banner__action:hover {
  background: rgba(245, 166, 35, 0.35);
}

.alert-banner--error .alert-banner__action {
  background: rgba(255, 138, 128, 0.2);
  color: #c62828;
}

.alert-banner--error .alert-banner__action:hover {
  background: rgba(255, 138, 128, 0.35);
}

/* 닫기 버튼 */
.alert-banner__dismiss {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.alert-banner__dismiss:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #555;
}

/* 컴팩트 모드 */
.alert-banner--compact {
  padding: 12px 16px;
  border-radius: 14px;
  gap: 10px;
}

.alert-banner--compact .alert-banner__icon svg {
  width: 18px;
  height: 18px;
}

.alert-banner--compact .alert-banner__message {
  font-size: 14px;
}

.alert-banner--compact .alert-banner__dismiss {
  width: 28px;
  height: 28px;
}

/* 애니메이션 */
.alert-slide-enter-active,
.alert-slide-leave-active {
  transition: all 0.3s ease;
}

.alert-slide-enter-from,
.alert-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 반응형 - 모바일 */
@media (max-width: 520px) {
  .alert-banner {
    padding: 14px 16px;
    border-radius: 14px;
    gap: 12px;
  }

  .alert-banner__content {
    gap: 8px;
  }

  .alert-banner__message {
    font-size: 14px;
  }

  .alert-banner__action {
    width: 100%;
    text-align: center;
  }
}
</style>
