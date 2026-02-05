<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import MRIImageDisplay from '../mri/MRIImageDisplay.vue';
import RegionContributionChart from '../mri/RegionContributionChart.vue';
import DoctorDiagnosisForm from '../mri/DoctorDiagnosisForm.vue';
import EmptyState from '../common/EmptyState.vue';
import AlertBanner from '../common/AlertBanner.vue';

// 임상 추세 데이터 타입 정의
interface ClinicalTrends {
  adasCog13?: number[];
  faq?: number[];
  labels?: string[];
  mmse?: number[];
  moca?: number[];
}

interface VisitRecord {
  examDate: string;
  viscode2?: string | null;
  imageId?: string | null;
}

interface VisitRecordWithImage extends VisitRecord {
  imageId: string;
}

interface BiomarkerResults {
  abeta42?: number;
  abeta40?: number;
  ptau?: number;
  tau?: number;
  ratioAb42Ab40?: number;
  ratioPtauAb42?: number;
  ratioPtauTau?: number;
}

type DataAvailability = {
  hasCognitiveTests: boolean;
  hasMMSE: boolean;
  hasMoCA: boolean;
  hasADAS: boolean;
  hasFAQ: boolean;
  hasBiomarkers: boolean;
  hasMRI: boolean;
  mriCount: number;
  hasVoiceData: boolean;
  voiceDataDays: number;
  dataCompleteness: 'none' | 'minimal' | 'partial' | 'complete';
  lastUpdateDate: string | null;
  daysSinceLastUpdate: number;
};

type UserType = 'prevention' | 'suspected' | 'confirmed' | 'inactive';

type EmptyStateType = 'info' | 'warning' | 'success' | 'no-data' | 'partial-data' | 'not-applicable';

interface EmptyStateContent {
  type: EmptyStateType;
  icon?: string;
  title: string;
  description: string;
  benefits?: string[];
  note?: string;
  actionText?: string;
}

interface ScoreCardConfig {
  id: string;
  label: string;
  value: number | null;
  unit: string;
  max: number;
  direction: 'higher-better' | 'higher-worse';
  goodThreshold: number;
  warnThreshold: number;
  referenceRange: string;
  digits?: number;
}

const STALE_THRESHOLD_DAYS = 120;
const VOICE_CHART_WIDTH = 640;
const VOICE_CHART_HEIGHT = 200;

const ensureArray = <T,>(value: T[] | null | undefined) => (Array.isArray(value) ? value : []);

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const formatScoreValue = (value: number | null, digits = 0) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  if (digits > 0) return value.toFixed(digits);
  return String(Math.round(value));
};

const formatBiomarkerValue = (value: number | null, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return value.toFixed(digits);
};

const normalizeSeries = (values: number[]) => {
  if (!values || values.length < 2) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) return values.map(() => 0.5);
  return values.map((value) => (value - min) / (max - min));
};

const getNormalizedPath = (values: number[], width = VOICE_CHART_WIDTH, height = VOICE_CHART_HEIGHT) => {
  if (!values || values.length < 2) return '';
  const padding = 18;
  const points = values.map((value, i) => {
    const x = padding + (i / (values.length - 1)) * (width - padding * 2);
    const clamped = Math.min(1, Math.max(0, value));
    const y = height - padding - clamped * (height - padding * 2);
    return `${x},${y}`;
  });
  return `M ${points.join(' L ')}`;
};

const getTrendDirection = (values: number[]) => {
  if (!values || values.length < 2) return 'stable';
  const normalized = normalizeSeries(values);
  if (normalized.length < 2) return 'stable';
  const diff = normalized.at(-1)! - normalized.at(-2)!;
  if (Math.abs(diff) < 0.05) return 'stable';
  return diff > 0 ? 'increase' : 'decrease';
};

const getLatestDate = (dates: Array<string | null | undefined>) => {
  let latest: string | null = null;
  let latestTime = 0;

  dates.forEach((dateString) => {
    if (!dateString) return;
    const time = new Date(dateString).getTime();
    if (Number.isNaN(time)) return;
    if (time >= latestTime) {
      latestTime = time;
      latest = dateString;
    }
  });

  return latest;
};

const calculateDaysSince = (dateString: string | null) => {
  if (!dateString) return 0;
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return 0;
  const today = new Date();
  const normalizedToday = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const normalizedDate = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const diff = normalizedToday - normalizedDate;
  return diff > 0 ? Math.floor(diff / (1000 * 60 * 60 * 24)) : 0;
};

const makeScoreCard = (config: ScoreCardConfig) => {
  const {
    id,
    label,
    value,
    unit,
    max,
    direction,
    goodThreshold,
    warnThreshold,
    referenceRange,
    digits = 0
  } = config;

  let status: 'good' | 'warn' | 'bad' | 'empty' = 'empty';
  if (value !== null && value !== undefined) {
    if (direction === 'higher-better') {
      if (value >= goodThreshold) status = 'good';
      else if (value >= warnThreshold) status = 'warn';
      else status = 'bad';
    } else {
      if (value <= goodThreshold) status = 'good';
      else if (value <= warnThreshold) status = 'warn';
      else status = 'bad';
    }
  }

  const interpretationMap = {
    good: '정상 범위',
    warn: '주의 필요',
    bad: '저하 가능성',
    empty: '측정 없음'
  };

  const percent = value !== null && value !== undefined ? Math.round((clamp(value, 0, max) / max) * 100) : 0;

  return {
    id,
    label,
    value,
    unit,
    displayValue: formatScoreValue(value, digits),
    max,
    percent,
    status,
    interpretation: interpretationMap[status],
    referenceRange
  };
};

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

