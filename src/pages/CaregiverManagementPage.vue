<script setup>
import { ref } from 'vue';
import CaregiverShell from '@/components/shells/CaregiverShell.vue';
import { verifySubjectLinkCode } from '@/api/signup';

const connectedSubjects = ref([
  {
    id: 1,
    name: '김어르신',
    relation: '부모님',
    status: 'active',
    lastActive: '오늘 14:30'
  }
]);

const memberNumberInput = ref('');
const inviteMessage = ref('');
const inviteError = ref(false);
const isSubmitting = ref(false);

const removeConnection = (subjectId) => {
  connectedSubjects.value = connectedSubjects.value.filter((subject) => subject.id !== subjectId);
};

const sendInvite = async () => {
  const code = memberNumberInput.value.trim().toUpperCase();

  if (!code) {
    inviteMessage.value = '대상자 회원번호를 입력해 주세요.';
    inviteError.value = true;
    return;
  }

  isSubmitting.value = true;
  inviteMessage.value = '';

  try {
    const result = await verifySubjectLinkCode(code);

    if (!result.valid) {
      inviteMessage.value = result.message;
      inviteError.value = true;
      return;
    }

    const alreadyConnected = connectedSubjects.value.some((subject) => subject.memberNumber === code);
    if (!alreadyConnected) {
      connectedSubjects.value.unshift({
        id: Date.now(),
        name: result.linked_subject_name || '대상자',
        relation: '연결됨',
        status: 'active',
        lastActive: '방금 전',
        memberNumber: code
      });
    }

    inviteMessage.value = '대상자 회원번호 확인이 완료되어 연결 요청을 보냈습니다.';
    inviteError.value = false;
    memberNumberInput.value = '';
  } catch (error) {
    console.error('Failed to validate member number:', error);
    inviteMessage.value = '회원번호 확인 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
    inviteError.value = true;
  } finally {
    isSubmitting.value = false;
  }
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
            <div class="subject-actions">
              <div class="subject-status" :class="subject.status">
                {{ subject.status === 'active' ? '활성' : '비활성' }}
              </div>
              <button type="button" class="remove-button" @click="removeConnection(subject.id)">연결 해제</button>
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <h2 class="section-title">새 대상자 연결</h2>
        <p class="section-desc">대상자에게 공유받은 회원번호를 입력해 연결할 수 있습니다.</p>

        <div class="invite-form">
          <input
            v-model="memberNumberInput"
            type="text"
            placeholder="대상자 회원번호 입력 (예: SM-123456)"
            class="invite-input"
          />
          <button class="invite-button" :disabled="isSubmitting" @click="sendInvite">
            {{ isSubmitting ? '확인 중...' : '연결하기' }}
          </button>
        </div>
        <p v-if="inviteMessage" :class="['invite-message', inviteError ? 'error' : 'success']">{{ inviteMessage }}</p>
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
            <h4>대상자 회원번호는 어디서 확인하나요?</h4>
            <p>대상자의 기기의 설정 -> 프로필에서 대상자의 회원번호를 확인할 수 있습니다.</p>
          </div>
        </div>
      </section>
    </div>
  </CaregiverShell>
</template>

<style scoped>
.caregiver-management {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-title {
  font-size: 20px;
  font-weight: 800;
  color: #2e2e2e;
  margin: 0;
}

.section-desc {
  font-size: 15px;
  font-weight: 600;
  color: #777;
  margin: 0;
  line-height: 1.5;
}

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

.subject-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.subject-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f5f6f7;
  border-radius: 24px;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
}

.subject-avatar {
  width: 52px;
  height: 52px;
  min-width: 52px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
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

.subject-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.subject-status {
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
}

.subject-status.active {
  background: rgba(76, 183, 183, 0.15);
  color: #4cb7b7;
}

.subject-status.inactive {
  background: rgba(153, 153, 153, 0.15);
  color: #999;
}

.remove-button {
  border: none;
  background: transparent;
  color: #ef4444;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.invite-form {
  display: flex;
  gap: 12px;
}

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

.invite-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.invite-button:active {
  transform: scale(0.98);
  box-shadow: 0 4px 8px rgba(76, 183, 183, 0.2);
}

.invite-message {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}

.invite-message.success {
  color: #176a3a;
}

.invite-message.error {
  color: #b91c1c;
}

.help-section {
  margin-top: 8px;
}

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

@media (max-width: 680px) {
  .invite-form {
    flex-direction: column;
  }

  .subject-card {
    align-items: flex-start;
  }

  .subject-actions {
    align-items: flex-start;
  }
}
</style>
