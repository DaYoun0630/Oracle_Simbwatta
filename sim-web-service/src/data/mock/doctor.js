const riskLevels = ['low', 'mid', 'high'];
const diagnoses = ['CN', 'MCI'];
const hospitals = ['서울대학교병원', '삼성서울병원', '세브란스병원'];

const randomPick = (arr) => arr[Math.floor(Math.random() * arr.length)];

const randomInt = (min, max) =>
  Math.floor(Math.random() * (max - min + 1)) + min;

const generateMockPatients = (count = 50) => {
  return Array.from({ length: count }, (_, i) => {
    const idx = String(i + 100).padStart(3, '0');
    const risk = randomPick(riskLevels);

    return {
      id: `${idx}_S_${randomInt(1000, 9999)}`,
      rid: `RID-${randomInt(1000, 9999)}`,
      name: `환자${idx}`,
      age: randomInt(60, 85),
      gender: Math.random() > 0.5 ? 'F' : 'M',
      lastVisit: `2026-02-${randomInt(1, 28).toString().padStart(2, '0')}`,
      examDate: `2026-02-${randomInt(1, 28).toString().padStart(2, '0')}`,
      latestViscode2: 'm12',
      riskLevel: risk,
      cdrSB: risk === 'low' ? 0.5 : risk === 'mid' ? 2.0 : 4.5,
      mmse:
        risk === 'low'
          ? randomInt(28, 30)
          : risk === 'mid'
          ? randomInt(23, 27)
          : randomInt(15, 22),
      moca:
        risk === 'low'
          ? randomInt(24, 27)
          : risk === 'mid'
          ? randomInt(18, 23)
          : randomInt(10, 17),
      participationRate: randomInt(55, 100),
      diagnosis: randomPick(diagnoses),
      hospital: randomPick(hospitals)
    };
  });
};

export const doctorMockData = {
  patients: [
    {
      id: '029_S_6726',
      rid: 'RID-6726',
      name: '김성신',
      age: 68,
      gender: 'F',
      lastVisit: '2026-02-02',
      examDate: '2026-02-02',
      latestViscode2: 'm12',
      riskLevel: 'low',
      cdrSB: 0.5,
      mmse: 30,
      moca: 25,
      participationRate: 95,
      diagnosis: 'MCI',
      hospital: '서울대학교병원',
      userType: 'confirmed'
    },
    {
      id: '126_S_6724',
      rid: 'RID-6724',
      name: '이영희',
      age: 72,
      gender: 'F',
      lastVisit: '2026-02-01',
      examDate: '2026-02-01',
      latestViscode2: 'm12',
      riskLevel: 'mid',
      cdrSB: 2.0,
      mmse: 26,
      moca: 21,
      participationRate: 71,
      diagnosis: 'MCI',
      hospital: '서울대학교병원',
      userType: 'confirmed'
    },
    // 예방형 사용자 (CN - 음성 데이터만)
    {
      id: '001_S_0001',
      rid: 'RID-0001',
      name: '박예방',
      age: 62,
      gender: 'M',
      lastVisit: '2026-02-04',
      examDate: '2026-02-04',
      latestViscode2: null,
      riskLevel: 'low',
      cdrSB: 0,
      mmse: null,
      moca: null,
      participationRate: 85,
      diagnosis: 'CN',
      hospital: '삼성서울병원',
      userType: 'prevention'
    },
    // MCI 의심 사용자 (부분 데이터)
    {
      id: '002_S_0002',
      rid: 'RID-0002',
      name: '최의심',
      age: 70,
      gender: 'F',
      lastVisit: '2026-01-15',
      examDate: '2026-01-15',
      latestViscode2: 'm00',
      riskLevel: 'mid',
      cdrSB: 1.0,
      mmse: 27,
      moca: 23,
      participationRate: 60,
      diagnosis: 'MCI',
      hospital: '세브란스병원',
      userType: 'suspected'
    },
    // 비활성 사용자 (오래된 데이터)
    {
      id: '003_S_0003',
      rid: 'RID-0003',
      name: '정비활',
      age: 75,
      gender: 'M',
      lastVisit: '2025-08-10',
      examDate: '2025-08-10',
      latestViscode2: 'm12',
      riskLevel: 'high',
      cdrSB: 3.5,
      mmse: 22,
      moca: 18,
      participationRate: 45,
      diagnosis: 'MCI',
      hospital: '서울대학교병원',
      userType: 'inactive'
    },
    ...generateMockPatients(80)
  ],

  currentPatient: {
    id: '029_S_6726',
    rid: 'RID-6726',
    name: '김성신',
    age: 68,
    gender: 'F',
    diagnosis: 'MCI',
    hospital: '서울대학교병원'
  }
};

