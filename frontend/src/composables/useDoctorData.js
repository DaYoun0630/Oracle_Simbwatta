import { ref } from 'vue';
import { DoctorAdapter } from '@/data/adapters/DoctorAdapter';

const adapter = new DoctorAdapter(true);

export function useDoctorData() {
  const data = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const currentPatientId = ref('029_S_6726');

  const fetchData = async (patientId = currentPatientId.value) => {
    loading.value = true;
    error.value = null;
    try {
      data.value = await adapter.fetch(patientId);
      currentPatientId.value = patientId;
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
