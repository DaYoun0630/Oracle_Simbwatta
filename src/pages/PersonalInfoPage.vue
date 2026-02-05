<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import CaregiverShell from '@/components/shells/CaregiverShell.vue';
import DoctorShell from '@/components/shells/DoctorShell.vue';
import SubjectShell from '@/components/shells/SubjectShell.vue';

const authStore = useAuthStore();
const router = useRouter();
const role = computed(() => authStore.role);

const userName = ref(authStore.userName || '');
const phoneNumber = ref(localStorage.getItem('user-phone') || '');
const avatarUrl = ref(localStorage.getItem('user-avatar') || null);

const handleAvatarUpload = (event) => {
  const file = event.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      avatarUrl.value = e.target.result;
    };
    reader.readAsDataURL(file);
  }
};

const triggerAvatarUpload = () => {
  document.getElementById('avatar-input').click();
};

const saveChanges = () => {
  if (userName.value) {
    authStore.setUser({
      ...authStore.user,
      name: userName.value
    });
  }
  if (phoneNumber.value) {
    localStorage.setItem('user-phone', phoneNumber.value);
  }
  if (avatarUrl.value) {
    localStorage.setItem('user-avatar', avatarUrl.value);
  }
  router.back();
};
</script>

<template>
  <component
    :is="role === 'caregiver' ? CaregiverShell : role === 'doctor' ? DoctorShell : SubjectShell"
    title="개인정보 수정"
  >
    <div class="personal-info-container">
      <section class="avatar-section">
        <div
          class="avatar-preview"
          :style="avatarUrl ? { backgroundImage: `url(${avatarUrl})`, backgroundSize: 'cover' } : {}"
          @click="triggerAvatarUpload"
        >
          <div class="avatar-overlay">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
              <circle cx="12" cy="13" r="4"/>
            </svg>
          </div>
        </div>
        <input
          id="avatar-input"
          type="file"
          accept="image/*"
          @change="handleAvatarUpload"
          hidden
        />
        <p class="avatar-hint">사진을 터치하여 변경</p>
      </section>

      <section class="form-section">
        <div class="input-group">
          <label for="userName">이름</label>
          <input
            id="userName"
            v-model="userName"
            type="text"
            placeholder="이름을 입력하세요"
            class="neumorphic-input"
          />
        </div>

        <div class="input-group">
          <label for="phoneNumber">연락처</label>
          <input
            id="phoneNumber"
            v-model="phoneNumber"
            type="tel"
            placeholder="010-0000-0000"
            class="neumorphic-input"
          />
        </div>
      </section>

      <button class="save-button" @click="saveChanges">
        저장하기
      </button>
    </div>
  </component>
</template>

<style scoped>
.personal-info-container {
  display: flex;
  flex-direction: column;
  gap: 32px;
  padding-bottom: 24px;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.avatar-preview {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: #e0e5ec;
  box-shadow: 14px 14px 28px #cfd6df, -14px -14px 28px #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: transform 0.2s;
}

.avatar-preview:active {
  transform: scale(0.98);
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-preview:hover .avatar-overlay {
  opacity: 1;
}

.avatar-hint {
  font-size: 16px;
  font-weight: 600;
  color: #777;
  margin: 0;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.input-group label {
  font-size: 18px;
  font-weight: 800;
  color: #2e2e2e;
  padding-left: 4px;
}

.neumorphic-input {
  width: 100%;
  padding: 20px 24px;
  border: none;
  border-radius: 20px;
  background: #f5f6f7;
  box-shadow: inset 4px 4px 10px #d1d9e6, inset -4px -4px 10px #ffffff;
  font-size: 22px;
  font-weight: 700;
  color: #2e2e2e;
  outline: none;
  transition: box-shadow 0.2s;
  box-sizing: border-box;
}

.neumorphic-input:focus {
  box-shadow: inset 4px 4px 10px #d1d9e6,
              inset -4px -4px 10px #ffffff,
              0 0 0 3px rgba(76, 183, 183, 0.3);
}

.neumorphic-input::placeholder {
  color: #aaa;
  font-weight: 600;
}

.save-button {
  width: 100%;
  padding: 20px;
  border: none;
  border-radius: 24px;
  background: #4cb7b7;
  box-shadow: 0 10px 20px rgba(76, 183, 183, 0.3);
  font-size: 20px;
  font-weight: 800;
  color: #ffffff;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 16px;
}

.save-button:active {
  transform: scale(0.98);
  box-shadow: 0 5px 10px rgba(76, 183, 183, 0.2);
}
</style>
