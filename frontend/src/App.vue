<script setup>
// App.vue는 라우터 출력과 전역 데모 고지 배너를 담당
</script>

<template>
  <div class="app-shell">
    <router-view />
    <div class="demo-notice" role="note" aria-label="데모 안내">
      데모 안내: 본 서비스는 연구/시연용이며 의료진의 진단을 대체하지 않습니다. 배포 환경에는 합성/비식별 테스트 데이터만 사용합니다.
    </div>
  </div>
</template>

<style>
/* 전역 리셋 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  word-break: keep-all;
  overflow-wrap: normal;
}

html,
body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  background-color: #f4f7f8;
  overflow-x: hidden;
}

#app {
  margin: 0;
  padding: 0;
  width: 100%;
  min-height: 100vh;
  background-color: #f4f7f8;
}

.app-shell {
  min-height: 100vh;
  padding-bottom: 44px;
}

.demo-notice {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border-top: 1px solid #d8b36a;
  background: #fff7e8;
  color: #5a430f;
  font-size: 12px;
  line-height: 1.35;
  text-align: center;
}

@media (max-width: 640px) {
  .app-shell {
    padding-bottom: 56px;
  }

  .demo-notice {
    height: auto;
    min-height: 56px;
    padding: 8px 10px;
    font-size: 11px;
  }
}
</style>
