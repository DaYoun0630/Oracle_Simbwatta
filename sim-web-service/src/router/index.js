import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes = [
  {
    path: "/",
    name: "landing",
    component: () => import("../pages/LandingPage.vue")
  },
  {
    path: "/select-role",
    name: "select-role",
    component: () => import("../pages/RoleSelectPage.vue")
  },
  {
    path: "/login",
    name: "login",
    component: () => import("../pages/LoginPage.vue")
  },
  {
    path: "/signup",
    redirect: { name: "signup-role" }
  },
  {
    path: "/signup/role",
    name: "signup-role",
    component: () => import("../views/SignupRoleView.vue")
  },
  {
    path: "/signup/form",
    name: "signup-form",
    component: () => import("../views/SignupFormView.vue")
  },
  {
    path: "/signup/relationship-verify-return",
    name: "signup-relationship-verify-return",
    component: () => import("../pages/signup/SignupRelationshipVerifyReturn.vue")
  },
  {
    path: "/signup/terms",
    name: "signup-terms",
    component: () => import("../views/SignupTermsView.vue")
  },
  {
    path: "/signup/complete",
    name: "signup-complete",
    component: () => import("../views/SignupCompleteView.vue")
  },
  {
    path: "/home",
    name: "home",
    component: () => import("../pages/HomePage.vue"),
    // 인증 필요 및 전 역할 접근 가능
    meta: { requiresAuth: true, roles: ["subject", "caregiver", "doctor"] }
  },
  {
    path: "/doctor/patients",
    name: "doctor-patients",
    component: () => import("../pages/DoctorPatientsPage.vue"),
    // 의료진 전용 환자 현황
    meta: { requiresAuth: true, roles: ["doctor"] }
  },
  {
    path: "/doctor/patient/:patientId",
    name: "doctor-patient",
    component: () => import("../pages/HomePage.vue"),
    // 의료진 전용 환자 상세 (임시로 홈 페이지를 사용)
    meta: { requiresAuth: true, roles: ["doctor"] }
  },
  {
    path: "/doctor/report/:patientId",
    name: "doctor-report",
    component: () => import("../pages/HistoryPage.vue"),
    // 의료진 전용 환자 리포트 (임시로 히스토리 페이지를 사용)
    meta: { requiresAuth: true, roles: ["doctor"] }
  },
  {
    path: "/chat",
    name: "chat",
    component: () => import("../pages/ChatPage.vue"),
    // 피보호자 전용 접근
    meta: { requiresAuth: true, roles: ["subject"] }
  },
  {
    path: "/session-result",
    name: "session-result",
    component: () => import("../pages/SessionResultPage.vue"),
    meta: { requiresAuth: true, roles: ["subject"] }
  },
  {
    path: "/history",
    name: "history",
    component: () => import("../pages/HistoryPage.vue"),
    meta: { requiresAuth: true, roles: ["subject", "caregiver", "doctor"] }
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("../pages/SettingsPage.vue"),
    meta: { requiresAuth: true, roles: ["subject", "caregiver", "doctor"] }
  },
  {
    path: "/doctor-settings",
    name: "doctor-settings",
    component: () => import("../pages/DoctorSettings.vue"),
    // 의료진 전용 설정
    meta: { requiresAuth: true, roles: ["doctor"] }
  },
  {
    path: "/doctor-settings/profile",
    name: "doctor-profile-edit",
    component: () => import("../pages/DoctorProfileEdit.vue"),
    meta: { requiresAuth: true, roles: ["doctor"] }
  },
  {
    path: "/doctor-settings/notifications",
    name: "doctor-notification",
    component: () => import("../pages/DoctorNotification.vue"),
    meta: { requiresAuth: true, roles: ["doctor"] }
  },
  {
    path: "/settings/personal-info",
    name: "personal-info",
    component: () => import("../pages/PersonalInfoPage.vue"),
    meta: { requiresAuth: true, roles: ["subject", "caregiver", "doctor"] }
  },
  {
    path: "/settings/caregiver-sharing",
    name: "caregiver-sharing-settings",
    component: () => import("../pages/CaregiverSharingSettingsPage.vue"),
    meta: { requiresAuth: true, roles: ["subject"] }
  },
  {
    path: "/settings/notifications",
    name: "notification-settings",
    component: () => import("../pages/NotificationSettingsPage.vue"),
    // 보호자 및 의료진 전용
    meta: { requiresAuth: true, roles: ["caregiver", "doctor"] }
  },
  {
    path: "/settings/caregiver-management",
    name: "caregiver-management",
    component: () => import("../pages/CaregiverManagementPage.vue"),
    // 보호자 전용 관리 페이지
    meta: { requiresAuth: true, roles: ["caregiver"] }
  },
  {
    path: "/profile",
    redirect: "/settings"
  },
  {
    // 정의되지 않은 모든 경로는 랜딩 페이지로 리다이렉트
    path: "/:pathMatch(.*)*",
    redirect: "/"
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 전역 네비게이션 가드: 페이지 접근 권한 검증
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  const role = authStore.role;

  // 비인증 사용자 허용 페이지 목록
  const publicPages = [
    "landing",
    "select-role",
    "login",
    "signup-role",
    "signup-form",
    "signup-relationship-verify-return",
    "signup-terms",
    "signup-complete",
  ];
  const isPublicPage = publicPages.includes(to.name);

  // 이미 로그인된 사용자가 로그인/역할선택 페이지 접근 시 홈으로 이동
  if (role && isPublicPage && to.name !== "landing") {
    return next({ name: "home" });
  }

  // 퍼블릭 페이지는 즉시 통과
  if (isPublicPage) {
    return next();
  }

  // 인증이 필요한 페이지인데 세션(role)이 없는 경우 로그인 유도
  if (to.meta.requiresAuth && !role) {
    return next({ name: "login" });
  }

  // 접근 허용 역할 확인 및 인가 제어
  if (to.meta.roles && !to.meta.roles.includes(role)) {
    return next({ name: "home" });
  }

  next();
});

export default router;