const isLoading = computed(() => props.loading || !props.data);
const currentPatient = computed(() => props.data?.currentPatient || null);
const visits = computed<VisitRecord[]>(
  () => (props.data?.visits as VisitRecord[] | undefined) ?? []
);
const clinicalTrends = computed<ClinicalTrends | null>(() =>
  props.data?.clinicalTrends ?? null
);
const dailyParticipation = computed(() => props.data?.dailyParticipation || null);
const acousticFeatures = computed(() => props.data?.acousticFeatures || []);
const mriAnalysis = computed(() => props.data?.mriAnalysis || null);

const aiAnalysis = computed(() => mriAnalysis.value?.aiAnalysis || null);
const originalImage = computed(() => aiAnalysis.value?.originalImage || '');
const attentionMap = computed(() => aiAnalysis.value?.attentionMap || '');
const regionContributions = computed(() => aiAnalysis.value?.regionContributions || []);

const patientSummary = computed(() => {
  const patientId = currentPatient.value?.id;
  if (!patientId) return null;
  return props.data?.patients?.find((patient: any) => patient.id === patientId) || null;
});

const dataAvailability = computed<DataAvailability>(() => {
  const base = (props.data?.dataAvailability ?? {}) as Partial<DataAvailability>;
  const clinical = clinicalTrends.value ?? {};
  const hasADAS = base.hasADAS ?? ensureArray(clinical.adasCog13).length > 0;
  const hasFAQ = base.hasFAQ ?? ensureArray(clinical.faq).length > 0;
  const hasMMSE =
    base.hasMMSE ??
    (ensureArray(clinical.mmse).length > 0 || patientSummary.value?.mmse != null);
  const hasMoCA =
    base.hasMoCA ??
    (ensureArray(clinical.moca).length > 0 || patientSummary.value?.moca != null);
  const hasCognitiveTests = base.hasCognitiveTests ?? (hasADAS || hasFAQ || hasMMSE || hasMoCA);

  const biomarkerSource = props.data?.biomarkerResults ?? props.data?.biomarkers ?? {};
  const hasBiomarkers =
    base.hasBiomarkers ??
    Object.values(biomarkerSource).some((value) => value !== null && value !== undefined);

  const participationCounts = ensureArray(dailyParticipation.value?.counts);
  const hasVoiceData = base.hasVoiceData ?? (acousticFeatures.value.length > 0 || participationCounts.length > 0);

  const reportCount = mriAnalysis.value?.reports ? Object.keys(mriAnalysis.value.reports).length : 0;
  const visitImageCount = ensureArray(visits.value).filter((visit) => visit?.imageId).length;
  const mriCount = base.mriCount ?? Math.max(reportCount, visitImageCount);
  const hasMRI = base.hasMRI ?? (mriCount > 0 || Boolean(mriAnalysis.value?.scanDate));

  const voiceDataDays = base.voiceDataDays ?? (participationCounts.length ? participationCounts.length * 7 : 0);

  const lastUpdateDate =
    base.lastUpdateDate ??
    mriAnalysis.value?.scanDate ??
    getLatestDate([
      ...ensureArray(visits.value).map((visit) => visit?.examDate),
      currentPatient.value?.examDate,
      currentPatient.value?.lastVisit
    ]);

  const daysSinceLastUpdate = calculateDaysSince(lastUpdateDate ?? null);
  const hasFullCognitive = hasMMSE && hasMoCA && hasADAS && hasFAQ;

  let dataCompleteness: DataAvailability['dataCompleteness'] = 'none';
  if (!hasCognitiveTests && !hasVoiceData && !hasMRI) {
    dataCompleteness = 'none';
  } else if (hasVoiceData && !hasCognitiveTests && !hasMRI) {
    dataCompleteness = 'minimal';
  } else if (hasCognitiveTests && hasVoiceData && hasMRI && hasFullCognitive) {
    dataCompleteness = 'complete';
  } else {
    dataCompleteness = 'partial';
  }

  return {
    hasCognitiveTests,
    hasMMSE,
    hasMoCA,
    hasADAS,
    hasFAQ,
    hasBiomarkers,
    hasMRI,
    mriCount,
    hasVoiceData,
    voiceDataDays,
    dataCompleteness,
    lastUpdateDate: lastUpdateDate ?? null,
    daysSinceLastUpdate
  };
});

const sortedVisits = computed(() => {
  if (!visits.value.length) return [];
  return [...visits.value].sort((a, b) => new Date(a.examDate).getTime() - new Date(b.examDate).getTime());
});

const visitOptions = computed<VisitRecordWithImage[]>(() =>
  sortedVisits.value.filter(
    (visit): visit is VisitRecordWithImage => Boolean(visit?.imageId)
  )
);
const selectedVisitImageId = ref('');

