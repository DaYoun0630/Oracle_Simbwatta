<script setup>
import { computed } from 'vue';
import { useAuthStore } from '@/stores/auth';
import SubjectShell from '@/components/shells/SubjectShell.vue';
import VoiceOrb from '@/components/VoiceOrb.vue';
import { useVoiceSession } from '@/composables/useVoiceSession';

const authStore = useAuthStore();
const userName = computed(() => authStore.userName);

const { state, isListening, startListening } = useVoiceSession();

const statusConfig = computed(() => {
  switch (state.value) {
    case 'idle':
      return {
        text: '안녕하세요!',
        subText: '여기를 눌러주세요',
        bgColor: '#f5f6f7'
      };
    case 'listening':
      return {
        text: '잘 듣고 있어요',
        subText: '편하게 말씀하세요',
        bgColor: '#eef4f4'
      };
    case 'processing':
      return {
        text: '잠시만 기다려주세요',
        subText: '',
        bgColor: '#f0f2f5'
      };
    case 'speaking':
      return {
        text: '대답하고 있어요',
        subText: '',
        bgColor: '#f5f6f7'
      };
    default:
      return {
        text: '안녕하세요!',
        subText: '여기를 눌러주세요',
        bgColor: '#f5f6f7'
      };
  }
});
</script>

<template>
  <SubjectShell :showHomeButton="state !== 'idle'">
    <div class="chat-wrapper" :style="{ backgroundColor: statusConfig.bgColor }">
      <div class="status-area">
        <h1 class="status-text">{{ statusConfig.text }}</h1>
        <p v-if="statusConfig.subText" class="sub-text">{{ statusConfig.subText }}</p>
      </div>

      <div class="orb-area">
        <div v-if="state === 'idle'" class="idle-button" @click="startListening">
          <div class="mic-circle">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="white">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          </div>
        </div>

        <div v-else class="orb-container">
          <VoiceOrb :state="state" />
        </div>
      </div>

      <div class="footer-area">
        <div v-if="state !== 'idle'" class="status-indicator">
          <span class="pulse-dot"></span>
        </div>
      </div>
    </div>
  </SubjectShell>
</template>

<style scoped>
.chat-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  flex: 1;
  min-height: 0;
  padding: 24px 20px 60px;
  transition: background-color 0.5s ease;
}

.status-area {
  text-align: center;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
}

.status-text {
  font-size: 2rem;
  font-weight: 900;
  color: #2e2e2e;
  margin: 0;
  line-height: 1.3;
}

.sub-text {
  font-size: 1.25rem;
  font-weight: 600;
  color: #4cb7b7;
  margin: 0;
}

.orb-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.idle-button {
  cursor: pointer;
  transition: transform 0.2s;
}

.idle-button:active {
  transform: scale(0.95);
}

.mic-circle {
  width: 180px;
  height: 180px;
  background: #4cb7b7;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 20px 40px rgba(76, 183, 183, 0.4);
  animation: gentle-pulse 3s ease-in-out infinite;
}

@keyframes gentle-pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 20px 40px rgba(76, 183, 183, 0.4);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 25px 50px rgba(76, 183, 183, 0.5);
  }
}

.orb-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.footer-area {
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pulse-dot {
  width: 12px;
  height: 12px;
  background: #4cb7b7;
  border-radius: 50%;
  animation: pulse-fade 2s ease-in-out infinite;
}

@keyframes pulse-fade {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.3;
    transform: scale(0.8);
  }
}
</style>
