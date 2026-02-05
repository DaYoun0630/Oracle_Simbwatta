<script setup>
import { computed } from 'vue';

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  showBackButton: {
    type: Boolean,
    default: true
  },
  showMenuButton: {
    type: Boolean,
    default: true
  },
  patientLabel: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['back', 'menu']);

const hasPatientLabel = computed(() => Boolean(props.patientLabel));

const handleBack = () => {
  emit('back');
};

const handleMenu = () => {
  emit('menu');
};
</script>

<template>
  <header class="app-header" :class="{ 'has-subline': hasPatientLabel }">
    <div class="header-row">
      <button
        v-if="showBackButton"
        class="back-btn"
        type="button"
        aria-label="뒤로 가기"
        @click="handleBack"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" fill="#2e2e2e" />
        </svg>
      </button>
      <div v-else class="header-spacer" aria-hidden="true"></div>

      <h1 class="title">{{ title }}</h1>

      <button
        v-if="showMenuButton"
        class="menu-button"
        type="button"
        aria-label="메뉴 열기"
        @click="handleMenu"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="5" cy="5" r="2" />
          <circle cx="12" cy="5" r="2" />
          <circle cx="19" cy="5" r="2" />
          <circle cx="5" cy="12" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="19" cy="12" r="2" />
          <circle cx="5" cy="19" r="2" />
          <circle cx="12" cy="19" r="2" />
          <circle cx="19" cy="19" r="2" />
        </svg>
      </button>
      <div v-else class="header-spacer" aria-hidden="true"></div>
    </div>

    <p v-if="hasPatientLabel" class="patient-label">
      {{ patientLabel }}
    </p>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 16px 8px;
  background: #f5f6f7;
  position: sticky;
  top: 0;
  z-index: 120;
}

.header-row {
  display: grid;
  grid-template-columns: 48px 1fr 48px;
  align-items: center;
}

.back-btn {
  width: 44px;
  height: 44px;
  border: none;
  background: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.menu-button {
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 16px;
  background: #f5f6f7;
  box-shadow: inset 4px 4px 10px #d1d9e6, inset -4px -4px 10px #ffffff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #555;
  transition: transform 0.2s ease;
}

.menu-button svg {
  fill: currentColor;
}

.menu-button:active {
  transform: scale(0.97);
}

.header-spacer {
  width: 48px;
  height: 48px;
}

.title {
  font-size: 20px;
  font-weight: 800;
  text-align: center;
  color: #2e2e2e;
  margin: 0;
}

.patient-label {
  margin: 0;
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  color: #5f5f5f;
}
</style>
