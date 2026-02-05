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
  background: #f5f6f7;
  border-radius: 18px;
  padding: 16px;
  box-shadow: 10px 10px 22px rgba(0, 0, 0, 0.06),
    -10px -10px 22px rgba(255, 255, 255, 0.8);
}
.h2 {
  font-size: 18px;
  margin: 0 0 6px;
}
.p {
  font-size: 13px;
  line-height: 1.6;
  color: rgba(46, 46, 46, 0.7);
  word-break: keep-all;
}
</style>
