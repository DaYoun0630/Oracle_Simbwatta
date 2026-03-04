<script setup lang="ts">
import { useSignupStore } from "@/stores/signup";

const signupStore = useSignupStore();

const genderOptions = [
  { label: "남성", value: "male" },
  { label: "여성", value: "female" },
] as const;
</script>

<template>
  <fieldset class="field-group">
    <legend>성별</legend>
    <div class="option-row">
      <label v-for="option in genderOptions" :key="option.value" class="radio-card">
        <input v-model="signupStore.gender" type="radio" :value="option.value" />
        <span>{{ option.label }}</span>
      </label>
    </div>
  </fieldset>
</template>

<style scoped>
.field-group {
  border: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}

legend {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 2px;
}

.option-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.radio-card {
  min-width: 120px;
  padding: 12px 14px;
  border: 1px solid #d5dce2;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  cursor: pointer;
  font-size: 16px;
}

input[type="radio"] {
  width: 18px;
  height: 18px;
}
</style>
