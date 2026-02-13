import { ref } from 'vue';
import { DoctorAdapter } from '@/data/adapters/DoctorAdapter';

const adapter = new DoctorAdapter(import.meta.env.VITE_DOCTOR_USE_MOCK === 'true');

export function useDoctorData() {
  const data = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const currentPatientId = ref('029_S_6726');

  const fetchData = async (patientId = currentPatientId.value) => {
    const resolvedPatientId = patientId || currentPatientId.value;
    loading.value = true;
    error.value = null;
    try {
      data.value = await adapter.fetch(resolvedPatientId);
      currentPatientId.value = resolvedPatientId;
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  };

  const switchPatient = (patientId) => {
    fetchData(patientId);
  };

  return { data, loading, error, currentPatientId, fetchData, switchPatient };
}
