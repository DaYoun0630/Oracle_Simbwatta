<script setup>
// App.vue는 라우터 출력만 담당
</script>

<template>
  <router-view />
</template>

<style>
/* 전역 리셋 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
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
</style>
