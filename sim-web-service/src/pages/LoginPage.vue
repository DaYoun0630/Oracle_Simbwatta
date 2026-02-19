<!--
  LoginPage.vue
  ─────────────────────────────────────────────────
  뉴모피즘(Neumorphism) 이중 양각 로그인 페이지

  레이어 구조:
    login-viewport  → 전체 화면을 채우며 콘텐츠를 정중앙에 배치
    └ login-frame   → 바깥 양각(볼록) 프레임 — "액자" 역할
       └ login-card → 안쪽 음각(오목) 패널 — 실제 입력 UI
-->

<script setup>
/* ── Vue 라우터 & 상태관리 임포트 ── */
import { useRoute, useRouter } from "vue-router";
import { computed, ref } from "vue";
import { useAuthStore } from "../stores/auth";

/* ── 라우터·스토어 인스턴스 ── */
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

/* ── 역할(role)별 한글 레이블 매핑 ── */
const roleLabelMap = {
  subject: "대상자",
  caregiver: "보호자",
  doctor: "의료진",
};

/**
 * 쿼리스트링에서 role 파라미터를 추출한다.
 * 배열로 올 수 있으므로 첫 번째 값만 사용하며,
 * 값이 없으면 기본값 "subject"를 반환한다.
 */
const selectedRole = computed(() => {
  const roleParam = Array.isArray(route.query.role)
    ? route.query.role[0]
    : route.query.role;
  return roleParam || "subject";
});

/** 현재 역할에 해당하는 한글 레이블 (예: "대상자") */
const roleLabel = computed(() => roleLabelMap[selectedRole.value] ?? "대상자");

/* ── 폼 상태 (양방향 바인딩) ── */
const username = ref("");   // 아이디 입력값
const password = ref("");   // 비밀번호 입력값
const error = ref("");      // 유효성 검증 에러 메시지

/**
 * 로그인 처리 핸들러
 * 1) 빈 입력 검증
 * 2) 스토어에 역할 저장
 * 3) 홈 화면으로 이동
 */
const handleLogin = () => {
  /* 빈 값 체크 — 아이디·비밀번호 모두 입력해야 통과 */
  if (!username.value || !password.value) {
    error.value = "아이디와 비밀번호를 입력해주세요";
    return;
  }

  /* 역할 정규화는 store 내부에서 자동 처리 */
  authStore.setRole(selectedRole.value);

  /* 인증 완료 후 홈으로 라우팅 */
  router.push({ name: "home" });
};
</script>

