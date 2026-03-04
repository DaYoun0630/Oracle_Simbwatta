<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useSignupStore } from "@/stores/signup";

const route = useRoute();
const router = useRouter();
const signupStore = useSignupStore();

const message = ref("인증 결과 확인 중...");
const isError = ref(false);

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

onMounted(async () => {
  const txIdRaw = route.query.txId;
  const txId = Array.isArray(txIdRaw) ? String(txIdRaw[0] ?? "") : String(txIdRaw ?? "");

  const resolvedTxId = txId || `mock-${Date.now()}`;
  if (!txId) {
    isError.value = true;
    message.value = "개발 모드: txId 없이 접근되어 mock 인증으로 처리합니다.";
    await sleep(700);
  } else {
    message.value = "개발 모드: 인증 완료 처리 중입니다...";
    await sleep(700);
  }

  signupStore.setRelationshipVerificationResult({
    status: "verified",
    txId: resolvedTxId,
    verifiedAt: new Date().toISOString(),
    message: "개발 모드: 가족관계 인증이 완료되었습니다.",
  });
  router.replace({ name: "signup-form" });
});
</script>

<template>
  <main class="return-page">
    <section class="card">
      <h1>가족관계 인증</h1>
      <p :class="['msg', isError && 'err']">{{ message }}</p>
      <p class="sub">잠시만 기다려 주세요. 자동으로 이전 화면으로 이동합니다.</p>
    </section>
  </main>
</template>

<style scoped>
.return-page {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: 18px;
  background: #eef3f7;
}

.card {
  width: min(520px, 100%);
  background: white;
  border-radius: 18px;
  padding: 22px;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 10px;
}

h1 {
  margin: 0;
  font-size: 22px;
  color: #0f172a;
}

.msg {
  margin: 0;
  font-weight: 800;
  color: #1d4ed8;
}

.msg.err {
  color: #b91c1c;
}

.sub {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
</style>