const hasClinicalData = computed(() => dataAvailability.value.hasCognitiveTests);
const hasVoiceData = computed(() => dataAvailability.value.hasVoiceData);
const hasMRIData = computed(() => dataAvailability.value.hasMRI);

const showClinicalEmpty = computed(() => !hasClinicalData.value);
const showVoiceEmpty = computed(() => !hasVoiceData.value);
const showMriEmpty = computed(() => !hasMRIData.value);

const isDataStale = computed(() => dataAvailability.value.daysSinceLastUpdate >= STALE_THRESHOLD_DAYS);
const dataStaleMessage = computed(() => {
  if (!isDataStale.value) return '';
  const lastDate = dataAvailability.value.lastUpdateDate;
  const days = dataAvailability.value.daysSinceLastUpdate;
  if (lastDate) {
    return `마지막 업데이트가 ${lastDate} (${days}일 전)입니다. 최신 검사 및 음성 데이터를 업데이트해 주세요.`;
  }
  return '최근 데이터가 업데이트되지 않았습니다. 최신 검사 및 음성 데이터를 업데이트해 주세요.';
});

const userType = computed<UserType>(() => {
  if (props.data?.userType) return props.data.userType as UserType;
  if (isDataStale.value) return 'inactive';
  switch (dataAvailability.value.dataCompleteness) {
    case 'minimal':
      return 'prevention';
    case 'partial':
      return 'suspected';
    case 'complete':
      return 'confirmed';
    default:
      return 'prevention';
  }
});

const emptyStateContent = computed<Record<'clinical' | 'voice' | 'mri', EmptyStateContent>>(() => {
  const staleNote = dataStaleMessage.value || undefined;

  switch (userType.value) {
    case 'prevention':
      return {
        clinical: {
          type: 'no-data',
          icon: 'clipboard',
          title: '인지 검사 데이터가 없습니다',
          description: '예방형 환자는 음성 데이터 중심으로 모니터링합니다.',
          benefits: ['필요 시 MMSE · MoCA 검사를 추가해 주세요.']
        },
        voice: {
          type: 'warning',
          icon: 'microphone',
          title: '음성 데이터가 없습니다',
          description: '예방형 리포트는 음성 데이터가 필요합니다.',
          benefits: ['일상 대화 참여 데이터가 누적되면 추세를 확인할 수 있습니다.']
        },
        mri: {
          type: 'not-applicable',
          icon: 'brain',
          title: 'MRI는 선택 항목입니다',
          description: '현재 MRI 촬영 기록이 없습니다.',
          note: '필요 시 촬영을 진행해 주세요.'
        }
      };
    case 'suspected':
      return {
        clinical: {
          type: 'partial-data',
          icon: 'chart',
          title: '인지 검사 데이터가 일부만 있습니다',
          description: 'MMSE · MoCA 중심으로 확인할 수 있습니다.',
          benefits: ['ADAS-cog13 및 FAQ를 추가하면 더 정확한 판단이 가능합니다.']
        },
        voice: {
          type: 'no-data',
          icon: 'microphone',
          title: '음성 데이터가 없습니다',
          description: '음성·대화 데이터가 있어야 변화 추이를 확인할 수 있습니다.'
        },
        mri: {
          type: 'no-data',
          icon: 'brain',
          title: 'MRI 데이터가 없습니다',
          description: 'MRI 촬영 후 분석 결과가 표시됩니다.'
        }
      };
    case 'inactive':
      return {
        clinical: {
          type: 'warning',
          icon: 'alert',
          title: '인지 검사 기록이 오래되었습니다',
          description: '최근 인지 검사 데이터가 없습니다.',
          note: staleNote
        },
        voice: {
          type: 'warning',
          icon: 'alert',
          title: '음성 데이터가 오래되었습니다',
          description: '최근 음성 데이터가 없습니다.',
          note: staleNote
        },
        mri: {
          type: 'warning',
          icon: 'alert',
          title: 'MRI 데이터가 오래되었습니다',
          description: '최근 MRI 촬영 기록이 없습니다.',
          note: staleNote
        }
      };
    default:
      return {
        clinical: {
          type: 'no-data',
          icon: 'clipboard',
          title: '인지 검사 데이터가 없습니다',
          description: '등록된 인지 검사 결과가 없습니다.'
        },
        voice: {
          type: 'no-data',
          icon: 'microphone',
          title: '음성 데이터가 없습니다',
          description: '등록된 음성 데이터가 없습니다.'
        },
        mri: {
          type: 'no-data',
          icon: 'brain',
          title: 'MRI 데이터가 없습니다',
          description: '촬영 기록이 없습니다.'
        }
      };
  }
});

const clinicalEmptyState = computed(() => emptyStateContent.value.clinical);
const voiceEmptyState = computed(() => emptyStateContent.value.voice);
const mriEmptyState = computed(() => emptyStateContent.value.mri);

const adasSeries = computed(() => clinicalTrends.value?.adasCog13 || []);
const faqSeries = computed(() => clinicalTrends.value?.faq || []);

