import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # pragma: no cover

try:
    from ..states.dialog_state import DialogState
except ImportError:
    from states.dialog_state import DialogState

if ZoneInfo is not None:
    try:
        KST_TZ = ZoneInfo("Asia/Seoul")
    except Exception:
        KST_TZ = timezone(timedelta(hours=9))
else:
    KST_TZ = timezone(timedelta(hours=9))

MAX_RECENT_TURNS = 12
STOPWORDS = {
    "오늘", "그냥", "이제", "저는", "저도", "진짜", "약간", "너무", "좀", "그거", "이거", "저거",
    "그리고", "근데", "그래서", "근데요", "정말", "아주", "제가", "저희",
}


def _get_kst_timestamp() -> str:
    now = datetime.now(KST_TZ)
    return now.strftime("%Y-%m-%d %H:%M")


def _short_text(value: str, max_len: int = 320) -> str:
    text = " ".join((value or "").split()).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _normalize_turns(turns: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for turn in turns[-MAX_RECENT_TURNS:]:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or "").strip().lower()
        content = _short_text(str(turn.get("content") or ""), max_len=240)
        if role not in ("user", "assistant") or not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized


def _pick_observation_events(
    weekly_profile: dict[str, Any],
    therapy_profile: dict[str, Any],
    state: DialogState,
) -> dict[str, Any]:
    event_candidates = {
        "silence_duration": None,
        "recognition_failed": None,
        "consecutive_failures": None,
        "stt_fail_count": None,
    }

    for key in event_candidates:
        if key in weekly_profile:
            event_candidates[key] = weekly_profile.get(key)
        elif key in therapy_profile:
            event_candidates[key] = therapy_profile.get(key)
        elif hasattr(state, key):
            event_candidates[key] = getattr(state, key)

    return {k: v for k, v in event_candidates.items() if v is not None}


def _extract_topic_candidates(user_text: str, *, limit: int = 3) -> list[str]:
    tokens = re.findall(r"[가-힣A-Za-z]{2,}", user_text or "")
    topics: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        t = token.strip().lower()
        if not t or t in STOPWORDS:
            continue
        if t in seen:
            continue
        seen.add(t)
        topics.append(token)
        if len(topics) >= limit:
            break
    return topics


def _build_followup_question(user_text: str, topics: list[str]) -> str:
    base = _short_text(user_text, max_len=80)
    if topics:
        return f"{topics[0]} 얘기에서 가장 기억에 남는 한 가지만 더 말해주실래요?"
    if base:
        return "방금 말씀하신 내용에서 이어서 한 가지만 더 들려주실래요?"
    return ""


def _build_mini_intervention(state: DialogState, user_text: str, topics: list[str]) -> str:
    if not user_text:
        return ""

    training_type = str(getattr(state, "training_type", "") or "").strip().lower()

    if training_type == "semantic_naming" and topics:
        return f"핵심 단어를 직접 말하기 어렵다면, {topics[0]}의 특징 한 가지를 먼저 말하게 유도"
    if training_type == "semantic_fluency" and topics:
        return f"{topics[0]}와 같은 범주에서 단어 1개만 추가로 떠올리게 유도"
    if training_type == "discourse":
        return "누가/어디서/무슨 일 중 한 요소만 짧게 보강하게 유도"
    if training_type == "wm_discourse":
        return "방금 언급한 정보 중 핵심 하나만 다시 떠올리게 유도"

    return "사용자 발화를 반영한 짧은 확장 질문 1개만 사용"


def update_memory_summary(
    state: DialogState,
    recent_turns: list[dict[str, Any]] | None,
) -> str:
    turns = _normalize_turns(recent_turns or [])
    user_utts = [t["content"] for t in turns if t["role"] == "user"]
    if not user_utts:
        summary = _short_text(getattr(state, "memory_summary", "") or "")
        state.memory_summary = summary
        return summary

    last = _short_text(user_utts[-1], max_len=90)
    topics = _extract_topic_candidates(last)
    topic_part = ", ".join(topics[:2]) if topics else "일상 이야기"
    summary = f"사용자는 최근 {topic_part} 중심으로 대화를 이어가고 있어요. 마지막 핵심은 '{last}'입니다."
    state.memory_summary = summary
    return summary


def build_context(
    model_result: dict,
    state: DialogState,
    weekly_profile: dict | None = None,
    therapy_profile: dict | None = None,
    recent_summary: str = "",
    recent_turns: list[dict[str, Any]] | None = None,
    last_questions: list[str] | None = None,
) -> str:
    del model_result, last_questions
    weekly_profile = weekly_profile or {}
    therapy_profile = therapy_profile or {}
    recent_turns = recent_turns or []

    normalized_turns = _normalize_turns(recent_turns)
    user_last = _short_text(str(getattr(state, "last_user_utterance", "") or ""), max_len=200)
    if not user_last:
        for turn in reversed(normalized_turns):
            if turn["role"] == "user":
                user_last = turn["content"]
                break

    topic_candidates = _extract_topic_candidates(user_last)
    followup_question_candidate = _build_followup_question(user_last, topic_candidates)
    mini_intervention = _build_mini_intervention(state, user_last, topic_candidates)

    memory_summary = _short_text(
        getattr(state, "memory_summary", "") or update_memory_summary(state, normalized_turns),
        max_len=260,
    )

    session_meta = {
        "session_id": therapy_profile.get("session_id") or weekly_profile.get("session_id"),
        "turn_index": state.turn_index,
    }
    session_meta = {k: v for k, v in session_meta.items() if v is not None}

    user_profile = {
        "preferred_topics": therapy_profile.get("preferred_topics"),
        "conversation_style": therapy_profile.get("conversation_style"),
        "difficulty_patterns": therapy_profile.get("difficulty_patterns"),
    }
    user_profile = {k: v for k, v in user_profile.items() if v}

    context = {
        "current_kst_time": _get_kst_timestamp(),
        "session_meta": session_meta,
        "recent_summary": _short_text(recent_summary, max_len=400),
        "memory_summary": memory_summary,
        "recent_turns": normalized_turns,
        "user_last_utterance": user_last,
        "topic_candidates": topic_candidates,
        "followup_question_candidate": followup_question_candidate,
        "mini_intervention": mini_intervention,
        "user_profile": user_profile,
        "observation_events": _pick_observation_events(
            weekly_profile=weekly_profile,
            therapy_profile=therapy_profile,
            state=state,
        ),
    }

    return json.dumps(context, ensure_ascii=False, indent=2)