// MRI 분석 기여도 데이터 생성 함수
const generateRegionContributions = () => {
  const regions = [
    { region: '해마 위축', basePercentage: 35.5 },
    { region: '측두엽 위축', basePercentage: 28.3 },
    { region: '전체 뇌 부피 감소', basePercentage: 22.1 },
    { region: '백질 병변', basePercentage: 14.1 }
  ];

  return regions.map(item => {
    const percentage = item.basePercentage + (Math.random() * 10 - 5); // 약간의 변동
    const normalizedPercentage = Math.max(5, Math.min(50, percentage)); // 5-50% 범위로 제한
    let severity;
    if (normalizedPercentage >= 30) severity = 'high';
    else if (normalizedPercentage >= 15) severity = 'medium';
    else severity = 'low';

    return {
      region: item.region,
      percentage: parseFloat(normalizedPercentage.toFixed(1)),
      severity
    };
  });
};

export const patientDetails = {
  '029_S_6726': {
    ...doctorMockData,
    currentPatient: {
      id: '029_S_6726',
      rid: 'RID-6726',
      name: '김성신',
      age: 68,
      gender: 'F',
      diagnosis: 'MCI',
      hospital: '서울대학교병원'
    },
    // 사용자 유형 및 데이터 가용성
    userType: 'confirmed',
    dataAvailability: {
      hasCognitiveTests: true,
      hasMMSE: true,
      hasMoCA: true,
      hasADAS: true,
      hasFAQ: true,
      hasBiomarkers: true,
      hasMRI: true,
      mriCount: 3,
      hasVoiceData: true,
      voiceDataDays: 28,
      dataCompleteness: 'complete',
      lastUpdateDate: '2026-02-01',
      daysSinceLastUpdate: 4
    },
    // 임상 추세 데이터
    clinicalTrends: {
      adasCog13: [18, 20, 22, 25, 28],
      faq: [5, 6, 8, 10, 12],
      labels: ['M00', 'M06', 'M12', 'M18', 'M24']
    },
    // 바이오마커 결과
    biomarkerResults: {
      abeta42: 420,
      abeta40: 980,
      ptau: 28,
      tau: 340,
      ratioAb42Ab40: 0.43,
      ratioPtauAb42: 0.067,
      ratioPtauTau: 0.082
    },
    // 방문 기록
    visits: [
      { examDate: '2025-02-01', viscode2: 'M00', imageId: 'img_029_m00' },
      { examDate: '2025-08-01', viscode2: 'M06', imageId: 'img_029_m06' },
      { examDate: '2026-02-01', viscode2: 'M12', imageId: 'img_029_m12' }
    ],
    // 음성 특징 데이터
    acousticFeatures: [
      { label: '발화 속도', current: '3.2 음절/초', baseline: '3.5 음절/초', trend: [3.5, 3.4, 3.3, 3.2, 3.2] },
      { label: '멈춤 빈도', current: '12회/분', baseline: '8회/분', trend: [8, 9, 10, 11, 12] },
      { label: '음성 강도', current: '65 dB', baseline: '70 dB', trend: [70, 68, 67, 66, 65] }
    ],
    // 일상 대화 참여
    dailyParticipation: {
      labels: ['1주', '2주', '3주', '4주'],
      counts: [7, 6, 5, 6]
    },
    // MRI 분석 결과 (확장된 구조)
    mriAnalysis: {
      // 기존 이미지 데이터
      reports: {
        'img_029_m00': {
          imagePaths: {
            axial: '/static/mri/029_S_6726/m00_axial.png',
            sagittal: '/static/mri/029_S_6726/m00_sagittal.png',
            coronal: '/static/mri/029_S_6726/m00_coronal.png'
          }
        },
        'img_029_m06': {
          imagePaths: {
            axial: '/static/mri/029_S_6726/m06_axial.png',
            sagittal: '/static/mri/029_S_6726/m06_sagittal.png',
            coronal: '/static/mri/029_S_6726/m06_coronal.png'
          }
        },
        'img_029_m12': {
          imagePaths: {
            axial: '/static/mri/029_S_6726/m12_axial.png',
            sagittal: '/static/mri/029_S_6726/m12_sagittal.png',
            coronal: '/static/mri/029_S_6726/m12_coronal.png'
          }
        }
      },
      scanDate: '2026-02-01',
      latestImageId: 'img_029_m12',
      // AI 분석 결과 (새로 추가)
      aiAnalysis: {
        originalImage: '/static/mri/029_S_6726/original.png',
        attentionMap: '/static/mri/029_S_6726/attention_map.png',
        regionContributions: [
          { region: '해마 위축', percentage: 35.5, severity: 'high' },
          { region: '측두엽 위축', percentage: 28.3, severity: 'medium' },
          { region: '전체 뇌 부피 감소', percentage: 22.1, severity: 'medium' },
          { region: '백질 병변', percentage: 14.1, severity: 'low' }
        ]
      },
      // 의사 진단 기록 (기존 진단이 있는 경우)
      doctorDiagnosis: null
    }
  },

  '126_S_6724': {
    patients: doctorMockData.patients,
    currentPatient: {
      id: '126_S_6724',
      rid: 'RID-6724',
      name: '이영희',
      age: 72,
      gender: 'F',
      diagnosis: 'MCI',
      hospital: '서울대학교병원'
    },
    summary: {
      overallRisk: 'mid',
      riskScore: 42.8,
      lastSession: '2026-02-01',
      totalSessions: 18,
      averageParticipation: '71%'
    },
    // 임상 추세 데이터
    clinicalTrends: {
      adasCog13: [22, 25, 28, 32, 35],
      faq: [8, 10, 12, 14, 16],
      labels: ['M00', 'M06', 'M12', 'M18', 'M24']
    },
    // 바이오마커 결과
    biomarkerResults: {
      abeta42: 520,
      abeta40: 1020,
      ptau: 22,
      tau: 300,
      ratioAb42Ab40: 0.51,
      ratioPtauAb42: 0.042,
      ratioPtauTau: 0.073
    },
    // 방문 기록
    visits: [
      { examDate: '2025-02-01', viscode2: 'M00', imageId: 'img_126_m00' },
      { examDate: '2025-08-01', viscode2: 'M06', imageId: 'img_126_m06' },
      { examDate: '2026-02-01', viscode2: 'M12', imageId: 'img_126_m12' }
    ],
    // 음성 특징 데이터
    acousticFeatures: [
      { label: '발화 속도', current: '2.8 음절/초', baseline: '3.2 음절/초', trend: [3.2, 3.1, 3.0, 2.9, 2.8] },
      { label: '멈춤 빈도', current: '15회/분', baseline: '10회/분', trend: [10, 11, 13, 14, 15] },
      { label: '음성 강도', current: '62 dB', baseline: '68 dB', trend: [68, 66, 65, 63, 62] }
    ],
    // 일상 대화 참여
    dailyParticipation: {
      labels: ['1주', '2주', '3주', '4주'],
      counts: [5, 4, 4, 5]
    },
    // MRI 분석 결과 (확장된 구조)
    mriAnalysis: {
      reports: {
        'img_126_m00': {
          imagePaths: {
            axial: '/static/mri/126_S_6724/m00_axial.png',
            sagittal: '/static/mri/126_S_6724/m00_sagittal.png',
            coronal: '/static/mri/126_S_6724/m00_coronal.png'
          }
        },
        'img_126_m06': {
          imagePaths: {
            axial: '/static/mri/126_S_6724/m06_axial.png',
            sagittal: '/static/mri/126_S_6724/m06_sagittal.png',
            coronal: '/static/mri/126_S_6724/m06_coronal.png'
          }
        },
        'img_126_m12': {
          imagePaths: {
            axial: '/static/mri/126_S_6724/m12_axial.png',
            sagittal: '/static/mri/126_S_6724/m12_sagittal.png',
            coronal: '/static/mri/126_S_6724/m12_coronal.png'
          }
        }
      },
      scanDate: '2026-02-01',
      latestImageId: 'img_126_m12',
      // AI 분석 결과
      aiAnalysis: {
        originalImage: '/static/mri/126_S_6724/original.png',
        attentionMap: '/static/mri/126_S_6724/attention_map.png',
        regionContributions: [
          { region: '해마 위축', percentage: 42.3, severity: 'high' },
          { region: '측두엽 위축', percentage: 31.5, severity: 'high' },
          { region: '전체 뇌 부피 감소', percentage: 18.7, severity: 'medium' },
          { region: '백질 병변', percentage: 7.5, severity: 'low' }
        ]
      },
      doctorDiagnosis: null
    },
    // 사용자 유형 및 데이터 가용성
    userType: 'confirmed',
    dataAvailability: {
      hasCognitiveTests: true,
      hasMMSE: true,
      hasMoCA: true,
      hasADAS: true,
      hasFAQ: true,
      hasBiomarkers: true,
      hasMRI: true,
      mriCount: 3,
      hasVoiceData: true,
      voiceDataDays: 28,
      dataCompleteness: 'complete',
      lastUpdateDate: '2026-02-01',
      daysSinceLastUpdate: 4
    }
  },

  // === 예방형 사용자 (CN - 음성 데이터만) ===
  '001_S_0001': {
    patients: doctorMockData.patients,
    currentPatient: {
      id: '001_S_0001',
      rid: 'RID-0001',
      name: '박예방',
      age: 62,
      gender: 'M',
      diagnosis: 'CN',
      hospital: '삼성서울병원'
    },
    // 임상 추세 데이터 (없음)
    clinicalTrends: {
      adasCog13: [],
      faq: [],
      labels: []
    },
    // 방문 기록 (없음)
    visits: [],
    // 음성 특징 데이터 (있음 - 유일한 데이터)
    acousticFeatures: [
      { label: '발화 속도', current: '4.1 음절/초', baseline: '4.0 음절/초', trend: [4.0, 4.1, 4.0, 4.1, 4.1] },
      { label: '멈춤 빈도', current: '5회/분', baseline: '5회/분', trend: [5, 5, 6, 5, 5] },
      { label: '음성 강도', current: '72 dB', baseline: '70 dB', trend: [70, 71, 72, 72, 72] }
    ],
    // 일상 대화 참여
    dailyParticipation: {
      labels: ['1주', '2주', '3주', '4주'],
      counts: [5, 6, 7, 6]
    },
    // MRI 분석 결과 (없음)
    mriAnalysis: null,
    // 사용자 유형 및 데이터 가용성
    userType: 'prevention',
    dataAvailability: {
      hasCognitiveTests: false,
      hasMMSE: false,
      hasMoCA: false,
      hasADAS: false,
      hasFAQ: false,
      hasBiomarkers: false,
      hasMRI: false,
      mriCount: 0,
      hasVoiceData: true,
      voiceDataDays: 28,
      dataCompleteness: 'minimal',
      lastUpdateDate: '2026-02-04',
      daysSinceLastUpdate: 1
    }
  },

  // === MCI 의심 사용자 (부분 데이터 - MMSE/MoCA만) ===
  '002_S_0002': {
    patients: doctorMockData.patients,
    currentPatient: {
      id: '002_S_0002',
      rid: 'RID-0002',
      name: '최의심',
      age: 70,
      gender: 'F',
      diagnosis: 'MCI',
      hospital: '세브란스병원'
    },
    // 임상 추세 데이터 (부분 - ADAS/FAQ 없음)
    clinicalTrends: {
      adasCog13: [],
      faq: [],
      labels: ['M00'],
      mmse: [27],
      moca: [23]
    },
    // 방문 기록 (1회만)
    visits: [
      { examDate: '2026-01-15', viscode2: 'M00', imageId: null }
    ],
    // 음성 특징 데이터
    acousticFeatures: [
      { label: '발화 속도', current: '3.5 음절/초', baseline: '3.8 음절/초', trend: [3.8, 3.7, 3.6, 3.5, 3.5] },
      { label: '멈춤 빈도', current: '9회/분', baseline: '7회/분', trend: [7, 7, 8, 8, 9] },
      { label: '음성 강도', current: '68 dB', baseline: '70 dB', trend: [70, 69, 69, 68, 68] }
    ],
    // 일상 대화 참여
    dailyParticipation: {
      labels: ['1주', '2주', '3주', '4주'],
      counts: [4, 3, 4, 3]
    },
    // MRI 분석 결과 (없음)
    mriAnalysis: null,
    // 사용자 유형 및 데이터 가용성
    userType: 'suspected',
    dataAvailability: {
      hasCognitiveTests: true,
      hasMMSE: true,
      hasMoCA: true,
      hasADAS: false,
      hasFAQ: false,
      hasBiomarkers: false,
      hasMRI: false,
      mriCount: 0,
      hasVoiceData: true,
      voiceDataDays: 28,
      dataCompleteness: 'partial',
      lastUpdateDate: '2026-01-15',
      daysSinceLastUpdate: 21
    }
  },

  // === 비활성 사용자 (오래된 데이터) ===
  '003_S_0003': {
    patients: doctorMockData.patients,
    currentPatient: {
      id: '003_S_0003',
      rid: 'RID-0003',
      name: '정비활',
      age: 75,
      gender: 'M',
      diagnosis: 'MCI',
      hospital: '서울대학교병원'
    },
    // 임상 추세 데이터 (있지만 오래됨)
    clinicalTrends: {
      adasCog13: [25, 28, 32],
      faq: [10, 12, 15],
      labels: ['M00', 'M06', 'M12']
    },
    // 바이오마커 결과 (오래됨)
    biomarkerResults: {
      abeta42: 360,
      abeta40: 900,
      ptau: 31,
      tau: 380,
      ratioAb42Ab40: 0.4,
      ratioPtauAb42: 0.086,
      ratioPtauTau: 0.082
    },
    // 방문 기록
    visits: [
      { examDate: '2024-08-10', viscode2: 'M00', imageId: 'img_003_m00' },
      { examDate: '2025-02-10', viscode2: 'M06', imageId: 'img_003_m06' },
      { examDate: '2025-08-10', viscode2: 'M12', imageId: 'img_003_m12' }
    ],
    // 음성 특징 데이터 (오래됨)
    acousticFeatures: [
      { label: '발화 속도', current: '2.5 음절/초', baseline: '3.2 음절/초', trend: [3.2, 3.0, 2.8, 2.6, 2.5] },
      { label: '멈춤 빈도', current: '18회/분', baseline: '10회/분', trend: [10, 12, 14, 16, 18] },
      { label: '음성 강도', current: '58 dB', baseline: '68 dB', trend: [68, 65, 62, 60, 58] }
    ],
    // 일상 대화 참여 (마지막 참여 오래됨)
    dailyParticipation: {
      labels: ['1주', '2주', '3주', '4주'],
      counts: [2, 1, 0, 0]
    },
    // MRI 분석 결과
    mriAnalysis: {
      reports: {
        'img_003_m00': {
          imagePaths: {
            axial: '/static/mri/003_S_0003/m00_axial.png',
            sagittal: '/static/mri/003_S_0003/m00_sagittal.png',
            coronal: '/static/mri/003_S_0003/m00_coronal.png'
          }
        },
        'img_003_m06': {
          imagePaths: {
            axial: '/static/mri/003_S_0003/m06_axial.png',
            sagittal: '/static/mri/003_S_0003/m06_sagittal.png',
            coronal: '/static/mri/003_S_0003/m06_coronal.png'
          }
        },
        'img_003_m12': {
          imagePaths: {
            axial: '/static/mri/003_S_0003/m12_axial.png',
            sagittal: '/static/mri/003_S_0003/m12_sagittal.png',
            coronal: '/static/mri/003_S_0003/m12_coronal.png'
          }
        }
      },
      scanDate: '2025-08-10',
      latestImageId: 'img_003_m12',
      aiAnalysis: {
        originalImage: '/static/mri/003_S_0003/original.png',
        attentionMap: '/static/mri/003_S_0003/attention_map.png',
        regionContributions: [
          { region: '해마 위축', percentage: 48.2, severity: 'high' },
          { region: '측두엽 위축', percentage: 35.8, severity: 'high' },
          { region: '전체 뇌 부피 감소', percentage: 12.5, severity: 'low' },
          { region: '백질 병변', percentage: 3.5, severity: 'low' }
        ]
      },
      doctorDiagnosis: {
        diagnoses: ['hippocampus_atrophy', 'temporal_lobe_atrophy'],
        additionalNotes: '환자 추적 관찰 필요. 6개월 후 재검 권장.',
        timestamp: '2025-08-15T10:30:00.000Z',
        doctorId: 'doctor_001'
      }
    },
    // 사용자 유형 및 데이터 가용성
    userType: 'inactive',
    dataAvailability: {
      hasCognitiveTests: true,
      hasMMSE: true,
      hasMoCA: true,
      hasADAS: true,
      hasFAQ: true,
      hasBiomarkers: true,
      hasMRI: true,
      mriCount: 3,
      hasVoiceData: true,
      voiceDataDays: 60,
      dataCompleteness: 'complete',
      lastUpdateDate: '2025-08-10',
      daysSinceLastUpdate: 179
    }
  }
};
