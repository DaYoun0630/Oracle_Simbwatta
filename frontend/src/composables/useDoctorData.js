import { ref } from 'vue';
import { DoctorAdapter } from '@/data/adapters/DoctorAdapter';
import { useAuthStore } from '@/stores/auth';

const doctorUseMockFlag = String(import.meta.env.VITE_DOCTOR_USE_MOCK ?? "false").toLowerCase();
const doctorUseMock = doctorUseMockFlag === "true" || doctorUseMockFlag === "1";
const adapter = new DoctorAdapter(doctorUseMock);
const DEFAULT_AUTO_REFRESH_MS = Number(import.meta.env.VITE_DOCTOR_AUTO_REFRESH_MS ?? 7000);
const MIN_AUTO_REFRESH_MS = 3000;

const DEFAULT_MOCK_PATIENT_ID = '029_S_6726';

const createEmptyDoctorData = () => ({
  patients: [],
  currentPatient: null,
  clinicalTrends: {
    mmse: [],
    moca: [],
    adasCog13: [],
    faq: [],
    labels: [],
  },
  biomarkerResults: {},
  biomarkerMeta: {},
  visits: [],
  dailyParticipation: {
    labels: [],
    counts: [],
  },
  acousticFeatures: [],
  mriAnalysis: null,
  dataAvailability: {
    hasCognitiveTests: false,
    hasMMSE: false,
    hasMoCA: false,
    hasADAS: false,
    hasFAQ: false,
    hasBiomarkers: false,
    hasMRI: false,
    mriCount: 0,
    hasVoiceUploads: false,
    hasVoiceData: false,
    voiceDataStatus: 'none',
    voiceDataDays: 0,
    dataCompleteness: 'none',
    lastUpdateDate: null,
    daysSinceLastUpdate: 0,
  },
});

const normalizePatientId = (value) => {
  if (value === null || value === undefined) {
    return null;
  }
  const normalized = String(value).trim();
  return normalized || null;
};

export function useDoctorData() {
  const authStore = useAuthStore();
  const data = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const currentPatientId = ref(null);
  let autoRefreshTimerId = null;

  const fetchData = async (patientId = currentPatientId.value, options = {}) => {
    const silent = Boolean(options?.silent);
    if (!silent) {
      loading.value = true;
      error.value = null;
    }
    try {
      let targetPatientId = normalizePatientId(patientId);

      if (!targetPatientId) {
        if (doctorUseMock) {
          targetPatientId = DEFAULT_MOCK_PATIENT_ID;
        } else {
          targetPatientId = await adapter.resolveDefaultPatientId(authStore.userId);
        }
      }

      if (!targetPatientId) {
        data.value = createEmptyDoctorData();
        currentPatientId.value = null;
        return;
      }

      data.value = await adapter.fetch(targetPatientId);
      currentPatientId.value = targetPatientId;
    } catch (e) {
      if (!silent) {
        error.value = e instanceof Error ? e.message : String(e);
      }
    } finally {
      if (!silent) {
        loading.value = false;
      }
    }
  };

  const switchPatient = (patientId) => {
    return fetchData(patientId);
  };

  const stopAutoRefresh = () => {
    if (autoRefreshTimerId !== null) {
      clearInterval(autoRefreshTimerId);
      autoRefreshTimerId = null;
    }
  };

  const startAutoRefresh = (intervalMs = DEFAULT_AUTO_REFRESH_MS) => {
    if (doctorUseMock) return;
    if (typeof window === 'undefined') return;
    if (autoRefreshTimerId !== null) return;

    const rawInterval = Number(intervalMs);
    const resolvedInterval = Number.isFinite(rawInterval)
      ? Math.max(rawInterval, MIN_AUTO_REFRESH_MS)
      : DEFAULT_AUTO_REFRESH_MS;

    autoRefreshTimerId = window.setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
        return;
      }
      if (!currentPatientId.value) return;
      void fetchData(currentPatientId.value, { silent: true });
    }, resolvedInterval);
  };

  return {
    data,
    loading,
    error,
    currentPatientId,
    fetchData,
    switchPatient,
    startAutoRefresh,
    stopAutoRefresh,
  };
}
