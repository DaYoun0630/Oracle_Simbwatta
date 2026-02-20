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
.achievement-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

.praise-hero {
  background: #f4f7f8;
  padding: 28px 20px;
  border-radius: 24px;
  text-align: center;
  border: 1px solid rgba(46, 46, 46, 0.04);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
}

.medal-icon {
  font-size: 40px;
  margin-bottom: 14px;
}

h2 {
  font-size: 1.25rem;
  font-weight: 900;
  line-height: 1.55;
  color: #2e2e2e;
}

.sub-praise {
  font-size: 0.95rem;
  color: #4cb7b7;
  margin-top: 12px;
  font-weight: 700;
}

.progress-section {
  background: #f4f7f8;
  border-radius: 24px;
  border: 1px solid rgba(46, 46, 46, 0.04);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  padding: 18px 16px;
}

.progress-section h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 900;
  color: #2e2e2e;
}

.calendar-row {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
}

.day-card {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 9px;
  padding: 12px 0;
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(46, 46, 46, 0.06);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}

.day-label {
  font-size: 0.85rem;
  font-weight: 800;
}

.day-card.completed {
  background: rgba(76, 183, 183, 0.95);
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 3px 8px rgba(76, 183, 183, 0.35);
}

.check-mark {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ccd4d8;
}

.completed .check-mark {
  background: #ffffff;
}

@media (max-width: 560px) {
  .praise-hero {
    padding: 22px 16px;
  }

  .medal-icon {
    font-size: 34px;
    margin-bottom: 10px;
  }

  h2 {
    font-size: 1.05rem;
  }

  .calendar-row {
    gap: 6px;
  }

  .day-card {
    padding: 10px 0;
    gap: 7px;
  }

  .day-label {
    font-size: 0.78rem;
  }
}
</style>