const mmseValue = computed(() => {
  const series = ensureArray(clinicalTrends.value?.mmse);
  if (series.length) return series.at(-1) ?? null;
  return patientSummary.value?.mmse ?? null;
});

const mocaValue = computed(() => {
  const series = ensureArray(clinicalTrends.value?.moca);
  if (series.length) return series.at(-1) ?? null;
  return patientSummary.value?.moca ?? null;
});

const adasValue = computed(() => adasSeries.value.at(-1) ?? null);
const faqValue = computed(() => faqSeries.value.at(-1) ?? null);

const cognitiveScoreCards = computed(() => [
  makeScoreCard({
    id: 'mmse',
    label: 'MMSE',
    value: mmseValue.value,
    unit: '점',
    max: 30,
    direction: 'higher-better',
    goodThreshold: 27,
    warnThreshold: 21,
    referenceRange: '27-30'
  }),
  makeScoreCard({
    id: 'moca',
    label: 'MoCA',
    value: mocaValue.value,
    unit: '점',
    max: 30,
    direction: 'higher-better',
    goodThreshold: 26,
    warnThreshold: 18,
    referenceRange: '26-30'
  }),
  makeScoreCard({
    id: 'adas',
    label: 'ADAS-cog13',
    value: adasValue.value,
    unit: '점',
    max: 85,
    direction: 'higher-worse',
    goodThreshold: 10,
    warnThreshold: 20,
    referenceRange: '0-10',
    digits: 1
  }),
  makeScoreCard({
    id: 'faq',
    label: 'FAQ',
    value: faqValue.value,
    unit: '점',
    max: 30,
    direction: 'higher-worse',
    goodThreshold: 9,
    warnThreshold: 20,
    referenceRange: '0-9'
  })
]);

const biomarkerResults = computed<BiomarkerResults | null>(() =>
  props.data?.biomarkerResults ?? props.data?.biomarkers ?? null
);

const biomarkerItems = computed(() => {
  const base = biomarkerResults.value || {};
  const abeta42 = base.abeta42 ?? null;
  const abeta40 = base.abeta40 ?? null;
  const ptau = base.ptau ?? null;
  const tau = base.tau ?? null;
  const ratioAb42Ab40 = base.ratioAb42Ab40 ?? (abeta42 && abeta40 ? abeta42 / abeta40 : null);
  const ratioPtauAb42 = base.ratioPtauAb42 ?? (ptau && abeta42 ? ptau / abeta42 : null);
  const ratioPtauTau = base.ratioPtauTau ?? (ptau && tau ? ptau / tau : null);

  return [
    {
      id: 'abeta42',
      label: 'ABETA42',
      value: abeta42,
      unit: 'pg/mL',
      range: '정상 범위: > 500'
    },
    {
      id: 'abeta40',
      label: 'ABETA40',
      value: abeta40,
      unit: 'pg/mL',
      range: '정상 범위: 800-1200'
    },
    {
      id: 'ptau',
      label: 'PTAU',
      value: ptau,
      unit: 'pg/mL',
      range: '정상 범위: < 20'
    },
    {
      id: 'tau',
      label: 'TAU',
      value: tau,
      unit: 'pg/mL',
      range: '정상 범위: < 300'
    },
    {
      id: 'ratio-ab42-ab40',
      label: 'AB42/40',
      value: ratioAb42Ab40,
      unit: '',
      range: '기준 비율: > 0.6'
    },
    {
      id: 'ratio-ptau-ab42',
      label: 'PTAU/AB42',
      value: ratioPtauAb42,
      unit: '',
      range: '기준 비율: < 0.05'
    },
    {
      id: 'ratio-ptau-tau',
      label: 'PTAU/TAU',
      value: ratioPtauTau,
      unit: '',
      range: '기준 비율: < 0.2'
    }
  ];
});

const hasBiomarkerData = computed(() =>
  biomarkerItems.value.some((item) => item.value !== null && item.value !== undefined)
);

const findFeature = (keywords: string[]) =>
  acousticFeatures.value.find((feature: any) =>
    keywords.some((keyword) => String(feature?.label ?? '').includes(keyword))
  );

const buildSeries = (values: number[] | undefined) =>
  ensureArray(values)
    .map((value) => Number(value))
    .filter((value) => !Number.isNaN(value));

const voiceMetrics = computed(() => {
  const utteranceFeature = findFeature(['발화', '속도', '빈도']);
  const lengthFeature = findFeature(['길이', 'length', '발화 길이']) || findFeature(['강도']);
  const pauseFeature = findFeature(['멈춤', 'pause']);

  const metrics = [
    {
      id: 'utterance',
      label: '발화 빈도',
      color: '#4cb7b7',
      values: buildSeries(utteranceFeature?.trend)
    },
    {
      id: 'length',
      label: '평균 발화 길이',
      color: '#8bc34a',
      values: buildSeries(lengthFeature?.trend)
    },
    {
      id: 'pause',
      label: 'Pause 비율',
      color: '#ffb74d',
      values: buildSeries(pauseFeature?.trend)
    },
    {
      id: 'participation',
      label: '대화 참여 빈도',
      color: '#ff8a80',
      values: buildSeries(dailyParticipation.value?.counts)
    }
  ];

  return metrics.map((metric) => ({
    ...metric,
    hasData: metric.values.length > 1
  }));
});

