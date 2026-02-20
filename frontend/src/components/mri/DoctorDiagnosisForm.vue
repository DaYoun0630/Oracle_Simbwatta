<script setup lang="ts">
import { ref, computed } from 'vue';

interface DiagnosisOption {
  id: string;
  label: string;
  value: string;
}

interface DiagnosisSubmitData {
  patientId: string;
  diagnoses: string[];
  additionalNotes: string;
  timestamp: string;
  doctorId: string;
}

const props = defineProps<{
  patientId: string;
  doctorId?: string;
}>();

const API_BASE_RAW = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
const API_BASE = /\/api$/i.test(API_BASE_RAW) ? API_BASE_RAW : `${API_BASE_RAW}/api`;

const emit = defineEmits<{
  (e: 'submit', data: DiagnosisSubmitData): void;
}>();

// 진단 옵션 목록
const diagnosisOptions: DiagnosisOption[] = [
  { id: 'hippocampus', label: '해마 위축', value: 'hippocampus_atrophy' },
  { id: 'temporal', label: '측두엽 위축', value: 'temporal_lobe_atrophy' },
  { id: 'brain_volume', label: '전체 뇌 부피 감소', value: 'total_brain_volume_loss' },
  { id: 'white_matter', label: '백질 병변', value: 'white_matter_lesion' },
  { id: 'frontal', label: '전두엽 위축', value: 'frontal_lobe_atrophy' },
  { id: 'parietal', label: '두정엽 위축', value: 'parietal_lobe_atrophy' }
];

// 상태 관리
const selectedDiagnoses = ref<string[]>([]);
const additionalNotes = ref('');
const isSubmitting = ref(false);

// 유효성 검사
const isValid = computed(() => selectedDiagnoses.value.length > 0);

// 체크박스 토글
const handleCheckboxChange = (value: string) => {
  const index = selectedDiagnoses.value.indexOf(value);
  if (index === -1) {
    selectedDiagnoses.value.push(value);
  } else {
    selectedDiagnoses.value.splice(index, 1);
  }
};

// 체크 여부 확인
const isChecked = (value: string) => selectedDiagnoses.value.includes(value);

// 폼 초기화
const handleReset = () => {
  selectedDiagnoses.value = [];
  additionalNotes.value = '';
};

