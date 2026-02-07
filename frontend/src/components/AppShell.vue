<script setup lang="ts">
import { useRouter } from "vue-router";
import AppHeader from "@/components/AppHeader.vue";

const props = defineProps({
  title: { type: String, required: true },
  showBack: { type: Boolean, default: false },
  showMenu: { type: Boolean, default: true },
});

const router = useRouter();
</script>

<template>
  <div class="app-shell">
    <AppHeader
      :title="title"
      :showBackButton="showBack"
      :showMenuButton="false"
      @back="router.back()"
    />

    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background-color: #f5f6f7;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  max-width: 460px;
  margin: 0 auto;
  padding: 16px 20px 20px;
  width: 100%;
  box-sizing: border-box;
}


</style>
