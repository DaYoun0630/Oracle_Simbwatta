import { computed, onMounted, ref, watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import { fetchUserSettings, updateUserSettings } from "@/api/settings";

const STORAGE_KEYS = {
  dialogSummary: "caregiver-share-dialog-summary",
  anomalyAlert: "caregiver-share-anomaly-alert",
  medicationReminder: "caregiver-share-medication-reminder",
} as const;

const readToggle = (key: string): boolean => localStorage.getItem(key) !== "off";

export function useCaregiverSharingSettings() {
  const authStore = useAuthStore();
  const dialogSummary = ref(readToggle(STORAGE_KEYS.dialogSummary));
  const anomalyAlert = ref(readToggle(STORAGE_KEYS.anomalyAlert));
  const medicationReminder = ref(readToggle(STORAGE_KEYS.medicationReminder));
  const isHydrating = ref(false);
  const syncError = ref("");

  const persistSettings = async () => {
    if (isHydrating.value || !authStore.token) return;

    try {
      await updateUserSettings(authStore.token, {
        share_dialog_summary: dialogSummary.value,
        share_anomaly_alert: anomalyAlert.value,
        share_medication_reminder: medicationReminder.value,
      });
      syncError.value = "";
    } catch (error) {
      console.error("Failed to sync caregiver sharing settings:", error);
      syncError.value = error instanceof Error ? error.message : "설정 저장에 실패했습니다.";
    }
  };

  watch(dialogSummary, (value) => {
    localStorage.setItem(STORAGE_KEYS.dialogSummary, value ? "on" : "off");
    void persistSettings();
  });
  watch(anomalyAlert, (value) => {
    localStorage.setItem(STORAGE_KEYS.anomalyAlert, value ? "on" : "off");
    void persistSettings();
  });
  watch(medicationReminder, (value) => {
    localStorage.setItem(STORAGE_KEYS.medicationReminder, value ? "on" : "off");
    void persistSettings();
  });

  onMounted(async () => {
    if (!authStore.token) return;

    isHydrating.value = true;
    try {
      const settings = await fetchUserSettings(authStore.token);
      dialogSummary.value = settings.share_dialog_summary;
      anomalyAlert.value = settings.share_anomaly_alert;
      medicationReminder.value = settings.share_medication_reminder;
      syncError.value = "";
    } catch (error) {
      console.error("Failed to load caregiver sharing settings:", error);
      syncError.value = error instanceof Error ? error.message : "설정을 불러오지 못했습니다.";
    } finally {
      isHydrating.value = false;
    }
  });

  const allEnabled = computed(
    () => dialogSummary.value && anomalyAlert.value && medicationReminder.value
  );

  return {
    dialogSummary,
    anomalyAlert,
    medicationReminder,
    allEnabled,
    syncError,
  };
}
