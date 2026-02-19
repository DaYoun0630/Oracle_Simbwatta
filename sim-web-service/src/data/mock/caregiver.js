export const caregiverMockData = {
  subject: {
    name: '김성신',
    relation: '어머니'
  },

  todayStatus: {
    label: '관찰 필요',
    message: '최근 대화 참여 리듬이 평소와 달라 보여 최근 일정을 함께 살펴보면 좋겠습니다.',
    lastChat: '어제 저녁'
  },

  weeklyTrend: {
    dates: [],
    scores: [78, 74, 80, 68, 82, 76, 84],
    trend: 'up',
    change: '안정 흐름'
  },

  weeklyActivity: {
    completed: 2,
    total: 7,
    comparedToLastWeek: '지난주보다 2회 감소'
  },

  weeklyObservations: [
    {
      dayOffset: 1,
      type: 'pause',
      title: '대화 리듬의 여유',
      detail: '평소보다 응답에 여유를 가지는 구간이 있었습니다.'
    },
    {
      dayOffset: 3,
      type: 'hesitation',
      title: '발화 흐름의 정체',
      detail: '단어 선택에 평소보다 시간이 필요한 구간이 관찰되었습니다.'
    },
    {
      dayOffset: 5,
      type: 'encouragement',
      title: '대화 독려 필요',
      detail: '활동 참여에 더 많은 격려가 도움이 될 수 있습니다.'
    }
  ],

  alerts: [
    {
      id: 'alert-001',
      level: 'alert',
      title: '훈련 참여 확인 필요',
      message: '최근 일주일에 참여 공백이 반복되어 생활 리듬 점검이 권장됩니다.',
    },
  ],

  medicationReminders: [
    {
      time: '오늘 20:00',
      name: '인지기능 보조약'
    }
  ],

  cognitiveScores: []
};
