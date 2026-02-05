<script setup lang="ts">
import { computed, ref, watch } from 'vue';

// 전달받는 데이터 정의: 탭 상태/데이터/로딩 플래그
const props = defineProps({
  currentTab: {
    type: String,
    default: 'clinical'
  },
  data: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
});


// 데이터 준비 여부 판단(로딩 중이거나 데이터가 없으면 true)
const isLoading = computed(() => props.loading || !props.data);
// 현재 선택된 환자 정보
const currentPatient = computed(() => props.data?.currentPatient || null);
// 전체 검사 방문 기록
const visits = computed(() => props.data?.visits || []);
// 임상 지표 추세 데이터
const clinicalTrends = computed<ClinicalTrends | null>(() =>
  props.data?.clinicalTrends ?? null
);
// 일상 대화 참여 데이터
const dailyParticipation = computed(() => props.data?.dailyParticipation || null);
// 음성 특징(Feature) 목록
const acousticFeatures = computed(() => props.data?.acousticFeatures || []);
// MRI 분석 결과
const mriAnalysis = computed(() => props.data?.mriAnalysis || null);

// 분석 기록 페이지의 시각화 섹션 구조를 정의한다
const recordPlaceholders = [
  {
    id: 'voice-frequency',
    title: '음성 대화 참여 빈도 추세',
    description: '주간/월간 참여 빈도 변화 그래프 영역'
  },
  {
    id: 'utterance-length',
    title: '발화 길이 변화',
    description: '평균 발화 길이 추세 그래프 영역'
  },
  {
    id: 'pause-frequency',
    title: 'Pause 빈도 변화',
    description: '침묵 구간 빈도 추세 그래프 영역'
  },
  {
    id: 'cognitive-scores',
    title: '인지 검사 점수 변화 (MMSE · MoCA)',
    description: '인지 검사 점수 변화 추세 그래프 영역'
  },
  {
    id: 'mci-subtype',
    title: 'MCI Subtype 변화',
    description: 'Subtype 변동 기록 시각화 영역'
  },
  {
    id: 'biomarker',
    title: '바이오마커 변화 추세',
    description: '선택 제공 지표 시각화 영역'
  }
];

// 방문 기록을 날짜 기준으로 정렬
const sortedVisits = computed(() => {
  if (!visits.value.length) return [];
  return [...visits.value].sort((a, b) => new Date(a.examDate).getTime() - new Date(b.examDate).getTime());
});

// 차트 라벨: 제공된 labels가 있으면 사용, 없으면 방문 코드 사용
const trendLabels = computed(() => {
  if (clinicalTrends.value?.labels?.length) {
    return clinicalTrends.value.labels.map((label) => String(label).toUpperCase());
  }
  return sortedVisits.value.map((visit) => String(visit.viscode2 || '').toUpperCase());
});

// 임상 추세 시리즈
const adasSeries = computed(() => clinicalTrends.value?.adasCog13 || []);
const faqSeries = computed(() => clinicalTrends.value?.faq || []);

// 최신 측정값(요약 카드에 표시)
const latestAdas = computed(() => adasSeries.value.at(-1));
const latestFaq = computed(() => faqSeries.value.at(-1));

// 참여도 라벨/시리즈 및 최신값
const participationLabels = computed(() => dailyParticipation.value?.labels || []);
const participationSeries = computed(() => dailyParticipation.value?.counts || []);
const latestParticipation = computed(() => participationSeries.value.at(-1));

// MRI 이미지가 존재하는 방문만 선택 옵션으로 구성
const visitOptions = computed(() => sortedVisits.value.filter((visit) => visit.imageId));
// 현재 선택된 이미지 ID
const selectedVisitImageId = ref('');

// 선택된 방문(없으면 최신 방문으로 대체)
const activeVisit = computed(() => {
  if (!visitOptions.value.length) return null;
  return visitOptions.value.find((visit) => visit.imageId === selectedVisitImageId.value) || visitOptions.value.at(-1);
});

