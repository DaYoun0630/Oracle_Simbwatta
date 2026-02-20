<script setup lang="ts">
import { useRouter } from "vue-router";
const router = useRouter();
const startChat = () => router.push("/chat");
</script>

<template>
  <div class="role-content">
    <section class="main-card" @click="startChat">
      <p class="tag">오늘의 대화</p>
      <h2>성신 님,<br/>저와 이야기 나누실래요?</h2>
      <div class="mic-orb">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="white">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
      </div>
      <p class="guide">눌러서 대화 시작</p>
    </section>

    <section class="memory-card" @click="router.push('/history')">
      <div class="text">
        <h3>우리가 나눈 이야기</h3>
        <p>지난 기록 확인하기</p>
      </div>
      <div class="icon-box">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="#4cb7b7">
          <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/>
        </svg>
      </div>
    </section>
  </div>
</template>

<style scoped>
.role-content { display: flex; flex-direction: column; gap: 24px; }
.main-card { 
  background: #f5f6f7; padding: 48px 24px; border-radius: 32px; text-align: center;
  box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff; cursor: pointer;
}
.tag { font-size: 13px; font-weight: 800; color: #4cb7b7; margin-bottom: 16px; }
h2 { font-size: 22px; font-weight: 800; color: #2e2e2e; line-height: 1.5; margin-bottom: 32px; }
.mic-orb { 
  width: 90px; height: 90px; background: #4cb7b7; border-radius: 50%; margin: 0 auto 16px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 10px 20px rgba(76, 183, 183, 0.4);
}
.guide { font-size: 14px; font-weight: 700; color: #888; }
.memory-card { 
  display: flex; justify-content: space-between; align-items: center; padding: 24px;
  background: #f5f6f7; border-radius: 24px; box-shadow: 8px 8px 16px #d1d9e6, -8px -8px 16px #ffffff;
}
.memory-card h3 { font-size: 16px; font-weight: 800; margin-bottom: 4px; }
.memory-card p { font-size: 13px; color: #888; }
.icon-box { width: 48px; height: 48px; background: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 4px 4px 8px #d1d9e6; }
</style>