const normalizedVoiceMetrics = computed(() =>
  voiceMetrics.value.map((metric) => ({
    ...metric,
    normalized: normalizeSeries(metric.values)
  }))
);

const activeVoiceMetricIds = ref<string[]>([]);

const activeVoiceMetrics = computed(() =>
  normalizedVoiceMetrics.value.filter(
    (metric) => activeVoiceMetricIds.value.includes(metric.id) && metric.normalized.length > 1
  )
);

const voiceTimelineLabels = computed(() => {
  const labels = dailyParticipation.value?.labels;
  if (labels?.length) return labels;
  const maxLength = Math.max(0, ...normalizedVoiceMetrics.value.map((metric) => metric.normalized.length));
  return Array.from({ length: maxLength }, (_, index) => `T${index + 1}`);
});

const voiceSummary = computed(() => {
  if (!activeVoiceMetrics.value.length) {
    return {
      statusKey: 'empty',
      statusLabel: '선택 필요',
      detail: '표시할 지표를 선택해 주세요.'
    };
  }

  const directions = activeVoiceMetrics.value.map((metric) => getTrendDirection(metric.values));
  const hasIncrease = directions.includes('increase');
  const hasDecrease = directions.includes('decrease');

  if (hasIncrease && hasDecrease) {
    return {
      statusKey: 'mixed',
      statusLabel: '혼합',
      detail: '이전 대비 혼합 변화 경향입니다.'
    };
  }

  if (hasIncrease) {
    return {
      statusKey: 'increase',
      statusLabel: '증가',
      detail: '이전 대비 증가 경향입니다.'
    };
  }

  if (hasDecrease) {
    return {
      statusKey: 'decrease',
      statusLabel: '감소',
      detail: '이전 대비 감소 경향입니다.'
    };
  }

  return {
    statusKey: 'stable',
    statusLabel: '안정',
    detail: '이전 대비 안정적인 흐름입니다.'
  };
});

const mriScanDate = computed(() => mriAnalysis.value?.scanDate || dataAvailability.value.lastUpdateDate || '-');
const mriScanCount = computed(() => (dataAvailability.value.mriCount ? `${dataAvailability.value.mriCount}건` : '-'));

const handleDiagnosisSubmit = (data: any) => {
  console.log('진단 데이터 제출:', data);
  // 실제 구현 시 POST /api/doctor-diagnosis 호출
};

const handleSendDiagnosis = () => {
  if (!currentPatient.value?.id) return;
  console.log('진단 결과 전달:', currentPatient.value.id);
};

watch(
  () => visitOptions.value,
  (value) => {
    if (!value?.length) return;
    selectedVisitImageId.value = value.at(-1)?.imageId || '';
  },
  { immediate: true }
);

