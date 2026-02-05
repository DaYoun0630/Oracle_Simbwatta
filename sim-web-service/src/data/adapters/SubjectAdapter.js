import { DataAdapter } from './DataAdapter';
import { subjectMockData } from '../mock/subject';

export class SubjectAdapter extends DataAdapter {
  getMockData() {
    return subjectMockData;
  }

  async getApiData() {
    const response = await fetch('/api/subject/dashboard');
    return response.json();
  }
}