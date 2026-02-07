import { ref } from 'vue';
import { CaregiverAdapter } from '@/data/adapters/CaregiverAdapter';

const adapter = new CaregiverAdapter(true);

export function useCaregiverData() {
  const data = ref(null);
  const loading = ref(false);
  const error = ref(null);

  const fetchData = async () => {
    loading.value = true;
    error.value = null;
    try {
      data.value = await adapter.fetch();
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  };

  return { data, loading, error, fetchData };
}