// 선택된 방문의 이미지 묶음(없으면 기본 이미지)
const activeImages = computed(() => {
  const reports = mriAnalysis.value?.reports || {};
  if (activeVisit.value?.imageId && reports[activeVisit.value.imageId]?.imagePaths) {
    return reports[activeVisit.value.imageId].imagePaths;
  }
  return mriAnalysis.value?.imagePaths || {};
});

// 실제로 표시할 이미지(축/시상/관상 순으로 우선순위)
const activeImage = computed(() =>
  activeImages.value?.axial || activeImages.value?.sagittal || activeImages.value?.coronal || ''
);

// 스파크라인(SVG) 경로 생성
const getSparklinePath = (scores: number[], width = 120, height = 40) => {
  if (!scores || scores.length < 2) return '';
  const padding = 4;
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const range = max - min || 1;
  const points = scores.map((score, i) => {
    const x = padding + (i / (scores.length - 1)) * (width - padding * 2);
    const y = height - padding - ((score - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });
  return `M ${points.join(' L ')}`;
};

// 라인 차트(SVG) 경로 생성
const getLinePath = (values: number[], maxScore: number, width = 240, height = 120) => {
  if (!values || values.length < 2) return '';
  const padding = 12;
  const points = values.map((value, i) => {
    const x = padding + (i / (values.length - 1)) * (width - padding * 2);
    const clamped = Math.min(maxScore, Math.max(0, value));
    const y = height - padding - (clamped / maxScore) * (height - padding * 2);
    return `${x},${y}`;
  });
  return `M ${points.join(' L ')}`;
};

watch(
  () => visitOptions.value,
  (value) => {
    // 선택 가능한 방문이 생기면 가장 최신 이미지로 기본 선택
    if (!value?.length) return;
    selectedVisitImageId.value = value.at(-1)?.imageId || '';
  },
  { immediate: true }
);
</script>

<template>
  <!-- 히스토리 페이지 전체 래퍼 -->
  <div class="doctor-history">
    <!-- 로딩 상태일 때 스켈레톤 표시 -->
    <div v-if="isLoading" class="loading">
      <div class="skeleton-line"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
    </div>

    <!-- 데이터 준비 후 탭 전환 애니메이션 -->
    <transition v-else name="fade" mode="out-in">
      <!-- 탭 변경 시 재렌더링을 위해 key에 currentTab 사용 -->
      <div :key="currentTab" class="tab-panel">
        <!-- 환자 기본 정보 배너 -->
        <section class="patient-banner">
          <div>
            <h3>{{ currentPatient?.name }}</h3>
            <p>{{ currentPatient?.id }} · {{ currentPatient?.rid || '-' }}</p>
          </div>
          <span class="patient-meta">{{ currentPatient?.age }}세 · {{ currentPatient?.gender === 'F' ? '여' : '남' }}</span>
        </section>

        <section class="record-outline">
          <div class="record-outline-header">
            <h4>장기 모니터링 핵심 지표</h4>
            <p>그래프가 들어갈 영역만 미리 구성했습니다.</p>
          </div>
          <div class="record-grid">
            <div v-for="item in recordPlaceholders" :key="item.id" class="record-card">
              <div class="record-card-header">
                <span class="record-title">{{ item.title }}</span>
                <span class="record-tag">Placeholder</span>
              </div>
              <div class="record-placeholder"></div>
              <p class="record-desc">{{ item.description }}</p>
            </div>
          </div>
        </section>

        <!-- 임상 데이터 탭 -->
        <section v-if="currentTab === 'clinical'" class="panel">
          <!-- ADAS/FAQ 요약 카드 -->
          <div class="summary-grid">
            <div class="summary-card">
              <span>ADAS-cog13</span>
              <strong>{{ latestAdas ?? '-' }}</strong>
              <p>최근 측정</p>
            </div>
            <div class="summary-card">
              <span>FAQ</span>
              <strong>{{ latestFaq ?? '-' }}</strong>
              <p>최근 측정</p>
            </div>
          </div>

          <!-- 추세 라인 차트 -->
          <div class="card">
            <h4>ADAS-cog13 · FAQ 변화</h4>
            <div class="line-chart">
              <svg viewBox="0 0 240 120">
                <path :d="getLinePath(adasSeries, 85)" stroke="#4cb7b7" stroke-width="3" fill="none" />
                <path :d="getLinePath(faqSeries, 30)" stroke="#ffb74d" stroke-width="3" fill="none" />
              </svg>
              <div class="chart-legend">
                <span><i class="legend-dot adas"></i>ADAS-cog13</span>
                <span><i class="legend-dot faq"></i>FAQ</span>
              </div>
              <div class="chart-labels">
                <span v-for="label in trendLabels" :key="label">{{ label }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 음성 분석 탭 -->
        <section v-else-if="currentTab === 'voice'" class="panel">
          <!-- 음성 특징 카드 목록 -->
          <div class="card">
            <h4>음성 지표 트렌드</h4>
            <div class="trend-grid">
              <div v-for="feature in acousticFeatures" :key="feature.label" class="trend-card">
                <div class="trend-header">
                  <span>{{ feature.label }}</span>
                  <strong>{{ feature.current }}</strong>
                </div>
                <span class="trend-sub">기준 {{ feature.baseline }}</span>
                <svg class="sparkline" viewBox="0 0 120 40">
                  <path :d="getSparklinePath(feature.trend)" stroke="#4cb7b7" fill="none" stroke-width="2" stroke-linecap="round" />
                </svg>
              </div>
            </div>
          </div>

          <!-- 일상 대화 참여 타임라인 -->
          <div class="card">
            <h4>일상 대화 참여 타임라인</h4>
            <div class="participation">
              <strong>{{ latestParticipation ?? '-' }}회</strong>
              <span>최근 참여 횟수</span>
            </div>
            <div class="line-chart">
              <svg viewBox="0 0 240 120">
                <path :d="getLinePath(participationSeries, 10)" stroke="#4cb7b7" stroke-width="3" fill="none" />
              </svg>
              <div class="chart-labels">
                <span v-for="label in participationLabels" :key="label">{{ label }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- MRI 분석 탭 -->
        <section v-else class="panel">
          <div class="card mri-card">
            <!-- MRI 헤더(제목 + 이미지 선택) -->
            <div class="mri-header">
              <h4>MRI 슬라이스</h4>
              <div class="visit-selector">
                <label>Image ID</label>
                <select v-model="selectedVisitImageId" :disabled="visitOptions.length === 0">
                  <option v-for="visit in visitOptions" :key="visit.imageId" :value="visit.imageId">
                    {{ String(visit.viscode2 || '').toUpperCase() }} · {{ visit.examDate }} · {{ visit.imageId }}
                  </option>
                </select>
              </div>
            </div>
            <!-- MRI 이미지 뷰어 -->
            <div class="mri-viewer" v-if="activeImage">
              <img :src="activeImage" alt="MRI Slice" loading="lazy" />
            </div>
            <!-- 이미지가 없을 때 안내 -->
            <div v-else class="empty-image">MRI 이미지가 없습니다.</div>
            <!-- MRI 메타 정보 -->
            <div class="mri-meta">
              <span>{{ activeVisit?.examDate || mriAnalysis?.scanDate || '-' }}</span>
              <span>{{ activeVisit?.imageId || mriAnalysis?.latestImageId || '-' }}</span>
            </div>
          </div>
        </section>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* 전체 레이아웃 */
.doctor-history {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-height: 0;
  font-size: 18px;
}

/* 로딩 스켈레톤 영역 */
.loading {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.skeleton-line {
  height: 26px;
  border-radius: 14px;
  background: linear-gradient(90deg, #e0e5ec 25%, #f0f3f6 50%, #e0e5ec 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-card {
  height: 180px;
  border-radius: 24px;
  background: linear-gradient(90deg, #e0e5ec 25%, #f0f3f6 50%, #e0e5ec 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 탭 컨텐츠 래퍼 */
.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 12px 12px 24px;
}

/* 환자 요약 배너 */
.patient-banner {
  background: #f5f6f7;
  border-radius: 24px;
  padding: 20px 24px;
  box-shadow: 10px 10px 20px #d1d9e6, -10px -10px 20px #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.patient-banner h3 {
  font-size: 22px;
  font-weight: 800;
  margin: 0 0 6px;
}

.patient-banner p {
  margin: 0;
  font-weight: 700;
  color: #4cb7b7;
}

.patient-meta {
  font-weight: 700;
  color: #555;
}

/* 장기 모니터링 지표 프레임 */
.record-outline {
  background: #f5f6f7;
  border-radius: 26px;
  padding: 24px;
  box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.record-outline-header h4 {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 800;
  color: #2e2e2e;
}

.record-outline-header p {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #777;
}

.record-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.record-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 16px;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.record-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.record-title {
  font-size: 16px;
  font-weight: 800;
  color: #2e2e2e;
}

.record-tag {
  font-size: 11px;
  font-weight: 900;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(76, 183, 183, 0.16);
  color: #4cb7b7;
  letter-spacing: 0.4px;
}

.record-placeholder {
  width: 100%;
  height: 70px;
  border-radius: 14px;
  background: linear-gradient(135deg, #eef1f3 0%, #f7f9fa 100%);
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.5), inset -4px -4px 10px #ffffff;
}

.record-desc {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #777;
  line-height: 1.4;
}

/* 탭 공통 패널 */
.panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 카드 공통 스타일 */
.card {
  background: #f5f6f7;
  padding: 24px;
  border-radius: 26px;
  box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card h4 {
  font-size: 20px;
  font-weight: 800;
  margin: 0;
  color: #2e2e2e;
}

/* 임상 요약 그리드 */
.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.summary-card {
  background: #ffffff;
  border-radius: 24px;
  padding: 24px;
  box-shadow: inset 6px 6px 12px rgba(209, 217, 230, 0.6), inset -6px -6px 12px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-card span {
  font-size: 18px;
  font-weight: 800;
  color: #777;
}

.summary-card strong {
  font-size: 36px;
  font-weight: 900;
  color: #2e2e2e;
}

.summary-card p {
  margin: 0;
  font-weight: 700;
  color: #888;
}

/* 라인 차트 영역 */
.line-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.line-chart svg {
  width: 100%;
  height: 120px;
}

.chart-legend {
  display: flex;
  gap: 18px;
  font-weight: 700;
  color: #666;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
}

.legend-dot.adas {
  background: #4cb7b7;
}

.legend-dot.faq {
  background: #ffb74d;
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  font-weight: 700;
  color: #999;
}

/* 음성 트렌드 카드 그리드 */
.trend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.trend-card {
  background: #ffffff;
  border-radius: 18px;
  padding: 16px;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.5), inset -4px -4px 8px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 800;
  color: #2e2e2e;
}

.trend-sub {
  font-weight: 700;
  color: #888;
}

.sparkline {
  width: 100%;
  height: 40px;
}

/* 참여도 요약 */
.participation {
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-weight: 800;
  color: #2e2e2e;
}

.participation strong {
  font-size: 28px;
}

/* MRI 카드 */
.mri-card {
  gap: 20px;
}

.mri-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.visit-selector {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.visit-selector label {
  font-size: 18px;
  font-weight: 800;
  color: #777;
}

.visit-selector select {
  padding: 12px 14px;
  border-radius: 14px;
  border: none;
  background: #ffffff;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.6), inset -4px -4px 8px #ffffff;
  font-size: 18px;
  font-weight: 700;
  color: #2e2e2e;
}

/* MRI 이미지 뷰어 */
.mri-viewer {
  width: 100%;
  border-radius: 22px;
  overflow: hidden;
  background: #1f2428;
}

.mri-viewer img {
  width: 100%;
  display: block;
  object-fit: cover;
}

/* MRI 이미지 없음 안내 */
.empty-image {
  padding: 32px;
  text-align: center;
  font-weight: 700;
  color: #888;
  background: #f5f6f7;
  border-radius: 20px;
}

/* MRI 메타 정보 */
.mri-meta {
  display: flex;
  justify-content: space-between;
  font-weight: 700;
  color: #555;
}

/* 탭 전환 페이드 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 모바일 대응 */
@media (max-width: 520px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .patient-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .mri-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
