export const caregiverMockData = {
  subject: {
    name: '김성신',
    relation: '어머니'
  },

  todayStatus: {
    label: '안정',
    message: '오늘 대화 리듬이 부드럽고 안정적으로 유지되었습니다.',
    lastChat: '2시간 전'
  },

  weeklyTrend: {
    dates: [],
    scores: [78, 74, 80, 68, 82, 76, 84],
    trend: 'up',
    change: '안정 흐름'
  },

  weeklyActivity: {
    completed: 5,
    total: 7,
    comparedToLastWeek: '지난주보다 1회 더 진행'
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

  alerts: [],

  cognitiveScores: []
};