<script setup>
// Vue의 반응형 상태와 감시 기능 import
import { onMounted, ref, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { fetchUserSettings, updateUserSettings } from '@/api/settings';

// 공통 레이아웃 컴포넌트 import
import AppShell from '@/components/AppShell.vue';
const authStore = useAuthStore();

// 위험 환자 실시간 알림 상태
// localStorage 값이 'off'가 아니면 기본 활성화
const riskAlert = ref(localStorage.getItem('doctor-notify-risk') !== 'off');

// 주간 환자군 요약 리포트 알림 상태
const weeklyReport = ref(localStorage.getItem('doctor-notify-weekly') !== 'off');

// MRI 분석 완료 알림 상태
const mriReport = ref(localStorage.getItem('doctor-notify-mri') !== 'off');
const isHydrating = ref(false);
const syncMessage = ref('');
let syncMessageTimer = null;

const setSyncMessage = (message) => {
  syncMessage.value = message;
  if (syncMessageTimer) {
    clearTimeout(syncMessageTimer);
    syncMessageTimer = null;
  }
  if (message) {
    syncMessageTimer = setTimeout(() => {
      syncMessage.value = '';
      syncMessageTimer = null;
    }, 2400);
  }
};

const persistSettings = async () => {
  if (isHydrating.value || !authStore.token) return;

  try {
    await updateUserSettings(authStore.token, {
      doctor_notify_risk: riskAlert.value,
      doctor_notify_weekly: weeklyReport.value,
      doctor_notify_mri: mriReport.value,
    });
    setSyncMessage('');
  } catch (error) {
    console.error('Failed to sync doctor notification settings:', error);
    setSyncMessage(error instanceof Error ? `DB 동기화 실패: ${error.message}` : 'DB 동기화에 실패했습니다.');
  }
};

// 위험 환자 알림 상태 변경 시 localStorage에 즉시 반영
watch(riskAlert, (value) => {
  localStorage.setItem('doctor-notify-risk', value ? 'on' : 'off');
  void persistSettings();
});

// 주간 리포트 알림 상태 변경 시 localStorage에 즉시 반영
watch(weeklyReport, (value) => {
  localStorage.setItem('doctor-notify-weekly', value ? 'on' : 'off');
  void persistSettings();
});

// MRI 알림 상태 변경 시 localStorage에 즉시 반영
watch(mriReport, (value) => {
  localStorage.setItem('doctor-notify-mri', value ? 'on' : 'off');
  void persistSettings();
});

// 알림 설정 화면에 표시할 카테고리 정의
// model에는 ref 자체를 전달하여 상태 동기화
const notificationCategories = [
  {
    id: 'risk',
    title: '위험 환자 실시간 알림',
    description: 'CDR-SB 급상승 및 참여율 급감 시 즉시 알림',
    model: riskAlert
  },
  {
    id: 'weekly',
    title: '주간 환자군 요약 리포트',
    description: '환자군 평균 변화 및 주요 인사이트 정리',
    model: weeklyReport
  },
  {
    id: 'mri',
    title: 'MRI 분석 완료 알림',
    description: '서버 분석 완료 시 요약 리포트 전달',
    model: mriReport
  }
];

// 토글 버튼 클릭 시 해당 알림 상태 반전
// ref 값을 직접 변경하므로 watch가 자동 실행
const toggleNotification = (category) => {
  category.model.value = !category.model.value;
};

onMounted(async () => {
  if (!authStore.token) return;

  isHydrating.value = true;
  try {
    const settings = await fetchUserSettings(authStore.token);
    riskAlert.value = settings.doctor_notify_risk;
    weeklyReport.value = settings.doctor_notify_weekly;
    mriReport.value = settings.doctor_notify_mri;
  } catch (error) {
    console.error('Failed to load doctor notification settings:', error);
    setSyncMessage(error instanceof Error ? `설정 불러오기 실패: ${error.message}` : '설정 불러오기에 실패했습니다.');
  } finally {
    isHydrating.value = false;
  }
});
</script>

<template>
  <!-- 의료진 알림 설정 화면 레이아웃 -->
  <AppShell title="의료진 알림 설정" :showBack="true" :showMenu="false">

    <!-- 알림 설정 전체 컨테이너 -->
    <div class="notification-settings">

      <!-- 알림 카테고리 카드 반복 렌더링 -->
      <section
        v-for="category in notificationCategories"
        :key="category.id"
        class="notification-card"
      >
        <!-- 알림 제목 및 설명 영역 -->
        <div class="card-content">
          <h3>{{ category.title }}</h3>
          <p>{{ category.description }}</p>
        </div>

        <!-- 토글 버튼 및 상태 표시 영역 -->
        <div class="toggle-wrapper">
          <!-- 알림 on/off 토글 버튼 -->
          <button
            class="toggle"
            :class="{ on: category.model.value }"
            @click="toggleNotification(category)"
          >
            <span class="knob"></span>
          </button>

          <!-- 현재 토글 상태 텍스트 표시 -->
          <span class="toggle-label">
            {{ category.model.value ? '켬' : '끔' }}
          </span>
        </div>
      </section>

      <p v-if="syncMessage" class="sync-message">{{ syncMessage }}</p>

    </div>
  </AppShell>
</template>

<style scoped>
/* 알림 설정 페이지 전체 레이아웃 */
.notification-settings {
  display: flex;
  flex-direction: column;
  gap: 20px;
  font-size: 16px;
  padding-bottom: 24px;
}

/* 개별 알림 카드 스타일 */
.notification-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  border-radius: 24px;
  background: #f5f6f7;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
}

/* 카드 텍스트 영역 */
.card-content {
  flex: 1;
}

/* 알림 제목 스타일 */
.card-content h3 {
  font-size: 18px;
  font-weight: 800;
  color: #2e2e2e;
  margin: 0 0 6px;
}

/* 알림 설명 텍스트 스타일 */
.card-content p {
  font-size: 16px;
  font-weight: 600;
  color: #777;
  margin: 0;
  line-height: 1.4;
}

/* 토글 버튼과 상태 텍스트 컨테이너 */
.toggle-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

/* 토글 버튼 기본 상태 */
.toggle {
  width: 64px;
  height: 36px;
  border-radius: 999px;
  border: none;
  background: #dfe6ec;
  position: relative;
  cursor: pointer;
  transition: background 0.2s ease;
}

/* 토글 내부 이동 노브 */
.toggle .knob {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s ease;
}

/* 토글 활성화 상태 배경 */
.toggle.on {
  background: #4cb7b7;
}

/* 활성화 시 노브 위치 이동 */
.toggle.on .knob {
  transform: translateX(28px);
}

/* 토글 상태 텍스트 */
.toggle-label {
  font-size: 16px;
  font-weight: 700;
  color: #777;
}

/* 토글이 켜진 상태에서 텍스트 강조 */
.toggle.on + .toggle-label {
  color: #4cb7b7;
}

.sync-message {
  margin: 4px 2px 0;
  font-size: 13px;
  color: #ff8a80;
  font-weight: 700;
}
</style>