watch(
  () => normalizedVoiceMetrics.value,
  (metrics) => {
    const available = metrics.filter((metric) => metric.hasData).map((metric) => metric.id);
    if (!available.length) {
      activeVoiceMetricIds.value = [];
      return;
    }
    const current = activeVoiceMetricIds.value.filter((id) => available.includes(id));
    if (current.length) {
      activeVoiceMetricIds.value = current;
      return;
    }
    activeVoiceMetricIds.value = available.slice(0, 2);
  },
  { immediate: true }
);
</script>
<template>
  <div class="doctor-history">
    <div v-if="isLoading" class="loading">
      <div class="skeleton-line"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
    </div>

    <transition v-else name="fade" mode="out-in">
      <div :key="currentTab" class="tab-panel">
        <section class="patient-banner" aria-label="환자 기본 정보">
          <div>
            <h3>{{ currentPatient?.name }}</h3>
            <p>{{ currentPatient?.id }} · {{ currentPatient?.rid || '-' }}</p>
          </div>
          <span class="patient-meta">{{ currentPatient?.age }}세 · {{ currentPatient?.gender === 'F' ? '여' : '남' }}</span>
        </section>

        <AlertBanner
          v-if="isDataStale"
          class="data-alert"
          type="warning"
          :message="dataStaleMessage"
          :dismissible="true"
          :action-required="true"
          aria-label="데이터 신선도 경고"
        />

        <section v-if="currentTab === 'clinical'" class="panel clinical-panel" aria-label="인지 검사">
          <EmptyState
            v-if="showClinicalEmpty"
            class="empty-state-slot"
            :type="clinicalEmptyState.type"
            :icon="clinicalEmptyState.icon"
            :title="clinicalEmptyState.title"
            :description="clinicalEmptyState.description"
            :benefits="clinicalEmptyState.benefits"
            :note="clinicalEmptyState.note"
            :action-text="clinicalEmptyState.actionText"
            aria-label="인지 검사 데이터 비어 있음"
          />

          <template v-else>
            <div class="section-header">
              <div>
                <h4>최근 측정 결과</h4>
                <p>연령 대비 기준 범위를 참고해 현재 인지 상태를 확인합니다.</p>
              </div>
              <span class="section-chip">현재 인지 상태</span>
            </div>

            <div class="score-grid">
              <article
                v-for="card in cognitiveScoreCards"
                :key="card.id"
                class="score-card"
                :class="`score-${card.status}`"
              >
                <div class="score-header">
                  <span class="score-label">{{ card.label }}</span>
                  <div class="score-value">
                    <strong>{{ card.displayValue }}</strong>
                    <span v-if="card.displayValue !== '-'" class="score-unit">{{ card.unit }}</span>
                  </div>
                </div>
                <p class="score-sub">최근 측정 결과</p>
                <div class="score-bar" aria-hidden="true">
                  <div class="score-bar__track"></div>
                  <div class="score-bar__fill" :style="{ width: `${card.percent}%` }"></div>
                  <div class="score-bar__marker" :style="{ left: `${card.percent}%` }"></div>
                </div>
                <div class="score-meta">
                  <span class="score-range">연령 대비 기준 범위: {{ card.referenceRange }}</span>
                  <span class="score-interpretation">현재 임상적 해석: {{ card.interpretation }}</span>
                </div>
              </article>
            </div>

            <div class="card biomarker-card">
              <div class="biomarker-header">
                <div>
                  <h4>바이오마커 결과</h4>
                  <p>혈액 기반 지표를 정적 정보로 요약합니다.</p>
                </div>
                <span class="biomarker-chip">정적 정보</span>
              </div>

              <div v-if="hasBiomarkerData" class="biomarker-grid">
                <div v-for="item in biomarkerItems" :key="item.id" class="biomarker-item">
                  <span class="biomarker-label">{{ item.label }}</span>
                  <strong class="biomarker-value">
                    {{ formatBiomarkerValue(item.value, item.unit ? 1 : 2) }}
                    <span v-if="item.unit" class="biomarker-unit">{{ item.unit }}</span>
                  </strong>
                  <span class="biomarker-range">{{ item.range }}</span>
                </div>
              </div>

              <p v-else class="biomarker-empty">바이오마커 데이터가 없습니다.</p>
            </div>
          </template>
        </section>

        <section v-else-if="currentTab === 'voice'" class="panel voice-panel" aria-label="음성 대화">
          <EmptyState
            v-if="showVoiceEmpty"
            class="empty-state-slot"
            :type="voiceEmptyState.type"
            :icon="voiceEmptyState.icon"
            :title="voiceEmptyState.title"
            :description="voiceEmptyState.description"
            :benefits="voiceEmptyState.benefits"
            :note="voiceEmptyState.note"
            :action-text="voiceEmptyState.actionText"
            aria-label="음성 데이터 비어 있음"
          />

          <template v-else>
            <div class="card voice-summary-card">
              <div>
                <h4>최근 4주간 변화 관찰</h4>
                <p>정규화된 지표 기준으로 변화 방향을 요약합니다.</p>
              </div>
              <div class="voice-summary-status" :class="`voice-status-${voiceSummary.statusKey}`">
                <span>이전 대비</span>
                <strong>{{ voiceSummary.statusLabel }}</strong>
                <small>{{ voiceSummary.detail }}</small>
              </div>
            </div>

            <div class="card voice-chart-card">
              <div class="voice-chart-header">
                <div>
                  <h4>음성 대화 지표 변화</h4>
                  <p>시간 축 기준 정규화된 지표 (percentile / index)</p>
                </div>
                <div class="voice-toggle-group">
                  <label
                    v-for="metric in normalizedVoiceMetrics"
                    :key="metric.id"
                    class="voice-toggle"
                    :class="{ disabled: !metric.hasData }"
                  >
                    <input
                      type="checkbox"
                      :value="metric.id"
                      v-model="activeVoiceMetricIds"
                      :disabled="!metric.hasData"
                    />
                    <span class="voice-toggle__dot" :style="{ background: metric.color }"></span>
                    <span class="voice-toggle__label">{{ metric.label }}</span>
                  </label>
                </div>
              </div>

              <div class="voice-chart">
                <svg :viewBox="`0 0 ${VOICE_CHART_WIDTH} ${VOICE_CHART_HEIGHT}`" role="img" aria-label="음성 지표 통합 그래프">
                  <g class="voice-grid">
                    <line v-for="y in [40, 80, 120, 160]" :key="y" :x1="0" :x2="VOICE_CHART_WIDTH" :y1="y" :y2="y" />
                  </g>
                  <path
                    v-for="metric in activeVoiceMetrics"
                    :key="metric.id"
                    :d="getNormalizedPath(metric.normalized)"
                    :stroke="metric.color"
                    stroke-width="3"
                    fill="none"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
                <div class="voice-chart-labels">
                  <span v-for="label in voiceTimelineLabels" :key="label">{{ label }}</span>
                </div>
              </div>

              <p v-if="activeVoiceMetrics.length === 0" class="voice-chart-empty">
                표시할 지표를 선택해 주세요.
              </p>
            </div>
          </template>
        </section>

        <section v-else class="panel mri-analysis-panel" aria-label="MRI 분석">
          <EmptyState
            v-if="showMriEmpty"
            class="empty-state-slot"
            :type="mriEmptyState.type"
            :icon="mriEmptyState.icon"
            :title="mriEmptyState.title"
            :description="mriEmptyState.description"
            :benefits="mriEmptyState.benefits"
            :note="mriEmptyState.note"
            :action-text="mriEmptyState.actionText"
            aria-label="MRI 데이터 비어 있음"
          />

          <template v-else>
            <div class="card mri-context-card">
              <div>
                <h4>공간적 해석 요약</h4>
                <p>관심 영역 하이라이트와 기여도 분석을 중심으로 구조적 원인을 해석합니다.</p>
              </div>
              <div class="mri-context-meta">
                <div class="mri-meta-item">
                  <span>최근 촬영일</span>
                  <strong>{{ mriScanDate }}</strong>
                </div>
                <div class="mri-meta-item">
                  <span>MRI 기록</span>
                  <strong>{{ mriScanCount }}</strong>
                </div>
              </div>
            </div>

            <div class="mri-analysis-grid">
              <div class="card mri-images-card">
                <h4>MRI 이미지</h4>
                <MRIImageDisplay
                  :original-image="originalImage"
                  :attention-map="attentionMap"
                  :loading="isLoading"
                />
                <div v-if="visitOptions.length > 0" class="visit-selector-row">
                  <label for="visit-selector">방문 기록</label>
                  <select id="visit-selector" v-model="selectedVisitImageId">
                    <option v-for="visit in visitOptions" :key="visit.imageId || visit.examDate" :value="visit.imageId || ''">
                      {{ String(visit.viscode2 || '').toUpperCase() }} · {{ visit.examDate }}
                    </option>
                  </select>
                </div>
              </div>

              <div class="card contribution-card">
                <RegionContributionChart
                  :contributions="regionContributions"
                  :loading="isLoading"
                />
              </div>
            </div>

            <DoctorDiagnosisForm
              v-if="currentPatient?.id"
              :patient-id="currentPatient.id"
              doctor-id="doctor_001"
              @submit="handleDiagnosisSubmit"
            />

            <div class="card mri-action-card">
              <div>
                <h4>진단 결과 전달</h4>
                <p>확정된 진단 결과를 챗봇 및 모델 학습 파이프라인으로 전달합니다.</p>
              </div>
              <button type="button" class="mri-action-button" @click="handleSendDiagnosis">
                진단 결과 전달
              </button>
            </div>
          </template>
        </section>
      </div>
    </transition>
  </div>
