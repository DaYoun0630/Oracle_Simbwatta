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
  --shell-max-width: 520px;
  --shell-nav-width: 520px;
  --shell-gutter: clamp(14px, 4vw, 20px);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f4f7f8;
  position: relative;
}


.content {
  flex: 1;
  padding: 8px var(--shell-gutter);
  padding-bottom: calc(88px + env(safe-area-inset-bottom, 0px));
  width: min(100%, var(--shell-max-width));
  margin: 0 auto;
  box-sizing: border-box;
  overflow-x: visible;
}

.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: min(100%, var(--shell-nav-width));
  height: 70px;
  background: rgba(244, 247, 248, 0.98);
  border-top-left-radius: 22px;
  border-top-right-radius: 22px;
  border-top: 1px solid rgba(46, 46, 46, 0.05);
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 8px var(--shell-gutter) calc(12px + env(safe-area-inset-bottom, 0px));
  box-shadow: 0 -2px 8px rgba(46, 46, 46, 0.08);
  z-index: 90;
  box-sizing: border-box;
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
  box-shadow: 0 2px 6px rgba(46, 46, 46, 0.08);
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

@media (min-width: 900px) {
  .caregiver-shell {
    --shell-max-width: 860px;
    --shell-nav-width: 620px;
    --shell-gutter: 24px;
  }
}

</style>
