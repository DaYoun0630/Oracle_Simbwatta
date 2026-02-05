<script setup>
import { ref, watch, computed } from 'vue';
import { useAuthStore } from '@/stores/auth';
import CaregiverShell from '@/components/shells/CaregiverShell.vue';
import DoctorShell from '@/components/shells/DoctorShell.vue';

const authStore = useAuthStore();
const role = computed(() => authStore.role);

const emergencyAlerts = ref(localStorage.getItem('notify-emergency') !== 'off');
const weeklyReport = ref(localStorage.getItem('notify-weekly') !== 'off');
const serviceInfo = ref(localStorage.getItem('notify-service') !== 'off');

watch(emergencyAlerts, (v) => localStorage.setItem('notify-emergency', v ? 'on' : 'off'));
watch(weeklyReport, (v) => localStorage.setItem('notify-weekly', v ? 'on' : 'off'));
watch(serviceInfo, (v) => localStorage.setItem('notify-service', v ? 'on' : 'off'));

const notificationCategories = [
  {
    id: 'emergency',
    title: '변화 알림',
    description: '대상자의 상태 변화 추이를 요약 알림',
    model: emergencyAlerts,
    icon: 'alert'
  },
  {
    id: 'weekly',
    title: '주간 요약 리포트',
    description: '매주 월요일 지난 주 대화 흐름 요약',
    model: weeklyReport,
    icon: 'calendar'
  },
  {
    id: 'service',
    title: '서비스 안내',
    description: '새 기능 및 업데이트 소식',
    model: serviceInfo,
    icon: 'info'
  }
];

const toggleNotification = (category) => {
  category.model.value = !category.model.value;
};
</script>

<template>
  <component
    :is="role === 'caregiver' ? CaregiverShell : DoctorShell"
    title="알림 설정"
  >
    <div class="notification-settings">
      <section
        v-for="category in notificationCategories"
        :key="category.id"
        class="notification-card"
      >
        <div class="card-icon" :class="category.icon">
          <svg v-if="category.icon === 'alert'" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4cb7b7" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <svg v-else-if="category.icon === 'calendar'" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4cb7b7" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4cb7b7" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </div>
        <div class="card-content">
          <h3>{{ category.title }}</h3>
          <p>{{ category.description }}</p>
        </div>
        <div class="toggle-wrapper">
          <button
            class="toggle"
            :class="{ on: category.model.value }"
            @click="toggleNotification(category)"
          >
            <span class="knob"></span>
          </button>
          <span class="toggle-label">{{ category.model.value ? '켬' : '끔' }}</span>
        </div>
      </section>
    </div>
  </component>
</template>

<style scoped>
.notification-settings {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.notification-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  border-radius: 24px;
  background: #f5f6f7;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
}

.card-icon {
  width: 56px;
  height: 56px;
  min-width: 56px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6),
              inset -4px -4px 10px #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-content {
  flex: 1;
}

.card-content h3 {
  font-size: 18px;
  font-weight: 800;
  color: #2e2e2e;
  margin: 0 0 6px;
}

.card-content p {
  font-size: 14px;
  font-weight: 600;
  color: #777;
  margin: 0;
  line-height: 1.4;
}

.toggle-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.toggle {
  width: 60px;
  height: 34px;
  border-radius: 999px;
  border: none;
  background: #dfe6ec;
  position: relative;
  cursor: pointer;
  transition: background 0.2s ease;
}

.toggle .knob {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s ease;
}

.toggle.on {
  background: #4cb7b7;
}

.toggle.on .knob {
  transform: translateX(26px);
}

.toggle-label {
  font-size: 14px;
  font-weight: 700;
  color: #777;
}

.toggle.on + .toggle-label {
  color: #4cb7b7;
}
</style>
