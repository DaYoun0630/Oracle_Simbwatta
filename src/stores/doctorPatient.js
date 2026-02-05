import { defineStore } from 'pinia';

export const useDoctorPatientStore = defineStore('doctorPatient', {
  state: () => ({
    selectedPatientId: null,
    selectedPatientSummary: null
  }),
  getters: {
    hasSelection: (state) => Boolean(state.selectedPatientId)
  },
  actions: {
    setSelectedPatientId(patientId) {
      this.selectedPatientId = patientId || null;
    },
    setSelectedPatientSummary(summary) {
      this.selectedPatientSummary = summary ? { ...summary } : null;
    },
    setSelectedPatient(summary) {
      if (!summary) return;
      this.setSelectedPatientId(summary.id);
      this.setSelectedPatientSummary(summary);
    },
    clearSelectedPatient() {
      this.selectedPatientId = null;
      this.selectedPatientSummary = null;
    }
  }
});
