import { DataAdapter } from './DataAdapter';
import { doctorMockData, patientDetails } from '../mock/doctor';

export class DoctorAdapter extends DataAdapter {
  getMockData(patientId) {
    // 환자별 상세 데이터가 있으면 사용
    if (patientDetails[patientId]) {
      return patientDetails[patientId];
    }

    // 기본 데이터 반환
    return {
      ...doctorMockData,
      currentPatient: doctorMockData.patients.find(p => p.id === patientId) || doctorMockData.patients[0]
    };
  }

  async getApiData(patientId) {
    const response = await fetch(`/api/doctor/patient/${patientId}`);
    return response.json();
  }
}
