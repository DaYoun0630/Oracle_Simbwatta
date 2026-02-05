<script setup>
import { ref, computed, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import AppHeader from '@/components/AppHeader.vue';

const props = defineProps({
  title: {
    type: String,
    default: '모니터링 홈'
  }
});

const router = useRouter();
const route = useRoute();

const tabs = [
  {
    name: 'home',
    label: '홈',
    icon: 'M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z'
  },
  {
    name: 'history',
    label: '기록',
    icon: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z'
  },
  {
    name: 'settings',
    label: '설정',
    icon: 'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'
  }
];

const currentTab = computed(() => route.name || 'home');
const fontScale = ref(localStorage.getItem('ui-font-scale') || 'medium');

const navigateTo = (tabName) => {
  router.push({ name: tabName });
};

const goBack = () => {
  router.back();
};

watch(fontScale, (value) => {
  const map = { small: '15px', medium: '16px', large: '18px' };
  document.documentElement.style.fontSize = map[value] || '16px';
  localStorage.setItem('ui-font-scale', value);
}, { immediate: true });
</script>

<template>
  <div class="caregiver-shell">
    <AppHeader
      :title="title"
      :showBackButton="true"
      :showMenuButton="false"
      @back="goBack"
    />

    <main class="content">
      <slot />
    </main>

    <nav class="bottom-nav">
      <button
        v-for="tab in tabs"
        :key="tab.name"
        :class="['nav-item', { active: currentTab === tab.name }]"
        @click="navigateTo(tab.name)"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" class="icon">
          <path :d="tab.icon" :fill="currentTab === tab.name ? '#4cb7b7' : '#999'" />
        </svg>
        <span class="label">{{ tab.label }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.caregiver-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f6f7;
  position: relative;
}


.content {
  flex: 1;
  padding: 16px;
  padding-bottom: 90px;
  max-width: 460px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 70px;
  background: #f5f6f7;
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 8px 16px 12px;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  max-width: 460px;
  margin: 0 auto;
  z-index: 90;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  padding: 8px 16px;
  cursor: pointer;
  border-radius: 12px;
  transition: all 0.2s;
}

.nav-item.active {
  background: #fff;
  box-shadow: 2px 2px 6px #d1d9e6, -2px -2px 6px #ffffff;
}

.icon {
  transition: transform 0.2s;
}

.nav-item.active .icon {
  transform: scale(1.1);
}

.label {
  font-size: 12px;
  font-weight: 700;
  color: #999;
}

.nav-item.active .label {
  color: #4cb7b7;
}

</style>