</template>
<style scoped>
.doctor-history {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-height: 0;
  font-size: 18px;
}

.data-alert {
  margin-top: 4px;
}

.empty-state-slot {
  width: 100%;
}

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

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 12px 12px 24px;
}

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

.panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.section-header h4 {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 800;
  color: #2e2e2e;
}

.section-header p {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #777;
}

.section-chip {
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(76, 183, 183, 0.15);
  color: #2e7d7d;
  font-size: 13px;
  font-weight: 800;
}

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

.score-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.score-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 18px;
  box-shadow: inset 4px 4px 10px rgba(209, 217, 230, 0.6), inset -4px -4px 10px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.score-card.score-good {
  border: 1px solid rgba(76, 183, 183, 0.35);
}

.score-card.score-warn {
  border: 1px solid rgba(255, 183, 77, 0.45);
}

.score-card.score-bad {
  border: 1px solid rgba(255, 138, 128, 0.45);
}

.score-card.score-empty {
  border: 1px dashed rgba(0, 0, 0, 0.08);
}

.score-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.score-label {
  font-size: 16px;
  font-weight: 800;
  color: #2e2e2e;
}

.score-value {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 22px;
  font-weight: 900;
  color: #2e2e2e;
}

.score-unit {
  font-size: 12px;
  font-weight: 700;
  color: #999;
}

.score-sub {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #777;
}

.score-bar {
  position: relative;
  height: 10px;
  border-radius: 999px;
  background: #eef1f3;
  overflow: hidden;
}

.score-bar__track {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(76, 183, 183, 0.15), rgba(255, 183, 77, 0.15), rgba(255, 138, 128, 0.12));
}

.score-bar__fill {
  position: absolute;
  inset: 0;
  width: 0;
  background: #4cb7b7;
  opacity: 0.6;
}

.score-card.score-warn .score-bar__fill {
  background: #ffb74d;
}

.score-card.score-bad .score-bar__fill {
  background: #ff8a80;
}

.score-bar__marker {
  position: absolute;
  top: -4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  transform: translateX(-50%);
  background: #ffffff;
  border: 2px solid #4cb7b7;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.score-card.score-warn .score-bar__marker {
  border-color: #ffb74d;
}

.score-card.score-bad .score-bar__marker {
  border-color: #ff8a80;
}

.score-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #777;
}

.biomarker-card {
  gap: 18px;
}

.biomarker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.biomarker-header p {
  margin: 6px 0 0;
  font-size: 14px;
  font-weight: 700;
  color: #777;
}

.biomarker-chip {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(76, 183, 183, 0.12);
  color: #2e7d7d;
  font-size: 12px;
  font-weight: 800;
}

