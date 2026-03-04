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
      :showMenuButton="showMenu"
      @back="router.back()"
    />

    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  --shell-max-width: 520px;
  --shell-gutter: clamp(14px, 4vw, 20px);
  min-height: 100vh;
  background-color: #f4f7f8;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  width: min(100%, var(--shell-max-width));
  margin: 0 auto;
  padding: 8px var(--shell-gutter) 24px;
  box-sizing: border-box;
}

@media (min-width: 900px) {
  .app-shell {
    --shell-max-width: 760px;
    --shell-gutter: 24px;
  }
}
</style>