<template>
  <!--
    login-viewport
    전체 뷰포트를 차지하며, 내부 콘텐츠를 수직·수평 정중앙에 배치한다.
    배경색은 뉴모피즘 기본색(#f5f6f7)으로 통일.
  -->
  <div class="login-viewport">

    <!--
      login-frame (바깥 양각 프레임)
      ─ 큰 box-shadow로 "튀어나온 액자" 느낌을 만든다.
      ─ 그림자 크기를 안쪽 카드보다 크게 설정하여 레이어 깊이를 표현.
    -->
    <div class="login-frame">

      <!--
        뒤로가기 버튼
        ─ 뉴모피즘 스타일의 원형 버튼
        ─ 이전 페이지(랜딩)로 돌아가는 역할
      -->
      <button class="back-btn" @click="router.back()" aria-label="뒤로가기">
        <svg width="24" height="24" viewBox="0 0 24 24">
          <path
            d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"
            fill="#888"
          />
        </svg>
      </button>

      <!--
        login-card (안쪽 음각 패널)
        ─ inset shadow로 "부드럽게 파인 패널" 느낌을 준다.
        ─ 실제 사용자 입력 UI가 이 안에 위치한다.
      -->
      <div class="login-card">

        <!-- 페이지 타이틀: 역할에 따라 "대상자 로그인" 등으로 변경 -->
        <h1 class="login-title">{{ roleLabel }} 로그인</h1>

        <!--
          입력 영역
          ─ 각 입력창은 pill(캡슐) 형태 + inset shadow로
            "안으로 파인" 뉴모피즘 텍스트필드를 구현한다.
        -->
        <div class="input-area">

          <!-- 아이디 입력 — placeholder를 흐리게 유지하여 뉴모피즘 느낌 보존 -->
          <input
            v-model="username"
            type="text"
            placeholder="아이디(이메일)"
            class="login-input"
          />

          <!-- 비밀번호 입력 -->
          <input
            v-model="password"
            type="password"
            placeholder="비밀번호"
            class="login-input"
          />

          <!-- 유효성 에러 메시지 — error 값이 있을 때만 표시 -->
          <p v-if="error" class="error-text">{{ error }}</p>
        </div>

        <!--
          로그인 버튼 (CTA)
          ─ 뉴모피즘 양각 금지: CTA는 항상 "떠 있는" 느낌이어야 한다.
          ─ 틸(teal) 계열 배경 + 아래쪽 드롭 쉐도우로 부양감 표현.
        -->
        <button class="login-button" @click="handleLogin">
          로그인 완료
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/*
  ╔══════════════════════════════════════════════════╗
  ║  1. login-viewport — 전체 화면 중앙 정렬 래퍼   ║
  ╚══════════════════════════════════════════════════╝
  - 100svh(small viewport height)로 모바일 주소창 변화에 대응
  - flexbox 중앙 정렬로 프레임을 화면 한가운데 배치
  - 뉴모피즘 기본 배경색 #f5f6f7 통일
*/
.login-viewport {
  min-height: 100svh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f6f7;
  padding: 20px;
}

/*
  ╔══════════════════════════════════════════════════╗
  ║  2. login-frame — 바깥 양각(볼록) 프레임        ║
  ╚══════════════════════════════════════════════════╝
  - 이중 양각의 "겉 프레임" 역할 (액자처럼 감싸는 레이어)
  - 큰 box-shadow(18px)로 볼록하게 튀어나온 느낌
  - 밝은면(왼쪽 위: #ffffff) + 어두운면(오른쪽 아래: #cfd6df)
  - border-radius를 카드보다 크게(32px) 잡아 부드러운 곡률
  - position:relative → 뒤로가기 버튼의 absolute 기준
*/
.login-frame {
  position: relative;
  width: 100%;
  max-width: 420px;
  padding: 20px;
  border-radius: 32px;
  background: #fbfcfe;
  box-shadow:
    18px 18px 36px rgba(214, 221, 232, 0.72),
    -18px -18px 36px #ffffff;
}

/*
  ╔══════════════════════════════════════════════════╗
  ║  3. back-btn — 뒤로가기 버튼                     ║
  ╚══════════════════════════════════════════════════╝
  - 프레임 왼쪽 상단에 절대 배치
  - 작은 뉴모피즘 양각 원형 버튼
  - 누르면(active) 살짝 눌리는 인터랙션
*/
.back-btn {
  position: absolute;
  top: -16px;
  left: -16px;
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 50%;
  background: #f5f6f7;
  box-shadow:
    6px 6px 12px rgba(207, 214, 223, 0.9),
    -6px -6px 12px #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 1;
}

/* 뒤로가기 버튼 누름 상태 — 살짝 안으로 들어가는 느낌 */
.back-btn:active {
  box-shadow:
    inset 4px 4px 8px rgba(209, 217, 230, 0.7),
    inset -4px -4px 8px #ffffff;
}

/*
  ╔══════════════════════════════════════════════════╗
  ║  4. login-card — 안쪽 음각(오목) 패널            ║
  ╚══════════════════════════════════════════════════╝
  - 이중 양각의 "안 카드" 역할
  - inset shadow로 부드럽게 파인 패널 느낌
  - 배경을 프레임보다 살짝 밝게(#f8f9fa) 하여 깊이감 강조
  - border-radius를 프레임보다 작게(28px) 하여 시각적 계층 구분
*/
.login-card {
  padding: 32px 28px;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/*
  ╔══════════════════════════════════════════════════╗
  ║  5. login-title — 페이지 제목                    ║
  ╚══════════════════════════════════════════════════╝
  - 역할 이름 + "로그인" 텍스트 표시
  - 굵은 폰트로 시인성 확보
  - 중앙 정렬하여 카드 내 균형감 유지
*/
.login-title {
  font-size: 22px;
  font-weight: 800;
  color: #2e2e2e;
  text-align: center;
  margin: 0;
}

/*
  ╔══════════════════════════════════════════════════╗
  ║  6. input-area — 입력창 그룹 컨테이너            ║
  ╚══════════════════════════════════════════════════╝
  - 아이디·비밀번호 입력창을 세로로 나열
  - gap으로 일정 간격 유지
*/
.input-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/*
  ╔══════════════════════════════════════════════════╗
  ║  7. login-input — 뉴모피즘 입력창                ║
  ╚══════════════════════════════════════════════════╝
  - pill(캡슐) 형태: border-radius 999px
  - inset shadow로 "안으로 파인" 느낌 구현
  - border를 제거하여 뉴모피즘 스타일 유지
    (테두리가 있으면 뉴모피즘이 깨짐)
  - 배경색을 카드보다 어둡게(#eef1f3) 하여
    입력 영역임을 시각적으로 구분
*/
.login-input {
  height: 52px;
  border-radius: 999px;
  border: none;
  padding: 0 20px;
  background: #f4f7fa;
  box-shadow:
    inset 4px 4px 8px rgba(209, 217, 230, 0.9),
    inset -4px -4px 8px #ffffff;
  font-size: 16px;
  color: #2e2e2e;
  outline: none;
  transition: box-shadow 0.2s ease;
}

/*
  placeholder 스타일
  ─ 흐린 색상으로 유지하여 뉴모피즘의 부드러운 인상 보존
  ─ 너무 진하면 입력값과 구분이 어려워짐
*/
.login-input::placeholder {
  color: #aab2bd;
  font-weight: 500;
}

/*
  포커스 상태
  ─ 그림자를 약간 더 깊게 하여 "눌림" 피드백 제공
  ─ border 대신 shadow로 포커스를 표현하여 뉴모피즘 유지
*/
.login-input:focus {
  box-shadow:
    inset 5px 5px 10px rgba(209, 217, 230, 1),
    inset -5px -5px 10px #ffffff;
}

/*
  ╔══════════════════════════════════════════════════╗
  ║  8. error-text — 유효성 검증 에러 메시지          ║
  ╚══════════════════════════════════════════════════╝
  - 부드러운 빨간색(#ff8a80)으로 경고 표시
  - 굵은 폰트로 눈에 잘 띄게
*/
.error-text {
  color: #ff8a80;
  font-size: 14px;
  margin: 4px 0 0;
  padding-left: 20px;
  font-weight: 700;
}

/*
  ╔══════════════════════════════════════════════════╗
  ║  9. login-button — CTA 로그인 버튼               ║
  ╚══════════════════════════════════════════════════╝
  - 뉴모피즘 양각(볼록) 금지 — CTA는 항상 "떠 있는" 느낌이어야 함
  - 틸(teal) 계열 단색 배경(#4cb7b7)
  - 아래 방향 드롭 쉐도우로 부양감(떠 있는 느낌) 표현
  - pill(캡슐) 형태로 입력창과 시각적 통일
  - active 상태에서 살짝 아래로 이동하여 누름 피드백 제공
*/
.login-button {
  margin-top: 4px;
  height: 56px;
  border-radius: 999px;
  border: none;
  background: #4cb7b7;
  color: #ffffff;
  font-size: 18px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 12px 22px rgba(76, 183, 183, 0.35);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

/* 버튼 누름 상태 — 살짝 내려가면서 그림자 줄어듦 */
.login-button:active {
  transform: translateY(3px);
  box-shadow: 0 6px 12px rgba(76, 183, 183, 0.25);
}
</style>

