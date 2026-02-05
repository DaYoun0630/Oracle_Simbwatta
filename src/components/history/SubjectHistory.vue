<template>
  <div class="achievement-container">
    <section class="praise-hero">
      <div class="medal-icon">🥇</div>
      <h2>성신 님, 대단해요!<br/>이번 주에 벌써 4번이나<br/>저와 이야기를 나누셨네요.</h2>
      <p class="sub-praise">함께 나눈 대화가 성신 님의 마음을 밝게 해주고 있어요.</p>
    </section>

    <section class="progress-section">
      <h3>이번 주 발자취</h3>
      <div class="calendar-row">
        <div v-for="day in ['월', '화', '수', '목', '금', '토', '일']" :key="day" class="day-card" :class="{ completed: day === '월' || day === '수' }">
          <span class="day-label">{{ day }}</span>
          <div class="check-mark"></div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.achievement-container { display: flex; flex-direction: column; gap: 32px; }
.praise-hero {
  background: #f5f6f7; padding: 40px 24px; border-radius: 32px; text-align: center;
  box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff;
}
.medal-icon { font-size: 48px; margin-bottom: 20px; }
h2 { font-size: 1.375rem; font-weight: 800; line-height: 1.6; color: #2e2e2e; }
.sub-praise { font-size: 1rem; color: #4cb7b7; margin-top: 16px; font-weight: 700; }

.calendar-row { display: flex; justify-content: space-between; gap: 8px; margin-top: 16px; }
.day-card {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 12px;
  padding: 16px 0; background: #f5f6f7; border-radius: 16px;
  box-shadow: 4px 4px 8px #d1d9e6, -4px -4px 8px #ffffff;
}
.day-card.completed { background: #4cb7b7; color: #fff; box-shadow: 0 4px 10px rgba(76, 183, 183, 0.4); }
.check-mark { width: 12px; height: 12px; border-radius: 50%; background: #e0e5ec; }
.completed .check-mark { background: #fff; }
</style>