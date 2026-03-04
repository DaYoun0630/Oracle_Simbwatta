<script setup lang="ts">
import { computed } from "vue";
import { useSignupStore } from "@/stores/signup";

const signupStore = useSignupStore();
const isOtherSelected = computed(() => signupStore.relationship === "other");

const relationshipOptions = [
  { label: "딸", value: "daughter" },
  { label: "아들", value: "son" },
  { label: "며느리", value: "daughter_in_law" },
  { label: "사위", value: "son_in_law" },
  { label: "배우자", value: "spouse" },
  { label: "형제자매", value: "sibling" },
  { label: "기타", value: "other" },
] as const;

const onRelationshipChange = () => {
  if (!isOtherSelected.value) {
    signupStore.relationship_detail = "";
  }
};
</script>

<template>
  <div class="field-group">
    <label class="field">
      <span class="field-label">대상자와의 관계</span>
      <select v-model="signupStore.relationship" @change="onRelationshipChange">
        <option value="">관계를 선택해 주세요</option>
        <option v-for="option in relationshipOptions" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
    </label>

    <label v-if="isOtherSelected" class="field">
      <span class="field-label">관계 상세 설명</span>
      <input
        v-model="signupStore.relationship_detail"
        type="text"
        placeholder="예: 친척, 지인, 법적 보호자"
      />
    </label>
  </div>
</template>

<style scoped>
.field-group {
  display: grid;
  gap: 10px;
}

.field {
  display: grid;
  gap: 8px;
}

.field-label {
  font-size: 18px;
  font-weight: 700;
}

select,
input {
  width: 100%;
  min-height: 48px;
  border: 1px solid #cfd8df;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 16px;
}
</style>
