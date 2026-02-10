<script setup>
import { ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useVoiceSession } from '@/composables/useVoiceSession';
import AppHeader from '@/components/AppHeader.vue';

const props = defineProps({
  title: {
    type: String,
    default: '홈'
  },
  showMenuButton: {
    type: Boolean,
    default: false
  },
  showHomeButton: {
    type: Boolean,
    default: false
  }
});

const router = useRouter();
const { resetSession } = useVoiceSession();
const fontScale = ref(localStorage.getItem('ui-font-scale') || 'medium');

const goBack = () => {
  router.back();
};

const goHome = () => {
  resetSession();
  router.push({ name: 'home' });
};

const goSettings = () => {
  if (router.currentRoute.value.name === 'settings') return;
  router.push({ name: 'settings' });
};

watch(fontScale, (value) => {
  const map = { small: '15px', medium: '16px', large: '18px' };
  document.documentElement.style.fontSize = map[value] || '16px';
  localStorage.setItem('ui-font-scale', value);
}, { immediate: true });
</script>

<template>
  <div class="subject-shell">
    <AppHeader
      :title="props.title"
      :showBackButton="true"
      :showMenuButton="props.showMenuButton"
      @back="goBack"
      @menu="goSettings"
    />

    <div class="content">
      <slot />
    </div>

    <button
      v-if="showHomeButton"
      class="floating-home"
      @click.stop="goHome"
      type="button"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
        <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
      </svg>
    </button>
  </div>
</template>

<style scoped>
.subject-shell {
  min-height: 100vh;
  background: linear-gradient(180deg, #f5f6f7 0%, #e8ecef 100%);
  display: flex;
  flex-direction: column;
  position: relative;
}


.content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.floating-home {
  position: fixed;
  bottom: 32px;
  right: 24px;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #4cb7b7;
  border: none;
  box-shadow: 0 10px 20px rgba(76, 183, 183, 0.4),
              inset 2px 2px 4px rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 998;
}

.floating-home:hover {
  transform: scale(1.05);
}

.floating-home:active {
  transform: scale(0.95);
  box-shadow: 0 5px 10px rgba(76, 183, 183, 0.3);
}

</style>
