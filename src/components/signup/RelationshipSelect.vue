<script setup lang="ts">
import { useSignupStore } from "@/stores/signup";

const signupStore = useSignupStore();

const relationshipOptions = [
  { label: "딸", value: "daughter" },
  { label: "아들", value: "son" },
  { label: "배우자", value: "spouse" },
  { label: "형제자매", value: "sibling" },
  { label: "기타", value: "other" },
] as const;
</script>

<template>
  <label class="field">
    <span class="field-label">대상자와의 관계</span>
    <select v-model="signupStore.relationship">
      <option value="">관계를 선택해 주세요</option>
      <option v-for="option in relationshipOptions" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
  </label>
</template>

<style scoped>
.field {
  display: grid;
  gap: 8px;
}

.field-label {
  font-size: 18px;
  font-weight: 700;
}

select {
  width: 100%;
  min-height: 48px;
  border: 1px solid #cfd8df;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 16px;
}
</style>
