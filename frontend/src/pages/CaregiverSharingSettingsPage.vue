<script setup lang="ts">
import SubjectShell from "@/components/shells/SubjectShell.vue";
import { useCaregiverSharingSettings } from "@/composables/useCaregiverSharingSettings";

const sharing = useCaregiverSharingSettings();

const categories = [
  {
    id: "dialog",
    title: "대화 요약 공유",
    description: "보호자에게 대화 요약과 최근 상태 메시지를 공유합니다.",
    model: sharing.dialogSummary,
  },
  {
    id: "anomaly",
    title: "관찰 필요 알림 공유",
    description: "이상 징후 및 관찰 필요 알림을 보호자에게 공유합니다.",
    model: sharing.anomalyAlert,
  },
  {
    id: "medication",
    title: "복약 리마인드 공유",
    description: "복약 예정 시간과 복약 상태를 보호자에게 공유합니다.",
    model: sharing.medicationReminder,
  },
] as const;

const toggleCategory = (id: (typeof categories)[number]["id"]) => {
  const category = categories.find((item) => item.id === id);
  if (!category) return;
  category.model.value = !category.model.value;
};
</script>

<template>
  <SubjectShell title="보호자 정보 공유 범위">
    <div class="sharing-container">
      <section class="intro-card">
        <h2>보호자에게 보여줄 정보 범위를 선택하세요.</h2>
        <p>아래 항목은 대상자 본인이 언제든지 끄고 다시 켤 수 있습니다.</p>
      </section>

      <section
        v-for="category in categories"
        :key="category.id"
        class="sharing-card"
      >
        <div class="card-content">
          <h3>{{ category.title }}</h3>
          <p>{{ category.description }}</p>
        </div>
        <button
          type="button"
          class="toggle"
          :class="{ on: category.model.value }"
          @click="toggleCategory(category.id)"
        >
          <span class="knob"></span>
        </button>
      </section>

      <p class="footer-note" v-if="!sharing.allEnabled">
        일부 항목의 공유가 철회된 상태입니다. 필요할 때 다시 켤 수 있습니다.
      </p>
      <p class="sync-error" v-if="sharing.syncError">{{ sharing.syncError }}</p>
    </div>
  </SubjectShell>
</template>

<style scoped>
.sharing-container {
  display: grid;
  gap: 16px;
  padding: 16px;
}

.intro-card,
.sharing-card {
  background: #f5f6f7;
  border-radius: 20px;
  padding: 18px;
  box-shadow: 12px 12px 24px #cfd6df, -12px -12px 24px #ffffff;
}

.intro-card h2 {
  margin: 0 0 8px;
  font-size: 20px;
}

.intro-card p {
  margin: 0;
  color: #5f5f5f;
  line-height: 1.45;
}

.sharing-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.card-content h3 {
  margin: 0 0 6px;
  font-size: 18px;
  color: #2e2e2e;
}

.card-content p {
  margin: 0;
  color: #666;
  line-height: 1.4;
}

.toggle {
  width: 58px;
  height: 34px;
  border-radius: 999px;
  border: none;
  background: #dfe6ec;
  position: relative;
  flex-shrink: 0;
  cursor: pointer;
  transition: background 0.2s ease;
}

.toggle .knob {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
  transition: transform 0.2s ease;
}

.toggle.on {
  background: #4cb7b7;
}

.toggle.on .knob {
  transform: translateX(24px);
}

.footer-note {
  margin: 2px 2px 0;
  color: #777;
  font-size: 14px;
}

.sync-error {
  margin: 2px 2px 0;
  color: #ff8a80;
  font-size: 13px;
  font-weight: 700;
}
</style>
