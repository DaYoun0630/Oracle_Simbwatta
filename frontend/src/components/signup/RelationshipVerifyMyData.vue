<script setup lang="ts">
import { computed, ref } from "vue";
import { useSignupStore } from "@/stores/signup";

const signupStore = useSignupStore();
const isLoading = ref(false);

const canStart = computed(() => signupStore.subjectCodeVerified && !isLoading.value);

const statusLabel = computed(() => {
  switch (signupStore.relationshipVerifyStatus) {
    case "idle":
      return "미인증";
    case "pending":
      return "인증 진행 중";
    case "verified":
      return "인증 완료";
    case "failed":
      return "인증 실패";
    case "expired":
      return "만료됨";
    default:
      return "미인증";
  }
});

const statusClass = computed(() => {
  switch (signupStore.relationshipVerifyStatus) {
    case "verified":
      return "badge success";
    case "pending":
      return "badge pending";
    case "failed":
    case "expired":
      return "badge danger";
    default:
      return "badge";
  }
});

const verifiedDetail = computed(() => {
  if (signupStore.relationshipVerifyStatus !== "verified") return "";
  const type = signupStore.relationshipVerifiedType;
  const map: Record<string, string> = {
    parent: "부/모",
    child: "자녀",
    spouse: "배우자",
    sibling: "형제자매",
    other: "기타",
  };
  return `확인된 관계: ${map[type] ?? type}`;
});

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const startVerification = async () => {
  if (!signupStore.subjectCodeVerified || isLoading.value) return;

  try {
    isLoading.value = true;

    if (signupStore.relationshipVerifyStatus !== "idle") {
      signupStore.resetRelationshipVerification();
    }

    // 개발 단계 목 처리: 버튼 클릭 시 즉시 인증 완료 상태로 전환
    signupStore.setRelationshipVerificationResult({
      status: "pending",
      txId: `mock-${Date.now()}`,
      message: "개발 모드: 인증 상태를 확인 중입니다.",
    });
    await sleep(350);

    signupStore.setRelationshipVerificationResult({
      status: "verified",
      verifiedType: signupStore.relationship === "other" ? "other" : signupStore.relationship,
      verifiedAt: new Date().toISOString(),
      message: "개발 모드: 가족관계 인증이 완료되었습니다.",
    });
  } catch (error) {
    signupStore.setRelationshipVerificationResult({
      status: "failed",
      message:
        error instanceof Error
          ? error.message
          : "인증 시작에 실패했습니다. 잠시 후 다시 시도해 주세요.",
    });
  } finally {
    isLoading.value = false;
  }
};

const retry = async () => {
  await startVerification();
};
</script>

<template>
  <div class="verify-card">
    <div class="header">
      <div>
        <p class="title">가족관계 인증</p>
        <p class="desc">공공 마이데이터 인증을 완료하면 가족관계가 자동 확인됩니다.</p>
      </div>

      <span :class="statusClass">{{ statusLabel }}</span>
    </div>

    <div v-if="signupStore.relationshipVerifyStatus === 'verified'" class="verified-box">
      <p class="verified-line">✅ {{ verifiedDetail }}</p>
      <p v-if="signupStore.relationshipVerifiedAt" class="verified-sub">
        인증 일시: {{ signupStore.relationshipVerifiedAt }}
      </p>
      <button type="button" class="secondary" @click="retry" :disabled="isLoading">재인증</button>
    </div>

    <div v-else-if="signupStore.relationshipVerifyStatus === 'pending'" class="pending-box">
      <p class="pending-line">외부 인증 완료 후 자동으로 반영됩니다.</p>
      <p v-if="signupStore.relationshipVerifyMessage" class="pending-sub">
        {{ signupStore.relationshipVerifyMessage }}
      </p>
      <button type="button" class="primary" disabled>인증 진행 중...</button>
    </div>

    <div v-else class="action-box">
      <p v-if="signupStore.relationshipVerifyMessage" class="error-msg">
        {{ signupStore.relationshipVerifyMessage }}
      </p>

      <button type="button" class="primary" @click="startVerification" :disabled="!canStart">
        공공 마이데이터로 인증하기
      </button>

      <p v-if="!signupStore.subjectCodeVerified" class="hint">
        먼저 “회원번호 확인”으로 대상자 연결 유효성을 검증해 주세요.
      </p>

      <button
        v-if="
          signupStore.relationshipVerifyStatus === 'failed' ||
          signupStore.relationshipVerifyStatus === 'expired'
        "
        type="button"
        class="secondary"
        @click="retry"
        :disabled="!canStart"
      >
        다시 시도
      </button>
    </div>
  </div>
</template>

<style scoped>
.verify-card {
  border: 1px solid #dde4ec;
  border-radius: 14px;
  padding: 14px;
  display: grid;
  gap: 12px;
}

.header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}

.title {
  margin: 0;
  font-weight: 800;
  font-size: 18px;
  color: #0f172a;
}

.desc {
  margin: 6px 0 0;
  color: #475569;
  font-size: 14px;
  line-height: 1.4;
}

.badge {
  padding: 6px 10px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 13px;
  background: #e2e8f0;
  color: #1e293b;
}

.badge.success {
  background: #dcfce7;
  color: #166534;
}

.badge.pending {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge.danger {
  background: #fee2e2;
  color: #991b1b;
}

.action-box,
.pending-box,
.verified-box {
  display: grid;
  gap: 10px;
}

.primary,
.secondary {
  min-height: 46px;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 800;
  padding: 0 14px;
}

.primary {
  background: #2563eb;
  color: white;
}

.primary:disabled {
  background: #9cb7f0;
}

.secondary {
  background: #e2e8f0;
  color: #1e293b;
}

.hint {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.4;
}

.error-msg {
  margin: 0;
  color: #b91c1c;
  font-weight: 700;
  font-size: 14px;
}

.verified-line {
  margin: 0;
  font-weight: 800;
  color: #0f172a;
}

.verified-sub,
.pending-sub {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.pending-line {
  margin: 0;
  font-weight: 800;
  color: #1d4ed8;
}
</style>
