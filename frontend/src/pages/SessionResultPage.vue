<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppShell from "../components/AppShell.vue";
import { useMockSession } from "../composables/useMockSession";

const route = useRoute();
const router = useRouter();

const { getSessionResult } = useMockSession();

const sessionId = computed(() => {
  const raw = route.query.sessionId;
  return typeof raw === "string" ? raw : undefined;
});

const result = computed(() => getSessionResult(sessionId.value));

const riskLabel = computed(() => {
  if (result.value.riskLevel === "high") return "주의";
  if (result.value.riskLevel === "mid") return "관찰";
  return "안정";
});

const goHome = () => {
  router.push({ name: "home" });
};

const goHistory = () => {
  router.push({ name: "history" });
};
</script>

<template>
  <AppShell title="대화 요약" :showBack="true">
    <section class="card">
      <h2 class="h2">오늘 대화는 여기까지예요</h2>
      <p class="sub">
        아래 내용은 예시 데이터이며, 추후 모델/DB 연결 시 실제 분석 결과로 대체됩니다.
      </p>

      <div class="risk">
        <div class="risk-top">
          <span class="risk-title">현재 상태</span>
          <span class="risk-badge">{{ riskLabel }}</span>
        </div>

        <div class="risk-score">
          <div class="score-label">위험도 점수</div>
          <div class="score-value">{{ result.riskScore }}</div>
        </div>

        <div class="chips">
          <span v-for="k in result.keywords" :key="k" class="chip">{{ k }}</span>
        </div>
      </div>

      <div class="meta">
        <div class="meta-item">
          <div class="meta-label">사용자 발화</div>
          <div class="meta-value">{{ result.userUtteranceCount }}회</div>
        </div>

        <div class="meta-item">
          <div class="meta-label">도우미 발화</div>
          <div class="meta-value">{{ result.aiUtteranceCount }}회</div>
        </div>
      </div>

      <div class="notes">
        <div class="notes-title">요약 메모</div>
        <ul class="notes-list">
          <li v-for="n in result.notes" :key="n">{{ n }}</li>
        </ul>
      </div>
    </section>

    <section class="cta-row">
      <button class="cta primary" type="button" @click="goHome">메인으로</button>
      <button class="cta ghost" type="button" @click="goHistory">기록 보기</button>
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

.sub {
  font-size: 13px;
  color: rgba(46, 46, 46, 0.7);
  line-height: 1.6;
  word-break: keep-all;
  margin: 0 0 14px;
}

.risk {
  background: #fff;
  border-radius: 14px;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.risk-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.risk-title {
  font-weight: 800;
  font-size: 13px;
}

.risk-badge {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(76, 183, 183, 0.12);
}

.risk-score {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.score-label {
  font-size: 12px;
  color: rgba(46, 46, 46, 0.6);
}

.score-value {
  font-size: 24px;
  font-weight: 900;
}

.chips {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  background: #f5f6f7;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.meta {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.meta-item {
  background: #fff;
  border-radius: 14px;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.meta-label {
  font-size: 12px;
  color: rgba(46, 46, 46, 0.6);
}

.meta-value {
  font-size: 16px;
  font-weight: 800;
  margin-top: 4px;
}

.notes {
  margin-top: 12px;
  background: #fff;
  border-radius: 14px;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.notes-title {
  font-size: 13px;
  font-weight: 800;
}

.notes-list {
  margin: 8px 0 0;
  padding-left: 18px;
  color: rgba(46, 46, 46, 0.78);
  line-height: 1.6;
}

.cta-row {
  margin-top: 14px;
  display: grid;
  gap: 10px;
}

.cta {
  padding: 14px;
  border-radius: 16px;
  font-weight: 900;
  line-height: 1;
}

.cta.primary {
  background: #4cb7b7;
  color: #fff;
  border: none;
}

.cta.ghost {
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
}
</style>
