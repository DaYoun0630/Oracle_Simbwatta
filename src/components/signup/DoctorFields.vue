<script setup lang="ts">
import { useSignupStore } from "@/stores/signup";

const signupStore = useSignupStore();
</script>

<template>
  <div class="doctor-fields">
    <label class="field">
      <span class="field-label">진료과</span>
      <input v-model="signupStore.department" type="text" placeholder="예: 신경과" />
    </label>

    <label class="field">
      <span class="field-label">면허번호</span>
      <input v-model="signupStore.license_number" type="text" placeholder="면허번호 입력" />
    </label>

    <label class="field">
      <span class="field-label">병원명</span>
      <input v-model="signupStore.hospital" type="text" placeholder="병원명을 입력해 주세요" />
    </label>

    <label class="field">
      <span class="field-label">병원 연락처</span>
      <input
        v-model="signupStore.hospital_number"
        type="tel"
        placeholder="예: 02-1234-5678"
      />
    </label>
  </div>
</template>

<style scoped>
.doctor-fields {
  display: grid;
  gap: 12px;
}

.field {
  display: grid;
  gap: 8px;
}

.field-label {
  font-size: 18px;
  font-weight: 700;
}

input {
  width: 100%;
  min-height: 48px;
  border: 1px solid #cfd8df;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 16px;
}
</style>
