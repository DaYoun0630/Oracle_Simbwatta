import { DataAdapter } from './DataAdapter';
import { doctorMockData, patientDetails } from '../mock/doctor';

const STALE_THRESHOLD_DAYS = 120;

const ensureArray = (value) => (Array.isArray(value) ? value : []);

const getLatestDate = (dateStrings) => {
  let latestDate = null;
  let latestTime = 0;

  dateStrings.forEach((dateString) => {
    if (!dateString) return;
    const time = new Date(dateString).getTime();
    if (Number.isNaN(time)) return;
    if (time >= latestTime) {
      latestTime = time;
      latestDate = dateString;
    }
  });

  return latestDate;
};

const calculateDaysSince = (dateString) => {
  if (!dateString) return 0;
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return 0;
  const today = new Date();
  const normalizedToday = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const normalizedDate = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const diff = normalizedToday - normalizedDate;
  return diff > 0 ? Math.floor(diff / (1000 * 60 * 60 * 24)) : 0;
};

export class DoctorAdapter extends DataAdapter {
  calculateDataAvailability(data) {
    const base = data?.dataAvailability || {};
    const clinical = data?.clinicalTrends || {};
    const patientId = data?.currentPatient?.id;
    const patientSummary = data?.patients?.find((patient) => patient.id === patientId) || {};

    const adasSeries = ensureArray(clinical.adasCog13);
    const faqSeries = ensureArray(clinical.faq);
    const mmseSeries = ensureArray(clinical.mmse);
    const mocaSeries = ensureArray(clinical.moca);

    const hasADAS = base.hasADAS ?? adasSeries.length > 0;
    const hasFAQ = base.hasFAQ ?? faqSeries.length > 0;
    const hasMMSE = base.hasMMSE ?? (mmseSeries.length > 0 || patientSummary.mmse != null);
    const hasMoCA = base.hasMoCA ?? (mocaSeries.length > 0 || patientSummary.moca != null);
    const hasCognitiveTests = base.hasCognitiveTests ?? (hasADAS || hasFAQ || hasMMSE || hasMoCA);

    const biomarkerResults = data?.biomarkerResults || data?.biomarkers || {};
    const hasBiomarkers =
      base.hasBiomarkers ??
      Object.values(biomarkerResults).some((value) => value !== null && value !== undefined);

    const acousticFeatures = ensureArray(data?.acousticFeatures);
    const participationCounts = ensureArray(data?.dailyParticipation?.counts);
    const hasVoiceData = base.hasVoiceData ?? (acousticFeatures.length > 0 || participationCounts.length > 0);

    const reports = data?.mriAnalysis?.reports || {};
    const reportCount = Object.keys(reports).length;
    const visitImageCount = ensureArray(data?.visits).filter((visit) => visit?.imageId).length;
    const mriCount = base.mriCount ?? Math.max(reportCount, visitImageCount);
    const hasMRI = base.hasMRI ?? (mriCount > 0 || Boolean(data?.mriAnalysis?.scanDate));

    const voiceDataDays = base.voiceDataDays ?? (participationCounts.length ? participationCounts.length * 7 : 0);

    const lastUpdateDate =
      base.lastUpdateDate ||
      data?.mriAnalysis?.scanDate ||
      getLatestDate([
        data?.summary?.lastSession,
        data?.currentPatient?.examDate,
        data?.currentPatient?.lastVisit,
        ...ensureArray(data?.visits).map((visit) => visit?.examDate)
      ]);

    const daysSinceLastUpdate = calculateDaysSince(lastUpdateDate);

    const hasFullCognitive = hasMMSE && hasMoCA && hasADAS && hasFAQ;

    let dataCompleteness = 'none';
    if (!hasCognitiveTests && !hasVoiceData && !hasMRI) {
      dataCompleteness = 'none';
    } else if (hasVoiceData && !hasCognitiveTests && !hasMRI) {
      dataCompleteness = 'minimal';
    } else if (hasCognitiveTests && hasVoiceData && hasMRI && hasFullCognitive) {
      dataCompleteness = 'complete';
    } else {
      dataCompleteness = 'partial';
    }

    return {
      hasCognitiveTests,
      hasMMSE,
      hasMoCA,
      hasADAS,
      hasFAQ,
      hasBiomarkers,
      hasMRI,
      mriCount,
      hasVoiceData,
      voiceDataDays,
      dataCompleteness,
      lastUpdateDate: lastUpdateDate || null,
      daysSinceLastUpdate
    };
  }

  calculateUserType(availability) {
    if (availability?.daysSinceLastUpdate > STALE_THRESHOLD_DAYS) return 'inactive';
    if (availability?.dataCompleteness === 'minimal') return 'prevention';
    if (availability?.dataCompleteness === 'partial') return 'suspected';
    if (availability?.dataCompleteness === 'complete') return 'confirmed';
    return 'prevention';
  }

  getMockData(patientId) {
    // 환자별 상세 데이터가 있으면 사용
    const baseData = patientDetails[patientId]
      ? patientDetails[patientId]
      : {
          ...doctorMockData,
          currentPatient: doctorMockData.patients.find((patient) => patient.id === patientId) || doctorMockData.patients[0]
        };

    const dataAvailability = this.calculateDataAvailability(baseData);
    const userType = baseData.userType || this.calculateUserType(dataAvailability);

    return {
      ...baseData,
      dataAvailability,
      userType
    };
  }

  async getApiData(patientId) {
    const response = await fetch(`/api/doctor/patient/${patientId}`);
    return response.json();
  }
}
