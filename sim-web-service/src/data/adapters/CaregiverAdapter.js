import { DataAdapter } from './DataAdapter';
import { caregiverMockData } from '../mock/caregiver';

export class CaregiverAdapter extends DataAdapter {
  getMockData() {
    return caregiverMockData;
  }

  async getApiData() {
    const response = await fetch('/api/caregiver/dashboard');
    return response.json();
  }
}