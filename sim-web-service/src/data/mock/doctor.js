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
      hospital: '서울대학교병원'
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
      hospital: '서울대학교병원'
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
    }
  }
};
