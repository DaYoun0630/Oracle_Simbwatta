import { ref } from 'vue';
import { CaregiverAdapter } from '@/data/adapters/CaregiverAdapter';
import { useAuthStore } from '@/stores/auth';

const adapter = new CaregiverAdapter(false);

export function useCaregiverData() {
  const authStore = useAuthStore();
  const data = ref(null);
  const loading = ref(false);
  const error = ref(null);

  const fetchData = async () => {
    loading.value = true;
    error.value = null;
    try {
      const familyId = authStore.user?.entity_id ?? authStore.user?.id ?? null;
      data.value = await adapter.fetch({
        familyId,
        accessToken: authStore.token ?? null,
      });
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  };

  return { data, loading, error, fetchData };
}
