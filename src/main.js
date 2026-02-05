import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";

const pinia = createPinia();
const app = createApp(App);

app.use(pinia);
app.use(router);

// Auth store 복원
const authStore = useAuthStore();
authStore.hydrate();

app.mount("#app");