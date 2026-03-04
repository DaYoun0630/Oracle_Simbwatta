import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";

console.log("VITE ENV CHECK:", import.meta.env.VITE_API_BASE_URL);

const pinia = createPinia();
const app = createApp(App);

app.use(pinia);

// 라우터 가드가 실행되기 전에 인증 세션을 복원한다.
const authStore = useAuthStore();
authStore.hydrate();

app.use(router);

app.mount("#app");
