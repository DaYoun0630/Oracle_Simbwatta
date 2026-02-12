import { computed, ref, watch } from "vue";

const STORAGE_KEYS = {
  dialogSummary: "caregiver-share-dialog-summary",
  anomalyAlert: "caregiver-share-anomaly-alert",
  medicationReminder: "caregiver-share-medication-reminder",
} as const;

const readToggle = (key: string): boolean => localStorage.getItem(key) !== "off";

export function useCaregiverSharingSettings() {
  const dialogSummary = ref(readToggle(STORAGE_KEYS.dialogSummary));
  const anomalyAlert = ref(readToggle(STORAGE_KEYS.anomalyAlert));
  const medicationReminder = ref(readToggle(STORAGE_KEYS.medicationReminder));

  watch(dialogSummary, (value) => localStorage.setItem(STORAGE_KEYS.dialogSummary, value ? "on" : "off"));
  watch(anomalyAlert, (value) => localStorage.setItem(STORAGE_KEYS.anomalyAlert, value ? "on" : "off"));
  watch(medicationReminder, (value) =>
    localStorage.setItem(STORAGE_KEYS.medicationReminder, value ? "on" : "off")
  );

  const allEnabled = computed(
    () => dialogSummary.value && anomalyAlert.value && medicationReminder.value
  );

  return {
    dialogSummary,
    anomalyAlert,
    medicationReminder,
    allEnabled,
  };
}