// 폼 제출
const handleSubmit = async (e: Event) => {
  e.preventDefault();

  if (!isValid.value) {
    alert('최소 하나 이상의 진단을 선택해주세요.');
    return;
  }

  isSubmitting.value = true;

  try {
    const submitData: DiagnosisSubmitData = {
      patientId: props.patientId,
      diagnoses: [...selectedDiagnoses.value],
      additionalNotes: additionalNotes.value.trim(),
      timestamp: new Date().toISOString(),
      doctorId: props.doctorId || 'doctor_001'
    };

    const response = await fetch(
      `${API_BASE}/doctor/patients/${encodeURIComponent(String(props.patientId).trim())}/mri/doctor-diagnosis`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(submitData)
      }
    );

    if (!response.ok) {
      let detail = '진단 저장 중 오류가 발생했습니다.';
      try {
        const body = await response.json();
        if (typeof body?.detail === 'string' && body.detail.trim()) {
          detail = body.detail;
        }
      } catch {
        // ignore parse errors
      }
      throw new Error(`${detail} (HTTP ${response.status})`);
    }

    // 부모 컴포넌트에 이벤트 전달
    emit('submit', submitData);

    alert('진단이 성공적으로 저장되었습니다.');

    // 폼 초기화
    handleReset();
  } catch (error) {
    console.error('진단 저장 실패:', error);
    alert(error instanceof Error ? error.message : '진단 저장 중 오류가 발생했습니다.');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div class="diagnosis-form-container">
    <div class="form-header">
      <h4>의사 진단 확정</h4>
      <p class="form-description">
        AI 분석 결과를 참고하여 확정 진단을 선택해주세요. (복수 선택 가능)
      </p>
    </div>

    <form @submit="handleSubmit">
      <!-- 체크박스 목록 -->
      <div class="checkbox-list">
        <label
          v-for="option in diagnosisOptions"
          :key="option.id"
          class="checkbox-item"
          :class="{ checked: isChecked(option.value) }"
        >
          <input
            type="checkbox"
            :value="option.value"
            :checked="isChecked(option.value)"
            @change="handleCheckboxChange(option.value)"
          />
          <span class="checkbox-custom">
            <svg v-if="isChecked(option.value)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </span>
          <span class="checkbox-label">{{ option.label }}</span>
        </label>
      </div>

      <!-- 추가 소견 -->
      <div class="textarea-group">
        <label class="textarea-label">추가 소견 (선택사항)</label>
        <textarea
          v-model="additionalNotes"
          placeholder="진단에 대한 추가 소견이나 특이사항을 입력해주세요..."
          rows="4"
        ></textarea>
      </div>

      <!-- 버튼 영역 -->
      <div class="button-group">
        <button
          type="button"
          class="btn-reset"
          @click="handleReset"
          :disabled="isSubmitting"
        >
          초기화
        </button>
        <button
          type="submit"
          class="btn-submit"
          :disabled="!isValid || isSubmitting"
        >
          <span v-if="isSubmitting">
            <span class="btn-spinner"></span>
            저장 중...
          </span>
          <span v-else>진단 확정</span>
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.diagnosis-form-container {
  background: #f5f6f7;
  border-radius: 26px;
  padding: 24px;
  box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-header h4 {
  font-size: 20px;
  font-weight: 800;
  color: #2e2e2e;
  margin: 0 0 8px;
}

.form-description {
  font-size: 15px;
  font-weight: 600;
  color: #777;
  margin: 0;
  line-height: 1.5;
}

/* 체크박스 목록 */
.checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background: #ffffff;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.5), inset -4px -4px 8px #ffffff;
}

.checkbox-item:hover {
  background: #fafbfc;
}

.checkbox-item.checked {
  background: rgba(76, 183, 183, 0.06);
  box-shadow: inset 4px 4px 8px rgba(76, 183, 183, 0.1), inset -4px -4px 8px #ffffff;
}

.checkbox-item input[type="checkbox"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-custom {
  width: 24px;
  height: 24px;
  border: 2px solid #d1d5db;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s ease;
  background: #ffffff;
}

.checkbox-item.checked .checkbox-custom {
  background: #4cb7b7;
  border-color: #4cb7b7;
}

.checkbox-custom svg {
  width: 14px;
  height: 14px;
  color: #ffffff;
}

.checkbox-label {
  font-size: 16px;
  font-weight: 700;
  color: #2e2e2e;
}

/* 텍스트 영역 */
.textarea-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.textarea-label {
  font-size: 16px;
  font-weight: 800;
  color: #555;
}

.textarea-group textarea {
  width: 100%;
  padding: 16px;
  border: none;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.6), inset -4px -4px 8px #ffffff;
  font-size: 16px;
  font-weight: 600;
  color: #2e2e2e;
  font-family: inherit;
  resize: vertical;
  min-height: 100px;
  transition: box-shadow 0.2s ease;
}

.textarea-group textarea::placeholder {
  color: #999;
}

.textarea-group textarea:focus {
  outline: none;
  box-shadow: inset 4px 4px 8px rgba(76, 183, 183, 0.15), inset -4px -4px 8px #ffffff, 0 0 0 3px rgba(76, 183, 183, 0.2);
}

/* 버튼 그룹 */
.button-group {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.btn-reset,
.btn-submit {
  padding: 14px 28px;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-reset {
  background: #ffffff;
  border: 2px solid #d1d5db;
  color: #555;
  box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
}

.btn-reset:hover:not(:disabled) {
  background: #f5f6f7;
  border-color: #b0b5bc;
}

.btn-reset:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-submit {
  background: #4cb7b7;
  border: none;
  color: #ffffff;
  box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
}

.btn-submit:hover:not(:disabled) {
  background: #3da5a5;
}

.btn-submit:disabled {
  background: #b0b5bc;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 반응형 */
@media (max-width: 520px) {
  .button-group {
    flex-direction: column;
  }

  .btn-reset,
  .btn-submit {
    width: 100%;
  }
}
</style>
