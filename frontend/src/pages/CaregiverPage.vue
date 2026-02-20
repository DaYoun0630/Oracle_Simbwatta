<script setup lang="ts">
import AppShell from "../components/AppShell.vue";
</script>

<template>
  <AppShell title="보호자 대시보드" :showBack="true">
    <section class="card">
      <h2 class="h2">대상자 상태 요약</h2>
      <p class="p">
        현재는 더미 화면입니다. 추후 DB/모델 연결 시, 최근 7일 변화 알림과 추세 그래프가 표시됩니다.
      </p>
    </section>
  </AppShell>
</template>

<style scoped>
.card {
  position: relative;
  overflow: hidden;
  display: grid;
  gap: 10px;
  background: linear-gradient(145deg, #f9fbfc, #eef3f5);
  border-radius: 24px;
  padding: clamp(18px, 4vw, 28px);
  box-shadow:
    0 14px 28px rgba(126, 140, 154, 0.18),
    0 3px 8px rgba(126, 140, 154, 0.12);
}

.card::before {
  content: "";
  position: absolute;
  right: -40px;
  bottom: -70px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(76, 183, 183, 0.24) 0%, rgba(76, 183, 183, 0) 72%);
  pointer-events: none;
}

.h2 {
  position: relative;
  margin: 0;
  font-size: clamp(1.125rem, 1rem + 0.6vw, 1.5rem);
  font-weight: 900;
  color: #2e2e2e;
}

.p {
  position: relative;
  margin: 0;
  max-width: 52ch;
  font-size: clamp(0.9rem, 0.85rem + 0.2vw, 1rem);
  line-height: 1.65;
  color: #4f5d66;
  word-break: keep-all;
}

@media (max-width: 520px) {
  .card {
    border-radius: 20px;
  }
}
</style>
