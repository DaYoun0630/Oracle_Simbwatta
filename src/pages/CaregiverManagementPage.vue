<script setup>
import { ref, computed } from 'vue';
import { useAuthStore } from '@/stores/auth';
import CaregiverShell from '@/components/shells/CaregiverShell.vue';

const authStore = useAuthStore();

// 현재 계정에 연결된 피보호자 목록 데이터
const connectedSubjects = ref([
  {
    id: 1,
    name: '김어르신',
    relation: '부모님',
    status: 'active',
    lastActive: '오늘 14:30'
  }
]);

// 대기 중인 초대 목록 (확장성 고려)
const pendingInvites = ref([]);

// 연결 해제 로직: 전달받은 ID를 제외한 목록으로 재할당
const removeConnection = (subjectId) => {
  connectedSubjects.value = connectedSubjects.value.filter(s => s.id !== subjectId);
};

// 신규 연결 요청 전송: API 연동 필요 구간
const sendInvite = () => {
  // 초대 기능 (추후 구현)
};
</script>

<template>
  <CaregiverShell title="보호자 연결 관리">
    <div class="caregiver-management">
      
      <section class="section">
        <h2 class="section-title">연결된 대상자</h2>

        <div v-if="connectedSubjects.length === 0" class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#aaa" stroke-width="2">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="8.5" cy="7" r="4"/>
            <line x1="20" y1="8" x2="20" y2="14"/>
            <line x1="23" y1="11" x2="17" y2="11"/>
          </svg>
          <p>연결된 대상자가 없습니다</p>
        </div>

        <div v-else class="subject-list">
          <div
            v-for="subject in connectedSubjects"
            :key="subject.id"
            class="subject-card"
          >
            <div class="subject-avatar">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4cb7b7" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="subject-info">
              <h3>{{ subject.name }}</h3>
              <p>{{ subject.relation }}</p>
              <span class="last-active">최근 활동: {{ subject.lastActive }}</span>
            </div>
            <div class="subject-status" :class="subject.status">
              {{ subject.status === 'active' ? '활성' : '비활성' }}
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <h2 class="section-title">새 대상자 연결</h2>
        <p class="section-desc">대상자 기기에서 생성된 연결 코드를 입력하여 연결할 수 있습니다.</p>

        <div class="invite-form">
          <input
            type="text"
            placeholder="연결 코드 입력"
            class="invite-input"
          />
          <button class="invite-button" @click="sendInvite">
            연결하기
          </button>
        </div>
      </section>

      <section class="section help-section">
        <h2 class="section-title">도움말</h2>
        <div class="help-card">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4cb7b7" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <div>
            <h4>연결 코드는 어디서 확인하나요?</h4>
            <p>대상자 기기의 설정 → 보호자 연결에서 연결 코드를 생성할 수 있습니다.</p>
          </div>
        </div>
      </section>
    </div>
  </CaregiverShell>
</template>

<style scoped>
/* 메인 컨테이너 레이아웃 */
.caregiver-management {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* 섹션 공통 간격 제어 */
.section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 타이포그래피: 섹션 제목 */
.section-title {
  font-size: 20px;
  font-weight: 800;
  color: #2e2e2e;
  margin: 0;
}

/* 설명 문구 스타일 */
.section-desc {
  font-size: 15px;
  font-weight: 600;
  color: #777;
  margin: 0;
  line-height: 1.5;
}

/* 빈 목록 상태의 뉴모피즘 스타일 적용 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 20px;
  background: #f5f6f7;
  border-radius: 24px;
  box-shadow: inset 4px 4px 10px #d1d9e6, inset -4px -4px 10px #ffffff;
}

.empty-state p {
  font-size: 16px;
  font-weight: 600;
  color: #888;
  margin: 0;
}

/* 대상자 카드 리스트 간격 */
.subject-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 카드 아이템의 입체감 효과(Drop Shadow) */
.subject-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f5f6f7;
  border-radius: 24px;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
}

/* 아바타 배경의 내측 그림자 효과 */
.subject-avatar {
  width: 52px;
  height: 52px;
  min-width: 52px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6),
              inset -4px -4px 10px #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.subject-info {
  flex: 1;
}

.subject-info h3 {
  font-size: 18px;
  font-weight: 800;
  color: #2e2e2e;
  margin: 0 0 4px;
}

.subject-info p {
  font-size: 14px;
  font-weight: 600;
  color: #4cb7b7;
  margin: 0 0 4px;
}

.last-active {
  font-size: 13px;
  font-weight: 600;
  color: #999;
}

/* 상태 뱃지 공통 스타일 */
.subject-status {
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
}

/* 활성 상태 컬러 스킴 */
.subject-status.active {
  background: rgba(76, 183, 183, 0.15);
  color: #4cb7b7;
}

/* 비활성 상태 컬러 스킴 */
.subject-status.inactive {
  background: rgba(153, 153, 153, 0.15);
  color: #999;
}

/* 입력 폼 가로 배치 */
.invite-form {
  display: flex;
  gap: 12px;
}

/* 인풋 필드 내측 그림자 및 포커스 스타일 */
.invite-input {
  flex: 1;
  padding: 16px 20px;
  border: none;
  border-radius: 20px;
  background: #f5f6f7;
  box-shadow: inset 4px 4px 10px #d1d9e6, inset -4px -4px 10px #ffffff;
  font-size: 18px;
  font-weight: 700;
  color: #2e2e2e;
  outline: none;
}

.invite-input::placeholder {
  color: #aaa;
  font-weight: 600;
}

.invite-input:focus {
  box-shadow: inset 4px 4px 10px #d1d9e6,
              inset -4px -4px 10px #ffffff,
              0 0 0 3px rgba(76, 183, 183, 0.3);
}

/* 강조 버튼 스타일 및 클릭 피드백(Scale) */
.invite-button {
  padding: 16px 24px;
  border: none;
  border-radius: 20px;
  background: #4cb7b7;
  box-shadow: 0 8px 16px rgba(76, 183, 183, 0.3);
  font-size: 16px;
  font-weight: 800;
  color: #ffffff;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.invite-button:active {
  transform: scale(0.98);
  box-shadow: 0 4px 8px rgba(76, 183, 183, 0.2);
}

.help-section {
  margin-top: 8px;
}

/* 도움말 카드 내측 그림자 디자인 */
.help-card {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: #f5f6f7;
  border-radius: 20px;
  box-shadow: inset 4px 4px 10px #d1d9e6, inset -4px -4px 10px #ffffff;
}

.help-card h4 {
  font-size: 16px;
  font-weight: 700;
  color: #2e2e2e;
  margin: 0 0 6px;
}

.help-card p {
  font-size: 14px;
  font-weight: 600;
  color: #777;
  margin: 0;
  line-height: 1.5;
}
</style>