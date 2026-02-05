export class DataAdapter {
  constructor(useMock = true) {
    this.useMock = useMock;
  }

  async fetch(params) {
    if (this.useMock) {
      return this.getMockData(params);
    }
    return this.getApiData(params);
  }

  getMockData(params) {
    throw new Error('getMockData must be implemented');
  }

  async getApiData(params) {
    throw new Error('getApiData must be implemented');
  }
}