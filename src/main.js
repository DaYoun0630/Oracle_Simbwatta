import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";

console.log("VITE ENV CHECK:", import.meta.env.VITE_API_BASE_URL);

const pinia = createPinia();
const app = createApp(App);

app.use(pinia);
app.use(router);

// Auth store 복원
const authStore = useAuthStore();
authStore.hydrate();

app.mount("#app");