.biomarker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.biomarker-item {
  background: #ffffff;
  border-radius: 16px;
  padding: 14px;
  box-shadow: inset 3px 3px 8px rgba(209, 217, 230, 0.5), inset -3px -3px 8px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.biomarker-label {
  font-size: 12px;
  font-weight: 800;
  color: #888;
}

.biomarker-value {
  font-size: 18px;
  font-weight: 900;
  color: #2e2e2e;
}

.biomarker-unit {
  font-size: 12px;
  font-weight: 700;
  color: #999;
  margin-left: 4px;
}

.biomarker-range {
  font-size: 12px;
  font-weight: 700;
  color: #777;
}

.biomarker-empty {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #777;
}

.voice-summary-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.voice-summary-card p {
  margin: 6px 0 0;
  font-size: 14px;
  font-weight: 700;
  color: #777;
}

.voice-summary-status {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 18px;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: inset 4px 4px 8px rgba(209, 217, 230, 0.5), inset -4px -4px 8px #ffffff;
  min-width: 140px;
  text-align: center;
  font-weight: 800;
  color: #2e2e2e;
}

.voice-summary-status strong {
  font-size: 20px;
}

.voice-summary-status small {
  font-size: 12px;
  font-weight: 700;
  color: #777;
}

.voice-status-increase {
  color: #2e2e2e;
  border: 1px solid rgba(255, 183, 77, 0.45);
}

.voice-status-decrease {
  color: #2e2e2e;
  border: 1px solid rgba(255, 138, 128, 0.45);
}

.voice-status-stable {
  color: #2e2e2e;
  border: 1px solid rgba(76, 183, 183, 0.45);
}

.voice-status-mixed {
  color: #2e2e2e;
  border: 1px solid rgba(120, 120, 120, 0.35);
}

.voice-status-empty {
  color: #2e2e2e;
  border: 1px dashed rgba(0, 0, 0, 0.12);
}

.voice-chart-card {
  gap: 18px;
}

.voice-chart-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.voice-chart-header p {
  margin: 6px 0 0;
  font-size: 14px;
  font-weight: 700;
  color: #777;
}

.voice-toggle-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.voice-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: #ffffff;
  box-shadow: inset 2px 2px 6px rgba(209, 217, 230, 0.4), inset -2px -2px 6px #ffffff;
  font-size: 13px;
  font-weight: 800;
  color: #2e2e2e;
}

.voice-toggle input {
  width: 14px;
  height: 14px;
}

.voice-toggle.disabled {
  opacity: 0.4;
  pointer-events: none;
}

.voice-toggle__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.voice-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.voice-chart svg {
  width: 100%;
  height: 220px;
}

.voice-grid line {
  stroke: rgba(0, 0, 0, 0.06);
  stroke-width: 1;
}

.voice-chart-labels {
  display: flex;
  justify-content: space-between;
  font-weight: 700;
  color: #999;
  font-size: 12px;
}

.voice-chart-empty {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #777;
}

.mri-analysis-panel {
  gap: 24px;
}

.mri-context-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.mri-context-card p {
  margin: 6px 0 0;
  font-size: 14px;
  font-weight: 700;
  color: #777;
}

.mri-context-meta {
  display: flex;
  gap: 16px;
}

.mri-meta-item {
  background: #ffffff;
  border-radius: 16px;
  padding: 12px 14px;
  box-shadow: inset 3px 3px 8px rgba(209, 217, 230, 0.5), inset -3px -3px 8px #ffffff;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 120px;
}

.mri-meta-item span {
  font-size: 12px;
  font-weight: 800;
  color: #888;
}

.mri-meta-item strong {
  font-size: 16px;
  font-weight: 900;
  color: #2e2e2e;
}

.mri-analysis-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.mri-images-card {
  gap: 20px;
}

.mri-images-card h4 {
  margin-bottom: 4px;
}

.contribution-card {
  padding: 0;
  background: transparent;
  box-shadow: none;
}

.visit-selector-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.visit-selector-row label {
  font-size: 15px;
  font-weight: 800;
  color: #777;
  white-space: nowrap;
}

.visit-selector-row select {
  flex: 1;
  padding: 10px 14px;
  border-radius: 12px;
  border: none;
  background: #f5f6f7;
  box-shadow: inset 3px 3px 6px rgba(209, 217, 230, 0.6), inset -3px -3px 6px #ffffff;
  font-size: 15px;
  font-weight: 700;
  color: #2e2e2e;
}

.mri-action-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.mri-action-card p {
  margin: 6px 0 0;
  font-size: 14px;
  font-weight: 700;
  color: #777;
}

.mri-action-button {
  padding: 14px 22px;
  border-radius: 16px;
  border: none;
  background: #4cb7b7;
  color: #ffffff;
  font-size: 15px;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
}

.mri-action-button:hover {
  background: #3da5a5;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 520px) {
  .patient-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .section-header {
    flex-direction: column;
  }

  .voice-summary-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .voice-chart-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .mri-analysis-grid {
    grid-template-columns: 1fr;
  }

  .mri-context-card {
    flex-direction: column;
  }

  .mri-context-meta {
    width: 100%;
    justify-content: space-between;
  }

  .mri-action-card {
    flex-direction: column;
    align-items: stretch;
  }

  .mri-action-button {
    width: 100%;
  }

  .visit-selector-row {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 1024px) {
  .mri-analysis-grid {
    grid-template-columns: 1fr;
  }
}
</style>
