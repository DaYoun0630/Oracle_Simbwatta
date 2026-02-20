# =============================================================================
# main.py - LLM 湲곕컲 ?몄??덈젴 梨쀫큸 ?쒕쾭 (FastAPI)
#
# 二쇱슂 湲곕뒫:
#   - MCI(寃쎈룄 ?몄??μ븷) ?섏옄 ????몄??덈젴 ?몄뀡 愿由?
#   - ?띿뒪???뚯꽦 ???泥섎━ (STT/TTS ?곕룞)
#   - ?됰룞 怨꾩빟(BehaviorContract) 湲곕컲 ?묐떟 ?꾨왂 寃곗젙
#   - ?먭레(stimulus) ?앹꽦 諛?以묐났 諛⑹?
#   - ?몄뀡蹂?濡쒓렇/?몃젅?댁뒪 湲곕줉
#   - OpenAI Realtime API ?대씪?댁뼵???쒗겕由?諛쒓툒
# =============================================================================

import asyncio
import base64
import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
import uuid
import wave
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

try:
    from .services.llm_service import generate_stimulus, run_llm, run_llm_summary
    from .services.speech_service import (
        ensure_wav_16k_mono_pcm16,
        inspect_wav,
        synthesize_speech,
        transcribe_audio,
    )
    from .states.dialog_state import DialogState
    from .states.state_transition import decide_next_state
except ImportError:
    from services.llm_service import generate_stimulus, run_llm, run_llm_summary
    from services.speech_service import (
        ensure_wav_16k_mono_pcm16,
        inspect_wav,
        synthesize_speech,
        transcribe_audio,
    )
    from states.dialog_state import DialogState
    from states.state_transition import decide_next_state

# =============================================================================
# ??珥덇린??諛?寃쎈줈/?꾩뿭 ?곸닔 ?ㅼ젙
# =============================================================================
app = FastAPI()

APP_DIR = Path(__file__).resolve().parent
TRANSCRIPT_PATH = APP_DIR / "transcript.txt"
CONVERSATION_LOG_PATH = APP_DIR / "conversation_log.txt"
TEMP_AUDIO_DIR = APP_DIR / "tmp_audio"
SESSION_LOG_DIR = APP_DIR / "session_logs"
SESSION_TRACE_DIR = APP_DIR / "session_traces"
AUDIO_SAVE_DIR = APP_DIR / "saved_audio"

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(APP_DIR / "storage")))
AUDIO_WAV_DIR = STORAGE_DIR / "audio_wav"
TEXT_DIR = STORAGE_DIR / "text"
META_DIR = STORAGE_DIR / "meta"
AUDIO_TTS_DIR = STORAGE_DIR / "audio_tts"
LOGS_DIR = STORAGE_DIR / "logs"
SESSION_ARCHIVE_DIR = STORAGE_DIR / "session_archive"

# ?꾩뿭 ?몃찓紐⑤━ ??μ냼
SESSION_CONTEXT_STORE: dict[str, "SessionContext"] = {}
SESSION_RUNTIME_STORE: dict[str, "RuntimeSessionState"] = {}
USER_POLICY_CACHE: dict[str, dict[str, Any]] | None = None

# ???愿由??곸닔
MAX_SUMMARY_CHARS = 8000
RECENT_MESSAGES_LIMIT = 14
SUMMARY_UPDATE_INTERVAL = 6
SILENCE_TURN_INCREMENT_SEC = 4
MAX_USED_STIMULI = 30
MAX_USED_PHRASES = 30
MAX_EVENT_ID_HISTORY = 200
STIMULUS_DUPLICATE_RETRY_LIMIT = 2
STIMULUS_KEYWORD_JACCARD_THRESHOLD = 0.7
STIMULUS_PROMPT_NGRAM_THRESHOLD = 0.82
MAX_TRACE_READ_LIMIT = 1000
DEFAULT_DIALOG_SUMMARY = "인사로 대화를 시작하고 안부를 나눔"

# OpenAI Realtime API ?ㅼ젙
REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-4o-realtime-preview")
REALTIME_SECRET_TTL_SEC = int(os.getenv("REALTIME_SECRET_TTL_SEC", "600"))
REALTIME_AUDIO_SAMPLE_RATE = int(os.getenv("REALTIME_AUDIO_SAMPLE_RATE", "24000"))
REALTIME_TRANSCRIBE_MODEL = os.getenv("REALTIME_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
REALTIME_VAD_MODE = os.getenv("REALTIME_VAD_MODE", "server_vad").strip().lower()
REALTIME_VAD_THRESHOLD = float(os.getenv("REALTIME_VAD_THRESHOLD", "0.65"))
REALTIME_SILENCE_DURATION_MS = int(os.getenv("REALTIME_SILENCE_DURATION_MS", "900"))
REALTIME_IDLE_TIMEOUT_MS = int(os.getenv("REALTIME_IDLE_TIMEOUT_MS", "9000"))
REALTIME_MAX_TURN_DURATION_SEC = int(os.getenv("REALTIME_MAX_TURN_DURATION_SEC", "18"))

if ZoneInfo is not None:
    try:
        KST_TZ = ZoneInfo("Asia/Seoul")
    except Exception:
        KST_TZ = timezone(timedelta(hours=9))
else:
    KST_TZ = timezone(timedelta(hours=9))

# =============================================================================
# ?몄뀡 ?щ’, ???紐⑤뱶, ?덈젴 ?좏삎, 諛쒗솕 ?좏겙 留ㅽ븨
# =============================================================================
SESSION_SLOT_LABEL = {
    "morning": "morning",
    "lunch": "lunch",
    "evening": "evening",
}

NEXT_SESSION_SLOT = {
    "morning": "lunch",
    "lunch": "evening",
    "evening": "morning",
}

CONVERSATION_MODE_ALIASES = {
    "daily": "daily",
    "일상": "daily",
    "therapy": "therapy",
    "치료": "therapy",
    "상담": "therapy",
    "mixed": "mixed",
    "both": "mixed",
    "hybrid": "mixed",
    "일상+치료": "mixed",
}

TRAINING_TYPE_SET = {"semantic_naming", "semantic_fluency", "discourse", "wm_discourse"}

TRAINING_TYPE_TO_MODULE = {
    "semantic_naming": "naming",
    "semantic_fluency": "fluency",
    "discourse": "discourse",
    "wm_discourse": "working_memory",
}

MODULE_TO_TRAINING_TYPE = {
    "naming": "semantic_naming",
    "fluency": "semantic_fluency",
    "discourse": "discourse",
    "working_memory": "wm_discourse",
}

MODULE_SEQUENCE = ("naming", "fluency", "discourse", "working_memory")

# ???곸뿭蹂??몄? ?덈젴 留ㅽ븨 (?붾? 湲곕컲, ?ㅼ젣 紐⑤뜽 寃곌낵濡?諛붾줈 ?泥?媛??
BRAIN_REGION_PROFILE_MAP: dict[str, dict[str, Any]] = {
    "hippocampus_atrophy": {
        "label": "해마 위축",
        "cognitive_targets": ["episodic_memory", "recent_memory", "sequence_memory", "spatial_memory"],
        "task_families": ["recent_event_recall", "timeline_recall", "daily_routine_sequence", "place_memory"],
        "module_weights": {"discourse": 3, "working_memory": 2, "naming": 1, "fluency": 1},
    },
    "temporal_atrophy": {
        "label": "측두엽 위축",
        "cognitive_targets": ["semantic_memory", "language_comprehension", "word_retrieval", "auditory_processing"],
        "task_families": ["semantic_naming", "category_fluency", "meaning_explanation", "synonym_antonym"],
        "module_weights": {"naming": 3, "fluency": 3, "discourse": 1, "working_memory": 1},
    },
    "prefrontal_cortex_reduction": {
        "label": "전전두엽 피질 감소",
        "cognitive_targets": ["executive_function", "planning", "decision_making", "working_memory"],
        "task_families": ["step_planning", "priority_sorting", "problem_solving", "rule_based_recall"],
        "module_weights": {"working_memory": 3, "discourse": 3, "fluency": 1, "naming": 1},
    },
    "white_matter_lesions": {
        "label": "백질 병변",
        "cognitive_targets": ["processing_speed", "attention", "response_latency", "cognitive_efficiency"],
        "task_families": ["quick_association", "simple_response", "yes_no_reaction", "short_calculation"],
        "module_weights": {"working_memory": 3, "fluency": 2, "naming": 1, "discourse": 1},
    },
    "frontal_atrophy": {
        "label": "전두엽 위축",
        "cognitive_targets": ["emotion_regulation", "language_generation", "behavior_control", "action_description"],
        "task_families": ["emotion_expression", "sentence_generation", "preference_reasoning", "action_explanation"],
        "module_weights": {"discourse": 3, "fluency": 2, "working_memory": 2, "naming": 1},
    },
    "parietal_atrophy": {
        "label": "두정엽 위축",
        "cognitive_targets": ["visuospatial_attention", "direction_orientation", "numeracy", "spatial_relation"],
        "task_families": ["location_relation", "direction_description", "simple_numeracy", "distance_estimation"],
        "module_weights": {"working_memory": 3, "discourse": 2, "naming": 1, "fluency": 1},
    },
}

BRAIN_REGION_ALIAS_MAP: dict[str, str] = {
    "해마": "hippocampus_atrophy",
    "hippocampus": "hippocampus_atrophy",
    "측두": "temporal_atrophy",
    "측두엽": "temporal_atrophy",
    "temporal": "temporal_atrophy",
    "전전두": "prefrontal_cortex_reduction",
    "전전두엽": "prefrontal_cortex_reduction",
    "prefrontal": "prefrontal_cortex_reduction",
    "executive": "prefrontal_cortex_reduction",
    "백질": "white_matter_lesions",
    "white matter": "white_matter_lesions",
    "wmh": "white_matter_lesions",
    "전두": "frontal_atrophy",
    "전두엽": "frontal_atrophy",
    "frontal lobe": "frontal_atrophy",
    "frontal": "frontal_atrophy",
    "두정": "parietal_atrophy",
    "두정엽": "parietal_atrophy",
    "parietal": "parietal_atrophy",
}

TIME_REFERENCE_PATTERN = re.compile(
    r"(지금|오늘|어제|내일|새벽|오전|점심|오후|저녁|밤|자정|낮|아침|\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?)"
)
KST_WEEKDAY_LABELS = ("월", "화", "수", "목", "금", "토", "일")

AGREEMENT_TOKENS = (
    "응",
    "네",
    "그래",
    "맞아",
    "맞아요",
    "그렇지",
    "좋아",
    "좋아요",
)

UNCERTAIN_TOKENS = (
    "모르겠어",
    "잘모르겠어",
    "기억 안 나",
    "기억안나",
    "몰라",
    "모름",
    "어려워",
    "idk",
    "don't know",
    "dont know",
)

DEFAULT_CONTRACT_CONSTRAINTS = {
    "max_sentences": 2,
    "one_question_only": True,
    "no_topic_announcement": True,
    "no_answer_leak": True,
    "no_examples": True,
    "warm_brief_tone": True,
}

# ?대씪?댁뼵?몄뿉???섏떊 媛?ν븳 ?몄뀡 ?대깽??紐⑸줉
KNOWN_CLIENT_SESSION_EVENTS = {
    "realtime_session_started",
    "realtime_turn_started",
    "realtime_turn_ended",
    "realtime_timeout_triggered",
    "realtime_error",
    "tts_start",
    "tts_end",
    "client_audio_started",
    "client_audio_commit",
    "client_audio_stopped",
    "session_start",
    "session_end",
}

# =============================================================================
# ?곗씠???대옒???뺤쓽 (?뺤콉, ?몄뀡 而⑦뀓?ㅽ듃, ?고????곹깭, ?됰룞 怨꾩빟)
# =============================================================================
@dataclass
class UserPolicy:
    """사용자별 LLM/STT/TTS 모델 및 세션 파라미터 정책."""
    llm_model: str = "gpt-4o"
    llm_fallback_model: str = "gpt-4o-mini"
    stt_model: str = "gpt-4o-transcribe"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"
    tts_style: str = "친절하고 다정하게, 천천히 또박또박 말해줘"
    warmup_turns: int = 2
    silence_hint_threshold: int = 1
    silence_switch_threshold: int = 2
    silence_close_threshold: int = 3
    stt_confirm_limit: int = 1
    wait_time_sec: int = 3
    max_sentences: int = 2
    max_turn_seconds: int = REALTIME_MAX_TURN_DURATION_SEC
    hint_speed: str = "medium"
    switch_sensitivity: str = "medium"


@dataclass
class SessionContext:
    """세션 컨텍스트(요약, 최근 메시지, 사용자 프로필, 감정 톤 등)."""
    session_id: str
    conversation_summary: str = ""
    recent_messages: list[dict[str, str]] = field(default_factory=list)
    user_profile: dict[str, Any] = field(default_factory=dict)
    emotional_tone: str = "neutral"
    elapsed_time: int = 0
    request_close: bool = False
    total_message_count: int = 0
    last_summary_count: int = 0
    session_slot: str = ""
    next_session_slot: str = ""
    conversation_mode: str = "therapy"
    diagnosis_label: str = "MCI"
    neuro_pattern: list[str] = field(default_factory=list)
    cognitive_profile: dict[str, Any] = field(default_factory=dict)
    training_type: str = "semantic_naming"
    training_level: int = 1
    profile_id: str | None = None
    policy: UserPolicy = field(default_factory=UserPolicy)


@dataclass
class RuntimeSessionState:
    """런타임 상태(턴 수, 힌트 레벨, 현재 자극, 사용 이력 등)."""
    session_id: str
    dialog_state: DialogState = field(default_factory=DialogState)
    turn_count: int = 0
    user_turn_count: int = 0
    silence_streak: int = 0
    silence_duration: int = 0
    stt_uncertain_streak: int = 0
    stt_confirm_count: int = 0
    consecutive_failures: int = 0
    hint_level: int = 0
    error_streak: int = 0
    module: str = "naming"
    difficulty: int = 1
    current_stimulus: dict[str, Any] = field(default_factory=dict)
    used_stimuli: list[dict[str, Any]] = field(default_factory=list)
    used_phrases: list[str] = field(default_factory=list)
    recent_event_ids: list[str] = field(default_factory=list)
    last_client_event_seq: int = 0
    last_outcome: str = "related"
    next_move: str = "ask"
    fatigue_state: str = "normal"


@dataclass
class BehaviorContract:
    """LLM 응답 제약 계약(의도, 모듈, 힌트, 제약 조건 등)."""
    intent: str
    module: str
    hint_level: str
    outcome: str
    next_move: str
    constraints: dict[str, Any] = field(default_factory=dict)
    stimulus: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


# =============================================================================
# ?좏떥由ы떚 ?⑥닔 (?곹깭 ?뚯떛, ?띿뒪???뺣━, ???蹂??
# =============================================================================
def init_dialog_state() -> DialogState:
    return DialogState()  # 湲곕낯 DialogState 媛앹껜 ?앹꽦


# ?섏씠濡쒕뱶瑜?DialogState 媛앹껜濡??뚯떛
def parse_state(payload: dict[str, Any] | None) -> DialogState:
    if not payload:
        return init_dialog_state()
    try:
        return DialogState(**payload)
    except Exception:
        return init_dialog_state()


def _clean_text(text: str) -> str:
    return " ".join((text or "").split()).strip()  # ?곗냽 怨듬갚???섎굹濡? ?욌뮘 怨듬갚 ?쒓굅


MOJIBAKE_HINT_TOKENS = (
    "몄궗濡",
    "쒖옉",
    "섎닎",
    "寃쎈룄",
    "留덉튌",
    "理쒓렐",
    "吏덈Ц",
)


def _looks_like_mojibake(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False

    if "\ufffd" in cleaned:
        return True
    if any(token in cleaned for token in MOJIBAKE_HINT_TOKENS):
        return True
    if "?" in cleaned and len(cleaned) >= 4:
        return True
    return False


def _repair_possible_utf8_mojibake(text: str) -> str:
    repaired = _clean_text(text)
    if not repaired:
        return repaired

    # Handles common mojibake pattern such as "ìë..." -> "안녕..."
    for _ in range(2):
        try:
            candidate = repaired.encode("latin-1").decode("utf-8")
        except Exception:
            break
        candidate = _clean_text(candidate)
        if not candidate or candidate == repaired:
            break
        repaired = candidate
    return repaired


def _sanitize_dialog_summary(summary: str, fallback: str = DEFAULT_DIALOG_SUMMARY) -> str:
    repaired = _repair_possible_utf8_mojibake(summary)
    fallback_clean = _repair_possible_utf8_mojibake(fallback)

    if not repaired:
        return fallback_clean[:MAX_SUMMARY_CHARS]
    if _looks_like_mojibake(repaired):
        if fallback_clean and not _looks_like_mojibake(fallback_clean):
            return fallback_clean[:MAX_SUMMARY_CHARS]
        return DEFAULT_DIALOG_SUMMARY[:MAX_SUMMARY_CHARS]
    return repaired[:MAX_SUMMARY_CHARS]


# ?덉쟾???뺤닔 蹂??(?ㅽ뙣 ??湲곕낯媛?諛섑솚)
def _safe_int(value: Any, default: int) -> int:
    try:
        if value is None:
            return int(default)
        return int(value)
    except Exception:
        return int(default)


# ?덉쟾???ㅼ닔 蹂??(?ㅽ뙣 ??湲곕낯媛?諛섑솚)
def _safe_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


# 遺덈━??蹂???⑥닔 (?ㅼ뼇???낅젰??bool濡?蹂??
def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")  # 臾몄옄??true ?먯젙
    if isinstance(value, (int, float)):
        return bool(value)  # ?レ옄媛 0???꾨땲硫?True
    return default


# JSON ?뺥깭??臾몄옄?댁쓣 ?뚯떛 (臾몄옄?댁씠 JSON?대㈃ 媛앹껜濡?蹂??
def _parse_json_like(value: Any) -> Any:
    if not isinstance(value, str):
        return value  # 臾몄옄?댁씠 ?꾨땲硫?洹몃?濡?諛섑솚
    text = value.strip()
    if not text:
        return value
    # JSON 媛앹껜??諛곗뿴 ?뺥깭?몄? ?뺤씤
    if not (
        (text.startswith("{") and text.endswith("}"))
        or (text.startswith("[") and text.endswith("]"))
    ):
        return value
    try:
        return json.loads(text)  # JSON ?뚯떛 ?쒕룄
    except Exception:
        return value  # ?ㅽ뙣 ???먮낯 諛섑솚


# 留ㅼ묶???띿뒪???뺢퇋??(怨듬갚, 援щ몢?? ?レ옄留??④린怨??뚮Ц?먰솕)
def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^\w\-\?]+", "", _clean_text(text)).lower()


def _list_from_any(value: Any) -> list[str]:
    if isinstance(value, list):
        source = value
    elif isinstance(value, str):
        source = re.split(r"[,/|]", value)
    else:
        return []
    result: list[str] = []
    for item in source:
        cleaned = _clean_text(str(item))
        if cleaned:
            result.append(cleaned)
    return result


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = _clean_text(str(item)).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _extract_region_keys(raw_text: str) -> list[str]:
    cleaned = _clean_text(raw_text).lower()
    if not cleaned:
        return []
    matches: list[str] = []
    if cleaned in BRAIN_REGION_PROFILE_MAP:
        matches.append(cleaned)
    for alias, region_key in BRAIN_REGION_ALIAS_MAP.items():
        if alias == "frontal" and "prefrontal" in cleaned:
            continue
        if alias == "전두" and "전전두" in cleaned:
            continue
        if alias in cleaned:
            matches.append(region_key)
    return _dedupe_keep_order(matches)


def _canonicalize_neuro_pattern(raw_values: list[str]) -> list[str]:
    canonical: list[str] = []
    for raw in raw_values:
        canonical.extend(_extract_region_keys(raw))
    canonical = _dedupe_keep_order(canonical)
    if canonical:
        return canonical
    return ["temporal_atrophy"]


def _module_priority_from_regions(region_keys: list[str]) -> list[str]:
    base_scores = {module: 0 for module in MODULE_SEQUENCE}
    for key in region_keys:
        profile = BRAIN_REGION_PROFILE_MAP.get(key) or {}
        weights = profile.get("module_weights")
        if not isinstance(weights, dict):
            continue
        for module_name, weight in weights.items():
            normalized_module = _normalize_module(module_name, default="")
            if normalized_module not in base_scores:
                continue
            base_scores[normalized_module] += max(0, _safe_int(weight, 0))

    if all(score == 0 for score in base_scores.values()):
        return list(MODULE_SEQUENCE)

    return sorted(
        list(MODULE_SEQUENCE),
        key=lambda module_name: (-base_scores.get(module_name, 0), MODULE_SEQUENCE.index(module_name)),
    )


def _kst_part_of_day(hour: int) -> str:
    if 0 <= hour < 5:
        return "dawn"
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "noon"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def _build_kst_time_context(*, session_slot: str, next_session_slot: str, now_kst: datetime | None = None) -> dict[str, Any]:
    current = now_kst or datetime.now(KST_TZ)
    weekday = KST_WEEKDAY_LABELS[current.weekday()] if 0 <= current.weekday() < len(KST_WEEKDAY_LABELS) else ""
    inferred_slot = _infer_session_slot(current.hour)
    normalized_slot = _normalize_session_slot(session_slot) or _infer_session_slot(current.hour)
    normalized_next_slot = _normalize_session_slot(next_session_slot) or _get_next_session_slot(normalized_slot)
    return {
        "timezone": "Asia/Seoul",
        "now_kst_iso": current.isoformat(),
        "date_kst": current.strftime("%Y-%m-%d"),
        "time_kst": current.strftime("%H:%M"),
        "hour_kst": current.hour,
        "minute_kst": current.minute,
        "weekday_kst": weekday,
        "part_of_day_kst": _kst_part_of_day(current.hour),
        "inferred_session_slot_kst": inferred_slot,
        "inferred_session_slot_label_kst": _get_session_label(inferred_slot),
        "session_slot_kst": normalized_slot,
        "session_slot_label_kst": _get_session_label(normalized_slot),
        "next_session_slot_kst": normalized_next_slot,
        "next_session_slot_label_kst": _get_session_label(normalized_next_slot),
    }


def _has_time_reference(user_text: str) -> bool:
    cleaned = _clean_text(user_text)
    if not cleaned:
        return False
    return bool(TIME_REFERENCE_PATTERN.search(cleaned))


def _build_cognitive_training_profile(
    *,
    diagnosis_label: str,
    neuro_pattern: list[str],
    model_result: dict[str, Any],
    session_slot: str,
    next_session_slot: str,
    base_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    region_keys = _canonicalize_neuro_pattern([*neuro_pattern, *_list_from_any(model_result.get("main_region"))])
    module_priority = _module_priority_from_regions(region_keys)

    region_details: list[dict[str, Any]] = []
    cognitive_targets: list[str] = []
    task_families: list[str] = []
    for key in region_keys:
        profile = BRAIN_REGION_PROFILE_MAP.get(key) or {}
        targets = _list_from_any(profile.get("cognitive_targets"))
        tasks = _list_from_any(profile.get("task_families"))
        cognitive_targets.extend(targets)
        task_families.extend(tasks)
        region_details.append(
            {
                "region_key": key,
                "label": _clean_text(str(profile.get("label") or key)),
                "cognitive_targets": targets,
                "task_families": tasks,
            }
        )

    recommended_training = _list_from_any(model_result.get("recommended_training"))
    time_context = _build_kst_time_context(session_slot=session_slot, next_session_slot=next_session_slot)

    profile_payload = {
        "schema_version": "dummy_v1",
        "source": "model_result_plus_region_map",
        "diagnosis_label": diagnosis_label or "MCI",
        "active_regions": region_keys,
        "dominant_region": region_keys[0] if region_keys else "",
        "region_details": region_details,
        "cognitive_targets": _dedupe_keep_order(cognitive_targets),
        "task_families": _dedupe_keep_order(task_families),
        "module_priority": module_priority,
        "model_snapshot": {
            "stage": _clean_text(str(model_result.get("stage") or "")),
            "risk_level": _clean_text(str(model_result.get("risk_level") or "")),
            "trend": _clean_text(str(model_result.get("trend") or "")),
            "recommended_training": recommended_training,
        },
        "time_context": time_context,
    }

    merged = dict(base_profile) if isinstance(base_profile, dict) else {}
    merged.update(profile_payload)
    return merged


# =============================================================================
# ?뺢퇋???⑥닔 (?몄뀡 ?щ’, ???紐⑤뱶, ?덈젴 ?좏삎, 紐⑤뱢 蹂??
# =============================================================================
def _normalize_session_slot(raw_slot: Any) -> str:
    value = str(raw_slot or "").strip().lower()
    if value in SESSION_SLOT_LABEL:
        return value
    alias = {
        "오전": "morning",
        "점심": "lunch",
        "저녁": "evening",
    }
    return alias.get(value, "")


def _infer_session_slot(hour: int | None = None) -> str:
    current_hour = datetime.now(KST_TZ).hour if hour is None else int(hour)
    if 5 <= current_hour < 11:
        return "morning"
    if 11 <= current_hour < 17:
        return "lunch"
    return "evening"


def _get_next_session_slot(session_slot: str) -> str:
    normalized = _normalize_session_slot(session_slot) or "morning"
    return NEXT_SESSION_SLOT.get(normalized, "lunch")


def _get_session_label(session_slot: str) -> str:
    normalized = _normalize_session_slot(session_slot) or "morning"
    return SESSION_SLOT_LABEL.get(normalized, "아침")


def _normalize_conversation_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "").strip().lower()
    return CONVERSATION_MODE_ALIASES.get(mode, "")


def _normalize_training_type(raw_type: Any, default: str = "semantic_naming") -> str:
    candidate = _clean_text(str(raw_type or "")).lower()
    if candidate in TRAINING_TYPE_SET:
        return candidate
    return default


def _normalize_module(raw_module: Any, default: str = "naming") -> str:
    candidate = _clean_text(str(raw_module or "")).lower()
    if candidate in MODULE_TO_TRAINING_TYPE:
        return candidate
    return default


def _training_type_to_module(training_type: str) -> str:
    return TRAINING_TYPE_TO_MODULE.get(_normalize_training_type(training_type), "naming")


def _module_to_training_type(module: str) -> str:
    return MODULE_TO_TRAINING_TYPE.get(_normalize_module(module), "semantic_naming")


def _next_module(current_module: str) -> str:
    normalized = _normalize_module(current_module)
    sequence = list(MODULE_SEQUENCE)
    if normalized not in sequence:
        return sequence[0]  # ?????녿뒗 紐⑤뱢?대㈃ 泥?踰덉㎏ 紐⑤뱢 諛섑솚
    idx = sequence.index(normalized)
    return sequence[(idx + 1) % len(sequence)]  # ?ㅼ쓬 紐⑤뱢 (?쒗솚)


# ?뚰듃 ?덈꺼 ?쇰꺼 ?앹꽦 (0~5瑜?"H0"~"H5"濡?蹂??
def _hint_label(level: int) -> str:
    bounded = max(0, min(5, _safe_int(level, 0)))  # 0~5 踰붿쐞濡??쒗븳
    return f"H{bounded}"


# ?몄뀡 ID ?앹꽦 (??꾩뒪?ы봽 + UUID)
def _create_session_id() -> str:
    return f"session_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{uuid.uuid4().hex[:6]}"


# =============================================================================
# OpenAI ?대씪?댁뼵??諛??ъ슜???뺤콉(UserPolicy) 愿由?
# =============================================================================
def _build_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")  # API ???놁쑝硫??먮윭
    return OpenAI(api_key=api_key)


# ?뺤뀛?덈━?먯꽌 UserPolicy 媛앹껜 ?앹꽦
def _policy_from_dict(data: dict[str, Any] | None, base: UserPolicy | None = None) -> UserPolicy:
    seed = asdict(base or UserPolicy())
    if isinstance(data, dict):
        seed.update(data)

    policy = UserPolicy(
        llm_model=_clean_text(str(seed.get("llm_model") or UserPolicy.llm_model)),
        llm_fallback_model=_clean_text(str(seed.get("llm_fallback_model") or UserPolicy.llm_fallback_model)),
        stt_model=_clean_text(str(seed.get("stt_model") or UserPolicy.stt_model)),
        tts_model=_clean_text(str(seed.get("tts_model") or UserPolicy.tts_model)),
        tts_voice=_clean_text(str(seed.get("tts_voice") or UserPolicy.tts_voice)),
        tts_style=_clean_text(str(seed.get("tts_style") or UserPolicy.tts_style)),
        warmup_turns=max(0, _safe_int(seed.get("warmup_turns"), UserPolicy.warmup_turns)),
        silence_hint_threshold=max(1, _safe_int(seed.get("silence_hint_threshold"), UserPolicy.silence_hint_threshold)),
        silence_switch_threshold=max(1, _safe_int(seed.get("silence_switch_threshold"), UserPolicy.silence_switch_threshold)),
        silence_close_threshold=max(1, _safe_int(seed.get("silence_close_threshold"), UserPolicy.silence_close_threshold)),
        stt_confirm_limit=max(0, _safe_int(seed.get("stt_confirm_limit"), UserPolicy.stt_confirm_limit)),
        wait_time_sec=max(1, _safe_int(seed.get("wait_time_sec"), UserPolicy.wait_time_sec)),
        max_sentences=max(1, min(3, _safe_int(seed.get("max_sentences"), UserPolicy.max_sentences))),
        max_turn_seconds=max(8, _safe_int(seed.get("max_turn_seconds"), UserPolicy.max_turn_seconds)),
        hint_speed=_clean_text(str(seed.get("hint_speed") or UserPolicy.hint_speed)),
        switch_sensitivity=_clean_text(str(seed.get("switch_sensitivity") or UserPolicy.switch_sensitivity)),
    )
    return policy


def _load_user_policy_config() -> dict[str, Any]:
    global USER_POLICY_CACHE
    if USER_POLICY_CACHE is not None:
        return USER_POLICY_CACHE  # ?대? 濡쒕뱶?섏뿀?쇰㈃ 罹먯떆 諛섑솚

    # 湲곕낯 ?ㅼ젙 (default 諛?mci_dummy)
    base_config: dict[str, Any] = {
        "default": asdict(UserPolicy()),  # 湲곕낯 ?뺤콉
        "mci_dummy": {  # MCI ?섏옄???붾? ?뺤콉
            "llm_model": "gpt-4o",
            "llm_fallback_model": "gpt-4o-mini",
            "stt_model": "gpt-4o-transcribe",
            "tts_model": "gpt-4o-mini-tts",
            "tts_voice": "alloy",
            "tts_style": "친절하고 다정하게, 천천히 또박또박 말해줘",
            "switch_sensitivity": "medium",
        },
    }

    # user_policies.json ?뚯씪???덉쑝硫?濡쒕뱶
    config_path = APP_DIR / "user_policies.json"
    if config_path.exists():
        try:
            parsed = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                base_config.update(parsed)  # ?뚯씪 ?댁슜?쇰줈 ?낅뜲?댄듃
        except Exception:
            pass  # ?뚯씪 濡쒕뱶 ?ㅽ뙣 ??湲곕낯 ?ㅼ젙 ?ъ슜

    USER_POLICY_CACHE = base_config
    return base_config


# ?꾨줈??ID? 硫뷀? ?뺣낫瑜?湲곕컲?쇰줈 ?ъ슜???뺤콉 寃곗젙
def _resolve_user_policy(profile_id: str | None, meta_payload: dict[str, Any]) -> UserPolicy:
    config = _load_user_policy_config()
    policy_key = _clean_text(str(meta_payload.get("policy_id") or "")).lower()
    profile_key = _clean_text(str(profile_id or "")).lower()
    default_policy = _policy_from_dict(config.get("default"))

    # ?곗꽑?쒖쐞: policy_id > profile_id > mci_dummy > default
    if policy_key and isinstance(config.get(policy_key), dict):
        return _policy_from_dict(config.get(policy_key), base=default_policy)
    if profile_key and isinstance(config.get(profile_key), dict):
        return _policy_from_dict(config.get(profile_key), base=default_policy)
    if isinstance(config.get("mci_dummy"), dict):
        return _policy_from_dict(config.get("mci_dummy"), base=default_policy)
    return default_policy


# ?좉꼍?숈쟻 ?⑦꽩 湲곕컲 湲곕낯 紐⑤뱢 寃곗젙
def _default_module_by_profile(neuro_pattern: list[str]) -> str:
    priorities = _module_priority_from_regions(_canonicalize_neuro_pattern(neuro_pattern))
    if priorities:
        return priorities[0]
    return "fluency"


# =============================================================================
# ?몄뀡 而⑦뀓?ㅽ듃 諛??고????곹깭 ?앹꽦/議고쉶
# =============================================================================
def _create_session_context(
    *,
    session_id: str,
    profile_id: str | None,
    policy: UserPolicy,
    conversation_mode: str,
) -> SessionContext:
    return SessionContext(
        session_id=session_id,
        profile_id=profile_id,
        policy=policy,
        conversation_mode=conversation_mode or "therapy",
        user_profile={"profile_id": profile_id} if profile_id else {},
    )


# ?고????곹깭 ?앹꽦
def _create_runtime_state(*, session_id: str, module: str) -> RuntimeSessionState:
    return RuntimeSessionState(
        session_id=session_id,
        dialog_state=init_dialog_state(),
        module=_normalize_module(module),
    )


# ?몄뀡 而⑦뀓?ㅽ듃 媛?몄삤湲??먮뒗 ?앹꽦
def _get_or_create_session_context(
    *,
    session_id: str,
    profile_id: str | None,
    policy: UserPolicy,
    conversation_mode: str,
) -> SessionContext:
    context = SESSION_CONTEXT_STORE.get(session_id)
    if isinstance(context, SessionContext):
        # ?대? 議댁옱?섎㈃ ?쇰? ?꾨뱶留??낅뜲?댄듃
        context.profile_id = profile_id or context.profile_id
        context.policy = policy
        if conversation_mode:
            context.conversation_mode = conversation_mode
        context.conversation_summary = _sanitize_dialog_summary(
            context.conversation_summary,
            fallback=DEFAULT_DIALOG_SUMMARY,
        )
        return context

    # ?놁쑝硫??덈줈 ?앹꽦
    created = _create_session_context(
        session_id=session_id,
        profile_id=profile_id,
        policy=policy,
        conversation_mode=conversation_mode,
    )
    created.conversation_summary = _sanitize_dialog_summary(
        created.conversation_summary,
        fallback=DEFAULT_DIALOG_SUMMARY,
    )
    SESSION_CONTEXT_STORE[session_id] = created
    return created


# ?고????곹깭 媛?몄삤湲??먮뒗 ?앹꽦
def _get_or_create_runtime_state(*, session_id: str, module: str) -> RuntimeSessionState:
    runtime = SESSION_RUNTIME_STORE.get(session_id)
    if isinstance(runtime, RuntimeSessionState):
        if not runtime.module:
            runtime.module = _normalize_module(module)
        return runtime

    # ?놁쑝硫??덈줈 ?앹꽦
    created = _create_runtime_state(session_id=session_id, module=module)
    SESSION_RUNTIME_STORE[session_id] = created
    return created


# =============================================================================
# 諛쒗솕 遺꾨쪟 (?숈쓽/遺덊솗???좏슚 ?먮퀎, ?ㅼ썙?쑣룹쓬??留ㅼ묶, ?묐떟 寃곌낵 遺꾨쪟)
# =============================================================================
# ?숈쓽 諛쒗솕 ?щ? ?먮떒 (?? ?? 留욎븘????
def _is_agreement_utterance(user_text: str) -> bool:
    normalized = _normalize_for_match(user_text)
    if not normalized:
        return False
    # AGREEMENT_TOKENS 以??섎굹? ?뺥솗???쇱튂?섎뒗吏 ?뺤씤
    return any(normalized == _normalize_for_match(token) for token in AGREEMENT_TOKENS)


# 遺덊솗??諛쒗솕 ?щ? ?먮떒 (紐⑤Ⅴ寃좎뼱?? 湲곗뼲 ???섏슂 ??
def _is_uncertain_utterance(user_text: str) -> bool:
    cleaned = _clean_text(user_text).lower()
    if not cleaned:
        return True  # 鍮?諛쒗솕??遺덊솗?ㅻ줈 媛꾩＜
    return any(token in cleaned for token in UNCERTAIN_TOKENS)


def _is_incomplete_utterance(user_text: str) -> bool:
    cleaned = _clean_text(user_text)
    if not cleaned:
        return False

    # Hard interruption markers usually indicate an unfinished sentence.
    if cleaned.endswith(("...", ",", "-", "(", "…")):
        return True

    # Explicit sentence-final endings.
    if re.search(r"(요|니다|죠|네|습니다|야)[.!?]?$", cleaned):
        return False

    # Common connective endings indicate "still speaking".
    if re.search(r"(그리고|근데|그래서|혹은|또는|이면|하고|에서|까지|처럼|이나)$", cleaned):
        return True
    if re.search(r"(무슨|어떤|언제|어디|누구|무엇)$", cleaned):
        return True

    normalized = _normalize_for_match(cleaned)
    if len(normalized) <= 1 and not re.search(r"[.!?]$", cleaned):
        return True
    return False


def _is_incremental_user_update(current_text: str, previous_text: str) -> bool:
    current = _normalize_for_match(current_text)
    previous = _normalize_for_match(previous_text)
    if not current or not previous:
        return False
    # Exact same final utterance repeated by the user is not an incremental partial update.
    if current == previous:
        return False
    if current.startswith(previous) and (len(current) - len(previous)) <= 14:
        return True
    if previous.startswith(current) and (len(previous) - len(current)) <= 10:
        return True

    min_len = min(len(current), len(previous))
    if min_len < 4:
        return False

    shared = 0
    for cur_char, prev_char in zip(current, previous):
        if cur_char != prev_char:
            break
        shared += 1
    if shared >= max(3, int(min_len * 0.7)) and abs(len(current) - len(previous)) <= 12:
        return True
    return False


# ?좏슚??湲곗뿬 諛쒗솕 ?щ? ?먮떒
def _is_valid_contribution(user_text: str) -> bool:
    cleaned = _clean_text(user_text)
    if not cleaned:
        return False  # 鍮??띿뒪?몃뒗 臾댄슚
    if _is_agreement_utterance(cleaned):
        return False  # ?⑥닚 ?숈쓽??臾댄슚
    if _is_uncertain_utterance(cleaned):
        return False  # 遺덊솗?ㅽ븳 ?쒗쁽??臾댄슚
    return len(_normalize_for_match(cleaned)) >= 2  # ?뺢퇋????2湲???댁긽?댁뼱???좏슚


def _list_from_item(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        cleaned = _clean_text(str(item))
        if cleaned:
            result.append(cleaned)
    return result


def _keyword_match(normalized_user: str, keywords: list[str]) -> bool:
    if not normalized_user or len(normalized_user) < 2:
        return False
    for keyword in keywords:
        needle = _normalize_for_match(keyword)
        if not needle or len(needle) < 2:
            continue
        # Match full keyword in user utterance.
        if needle in normalized_user:
            return True
        # Allow a near-complete prefix (missing <= 1 char).
        if normalized_user in needle and (len(needle) - len(normalized_user) <= 1):
            return True
    return False


# ?뚯슫濡좎쟻 留ㅼ묶 (珥덉꽦?대굹 ?뚯젅 ?쇱튂 ?뺤씤)
def _phonological_match(normalized_user: str, stimulus: dict[str, Any]) -> bool:
    if not normalized_user:
        return False

    targets = [
        _normalize_for_match(target)
        for target in _list_from_item(stimulus.get("target_keywords"))
        if _normalize_for_match(target)
    ]

    # ?뚯슫濡좎쟻 ?⑥꽌(phonological_cues)? 留ㅼ묶
    cues = _list_from_item(stimulus.get("phonological_cues"))
    for cue in cues:
        normalized_cue = _normalize_for_match(cue)
        if not normalized_cue:
            continue
        # Single-character cues are too broad for long utterances.
        if len(normalized_cue) == 1:
            if len(normalized_user) > 4:
                continue
            if len(normalized_user) >= 2:
                prefix2 = normalized_user[:2]
                if not any(target.startswith(prefix2) for target in targets):
                    continue
        if len(normalized_cue) == 2 and len(normalized_user) > 8 and not normalized_user.startswith(normalized_cue):
            continue
        # ?ъ슜??諛쒗솕媛 ?⑥꽌濡??쒖옉?섍굅?? 泥?3湲???덉뿉 ?ы븿
        if normalized_user.startswith(normalized_cue):
            return True
        if normalized_cue in normalized_user[:3]:
            return True

    # ?뺣떟 ?ㅼ썙?쒖쓽 泥?湲???쇱튂 ?뺤씤
    for normalized_target in targets:
        # 泥?湲?먭? 媛숈쑝硫??뚯슫濡좎쟻 留ㅼ묶?쇰줈 媛꾩＜
        if len(normalized_user) <= 3 and normalized_user[:1] and normalized_user[:1] == normalized_target[:1]:
            if len(normalized_user) == 1:
                return True
            if normalized_target.startswith(normalized_user[:2]):
                return True
    return False


# ?ъ슜???묐떟 寃곌낵 遺꾨쪟 (correct/related/unrelated ??
def _classify_outcome(
    *,
    user_text: str,
    stimulus: dict[str, Any],
    no_response: bool,
    stt_uncertain: bool,
    training_active: bool,
    user_input_incomplete: bool,
) -> str:
    if stt_uncertain:
        return "stt_uncertain"
    if no_response:
        return "no_response"

    cleaned = _clean_text(user_text)
    if not cleaned:
        return "no_response"
    if _is_uncertain_utterance(cleaned):
        return "no_response"
    if user_input_incomplete:
        return "incomplete"
    if not training_active:
        return "related"
    if not _is_valid_contribution(cleaned):
        return "related"

    if not isinstance(stimulus, dict) or not stimulus:
        return "related"

    normalized_user = _normalize_for_match(cleaned)
    target_keywords = _list_from_item(stimulus.get("target_keywords"))
    related_keywords = _list_from_item(stimulus.get("related_keywords"))
    superordinate_keywords = _list_from_item(stimulus.get("superordinate_keywords"))

    if _keyword_match(normalized_user, target_keywords):
        return "correct"
    if _keyword_match(normalized_user, superordinate_keywords):
        return "superordinate"
    if _keyword_match(normalized_user, related_keywords):
        return "related"
    if _phonological_match(normalized_user, stimulus):
        return "phonological"
    return "unrelated"


def _build_contract_constraints(policy: UserPolicy) -> dict[str, Any]:
    constraints = dict(DEFAULT_CONTRACT_CONSTRAINTS)  # 湲곕낯 ?쒖빟 議곌굔 蹂듭궗
    constraints["max_sentences"] = policy.max_sentences  # ?뺤콉??理쒕? 臾몄옣 ?섎줈 ?낅뜲?댄듃
    return constraints


# 理쒓렐 ??붿뿉??二쇱젣 異붾줎 (媛??理쒓렐 ?ъ슜??諛쒗솕??泥??⑥뼱 ?ъ슜)
def _infer_recent_topic(recent_messages: list[dict[str, str]]) -> str:
    for message in reversed(recent_messages):
        if str(message.get("role") or "").lower() != "user":
            continue
        content = _clean_text(str(message.get("content") or ""))
        if not content:
            continue
        tokens = re.findall(r"[가-힣A-Za-z]{2,}", content)
        if tokens:
            return tokens[0]
    return "일상 대화"


# =============================================================================
# ?먭레(stimulus) 愿由?(?앹꽦, 以묐났 寃?? ?대갚)
# =============================================================================
def _append_used_stimulus(runtime: RuntimeSessionState, stimulus: dict[str, Any]) -> None:
    if not isinstance(stimulus, dict):
        return
    prompt = _clean_text(str(stimulus.get("prompt") or ""))
    if not prompt:
        return
    entry = {
        "module": _clean_text(str(stimulus.get("module") or runtime.module)),
        "difficulty": _safe_int(stimulus.get("difficulty"), runtime.difficulty),
        "prompt": prompt[:120],
        "target_keywords": _list_from_item(stimulus.get("target_keywords"))[:3],
        "task_family": _clean_text(str(stimulus.get("task_family") or "")),
        "cognitive_domain": _clean_text(str(stimulus.get("cognitive_domain") or "")),
        "region_focus": _list_from_item(stimulus.get("region_focus"))[:3],
    }
    runtime.used_stimuli.append(entry)
    if len(runtime.used_stimuli) > MAX_USED_STIMULI:
        runtime.used_stimuli = runtime.used_stimuli[-MAX_USED_STIMULI:]


def _stimulus_keyword_set(stimulus: dict[str, Any]) -> set[str]:
    values = _list_from_item(stimulus.get("target_keywords"))
    return {token for token in (_normalize_for_match(item) for item in values) if token}


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _normalized_char_ngrams(text: str, n: int = 3) -> set[str]:
    normalized = _normalize_for_match(text)
    if len(normalized) < n:
        return {normalized} if normalized else set()
    return {normalized[idx : idx + n] for idx in range(0, len(normalized) - n + 1)}


def _is_duplicate_stimulus(candidate: dict[str, Any], used_stimuli: list[dict[str, Any]]) -> bool:
    candidate_keywords = _stimulus_keyword_set(candidate)
    candidate_prompt = _clean_text(str(candidate.get("prompt") or ""))
    candidate_ngrams = _normalized_char_ngrams(candidate_prompt, n=3)

    for previous in used_stimuli[-12:]:
        prev_keywords = _stimulus_keyword_set(previous)
        if _jaccard_similarity(candidate_keywords, prev_keywords) >= STIMULUS_KEYWORD_JACCARD_THRESHOLD:
            return True

        prev_prompt = _clean_text(str(previous.get("prompt") or ""))
        prev_ngrams = _normalized_char_ngrams(prev_prompt, n=3)
        if _jaccard_similarity(candidate_ngrams, prev_ngrams) >= STIMULUS_PROMPT_NGRAM_THRESHOLD:
            return True

    return False


def _build_fallback_stimulus(context: SessionContext, runtime: RuntimeSessionState, reason: str) -> dict[str, Any]:
    topic = _infer_recent_topic(context.recent_messages)
    cue = _normalize_for_match(topic)[:1] if _normalize_for_match(topic) else ""
    profile = context.cognitive_profile if isinstance(context.cognitive_profile, dict) else {}
    task_families = _list_from_any(profile.get("task_families"))
    cognitive_targets = _list_from_any(profile.get("cognitive_targets"))
    active_regions = _list_from_any(profile.get("active_regions"))
    return {
        "module": runtime.module,
        "difficulty": runtime.difficulty,
        "prompt": f"{topic}와 관련된 이야기를 한 가지 더 들려주실래요?",
        "target_keywords": [topic],
        "related_keywords": [],
        "superordinate_keywords": [],
        "phonological_cues": [cue] if cue else [],
        "task_family": task_families[0] if task_families else "",
        "cognitive_domain": cognitive_targets[0] if cognitive_targets else "",
        "region_focus": active_regions[:2],
        "note": reason,
    }


def _phrase_signature(text: str) -> str:
    return _normalize_for_match(text)[:80]  # ?뺢퇋????80?먭퉴吏留??ъ슜


# ?ъ슜??臾멸뎄 紐⑸줉??異붽?
def _append_used_phrase(runtime: RuntimeSessionState, text: str) -> None:
    signature = _phrase_signature(text)
    if not signature:
        return
    runtime.used_phrases.append(signature)
    # 理쒕? 媛쒖닔 珥덇낵 ???ㅻ옒??寃껊????쒓굅
    if len(runtime.used_phrases) > MAX_USED_PHRASES:
        runtime.used_phrases = runtime.used_phrases[-MAX_USED_PHRASES:]


# ?먭레 ?뺣낫 ?⑥닔 (?꾩옱 ?먭레???녾굅??媛뺤젣 媛깆떊 ???덈줈 ?앹꽦)
def _ensure_stimulus(
    *,
    context: SessionContext,
    runtime: RuntimeSessionState,
    policy: UserPolicy,
    force_new: bool = False,
) -> dict[str, Any]:
    if runtime.current_stimulus and not force_new:
        return runtime.current_stimulus  # ?대? ?먭레???덇퀬 媛뺤젣 媛깆떊 ?꾨땲硫?湲곗〈 寃?諛섑솚

    # 以묐났 諛⑹?瑜??꾪빐 理쒕? ?ъ떆???잛닔留뚰겮 ?앹꽦 ?쒕룄
    for attempt in range(STIMULUS_DUPLICATE_RETRY_LIMIT + 1):
        generated = generate_stimulus(
            module=runtime.module,
            difficulty=runtime.difficulty,
            used_stimuli=runtime.used_stimuli,
            conversation_summary=context.conversation_summary,
            recent_messages=context.recent_messages,
            user_profile=context.user_profile,
            training_profile=context.cognitive_profile,
            time_context=_build_kst_time_context(
                session_slot=context.session_slot,
                next_session_slot=context.next_session_slot,
            ),
            llm_model=policy.llm_model,
        )
        if not isinstance(generated, dict):
            generated = {}

        prompt = _clean_text(str(generated.get("prompt") or ""))
        if not prompt:
            # ?꾨＼?꾪듃媛 鍮꾩뼱?덉쑝硫??대갚 ?먭레 ?앹꽦
            generated = _build_fallback_stimulus(
                context,
                runtime,
                reason="fallback_due_to_empty_prompt",
            )

        # 以묐났???꾨땲硫??ъ슜
        if not _is_duplicate_stimulus(generated, runtime.used_stimuli):
            runtime.current_stimulus = generated
            _append_used_stimulus(runtime, generated)
            return generated

        # ?ъ떆???잛닔 誘몄냼吏꾩씠硫??ㅼ떆 ?쒕룄
        if attempt < STIMULUS_DUPLICATE_RETRY_LIMIT:
            continue

    # ?ъ떆???잛닔 珥덇낵 ??紐⑤뱢 ?꾪솚 ???대갚 ?먭레 ?ъ슜
    switched_module = _next_module(runtime.module)
    runtime.module = switched_module
    fallback = _build_fallback_stimulus(
        context,
        runtime,
        reason="fallback_due_to_duplicate_retry_exhausted",
    )
    runtime.current_stimulus = fallback
    _append_used_stimulus(runtime, fallback)
    # ?대깽??濡쒓렇 湲곕줉
    append_session_event(
        context.session_id,
        "event_unknown",
        {
            "reason": "stimulus_retry_exhausted",
            "retry_limit": STIMULUS_DUPLICATE_RETRY_LIMIT,
            "module_switched_to": switched_module,
            "fallback": "safe_local_stimulus",
        },
    )
    return fallback


# =============================================================================
# ?됰룞 怨꾩빟(BehaviorContract) 寃곗젙 諛??고????곹깭 ?낅뜲?댄듃
# =============================================================================
# ?쇰줈 ?곹깭 ?뺢퇋??(normal/warning/stop)
def _normalize_fatigue_state(raw: Any) -> str:
    value = _clean_text(str(raw or "")).lower()
    if value in ("normal", "warning", "stop"):
        return value
    if value in ("medium",):
        return "warning"
    if value in ("high",):
        return "stop"
    return "normal"


# ?쇰줈 ?곹깭瑜??덈꺼濡?蹂??(DialogState?먯꽌 ?ъ슜)
def _to_fatigue_level(fatigue_state: str) -> str:
    if fatigue_state == "stop":
        return "high"
    if fatigue_state == "warning":
        return "medium"
    return "low"


# ?꾩옱 ?곹솴???곕씪 ?됰룞 怨꾩빟 寃곗젙 (?대뼸寃??묐떟?좎? 寃곗젙)
def _decide_behavior_contract(
    *,
    runtime: RuntimeSessionState,
    policy: UserPolicy,
    request_close: bool,
    no_response: bool,
    stt_uncertain: bool,
    outcome: str,
    training_active: bool,
) -> BehaviorContract:
    constraints = _build_contract_constraints(policy)

    if request_close:
        return BehaviorContract(
            intent="wrapup",
            module=runtime.module,
            hint_level="H0",
            outcome=outcome,
            next_move="close",
            constraints=constraints,
            notes="Session close requested. Finish with a short 1-2 sentence wrap-up.",
        )

    if stt_uncertain:
        if runtime.stt_confirm_count < policy.stt_confirm_limit:
            return BehaviorContract(
                intent="confirm_stt",
                module=runtime.module,
                hint_level=_hint_label(runtime.hint_level),
                outcome="stt_uncertain",
                next_move="confirm_stt",
                constraints=constraints,
                notes="STT uncertain. Ask for one short repetition.",
            )
        return BehaviorContract(
            intent="feedback",
            module=runtime.module,
            hint_level=_hint_label(runtime.hint_level),
            outcome="stt_uncertain",
            next_move="retry",
            constraints=constraints,
            notes="STT confirmation failed repeatedly. Switch to one concise confirmation question.",
        )

    if no_response:
        if runtime.silence_streak >= policy.silence_close_threshold:
            return BehaviorContract(
                intent="wrapup",
                module=runtime.module,
                hint_level=_hint_label(runtime.hint_level),
                outcome="no_response",
                next_move="close",
                constraints=constraints,
                notes="Silence repeated over threshold. Close gently.",
            )
        return BehaviorContract(
            intent="check_in",
            module=runtime.module,
            hint_level=_hint_label(runtime.hint_level),
            outcome="no_response",
            next_move="ask",
            constraints=constraints,
            notes="No response. Use one easy check-in question without assumptions.",
        )

    if not training_active:
        return BehaviorContract(
            intent="rapport_followup",
            module=runtime.module,
            hint_level="H0",
            outcome=outcome,
            next_move="ask",
            constraints=constraints,
            notes="Warmup phase. Respond briefly and continue with one question.",
        )

    if outcome == "incomplete":
        return BehaviorContract(
            intent="clarify",
            module=runtime.module,
            hint_level=_hint_label(runtime.hint_level),
            outcome="incomplete",
            next_move="ask",
            constraints=constraints,
            notes="Incomplete utterance. Do not infer meaning; ask one short follow-up.",
        )

    if outcome == "correct":
        return BehaviorContract(
            intent="feedback",
            module=runtime.module,
            hint_level=_hint_label(runtime.hint_level),
            outcome="correct",
            next_move="ask",
            constraints=constraints,
            notes="Near-correct answer. Brief praise then one next question.",
        )

    if outcome in {"related", "superordinate", "phonological"}:
        next_hint = min(5, runtime.hint_level + 1)
        return BehaviorContract(
            intent="hint",
            module=runtime.module,
            hint_level=_hint_label(next_hint),
            outcome=outcome,
            next_move="hint_up",
            constraints=constraints,
            notes="Partially related answer. Increase hint level and retry.",
        )

    if runtime.error_streak + 1 >= 2:
        return BehaviorContract(
            intent="switch_task",
            module=_next_module(runtime.module),
            hint_level="H0",
            outcome="unrelated",
            next_move="switch",
            constraints=constraints,
            notes="Consecutive unrelated answers. Switch task.",
        )

    return BehaviorContract(
        intent="feedback",
        module=runtime.module,
        hint_level=_hint_label(runtime.hint_level),
        outcome="unrelated",
        next_move="retry",
        constraints=constraints,
        notes="Unrelated answer. Encourage and ask one retry question.",
    )


def _build_action_text(*, contract: BehaviorContract, policy: UserPolicy) -> str:
    constraints = contract.constraints or {}
    one_question = "one question only" if _to_bool(constraints.get("one_question_only"), True) else ""

    if contract.next_move == "close":
        return "Close with a warm 1-2 sentence wrap-up. Do not start a new task."
    if contract.next_move == "confirm_stt":
        return "Ask one short confirmation question for repetition."
    if contract.outcome == "stt_uncertain":
        return "Do not infer; request one concise reconfirmation question."
    if contract.outcome == "incomplete":
        return "Treat as incomplete speech and ask one continuation-friendly question."
    if contract.outcome == "no_response":
        return "Use one gentle check-in question to re-engage."
    if contract.next_move == "switch":
        return "Do not ask for topic-switch consent; immediately continue with one first question of the new task."
    if contract.next_move == "hint_up":
        return "Provide a short hint and continue with one next question without revealing the answer."
    if contract.next_move == "retry":
        return "Do not end with only encouragement; continue with one concrete retry question."

    base = "Give brief positive feedback and continue with one natural follow-up question."
    if one_question:
        return f"{base} ({one_question})"
    return base


def _apply_contract_to_runtime(
    *,
    runtime: RuntimeSessionState,
    contract: BehaviorContract,
    policy: UserPolicy,
) -> None:
    runtime.last_outcome = contract.outcome
    runtime.next_move = contract.next_move

    if contract.next_move == "confirm_stt":
        runtime.stt_confirm_count += 1
    elif contract.outcome != "stt_uncertain":
        runtime.stt_confirm_count = 0

    if contract.next_move == "switch":
        runtime.module = _normalize_module(contract.module, default=_next_module(runtime.module))
        runtime.current_stimulus = {}
        runtime.hint_level = 0
        runtime.error_streak = 0
        runtime.difficulty = max(1, runtime.difficulty - 1)
    elif contract.next_move == "hint_up":
        runtime.hint_level = min(5, runtime.hint_level + 1)
        runtime.error_streak += 1
    elif contract.next_move == "retry":
        runtime.error_streak += 1
    elif contract.outcome == "correct":
        runtime.hint_level = 0
        runtime.error_streak = 0
        runtime.difficulty = min(5, runtime.difficulty + 1)

    if contract.next_move == "close":
        runtime.fatigue_state = "stop"
    elif runtime.error_streak >= 3:
        runtime.fatigue_state = "warning"
    else:
        runtime.fatigue_state = "normal"


# =============================================================================
# 硫붿떆吏 愿由? 媛먯젙 媛먯?, ?붿빟 媛깆떊, 吏꾨떒/?좉꼍?⑦꽩 ?댁꽍
# =============================================================================
def _append_recent_message(context: SessionContext, role: Literal["user", "assistant"], content: str) -> None:
    cleaned = _clean_text(content)
    if not cleaned:
        return  # 鍮??댁슜? 異붽??섏? ?딆쓬
    context.recent_messages.append({"role": role, "content": cleaned})
    # 理쒕? 媛쒖닔 珥덇낵 ???ㅻ옒??寃껊????쒓굅
    if len(context.recent_messages) > RECENT_MESSAGES_LIMIT:
        context.recent_messages = context.recent_messages[-RECENT_MESSAGES_LIMIT:]
    context.total_message_count += 1  # 珥?硫붿떆吏 媛쒖닔 利앷?


# 媛먯젙 ??媛먯? (?ъ슜??諛쒗솕?먯꽌 湲띿젙/遺??以묐┰ 媛먯?)
def _detect_emotional_tone(user_text: str, previous: str = "neutral") -> str:
    normalized = _clean_text(user_text).lower()
    if not normalized:
        return previous

    positive_tokens = ("좋아", "행복", "기분 좋아", "신나", "만족")
    negative_tokens = ("싫어", "힘들", "어려워", "아파", "지쳤", "무서")
    neutral_tokens = ("그냥", "보통", "괜찮")

    if any(token in normalized for token in negative_tokens):
        return "negative"
    if any(token in normalized for token in positive_tokens):
        return "positive"
    if any(token in normalized for token in neutral_tokens):
        return "neutral"
    return previous


def _refresh_summary_if_needed(context: SessionContext) -> None:
    if (context.total_message_count - context.last_summary_count) < SUMMARY_UPDATE_INTERVAL:
        return

    summary = run_llm_summary(
        existing_summary=context.conversation_summary,
        recent_messages=context.recent_messages,
        user_profile=context.user_profile,
    )
    context.conversation_summary = _sanitize_dialog_summary(
        summary,
        fallback=context.conversation_summary or DEFAULT_DIALOG_SUMMARY,
    )
    context.last_summary_count = context.total_message_count


def _resolve_diagnosis_label(
    meta_payload: dict[str, Any],
    model_result: dict[str, Any],
    context: SessionContext,
) -> str:
    explicit = _clean_text(str(meta_payload.get("diagnosis_label") or ""))
    if explicit:
        return explicit

    from_profile = _clean_text(str(context.diagnosis_label or ""))
    if from_profile:
        return from_profile

    stage = _clean_text(str(model_result.get("diagnosis_label") or model_result.get("stage") or ""))
    lowered = stage.lower()
    if "mci" in lowered or "경도 인지저하" in stage:
        return "MCI"
    return stage or "MCI"


def _resolve_neuro_pattern(
    meta_payload: dict[str, Any],
    model_result: dict[str, Any],
    context: SessionContext,
) -> list[str]:
    parsed = _parse_json_like(meta_payload.get("neuro_pattern"))
    values: list[str] = []

    if isinstance(parsed, list):
        values.extend([_clean_text(str(item)) for item in parsed if _clean_text(str(item))])
    elif isinstance(parsed, str) and _clean_text(parsed):
        values.append(_clean_text(parsed))

    if not values and context.neuro_pattern:
        values.extend([_clean_text(str(item)) for item in context.neuro_pattern if _clean_text(str(item))])

    model_pattern = _parse_json_like(model_result.get("neuro_pattern"))
    if isinstance(model_pattern, list):
        values.extend([_clean_text(str(item)) for item in model_pattern if _clean_text(str(item))])
    elif isinstance(model_pattern, str) and _clean_text(model_pattern):
        values.append(_clean_text(model_pattern))

    main_region = _clean_text(str(model_result.get("main_region") or ""))
    if main_region:
        values.append(main_region)

    # Optional structured region scores from future model outputs.
    region_scores = _parse_json_like(model_result.get("region_scores"))
    if isinstance(region_scores, dict):
        for key, score in region_scores.items():
            normalized_key = _clean_text(str(key))
            if not normalized_key:
                continue
            score_value = _safe_float(score, 0.0)
            if score_value > 0:
                values.append(normalized_key)

    return _canonicalize_neuro_pattern(values)


def _finalize_closing_reply(reply: str, *, conversation_summary: str, user_text: str) -> str:
    text = _clean_text(reply)
    if not text:
        # ?묐떟??鍮꾩뼱?덉쑝硫?????붿빟?대굹 ?ъ슜??諛쒗솕 湲곕컲?쇰줈 ?앹꽦
        if conversation_summary:
            first = re.split(r"[.!?]+", conversation_summary)[0].strip()
            if first:
                return f"{first}. 오늘은 여기까지 할게요."
        if user_text:
            return f"오늘 '{user_text[:24]}' 이야기를 나눴어요. 여기서 마칠게요."
        return "오늘 대화는 여기서 마칠게요."

    # 臾쇱쓬?쒕? 留덉묠?쒕줈 蹂寃?(吏덈Ц ?쒓굅)
    text = text.replace("?", ".")
    # ?얜챷???브쑬??
    sentences = [segment.strip() for segment in re.split(r"[.!?]+", text) if segment.strip()]
    if not sentences:
        return "오늘 대화는 여기서 마칠게요."
    if len(sentences) == 1:
        return f"{sentences[0]}."
    # 理쒕? 2臾몄옣?쇰줈 ?쒗븳
    return f"{sentences[0]}. {sentences[1]}."


# =============================================================================
# 吏곷젹?? 濡쒓렇 湲곕줉, ?뚯씪 ????좏떥由ы떚
# =============================================================================
def serialize_state(state: DialogState) -> dict[str, Any]:
    if hasattr(state, "model_dump"):
        return state.model_dump()
    return asdict(state)


def append_transcript(text: str) -> None:
    with TRANSCRIPT_PATH.open("a", encoding="utf-8") as transcript_file:
        transcript_file.write(text + "\n")


# ?꾩껜 ???濡쒓렇 ?뚯씪????꾩뒪?ы봽? ?띿뒪??異붽?
def append_conversation(role: Literal["user", "assistant"], text: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    cleaned = text.replace("\n", " ").strip()
    with CONVERSATION_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {role}: {cleaned}\n")


def sanitize_session_id(raw_session_id: str) -> str:
    allowed = {"-", "_"}
    cleaned = "".join(
        char if char.isalnum() or char in allowed else "_"
        for char in raw_session_id.strip()
    )
    return cleaned[:120] or "unknown_session"


def get_session_dir(base_dir: Path, patient_id: str, session_id: str) -> Path:
    safe_patient = sanitize_session_id(patient_id or "unknown_patient")
    safe_session = sanitize_session_id(session_id or "unknown_session")
    target = base_dir / safe_patient / safe_session
    target.mkdir(parents=True, exist_ok=True)
    return target


def _create_turn_id(session_id: str, turn_index: int) -> str:
    _ = session_id
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    rand6 = uuid.uuid4().hex[:6]
    safe_index = max(0, _safe_int(turn_index, 0))
    return f"t_{timestamp}_{rand6}_{safe_index:04d}"


def normalize_transcript(raw_text: str) -> str:
    if not raw_text:
        return ""
    cleaned_chars: list[str] = []
    for ch in raw_text:
        if unicodedata.category(ch).startswith("C"):
            cleaned_chars.append(" ")
        else:
            cleaned_chars.append(ch)
    cleaned = "".join(cleaned_chars)
    return re.sub(r"\s+", " ", cleaned).strip()


def _get_turn_log_path(patient_id: str, session_id: str) -> Path:
    safe_patient = sanitize_session_id(patient_id or "unknown_patient")
    safe_session = sanitize_session_id(session_id or "unknown_session")
    target_dir = LOGS_DIR / safe_patient
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{safe_session}.jsonl"


def _save_audio_files_sync(
    patient_id: str,
    session_id: str,
    turn_id: str,
    original_bytes: bytes,
    converted_path_or_none: str | Path | None,
) -> None:
    session_dir = get_session_dir(AUDIO_WAV_DIR, patient_id, session_id)
    original_path = session_dir / f"{turn_id}.original.wav"
    final_path = session_dir / f"{turn_id}.wav"
    original_path.write_bytes(original_bytes)
    source_path = Path(converted_path_or_none) if converted_path_or_none else None
    if source_path and source_path.exists():
        with source_path.open("rb") as src, final_path.open("wb") as dst:
            dst.write(src.read())
        try:
            source_path.unlink()
        except Exception:
            pass
    else:
        final_path.write_bytes(original_bytes)


async def save_audio_files_async(
    patient_id: str,
    session_id: str,
    turn_id: str,
    original_bytes: bytes,
    converted_path_or_none: str | Path | None,
) -> None:
    await asyncio.to_thread(
        _save_audio_files_sync,
        patient_id,
        session_id,
        turn_id,
        original_bytes,
        converted_path_or_none,
    )


def _save_text_files_sync(
    patient_id: str,
    session_id: str,
    turn_id: str,
    raw_text: str,
    norm_text: str,
) -> None:
    session_dir = get_session_dir(TEXT_DIR, patient_id, session_id)
    (session_dir / f"{turn_id}.transcript_raw.txt").write_text(raw_text or "", encoding="utf-8")
    (session_dir / f"{turn_id}.transcript_norm.txt").write_text(norm_text or "", encoding="utf-8")


async def save_text_files_async(
    patient_id: str,
    session_id: str,
    turn_id: str,
    raw_text: str,
    norm_text: str,
) -> None:
    await asyncio.to_thread(
        _save_text_files_sync,
        patient_id,
        session_id,
        turn_id,
        raw_text,
        norm_text,
    )


def _save_metadata_sync(
    patient_id: str,
    session_id: str,
    turn_id: str,
    contract_dict: dict[str, Any],
    stimulus_dict_or_none: dict[str, Any] | None,
) -> None:
    session_dir = get_session_dir(META_DIR, patient_id, session_id)
    (session_dir / f"{turn_id}.contract.json").write_text(
        json.dumps(contract_dict or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if isinstance(stimulus_dict_or_none, dict) and stimulus_dict_or_none:
        (session_dir / f"{turn_id}.stimulus.json").write_text(
            json.dumps(stimulus_dict_or_none, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


async def save_metadata_async(
    patient_id: str,
    session_id: str,
    turn_id: str,
    contract_dict: dict[str, Any],
    stimulus_dict_or_none: dict[str, Any] | None,
) -> None:
    await asyncio.to_thread(
        _save_metadata_sync,
        patient_id,
        session_id,
        turn_id,
        contract_dict,
        stimulus_dict_or_none,
    )


def _save_assistant_data_sync(
    patient_id: str,
    session_id: str,
    turn_id: str,
    text: str,
    audio_bytes: bytes,
) -> None:
    text_dir = get_session_dir(TEXT_DIR, patient_id, session_id)
    audio_dir = get_session_dir(AUDIO_TTS_DIR, patient_id, session_id)
    (text_dir / f"{turn_id}.assistant.txt").write_text(text or "", encoding="utf-8")
    (audio_dir / f"{turn_id}.mp3").write_bytes(audio_bytes)


async def save_assistant_data_async(
    patient_id: str,
    session_id: str,
    turn_id: str,
    text: str,
    audio_bytes: bytes,
) -> None:
    await asyncio.to_thread(
        _save_assistant_data_sync,
        patient_id,
        session_id,
        turn_id,
        text,
        audio_bytes,
    )


def _append_turn_log_sync(
    patient_id: str,
    session_id: str,
    turn_log_dict: dict[str, Any],
) -> None:
    path = _get_turn_log_path(patient_id, session_id)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(turn_log_dict, ensure_ascii=False) + "\n")


async def append_turn_log_async(
    patient_id: str,
    session_id: str,
    turn_log_dict: dict[str, Any],
) -> None:
    await asyncio.to_thread(
        _append_turn_log_sync,
        patient_id,
        session_id,
        turn_log_dict,
    )


def _schedule_background(coro: Any) -> None:
    task = asyncio.create_task(coro)

    def _on_done(done_task: asyncio.Task[Any]) -> None:
        try:
            done_task.result()
        except asyncio.CancelledError:
            return
        except Exception as exc:
            # Keep request path fast; background save failures are logged only.
            print(f"[background-save-error] {exc}")

    task.add_done_callback(_on_done)


def _count_sentences(text: str) -> int:
    cleaned = _clean_text(text)
    if not cleaned:
        return 0
    parts = [segment.strip() for segment in re.split(r"[.!?]+", cleaned) if segment.strip()]
    return len(parts)


def _count_questions(text: str) -> int:
    return str(text or "").count("?")


def _build_uncertainty_features(
    *,
    is_speech_detected: bool,
    is_recognized: bool,
    recognition_confidence: float,
    transcript_length: int,
    recognition_failed: bool,
) -> tuple[float, dict[str, Any]]:
    clipped_conf = min(1.0, max(0.0, float(recognition_confidence)))
    short_text = transcript_length < 3
    no_text = transcript_length == 0
    features = {
        "recognition_confidence": clipped_conf,
        "is_speech_detected": bool(is_speech_detected),
        "is_recognized": bool(is_recognized),
        "transcript_length": int(transcript_length),
        "recognition_failed": bool(recognition_failed),
        "short_text": short_text,
        "no_text": no_text,
    }

    score = 0.0
    score += (1.0 - clipped_conf) * 0.6
    if recognition_failed:
        score += 0.25
    if short_text:
        score += 0.10
    if no_text:
        score += 0.25
    if (not is_speech_detected) and no_text:
        score = max(score, 0.95)
    score = max(0.0, min(1.0, score))
    return score, features


def get_session_log_path(session_id: str) -> Path:
    SESSION_LOG_DIR.mkdir(exist_ok=True)
    safe_session_id = sanitize_session_id(session_id)
    return SESSION_LOG_DIR / f"{safe_session_id}.log"


def append_session_conversation(session_id: str, role: Literal["user", "assistant"], text: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    cleaned = text.replace("\n", " ").strip()
    log_path = get_session_log_path(session_id)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {role}: {cleaned}\n")


# ?몄뀡蹂??대깽??濡쒓렇 異붽?
def append_session_event(session_id: str, event_name: str, payload: dict[str, Any]) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    log_path = get_session_log_path(session_id)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] event:{event_name} {json.dumps(payload, ensure_ascii=False)}\n")


def get_session_trace_path(session_id: str) -> Path:
    SESSION_TRACE_DIR.mkdir(exist_ok=True)
    safe_session_id = sanitize_session_id(session_id)
    return SESSION_TRACE_DIR / f"{safe_session_id}.jsonl"


def append_session_trace(session_id: str, trace_type: str, payload: dict[str, Any]) -> None:
    trace_path = get_session_trace_path(session_id)
    envelope = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_type": _clean_text(trace_type) or "unknown",
        "payload": payload if isinstance(payload, dict) else {"raw": str(payload)},
    }
    with trace_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(envelope, ensure_ascii=False) + "\n")


def _load_session_trace_entries(session_id: str, limit: int) -> list[dict[str, Any]]:
    trace_path = get_session_trace_path(session_id)
    if not trace_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with trace_path.open("r", encoding="utf-8") as file:
        for line_no, line in enumerate(file, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    entries.append(parsed)
                else:
                    entries.append({
                        "timestamp": None,
                        "trace_type": "raw_non_object",
                        "payload": {"line_no": line_no, "raw": raw},
                    })
            except Exception:
                entries.append({
                    "timestamp": None,
                    "trace_type": "raw_unparsed",
                    "payload": {"line_no": line_no, "raw": raw},
                })

    safe_limit = max(1, min(MAX_TRACE_READ_LIMIT, _safe_int(limit, 200)))
    return entries[-safe_limit:]


def save_audio_permanently(temp_path: Path, session_id: str) -> Path:
    AUDIO_SAVE_DIR.mkdir(exist_ok=True)

    safe_session_id = sanitize_session_id(session_id)
    session_folder = AUDIO_SAVE_DIR / safe_session_id
    session_folder.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    suffix = temp_path.suffix or ".webm"
    target_path = session_folder / f"{timestamp}{suffix}"

    temp_path.rename(target_path)
    return target_path


def _resolve_patient_id_for_archive(session_id: str, context: SessionContext | None) -> str:
    candidates: list[str] = []
    if isinstance(context, SessionContext):
        candidates.append(_clean_text(str(context.profile_id or "")))
        profile_id = context.user_profile.get("profile_id") if isinstance(context.user_profile, dict) else ""
        candidates.append(_clean_text(str(profile_id or "")))

    for candidate in candidates:
        if candidate:
            return sanitize_session_id(candidate)

    safe_session = sanitize_session_id(session_id)
    base_dirs = (AUDIO_WAV_DIR, TEXT_DIR, AUDIO_TTS_DIR, META_DIR)
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue
        for patient_dir in base_dir.iterdir():
            if not patient_dir.is_dir():
                continue
            if (patient_dir / safe_session).exists():
                return patient_dir.name

    if LOGS_DIR.exists():
        for patient_dir in LOGS_DIR.iterdir():
            if not patient_dir.is_dir():
                continue
            if (patient_dir / f"{safe_session}.jsonl").exists():
                return patient_dir.name

    return "unknown_patient"


def _read_dialog_lines_from_session_log(session_id: str) -> list[str]:
    log_path = get_session_log_path(session_id)
    if not log_path.exists():
        return []

    lines: list[str] = []
    with log_path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue
            _, _, suffix = line.partition("] ")
            body = suffix or line
            if body.startswith("user: "):
                user_text = _clean_text(body[len("user: "):])
                if user_text:
                    lines.append(user_text)
    return lines


def _collect_turn_wav_paths(patient_id: str, session_id: str) -> list[Path]:
    safe_patient = sanitize_session_id(patient_id or "unknown_patient")
    safe_session = sanitize_session_id(session_id or "unknown_session")
    session_dir = AUDIO_WAV_DIR / safe_patient / safe_session
    if not session_dir.exists():
        return []

    wav_paths: list[Path] = []
    for path in session_dir.glob("*.wav"):
        lower_name = path.name.lower()
        if lower_name.endswith(".original.wav"):
            continue
        wav_paths.append(path)
    wav_paths.sort(key=lambda p: p.name)
    return wav_paths


def _concat_wav_files(wav_paths: list[Path], output_path: Path) -> dict[str, Any]:
    merged_files = 0
    skipped_files = 0
    total_frames = 0
    base_params: tuple[int, int, int] | None = None

    if not wav_paths:
        return {
            "merged_files": 0,
            "skipped_files": 0,
            "duration_sec": 0.0,
            "sample_rate": None,
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as dst:
        for wav_path in wav_paths:
            try:
                with wave.open(str(wav_path), "rb") as src:
                    params = (src.getnchannels(), src.getsampwidth(), src.getframerate())
                    if base_params is None:
                        base_params = params
                        dst.setnchannels(params[0])
                        dst.setsampwidth(params[1])
                        dst.setframerate(params[2])
                    if params != base_params:
                        skipped_files += 1
                        continue
                    frame_count = src.getnframes()
                    dst.writeframes(src.readframes(frame_count))
                    total_frames += int(frame_count)
                    merged_files += 1
            except Exception:
                skipped_files += 1

    if merged_files <= 0:
        try:
            output_path.unlink()
        except Exception:
            pass
        return {
            "merged_files": 0,
            "skipped_files": skipped_files,
            "duration_sec": 0.0,
            "sample_rate": None,
        }

    sample_rate = base_params[2] if base_params else 0
    duration_sec = (total_frames / float(sample_rate)) if sample_rate > 0 else 0.0
    return {
        "merged_files": merged_files,
        "skipped_files": skipped_files,
        "duration_sec": round(duration_sec, 3),
        "sample_rate": sample_rate or None,
    }


def _remove_dir_quietly(target_dir: Path) -> None:
    try:
        if target_dir.exists() and target_dir.is_dir():
            shutil.rmtree(target_dir)
    except Exception:
        pass


def _archive_session_outputs(session_id: str, context: SessionContext | None) -> dict[str, Any]:
    safe_session = sanitize_session_id(session_id)
    patient_id = _resolve_patient_id_for_archive(safe_session, context)
    archive_dir = get_session_dir(SESSION_ARCHIVE_DIR, patient_id, safe_session)

    dialog_lines = _read_dialog_lines_from_session_log(safe_session)
    if not dialog_lines and isinstance(context, SessionContext):
        for message in context.recent_messages:
            role = _clean_text(str(message.get("role") or ""))
            content = _clean_text(str(message.get("content") or ""))
            if role == "user" and content:
                dialog_lines.append(content)

    text_path = archive_dir / "conversation.txt"
    text_body = "\n".join(dialog_lines).strip()
    text_path.write_text(f"{text_body}\n" if text_body else "", encoding="utf-8")

    wav_paths = _collect_turn_wav_paths(patient_id, safe_session)
    audio_path: Path | None = None
    wav_summary = {
        "merged_files": 0,
        "skipped_files": 0,
        "duration_sec": 0.0,
        "sample_rate": None,
    }
    existing_session_audio: Path | None = None
    existing_candidates = sorted(archive_dir.glob("conversation.user.*"))
    if existing_candidates:
        # Prefer WAV if it already exists, otherwise pick the first deterministic file.
        wav_candidate = next((path for path in existing_candidates if path.suffix.lower() == ".wav"), None)
        existing_session_audio = wav_candidate or existing_candidates[0]

    if wav_paths:
        audio_path = archive_dir / "conversation.user.wav"
        wav_summary = _concat_wav_files(wav_paths, audio_path)
        if wav_summary.get("merged_files", 0) <= 0:
            audio_path = None
    elif existing_session_audio and existing_session_audio.exists():
        audio_path = existing_session_audio
        wav_summary = {
            "merged_files": 1,
            "skipped_files": 0,
            "duration_sec": 0.0,
            "sample_rate": None,
            "source": "uploaded_session_audio",
        }

    # Remove turn-level files after creating session-level archive.
    _remove_dir_quietly(AUDIO_WAV_DIR / patient_id / safe_session)
    _remove_dir_quietly(TEXT_DIR / patient_id / safe_session)
    _remove_dir_quietly(AUDIO_TTS_DIR / patient_id / safe_session)
    _remove_dir_quietly(AUDIO_SAVE_DIR / safe_session)

    return {
        "ok": True,
        "patient_id": patient_id,
        "session_id": safe_session,
        "text_path": str(text_path),
        "audio_path": str(audio_path) if audio_path else None,
        "dialog_line_count": len(dialog_lines),
        "audio_summary": wav_summary,
    }


def _audio_suffix_from_upload(file: UploadFile) -> str:
    from_name = Path(file.filename or "").suffix.lower()
    if from_name in {".wav", ".webm", ".mp3", ".m4a", ".ogg"}:
        return from_name

    content_type = _clean_text(str(file.content_type or "")).lower()
    if "wav" in content_type:
        return ".wav"
    if "webm" in content_type:
        return ".webm"
    if "mpeg" in content_type or "mp3" in content_type:
        return ".mp3"
    if "mp4" in content_type or "m4a" in content_type:
        return ".m4a"
    if "ogg" in content_type:
        return ".ogg"
    return ".bin"


async def save_upload_to_temp(file: UploadFile) -> Path:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    TEMP_AUDIO_DIR.mkdir(exist_ok=True)
    suffix = Path(file.filename).suffix or ".webm"

    with tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False,
        dir=TEMP_AUDIO_DIR,
        suffix=suffix,
    ) as temp_audio_file:
        temp_path = Path(temp_audio_file.name)
        while chunk := await file.read(1024 * 1024):
            temp_audio_file.write(chunk)
        return temp_path


def parse_json_object_form(
    raw_value: str | None,
    *,
    field_name: str,
    default: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if raw_value is None or not raw_value.strip():
        return default  # 媛믪씠 ?놁쑝硫?湲곕낯媛?諛섑솚
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"'{field_name}' must be a valid JSON object.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail=f"'{field_name}' must be a JSON object.")
    return parsed


# ?곹깭 ?섏씠濡쒕뱶?먯꽌 硫뷀? ?뺣낫 異붿텧
def _extract_state_meta(state_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(state_payload, dict):
        return {}
    candidate = state_payload.get("meta")
    if isinstance(candidate, dict):
        return candidate
    return {}


def _normalize_client_event_name(name: Any) -> str:
    normalized = _clean_text(str(name or "")).lower().replace("-", "_")
    return normalized or "unknown"


def _remember_event_id(runtime: RuntimeSessionState, event_id: str) -> bool:
    normalized = _clean_text(event_id)
    if not normalized:
        return False
    if normalized in runtime.recent_event_ids:
        return True  # ?대? ?덉쑝硫?以묐났
    runtime.recent_event_ids.append(normalized)
    # 理쒕? 媛쒖닔 珥덇낵 ???ㅻ옒??寃껊????쒓굅
    if len(runtime.recent_event_ids) > MAX_EVENT_ID_HISTORY:
        runtime.recent_event_ids = runtime.recent_event_ids[-MAX_EVENT_ID_HISTORY:]
    return False  # ?덈줈??ID


# ?????녿뒗 ?대깽??湲곕줉
def _record_unknown_event(session_id: str, reason: str, payload: dict[str, Any] | None = None) -> None:
    append_session_event(
        session_id,
        "event_unknown",
        {
            "reason": reason,
            "payload": payload or {},
        },
    )


def _contract_to_dict(contract: BehaviorContract) -> dict[str, Any]:
    return {
        "intent": contract.intent,
        "module": contract.module,
        "hint_level": contract.hint_level,
        "outcome": contract.outcome,
        "next_move": contract.next_move,
        "constraints": contract.constraints,
        "stimulus": contract.stimulus,
        "notes": contract.notes,
    }


def _build_turn_phase(runtime: RuntimeSessionState, policy: UserPolicy, request_close: bool) -> str:
    if request_close or runtime.next_move == "close":
        return "closing"  # 醫낅즺 ?④퀎
    if runtime.user_turn_count <= policy.warmup_turns:
        return "warmup"  # ?뚮컢???④퀎
    return "dialog"  # ?쇰컲 ????④퀎


# =============================================================================
# ?듭떖 ???ㅽ뻾 濡쒖쭅 (?ъ슜??諛쒗솕 ??遺꾨쪟 ???됰룞 怨꾩빟 ??LLM ?몄텧 ???묐떟)
# =============================================================================
def _execute_turn(
    *,
    session_id: str,
    context: SessionContext,
    runtime: RuntimeSessionState,
    policy: UserPolicy,
    user_text: str,
    model_result: dict[str, Any],
    incoming_meta: dict[str, Any],
    request_close_override: bool | None = None,
) -> dict[str, Any]:
    # 寃쎄낵 ?쒓컙 ?낅뜲?댄듃
    context.elapsed_time = _safe_int(incoming_meta.get("elapsed_sec"), context.elapsed_time)
    context.conversation_summary = _sanitize_dialog_summary(
        context.conversation_summary,
        fallback=DEFAULT_DIALOG_SUMMARY,
    )
    # 醫낅즺 ?붿껌 ?뺤씤
    explicit_close = _to_bool(incoming_meta.get("request_close"), default=context.request_close)
    if request_close_override is not None:
        explicit_close = bool(request_close_override)
    context.request_close = explicit_close

    # ?몄뀡 ?щ’ 寃곗젙 (?쒓컙?)
    session_slot = (
        _normalize_session_slot(incoming_meta.get("session_slot"))
        or _normalize_session_slot(context.session_slot)
        or _infer_session_slot()
    )
    next_session_slot = (
        _normalize_session_slot(incoming_meta.get("next_session_slot"))
        or _normalize_session_slot(context.next_session_slot)
        or _get_next_session_slot(session_slot)
    )
    context.session_slot = session_slot
    context.next_session_slot = next_session_slot
    now_kst = datetime.now(KST_TZ)
    time_context = _build_kst_time_context(
        session_slot=session_slot,
        next_session_slot=next_session_slot,
        now_kst=now_kst,
    )
    
    # ???紐⑤뱶 ?낅뜲?댄듃
    incoming_mode = _normalize_conversation_mode(incoming_meta.get("conversation_mode"))
    if incoming_mode:
        context.conversation_mode = incoming_mode

    # 吏꾨떒 諛??좉꼍?숈쟻 ?⑦꽩 寃곗젙
    diagnosis_label = _resolve_diagnosis_label(incoming_meta, model_result, context)
    neuro_pattern = _resolve_neuro_pattern(incoming_meta, model_result, context)
    context.diagnosis_label = diagnosis_label
    context.neuro_pattern = neuro_pattern
    
    # ?덈젴 ?좏삎 諛??쒖씠??寃곗젙
    default_training_type = _module_to_training_type(_default_module_by_profile(neuro_pattern))
    incoming_training_type = _clean_text(str(incoming_meta.get("training_type") or ""))
    incoming_module = _clean_text(str(incoming_meta.get("module") or ""))
    context.training_type = _normalize_training_type(
        incoming_training_type or context.training_type,
        default=default_training_type,
    )
    context.training_level = max(1, _safe_int(incoming_meta.get("training_level"), runtime.difficulty))
    if incoming_module:
        runtime.module = _normalize_module(incoming_module, default=runtime.module)
    elif incoming_training_type:
        runtime.module = _training_type_to_module(context.training_type)
    runtime.difficulty = max(1, _safe_int(context.training_level, runtime.difficulty))

    # ?몄? ?꾨줈???낅뜲?댄듃 (?붾?+?ъ슜??紐⑤뜽 ?낅젰 寃고빀)
    profile_seed = dict(context.cognitive_profile) if isinstance(context.cognitive_profile, dict) else {}
    parsed_profile = _parse_json_like(incoming_meta.get("cognitive_profile"))
    if isinstance(parsed_profile, dict):
        profile_seed.update(parsed_profile)
    context.cognitive_profile = _build_cognitive_training_profile(
        diagnosis_label=diagnosis_label,
        neuro_pattern=neuro_pattern,
        model_result=model_result,
        session_slot=session_slot,
        next_session_slot=next_session_slot,
        base_profile=profile_seed,
    )

    previous_user_text = ""
    for message in reversed(context.recent_messages):
        if str(message.get("role") or "").lower() != "user":
            continue
        previous_user_text = _clean_text(str(message.get("content") or ""))
        if previous_user_text:
            break

    # ?ъ슜??諛쒗솕 泥섎━
    cleaned_user_text = _clean_text(user_text)
    user_time_reference = _has_time_reference(cleaned_user_text)
    if cleaned_user_text:
        _append_recent_message(context, "user", cleaned_user_text)
        context.emotional_tone = _detect_emotional_tone(cleaned_user_text, context.emotional_tone)

    # STT 愿???뺣낫 異붿텧
    stt_event = _clean_text(str(incoming_meta.get("stt_event") or "")).lower()
    is_speech_detected = _to_bool(incoming_meta.get("is_speech_detected"), default=bool(cleaned_user_text))
    is_recognized = _to_bool(incoming_meta.get("is_recognized"), default=bool(cleaned_user_text))
    recognition_confidence = _safe_float(incoming_meta.get("recognition_confidence"), 1.0 if cleaned_user_text else 0.0)
    stt_uncertain = _to_bool(incoming_meta.get("recognition_failed"), default=False)
    # STT 遺덊솗??議곌굔: 紐낆떆???ㅽ뙣 ?먮뒗 ?뚯꽦 媛먯??섏뿀?쇰굹 ?몄떇 ?????먮뒗 ?좊ː?꾧? ??쓬
    stt_uncertain = stt_uncertain or (is_speech_detected and ((not is_recognized) or recognition_confidence < 0.45))
    no_response = (stt_event == "no_speech") or (not cleaned_user_text)
    user_input_incremental = (
        bool(cleaned_user_text)
        and bool(previous_user_text)
        and _is_incremental_user_update(cleaned_user_text, previous_user_text)
    )
    user_input_incomplete = (
        bool(cleaned_user_text)
        and (not no_response)
        and (not stt_uncertain)
        and (_is_incomplete_utterance(cleaned_user_text) or user_input_incremental)
    )

    # 移⑤У 愿???곹깭 ?낅뜲?댄듃
    if no_response:
        runtime.silence_streak += 1
        runtime.silence_duration = _safe_int(incoming_meta.get("silence_duration"), runtime.silence_duration) + SILENCE_TURN_INCREMENT_SEC
    else:
        runtime.silence_streak = 0
        runtime.silence_duration = 0

    # STT 遺덊솗??愿???곹깭 ?낅뜲?댄듃
    if stt_uncertain:
        runtime.stt_uncertain_streak += 1
        runtime.consecutive_failures += 1
    else:
        runtime.stt_uncertain_streak = 0
        runtime.consecutive_failures = 0
        if not no_response:
            runtime.stt_confirm_count = 0

    # ??移댁슫??利앷?
    runtime.turn_count += 1
    if cleaned_user_text and not stt_uncertain and not no_response:
        runtime.user_turn_count += 1  # ?좏슚???ъ슜???대쭔 移댁슫??
    # ?덈젴 ?쒖꽦???щ? ?먮떒 諛??먭레 ?뺣낫
    training_active = runtime.user_turn_count > policy.warmup_turns
    if training_active:
        _ensure_stimulus(context=context, runtime=runtime, policy=policy, force_new=False)
    else:
        runtime.current_stimulus = {}  # ?뚮컢??以묒뿉???먭레 ?놁쓬

    # ?묐떟 寃곌낵 遺꾨쪟
    outcome = _classify_outcome(
        user_text=cleaned_user_text,
        stimulus=runtime.current_stimulus,
        no_response=no_response,
        stt_uncertain=stt_uncertain,
        training_active=training_active,
        user_input_incomplete=user_input_incomplete,
    )

    # ?됰룞 怨꾩빟 寃곗젙
    contract = _decide_behavior_contract(
        runtime=runtime,
        policy=policy,
        request_close=explicit_close,
        no_response=no_response,
        stt_uncertain=stt_uncertain,
        outcome=outcome,
        training_active=training_active,
    )

    # 怨쇱젣 ?꾪솚 ?????먭레 ?앹꽦
    if contract.next_move == "switch":
        runtime.module = _normalize_module(contract.module, default=_next_module(runtime.module))
        runtime.current_stimulus = {}
        _ensure_stimulus(context=context, runtime=runtime, policy=policy, force_new=True)
        contract.stimulus = runtime.current_stimulus
    elif training_active and runtime.current_stimulus:
        contract.stimulus = runtime.current_stimulus

    # LLM???꾨떖???≪뀡 ?띿뒪??諛?硫뷀? ?뺣낫 援ъ꽦
    action_text = _build_action_text(contract=contract, policy=policy)
    if user_time_reference and contract.next_move != "close":
        action_text = (
            f"{action_text} 사용자가 시간 표현을 말하면 한국 시간(Asia/Seoul) 기준으로 "
            "현재 시각을 짧게 확인하고, 같은 흐름에서 질문 1개를 이어가세요."
        )
    turn_phase = _build_turn_phase(runtime, policy, explicit_close or contract.next_move == "close")
    if turn_phase == "warmup":
        dialog_phase = "opening"
    elif turn_phase == "closing":
        dialog_phase = "closing"
    else:
        dialog_phase = "dialog"

    runtime_meta = {
        **incoming_meta,
        "session_id": session_id,
        "conversation_phase": dialog_phase,
        "request_close": explicit_close or contract.next_move == "close",
        "training_type": _module_to_training_type(contract.module),
        "training_level": runtime.difficulty,
        "training_step": runtime.hint_level,
        "fatigue_state": _normalize_fatigue_state(runtime.fatigue_state),
        "silence_duration": runtime.silence_duration,
        "recognition_failed": stt_uncertain,
        "consecutive_failures": runtime.consecutive_failures,
        "stt_event": "no_speech" if no_response else ("stt_error" if stt_uncertain else "speech"),
        "user_input_incomplete": user_input_incomplete,
        "user_input_incremental": user_input_incremental,
        "training_active": training_active,
        "time_context": time_context,
        "user_time_reference": user_time_reference,
        "behavior_contract": _contract_to_dict(contract),
        "action_text": action_text,
        "memory_summary": context.conversation_summary,
        "used_phrases": runtime.used_phrases[-12:],  # 理쒓렐 12媛쒕쭔
        "llm_model": policy.llm_model,
        "llm_fallback_model": policy.llm_fallback_model,
    }

    # LLM ?몄텧 (?꾩옱 ?ъ슜??諛쒗솕???덉뒪?좊━?먯꽌 ?쒖쇅)
    history_without_current = context.recent_messages[:-1] if cleaned_user_text else context.recent_messages
    llm_started = time.perf_counter()
    reply = run_llm(
        user_text=cleaned_user_text,
        dialog_state=runtime.dialog_state,
        model_result=model_result or {},
        meta=runtime_meta,
        conversation_history=history_without_current,
        conversation_summary=context.conversation_summary,
        recent_messages=context.recent_messages,
        user_profile={
            **context.user_profile,
            "policy": asdict(policy),
            "cognitive_profile": context.cognitive_profile,
            "time_context": time_context,
        },
        request_close=explicit_close or contract.next_move == "close",
        silence_duration=runtime.silence_duration,
        recognition_failed=stt_uncertain,
        consecutive_failures=runtime.consecutive_failures,
    )
    llm_duration_ms = int((time.perf_counter() - llm_started) * 1000)

    # 醫낅즺 ?묐떟 理쒖쥌 泥섎━
    if explicit_close or contract.next_move == "close":
        reply = _finalize_closing_reply(
            reply,
            conversation_summary=context.conversation_summary,
            user_text=cleaned_user_text,
        )
        context.request_close = True

    # 怨꾩빟???고??꾩뿉 ?곸슜
    _apply_contract_to_runtime(runtime=runtime, contract=contract, policy=policy)
    context.training_type = _module_to_training_type(runtime.module)
    context.training_level = runtime.difficulty
    # ?묐떟??理쒓렐 硫붿떆吏??異붽?
    _append_recent_message(context, "assistant", reply)
    _append_used_phrase(runtime, reply)
    # ?꾩슂 ??????붿빟 媛깆떊
    _refresh_summary_if_needed(context)
    context.conversation_summary = _sanitize_dialog_summary(
        context.conversation_summary,
        fallback=DEFAULT_DIALOG_SUMMARY,
    )

    # DialogState ?낅뜲?댄듃
    dialog_state = runtime.dialog_state
    dialog_state.turn_index = runtime.turn_count
    dialog_state.elapsed_sec = context.elapsed_time
    dialog_state.last_user_utterance = cleaned_user_text
    dialog_state.last_assistant_utterance = reply
    dialog_state.training_type = _module_to_training_type(runtime.module)
    dialog_state.training_level = runtime.difficulty
    dialog_state.training_step = runtime.hint_level
    dialog_state.memory_summary = context.conversation_summary
    dialog_state.fatigue_level = _to_fatigue_level(runtime.fatigue_state)
    dialog_state.conversation_phase = "closing" if context.request_close else dialog_phase
    dialog_state.dialog_state = "session_wrap" if context.request_close else "cognitive_training"

    # 嚥≪뮄??疫꿸퀡以?
    append_conversation("user", cleaned_user_text or "[no_speech]")
    append_conversation("assistant", reply)
    append_session_conversation(session_id, "user", cleaned_user_text or "[no_speech]")
    append_session_conversation(session_id, "assistant", reply)

    medical_topic = bool(context.conversation_mode == "therapy")
    response_meta = {
        "conversation_phase": "closing" if context.request_close else dialog_phase,
        "turn_index": dialog_state.turn_index,
        "request_close": context.request_close,
        "conversation_mode": context.conversation_mode,
        "medical_topic": medical_topic,
        "session_slot": session_slot,
        "session_slot_label": _get_session_label(session_slot),
        "next_session_slot": next_session_slot,
        "next_session_slot_label": _get_session_label(next_session_slot),
        "time_context": time_context,
        "diagnosis_label": diagnosis_label,
        "neuro_pattern": neuro_pattern,
        "active_regions": _list_from_any(context.cognitive_profile.get("active_regions"))[:6]
        if isinstance(context.cognitive_profile, dict)
        else [],
        "task_families": _list_from_any(context.cognitive_profile.get("task_families"))[:8]
        if isinstance(context.cognitive_profile, dict)
        else [],
        "training_type": _module_to_training_type(runtime.module),
        "training_level": runtime.difficulty,
        "training_step": runtime.hint_level,
        "fatigue_state": runtime.fatigue_state,
        "silence_duration": runtime.silence_duration,
        "recognition_failed": stt_uncertain,
        "consecutive_failures": runtime.consecutive_failures,
        "intent": contract.intent,
        "module": contract.module,
        "hint_level": contract.hint_level,
        "outcome": contract.outcome,
        "next_move": contract.next_move,
        "constraints": contract.constraints,
        "decision_notes": contract.notes,
        "used_stimuli_count": len(runtime.used_stimuli),
        "used_phrases_count": len(runtime.used_phrases),
        "stimulus_enabled": bool(runtime.current_stimulus),
        "stimulus_count": len(runtime.used_stimuli),
        "training_item": runtime.current_stimulus,
        "policy_id": incoming_meta.get("policy_id") or "mci_dummy",
        "llm_model": policy.llm_model,
        "stt_model": policy.stt_model,
        "tts_voice": policy.tts_voice,
    }

    append_session_trace(
        session_id,
        "llm_turn",
        {
            "turn_index": dialog_state.turn_index,
            "phase": response_meta["conversation_phase"],
            "user_text": cleaned_user_text or "",
            "assistant_text": reply,
            "behavior_contract": _contract_to_dict(contract),
            "action_text": action_text,
            "runtime_meta": {
                "stt_event": runtime_meta.get("stt_event"),
                "silence_duration": runtime_meta.get("silence_duration"),
                "recognition_failed": runtime_meta.get("recognition_failed"),
                "consecutive_failures": runtime_meta.get("consecutive_failures"),
            },
            "response_meta": response_meta,
            "dialog_summary": context.conversation_summary,
        },
    )

    return {
        "response": reply,
        "state": serialize_state(dialog_state),
        "dialog_summary": context.conversation_summary,
        "session_id": session_id,
        "meta": response_meta,
        "metrics": {
            "llm_duration_ms": llm_duration_ms,
        },
    }


# =============================================================================
# Pydantic ?붿껌 紐⑤뜽 ?뺤쓽
# =============================================================================
class ChatRequest(BaseModel):
    user_message: str
    model_result: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] | None = None
    dialog_summary: str | None = None
    meta: dict[str, Any] | None = None


class StartRequest(BaseModel):
    model_result: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] | None = None


class EndSessionRequest(BaseModel):
    session_id: str
    end_reason: str
    elapsed_sec: int | None = None
    turn_count: int | None = None
    session_mode: str | None = None


class SessionEventRequest(BaseModel):
    session_id: str
    event_name: str | None = None
    event_id: str | None = None
    event_seq: int | None = None
    event_ts: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TTSRequest(BaseModel):
    text: str
    voice: str = "alloy"
    response_format: Literal["mp3", "wav"] = "mp3"
    model: str = "gpt-4o-mini-tts"
    instructions: str | None = None


# CORS 誘몃뱾?⑥뼱 異붽? (?꾨줎?몄뿏?쒖????듭떊 ?덉슜)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API ?붾뱶?ъ씤??
# =============================================================================
@app.get("/")
def root():
    return {"message": "LLM chatbot server is running"}


@app.post("/realtime/client-secret")
async def create_realtime_client_secret():
    turn_detection: dict[str, Any]
    if REALTIME_VAD_MODE == "semantic_vad":
        turn_detection = {
            "type": "semantic_vad",
            "create_response": False,
            "silence_duration_ms": REALTIME_SILENCE_DURATION_MS,
        }
    else:
        turn_detection = {
            "type": "server_vad",
            "create_response": False,
            "threshold": REALTIME_VAD_THRESHOLD,
            "prefix_padding_ms": 280,
            "silence_duration_ms": REALTIME_SILENCE_DURATION_MS,
        }

    session_payload = {
        "type": "realtime",
        "model": REALTIME_MODEL,
        "output_modalities": ["text"],
        "audio": {
            "input": {
                "format": {"type": "audio/pcm", "rate": REALTIME_AUDIO_SAMPLE_RATE},
                "noise_reduction": {"type": "near_field"},
                "transcription": {"model": REALTIME_TRANSCRIBE_MODEL, "language": "ko"},
                "turn_detection": turn_detection,
            }
        },
    }

    try:
        secret = _build_openai_client().realtime.client_secrets.create(
            expires_after={"anchor": "created_at", "seconds": REALTIME_SECRET_TTL_SEC},
            session=session_payload,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create realtime client secret: {e}") from e

    return {
        "client_secret": secret.value,
        "expires_at": secret.expires_at,
        "model": REALTIME_MODEL,
        "sample_rate": REALTIME_AUDIO_SAMPLE_RATE,
        "vad_mode": REALTIME_VAD_MODE,
        "vad_threshold": REALTIME_VAD_THRESHOLD if REALTIME_VAD_MODE == "server_vad" else None,
        "silence_duration_ms": REALTIME_SILENCE_DURATION_MS,
        "idle_timeout_ms": REALTIME_IDLE_TIMEOUT_MS,
        "max_turn_duration_sec": REALTIME_MAX_TURN_DURATION_SEC,
    }


@app.get("/conversation-log")
def get_conversation_log(limit: int = 200):
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")
    if not CONVERSATION_LOG_PATH.exists():
        return {"path": str(CONVERSATION_LOG_PATH), "lines": []}

    with CONVERSATION_LOG_PATH.open("r", encoding="utf-8") as file:
        lines = [line.rstrip("\n") for line in file if line.strip()]
    return {"path": str(CONVERSATION_LOG_PATH), "lines": lines[-limit:]}


@app.get("/session/trace")
def get_session_trace(session_id: str, limit: int = 200):
    normalized_session_id = _clean_text(session_id)
    if not normalized_session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")

    entries = _load_session_trace_entries(normalized_session_id, limit)
    trace_path = get_session_trace_path(normalized_session_id)
    return {
        "session_id": normalized_session_id,
        "path": str(trace_path),
        "entries": entries,
    }


@app.get("/debug/session/{patient_id}/{session_id}/tail")
def debug_session_tail(patient_id: str, session_id: str, lines: int = 200):
    safe_limit = max(1, min(2000, _safe_int(lines, 200)))
    log_path = _get_turn_log_path(patient_id, session_id)
    if not log_path.exists():
        return {
            "path": str(log_path),
            "entries": [],
        }

    parsed_entries: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as fp:
        for line_no, raw in enumerate(fp, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except Exception:
                obj = {"line_no": line_no, "raw": stripped}
            parsed_entries.append(obj)

    return {
        "path": str(log_path),
        "entries": parsed_entries[-safe_limit:],
    }


@app.post("/start")
async def start_chat(req: StartRequest):
    try:
        meta_payload = req.meta or {}
        # ?몄뀡 ID 寃곗젙 (?쒓났?섏? ?딆쑝硫??덈줈 ?앹꽦)
        session_id = str(meta_payload.get("session_id") or "").strip() or _create_session_id()
        profile_id = str(meta_payload.get("profile_id") or "").strip() or None
        conversation_mode = _normalize_conversation_mode(meta_payload.get("conversation_mode")) or "therapy"
        policy = _resolve_user_policy(profile_id=profile_id, meta_payload=meta_payload)
        session_slot = _normalize_session_slot(meta_payload.get("session_slot")) or _infer_session_slot()
        next_session_slot = (
            _normalize_session_slot(meta_payload.get("next_session_slot"))
            or _get_next_session_slot(session_slot)
        )
        now_kst = datetime.now(KST_TZ)
        time_context = _build_kst_time_context(
            session_slot=session_slot,
            next_session_slot=next_session_slot,
            now_kst=now_kst,
        )

        # 湲곗〈 ?몄뀡 ?뺣━ (?ъ떆?묒슜)
        SESSION_CONTEXT_STORE.pop(session_id, None)
        SESSION_RUNTIME_STORE.pop(session_id, None)

        # ???몄뀡 而⑦뀓?ㅽ듃 ?앹꽦
        context = _create_session_context(
            session_id=session_id,
            profile_id=profile_id,
            policy=policy,
            conversation_mode=conversation_mode,
        )
        context.elapsed_time = _safe_int(meta_payload.get("elapsed_sec"), 0)
        context.session_slot = session_slot
        context.next_session_slot = next_session_slot
        context.diagnosis_label = _resolve_diagnosis_label(meta_payload, req.model_result or {}, context)
        context.neuro_pattern = _resolve_neuro_pattern(meta_payload, req.model_result or {}, context)
        context.cognitive_profile = _build_cognitive_training_profile(
            diagnosis_label=context.diagnosis_label,
            neuro_pattern=context.neuro_pattern,
            model_result=req.model_result or {},
            session_slot=session_slot,
            next_session_slot=next_session_slot,
            base_profile=context.cognitive_profile,
        )
        default_module = _default_module_by_profile(context.neuro_pattern)
        context.training_type = _module_to_training_type(default_module)
        context.training_level = 1

        # ???고????곹깭 ?앹꽦
        runtime = _create_runtime_state(session_id=session_id, module=default_module)
        runtime.difficulty = 1
        runtime.dialog_state = init_dialog_state()
        runtime.dialog_state.conversation_phase = "opening"
        runtime.dialog_state.dialog_state = "session_open"
        runtime.dialog_state.training_type = context.training_type
        runtime.dialog_state.training_level = 1
        runtime.dialog_state.training_step = 0
        runtime.dialog_state.fatigue_level = "low"

        # ?꾩뿭 ??μ냼?????
        SESSION_CONTEXT_STORE[session_id] = context
        SESSION_RUNTIME_STORE[session_id] = runtime

        # ?쒖옉 ?몄궗 ?됰룞 怨꾩빟 ?앹꽦
        opening_contract = BehaviorContract(
            intent="rapport_opening",
            module=runtime.module,
            hint_level="H0",
            outcome="related",
            next_move="ask",
            constraints=_build_contract_constraints(policy),
            notes="첫 인사 후 사용자의 반응을 확인하는 가벼운 질문 1개",
        )
        
        # ?쒖옉 硫뷀? ?뺣낫 援ъ꽦
        opening_meta = {
            **meta_payload,
            "session_id": session_id,
            "request_close": False,
            "conversation_phase": "opening",
            "stt_event": "speech",
            "training_type": context.training_type,
            "training_level": 1,
            "training_step": 0,
            "fatigue_state": "normal",
            "time_context": time_context,
            "user_time_reference": False,
            "behavior_contract": _contract_to_dict(opening_contract),
            "action_text": _build_action_text(contract=opening_contract, policy=policy),
            "memory_summary": context.conversation_summary,
            "used_phrases": runtime.used_phrases,
            "llm_model": policy.llm_model,
            "llm_fallback_model": policy.llm_fallback_model,
        }
        
        # LLM???듯빐 ?쒖옉 ?몄궗 ?앹꽦
        opening_message = run_llm(
            user_text="안녕하세요",
            dialog_state=runtime.dialog_state,
            model_result=req.model_result or {},
            meta=opening_meta,
            conversation_history=[],
            conversation_summary=context.conversation_summary,
            recent_messages=context.recent_messages,
            user_profile={
                **context.user_profile,
                "policy": asdict(policy),
                "cognitive_profile": context.cognitive_profile,
                "time_context": time_context,
            },
            request_close=False,
        )
        opening_message = _clean_text(opening_message) or "안녕하세요. 오늘 기분은 어떠세요?"

        # ?곹깭 ?낅뜲?댄듃
        runtime.dialog_state.last_assistant_utterance = opening_message
        _append_recent_message(context, "assistant", opening_message)
        _append_used_phrase(runtime, opening_message)
        context.conversation_summary = _sanitize_dialog_summary(
            DEFAULT_DIALOG_SUMMARY,
            fallback=DEFAULT_DIALOG_SUMMARY,
        )

        # 嚥≪뮄??疫꿸퀡以?
        append_conversation("assistant", opening_message)
        append_session_conversation(session_id, "assistant", opening_message)
        append_session_event(
            session_id,
            "session_start",
            {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "started_at_kst": now_kst.isoformat(),
                "timezone": "Asia/Seoul",
                "conversation_mode": context.conversation_mode,
                "session_slot": session_slot,
                "next_session_slot": next_session_slot,
                "policy": asdict(policy),
                "training_type": context.training_type,
            },
        )

        # ?묐떟 諛섑솚
        opening_meta_response = {
            "conversation_phase": "warmup",
            "turn_index": runtime.dialog_state.turn_index,
            "request_close": False,
            "conversation_mode": context.conversation_mode,
            "session_slot": session_slot,
            "session_slot_label": _get_session_label(session_slot),
            "next_session_slot": next_session_slot,
            "next_session_slot_label": _get_session_label(next_session_slot),
            "time_context": time_context,
            "diagnosis_label": context.diagnosis_label,
            "neuro_pattern": context.neuro_pattern,
            "active_regions": _list_from_any(context.cognitive_profile.get("active_regions"))[:6]
            if isinstance(context.cognitive_profile, dict)
            else [],
            "task_families": _list_from_any(context.cognitive_profile.get("task_families"))[:8]
            if isinstance(context.cognitive_profile, dict)
            else [],
            "training_type": context.training_type,
            "training_level": 1,
            "training_step": 0,
            "fatigue_state": "normal",
            "intent": opening_contract.intent,
            "module": opening_contract.module,
            "hint_level": opening_contract.hint_level,
            "outcome": opening_contract.outcome,
            "next_move": opening_contract.next_move,
            "constraints": opening_contract.constraints,
            "stimulus_enabled": False,
            "stimulus_count": 0,
            "policy_id": meta_payload.get("policy_id") or "mci_dummy",
            "llm_model": policy.llm_model,
            "stt_model": policy.stt_model,
            "tts_voice": policy.tts_voice,
        }

        append_session_trace(
            session_id,
            "session_start_turn",
            {
                "turn_index": runtime.dialog_state.turn_index,
                "user_text": "세션 인사 시작",
                "assistant_text": opening_message,
                "behavior_contract": _contract_to_dict(opening_contract),
                "response_meta": opening_meta_response,
                "dialog_summary": context.conversation_summary,
            },
        )

        return {
            "response": opening_message,
            "state": serialize_state(runtime.dialog_state),
            "dialog_summary": context.conversation_summary,
            "session_id": session_id,
            "meta": opening_meta_response,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 梨꾪똿 ?붾뱶?ъ씤??(?ъ슜??硫붿떆吏瑜?諛쏆븘 ?묐떟 ?앹꽦)
@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        meta_payload = req.meta or {}
        # ?몄뀡 ID 寃곗젙
        session_id = str(meta_payload.get("session_id") or "").strip() or _create_session_id()
        profile_id = str(meta_payload.get("profile_id") or "").strip() or None
        conversation_mode = _normalize_conversation_mode(meta_payload.get("conversation_mode")) or "therapy"
        policy = _resolve_user_policy(profile_id=profile_id, meta_payload=meta_payload)
        
        # ?몄뀡 而⑦뀓?ㅽ듃 諛??고????곹깭 媛?몄삤湲?(?놁쑝硫??앹꽦)
        context = _get_or_create_session_context(
            session_id=session_id,
            profile_id=profile_id,
            policy=policy,
            conversation_mode=conversation_mode,
        )
        default_module = _training_type_to_module(context.training_type or "semantic_naming")
        runtime = _get_or_create_runtime_state(session_id=session_id, module=default_module)

        # ???ㅽ뻾 (?듭떖 濡쒖쭅)
        response = _execute_turn(
            session_id=session_id,
            context=context,
            runtime=runtime,
            policy=policy,
            user_text=req.user_message,
            model_result=req.model_result or {},
            incoming_meta=meta_payload,
            request_close_override=None,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ?몄뀡 醫낅즺 ?붾뱶?ъ씤??
@app.post("/session/end")
async def end_session(req: EndSessionRequest):
    session_id = req.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    try:
        stored_context = SESSION_CONTEXT_STORE.get(session_id)
        context = stored_context if isinstance(stored_context, SessionContext) else None
        archive_result = _archive_session_outputs(session_id=session_id, context=context)

        payload = req.model_dump()
        now_utc = datetime.now(timezone.utc)
        now_kst = datetime.now(KST_TZ)
        payload["ended_at"] = now_utc.isoformat()
        payload["ended_at_kst"] = now_kst.isoformat()
        payload["timezone"] = "Asia/Seoul"
        payload["archive"] = archive_result
        append_session_event(session_id, "session_end", payload)
        append_session_trace(session_id, "session_end", payload)

        SESSION_CONTEXT_STORE.pop(session_id, None)
        SESSION_RUNTIME_STORE.pop(session_id, None)

        return {"ok": True, "session_id": session_id, "archive": archive_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/upload-audio")
async def upload_session_audio(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    profile_id: str = Form(default=""),
    audio_gate_meta: str = Form(default=""),
):
    safe_session = sanitize_session_id(session_id)
    if not safe_session:
        raise HTTPException(status_code=400, detail="session_id is required")

    context_raw = SESSION_CONTEXT_STORE.get(safe_session)
    context = context_raw if isinstance(context_raw, SessionContext) else None
    resolved_profile = sanitize_session_id(_clean_text(profile_id) or _clean_text(str((context.profile_id if context else "") or "")))
    patient_id = resolved_profile or _resolve_patient_id_for_archive(safe_session, context)
    archive_dir = get_session_dir(SESSION_ARCHIVE_DIR, patient_id, safe_session)

    suffix = _audio_suffix_from_upload(file)
    raw_path = archive_dir / f"conversation.user{suffix}"
    temp_raw_path: Path | None = None
    conversion_error: str | None = None

    gate_meta_payload = parse_json_object_form(
        audio_gate_meta,
        field_name="audio_gate_meta",
        default=None,
    )
    gate_meta_path: Path | None = None

    try:
        payload = await file.read()
        if not payload:
            raise HTTPException(status_code=400, detail="Uploaded audio is empty.")

        raw_path.write_bytes(payload)
        final_path = raw_path
        converted_to_wav = False

        if suffix != ".wav":
            try:
                TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
                temp_raw_path = TEMP_AUDIO_DIR / f"session_upload_{uuid.uuid4().hex}{suffix}"
                temp_raw_path.write_bytes(payload)
                wav_path = archive_dir / "conversation.user.wav"
                ensure_wav_16k_mono_pcm16(temp_raw_path, wav_path)
                final_path = wav_path
                converted_to_wav = True
                try:
                    raw_path.unlink()
                except Exception:
                    pass
            except Exception as exc:
                conversion_error = _clean_text(str(exc))[:240]
        else:
            try:
                inspect_wav(raw_path)
            except Exception:
                conversion_error = "invalid_wav_source_saved_as_is"

        if isinstance(gate_meta_payload, dict):
            gate_meta_path = archive_dir / "conversation.user.meta.json"
            gate_meta_path.write_text(
                json.dumps(gate_meta_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        event_payload = {
            "session_id": safe_session,
            "patient_id": patient_id,
            "audio_path": str(final_path),
            "audio_format": final_path.suffix.lstrip("."),
            "converted_to_wav": converted_to_wav,
            "conversion_error": conversion_error,
            "audio_gate_meta_path": str(gate_meta_path) if gate_meta_path else None,
            "audio_gate_meta": gate_meta_payload if isinstance(gate_meta_payload, dict) else None,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        append_session_event(safe_session, "session_audio_uploaded", event_payload)
        append_session_trace(safe_session, "session_audio_uploaded", event_payload)
        return {"ok": True, **event_payload}
    finally:
        await file.close()
        if temp_raw_path and temp_raw_path.exists():
            try:
                temp_raw_path.unlink()
            except Exception:
                pass


# ?몄뀡 ?대깽??湲곕줉 ?붾뱶?ъ씤??
@app.post("/session/event")
async def session_event(req: SessionEventRequest):
    session_id = req.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    event_name = _normalize_client_event_name(req.event_name)
    event_id = _clean_text(req.event_id or "")
    event_seq = req.event_seq
    payload = req.payload if isinstance(req.payload, dict) else {}

    runtime = SESSION_RUNTIME_STORE.get(session_id)
    if not isinstance(runtime, RuntimeSessionState):
        _record_unknown_event(
            session_id,
            "session_not_found_for_event",
            {
                "event_name": event_name,
                "event_id": event_id or None,
                "event_seq": event_seq,
            },
        )
        append_session_event(
            session_id,
            "event_unknown",
            {
                "event_name": event_name,
                "event_id": event_id or None,
                "event_seq": event_seq,
                "event_ts": req.event_ts,
                "payload": payload,
            },
        )
        append_session_trace(
            session_id,
            "client_event",
            {
                "status": "unknown_session_logged",
                "event_name": event_name,
                "event_id": event_id or None,
                "event_seq": event_seq,
                "payload": payload,
            },
        )
        return {"ok": True, "status": "unknown_session_logged", "session_id": session_id}

    if event_id and _remember_event_id(runtime, event_id):
        _record_unknown_event(
            session_id,
            "duplicate_event_id",
            {
                "event_name": event_name,
                "event_id": event_id,
                "event_seq": event_seq,
            },
        )
        append_session_trace(
            session_id,
            "client_event",
            {
                "status": "duplicate_ignored",
                "event_name": event_name,
                "event_id": event_id,
                "event_seq": event_seq,
            },
        )
        return {
            "ok": True,
            "status": "duplicate_ignored",
            "session_id": session_id,
            "event_id": event_id,
            "event_name": event_name,
        }

    if isinstance(event_seq, int):
        if event_seq <= 0:
            _record_unknown_event(
                session_id,
                "invalid_event_seq",
                {"event_name": event_name, "event_seq": event_seq},
            )
        else:
            previous = runtime.last_client_event_seq
            if previous > 0 and event_seq > previous + 1:
                _record_unknown_event(
                    session_id,
                    "missing_event_gap",
                    {
                        "expected_seq": previous + 1,
                        "received_seq": event_seq,
                        "missing_count": event_seq - previous - 1,
                    },
                )
            elif previous > 0 and event_seq <= previous:
                _record_unknown_event(
                    session_id,
                    "out_of_order_or_replayed_seq",
                    {"last_seq": previous, "received_seq": event_seq},
                )
            runtime.last_client_event_seq = max(previous, event_seq)

    if event_name not in KNOWN_CLIENT_SESSION_EVENTS:
        _record_unknown_event(
            session_id,
            "unknown_event_name",
            {
                "event_name": event_name,
                "event_id": event_id or None,
                "event_seq": event_seq,
            },
        )
        event_name = "event_unknown"

    if event_name in ("realtime_turn_ended", "turn_ended", "turn_end"):
        reason = _clean_text(str(payload.get("turn_end_reason") or ""))
        if not reason:
            payload["turn_end_reason"] = "unknown"
            _record_unknown_event(
                session_id,
                "missing_turn_end_reason",
                {
                    "event_name": event_name,
                    "event_id": event_id or None,
                    "event_seq": event_seq,
                },
            )

    event_record = {
        "event_id": event_id or None,
        "event_seq": event_seq,
        "event_ts": req.event_ts,
        "payload": payload,
    }
    append_session_event(session_id, event_name, event_record)
    append_session_trace(
        session_id,
        "client_event",
        {
            "status": "recorded",
            "event_name": event_name,
            **event_record,
        },
    )

    response_payload: dict[str, Any] = {
        "ok": True,
        "status": "recorded",
        "session_id": session_id,
        "event_name": event_name,
        "event_id": event_id or None,
        "event_seq": event_seq,
    }

    # When client reports timeout/silence, create a no-speech turn so the user gets a follow-up.
    if event_name == "realtime_timeout_triggered":
        context = SESSION_CONTEXT_STORE.get(session_id)
        if isinstance(context, SessionContext):
            try:
                effective_policy = context.policy if isinstance(context.policy, UserPolicy) else _resolve_user_policy(
                    profile_id=context.profile_id,
                    meta_payload=payload,
                )
                session_slot = _normalize_session_slot(context.session_slot) or _infer_session_slot()
                next_session_slot = _normalize_session_slot(context.next_session_slot) or _get_next_session_slot(session_slot)
                timeout_meta = {
                    **payload,
                    "session_id": session_id,
                    "conversation_mode": context.conversation_mode,
                    "session_slot": session_slot,
                    "next_session_slot": next_session_slot,
                    "stt_event": "no_speech",
                    "is_speech_detected": False,
                    "is_recognized": False,
                    "recognition_confidence": 0.0,
                    "recognition_failed": False,
                    "silence_duration": runtime.silence_duration,
                }
                turn_result = _execute_turn(
                    session_id=session_id,
                    context=context,
                    runtime=runtime,
                    policy=effective_policy,
                    user_text="",
                    model_result={},
                    incoming_meta=timeout_meta,
                    request_close_override=None,
                )
                response_payload.update(
                    {
                        "status": "turn_generated",
                        "response": turn_result.get("response"),
                        "state": turn_result.get("state"),
                        "dialog_summary": turn_result.get("dialog_summary"),
                        "meta": turn_result.get("meta"),
                    }
                )
                append_session_trace(
                    session_id,
                    "client_event_auto_turn",
                    {
                        "event_name": event_name,
                        "event_id": event_id or None,
                        "event_seq": event_seq,
                        "status": "turn_generated",
                    },
                )
            except Exception as exc:
                _record_unknown_event(
                    session_id,
                    "event_auto_turn_failed",
                    {
                        "event_name": event_name,
                        "event_id": event_id or None,
                        "event_seq": event_seq,
                        "error": str(exc),
                    },
                )

    return response_payload


@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    temp_path: Path | None = None

    try:
        temp_path = await save_upload_to_temp(file)
        policy = _resolve_user_policy(profile_id=None, meta_payload={})
        transcription = transcribe_audio(str(temp_path), model=policy.stt_model)
        transcript_text = transcription.text

        if transcript_text:
            append_transcript(transcript_text)
            append_conversation("user", transcript_text)

        return {
            "transcript": transcript_text,
            "transcription": asdict(transcription),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()
        if temp_path and temp_path.exists():
            temp_path.unlink()


@app.post("/turn")
async def turn(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    session_id: str = Form(...),
    turn_index: int = Form(...),
    end_reason: str = Form(default="client_commit"),
    duration_ms: int = Form(default=0),
    vad_mode: str = Form(default="server_vad"),
    client_rms: float | None = Form(default=None),
    state: str | None = Form(default=None),
    model_result: str | None = Form(default=None),
):
    started_at = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    temp_original_path: Path | None = None
    converted_path: Path | None = None

    try:
        safe_patient_id = sanitize_session_id(patient_id)
        safe_session_id = sanitize_session_id(session_id) or _create_session_id()
        safe_turn_index = max(0, _safe_int(turn_index, 0))
        turn_id = _create_turn_id(safe_session_id, safe_turn_index)

        state_payload = parse_json_object_form(
            state,
            field_name="state",
            default=None,
        )
        model_result_payload = parse_json_object_form(
            model_result,
            field_name="model_result",
            default={},
        ) or {}
        incoming_meta = _extract_state_meta(state_payload)

        conversation_mode = _normalize_conversation_mode(incoming_meta.get("conversation_mode")) or "therapy"
        policy = _resolve_user_policy(profile_id=safe_patient_id, meta_payload=incoming_meta)

        original_bytes = await file.read()
        if not original_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio is empty.")

        TEMP_AUDIO_DIR.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=TEMP_AUDIO_DIR,
            suffix=".wav",
        ) as temp_file:
            temp_original_path = Path(temp_file.name)
            temp_file.write(original_bytes)

        converted_path = TEMP_AUDIO_DIR / f"{turn_id}.wav"
        try:
            ensure_wav_16k_mono_pcm16(temp_original_path, converted_path)
            wav_info = inspect_wav(converted_path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid audio format: {exc}") from exc

        stt_started = time.perf_counter()
        transcription = transcribe_audio(str(converted_path), model=policy.stt_model)
        stt_duration_ms = int((time.perf_counter() - stt_started) * 1000)

        transcript_raw = transcription.text or ""
        transcript_norm = normalize_transcript(transcript_raw)
        _schedule_background(
            save_text_files_async(
                safe_patient_id,
                safe_session_id,
                turn_id,
                transcript_raw,
                transcript_norm,
            )
        )
        _schedule_background(
            save_audio_files_async(
                safe_patient_id,
                safe_session_id,
                turn_id,
                original_bytes,
                converted_path,
            )
        )

        recognition_failed = transcription.is_speech_detected and (
            (not transcription.is_recognized) or transcription.error_type == "low_confidence"
        )
        stt_uncertain = recognition_failed or (
            transcription.is_speech_detected
            and ((not transcription.is_recognized) or float(transcription.confidence) < 0.45)
        )
        stt_event = "speech"
        if not transcription.is_speech_detected:
            stt_event = "no_speech"
        elif stt_uncertain:
            stt_event = "stt_error"

        uncertainty_score, uncertainty_features = _build_uncertainty_features(
            is_speech_detected=transcription.is_speech_detected,
            is_recognized=transcription.is_recognized,
            recognition_confidence=float(transcription.confidence),
            transcript_length=len(transcript_norm),
            recognition_failed=stt_uncertain,
        )

        context = _get_or_create_session_context(
            session_id=safe_session_id,
            profile_id=safe_patient_id,
            policy=policy,
            conversation_mode=conversation_mode,
        )
        default_module = _training_type_to_module(context.training_type or "semantic_naming")
        runtime = _get_or_create_runtime_state(session_id=safe_session_id, module=default_module)

        turn_meta = {
            **incoming_meta,
            "session_id": safe_session_id,
            "turn_index": safe_turn_index,
            "elapsed_sec": _safe_int(incoming_meta.get("elapsed_sec"), _safe_int(duration_ms / 1000, 0)),
            "request_close": _to_bool(incoming_meta.get("request_close"), default=False),
            "conversation_mode": conversation_mode,
            "is_speech_detected": transcription.is_speech_detected,
            "is_recognized": transcription.is_recognized,
            "recognition_confidence": float(transcription.confidence),
            "recognition_failed": stt_uncertain,
            "stt_event": stt_event,
            "silence_duration": _safe_int(incoming_meta.get("silence_duration"), 0),
            "end_reason": _clean_text(end_reason),
            "duration_ms": _safe_int(duration_ms, 0),
            "vad_mode": _clean_text(vad_mode),
            "client_rms": client_rms,
        }

        turn_result = _execute_turn(
            session_id=safe_session_id,
            context=context,
            runtime=runtime,
            policy=policy,
            user_text=transcript_norm,
            model_result=model_result_payload,
            incoming_meta=turn_meta,
            request_close_override=None,
        )

        llm_duration_ms = _safe_int(
            ((turn_result.get("metrics") or {}).get("llm_duration_ms") if isinstance(turn_result, dict) else 0),
            0,
        )
        assistant_text = _clean_text(str(turn_result.get("response") or ""))
        response_meta = turn_result.get("meta") if isinstance(turn_result, dict) else {}
        if not isinstance(response_meta, dict):
            response_meta = {}

        contract_dict = {
            "intent": _clean_text(str(response_meta.get("intent") or "")),
            "module": _clean_text(str(response_meta.get("module") or "")),
            "hint_level": _clean_text(str(response_meta.get("hint_level") or "")),
            "outcome": _clean_text(str(response_meta.get("outcome") or "")),
            "next_move": _clean_text(str(response_meta.get("next_move") or "")),
            "constraints": response_meta.get("constraints") if isinstance(response_meta.get("constraints"), dict) else {},
            "decision_notes": _clean_text(str(response_meta.get("decision_notes") or "")),
        }
        stimulus_dict = response_meta.get("training_item") if isinstance(response_meta.get("training_item"), dict) else None

        tts_started = time.perf_counter()
        tts_audio_bytes = synthesize_speech(
            assistant_text,
            voice=policy.tts_voice,
            response_format="mp3",
            model=policy.tts_model,
            instructions=policy.tts_style,
        )
        tts_duration_ms = int((time.perf_counter() - tts_started) * 1000)

        _schedule_background(
            save_metadata_async(
                safe_patient_id,
                safe_session_id,
                turn_id,
                contract_dict,
                stimulus_dict,
            )
        )
        _schedule_background(
            save_assistant_data_async(
                safe_patient_id,
                safe_session_id,
                turn_id,
                assistant_text,
                tts_audio_bytes,
            )
        )

        confirm_reason: str | None = None
        if contract_dict.get("next_move") == "confirm_stt":
            if not transcription.is_recognized:
                confirm_reason = "not_recognized"
            elif float(transcription.confidence) < 0.45:
                confirm_reason = "low_confidence"
            else:
                confirm_reason = "high_uncertainty"

        total_duration_ms = int((time.perf_counter() - started_at) * 1000)
        turn_log = {
            "turn_id": turn_id,
            "turn_index": safe_turn_index,
            "timestamp": timestamp_utc,
            "patient_id": safe_patient_id,
            "session_id": safe_session_id,
            "end_reason": _clean_text(end_reason),
            "duration_ms": _safe_int(duration_ms, 0),
            "vad_mode": _clean_text(vad_mode),
            "client_rms": client_rms,
            "is_speech_detected": bool(transcription.is_speech_detected),
            "is_recognized": bool(transcription.is_recognized),
            "recognition_confidence": float(transcription.confidence),
            "stt_uncertain": bool(stt_uncertain),
            "transcript_length": len(transcript_norm),
            "intent": contract_dict["intent"],
            "module": contract_dict["module"],
            "hint_level": contract_dict["hint_level"],
            "outcome": contract_dict["outcome"],
            "next_move": contract_dict["next_move"],
            "constraints": contract_dict["constraints"],
            "decision_notes": contract_dict["decision_notes"],
            "uncertainty_score": uncertainty_score,
            "uncertainty_features": uncertainty_features,
            "stimulus": stimulus_dict if isinstance(stimulus_dict, dict) else {},
            "assistant_text_length": len(assistant_text),
            "num_sentences": _count_sentences(assistant_text),
            "num_questions": _count_questions(assistant_text),
            "stt_duration_ms": stt_duration_ms,
            "llm_duration_ms": llm_duration_ms,
            "tts_duration_ms": tts_duration_ms,
            "total_duration_ms": total_duration_ms,
            "wav_info": wav_info,
        }
        if confirm_reason:
            turn_log["confirm_reason"] = confirm_reason
        _schedule_background(
            append_turn_log_async(
                safe_patient_id,
                safe_session_id,
                turn_log,
            )
        )

        enriched_meta = {
            **response_meta,
            "turn_id": turn_id,
            "decision_notes": contract_dict["decision_notes"],
            "uncertainty_score": uncertainty_score,
            "uncertainty_features": uncertainty_features,
            "end_reason": _clean_text(end_reason),
            "duration_ms": _safe_int(duration_ms, 0),
            "vad_mode": _clean_text(vad_mode),
            "client_rms": client_rms,
            "stt_uncertain": stt_uncertain,
            "stt_duration_ms": stt_duration_ms,
            "llm_duration_ms": llm_duration_ms,
            "tts_duration_ms": tts_duration_ms,
            "processing_time_ms": total_duration_ms,
        }
        if confirm_reason:
            enriched_meta["confirm_reason"] = confirm_reason

        return {
            "turn_id": turn_id,
            "patient_id": safe_patient_id,
            "session_id": safe_session_id,
            "response": assistant_text,
            "transcript_raw": transcript_raw,
            "transcript_norm": transcript_norm,
            "state": turn_result.get("state"),
            "meta": enriched_meta,
            "audio_base64": base64.b64encode(tts_audio_bytes).decode("ascii"),
            "audio_mime_type": "audio/mpeg",
            "processing_time_ms": total_duration_ms,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()
        if temp_original_path and temp_original_path.exists():
            try:
                temp_original_path.unlink()
            except Exception:
                pass


@app.post("/tts")
async def tts(req: TTSRequest):
    try:
        audio_bytes = synthesize_speech(
            req.text,
            voice=req.voice,
            response_format=req.response_format,
            model=req.model,
            instructions=req.instructions,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    media_type = "audio/mpeg" if req.response_format == "mp3" else "audio/wav"
    return Response(content=audio_bytes, media_type=media_type)


@app.post("/voice-chat")
async def voice_chat(
    file: UploadFile = File(...),
    state: str | None = Form(default=None),
    model_result: str | None = Form(default=None),
    tts_voice: str = Form(default=""),
    tts_format: Literal["mp3", "wav"] = Form(default="mp3"),
    auto_chat: bool = Form(default=False),
):
    temp_path: Path | None = None
    converted_user_wav_path: Path | None = None
    saved_path: Path | None = None
    user_audio_save_note = ""

    try:
        state_payload = parse_json_object_form(state, field_name="state", default=None)
        incoming_meta = _extract_state_meta(state_payload)

        meta_session_id = _clean_text(str(incoming_meta.get("session_id") or ""))
        if not meta_session_id and isinstance(state_payload, dict):
            meta_session_id = _clean_text(str(state_payload.get("session_id") or ""))
        session_id = meta_session_id or _create_session_id()

        profile_id = _clean_text(str(incoming_meta.get("profile_id") or "")) or None
        conversation_mode = _normalize_conversation_mode(incoming_meta.get("conversation_mode")) or "therapy"
        policy = _resolve_user_policy(profile_id=profile_id, meta_payload=incoming_meta)

        context = _get_or_create_session_context(
            session_id=session_id,
            profile_id=profile_id,
            policy=policy,
            conversation_mode=conversation_mode,
        )
        default_module = _training_type_to_module(context.training_type or "semantic_naming")
        runtime = _get_or_create_runtime_state(session_id=session_id, module=default_module)

        temp_path = await save_upload_to_temp(file)
        archive_turn_id = _create_turn_id(session_id, runtime.turn_count + 1)
        converted_user_wav_path = TEMP_AUDIO_DIR / f"{archive_turn_id}.wav"
        stt_input_path = temp_path
        try:
            ensure_wav_16k_mono_pcm16(temp_path, converted_user_wav_path)
            stt_input_path = converted_user_wav_path
            user_audio_save_note = "converted_to_wav"
        except Exception as exc:
            # If ffmpeg is unavailable, still persist when upload is already a valid WAV.
            converted_user_wav_path = None
            try:
                inspect_wav(temp_path)
                converted_user_wav_path = TEMP_AUDIO_DIR / f"{archive_turn_id}.raw.wav"
                shutil.copyfile(temp_path, converted_user_wav_path)
                user_audio_save_note = "source_wav_copied_without_conversion"
            except Exception:
                user_audio_save_note = f"wav_conversion_failed:{_clean_text(str(exc))[:120]}"

        transcription = transcribe_audio(str(stt_input_path), model=policy.stt_model)
        transcript_text = _clean_text(transcription.text)

        archive_patient_id = sanitize_session_id(profile_id or context.profile_id or "unknown_patient")
        if converted_user_wav_path and converted_user_wav_path.exists():
            converted_bytes = converted_user_wav_path.read_bytes()
            await save_audio_files_async(
                archive_patient_id,
                sanitize_session_id(session_id),
                archive_turn_id,
                converted_bytes,
                converted_user_wav_path,
            )

        session_slot = _normalize_session_slot(incoming_meta.get("session_slot")) or _infer_session_slot()
        next_session_slot = (
            _normalize_session_slot(incoming_meta.get("next_session_slot"))
            or _get_next_session_slot(session_slot)
        )

        recognition_failed = transcription.is_speech_detected and (
            (not transcription.is_recognized) or transcription.error_type == "low_confidence"
        )
        stt_event = "speech"
        if not transcription.is_speech_detected:
            stt_event = "no_speech"
        elif recognition_failed:
            stt_event = "stt_error"

        silence_duration = _safe_int(incoming_meta.get("silence_duration"), runtime.silence_duration)
        if transcription.is_speech_detected:
            silence_duration = 0
        else:
            silence_duration += SILENCE_TURN_INCREMENT_SEC

        voice_meta = {
            **incoming_meta,
            "session_id": session_id,
            "is_speech_detected": transcription.is_speech_detected,
            "is_recognized": transcription.is_recognized,
            "recognition_confidence": transcription.confidence,
            "recognition_failed": recognition_failed,
            "stt_event": stt_event,
            "silence_duration": silence_duration,
            "session_slot": session_slot,
            "session_slot_label": _get_session_label(session_slot),
            "next_session_slot": next_session_slot,
            "next_session_slot_label": _get_session_label(next_session_slot),
            "conversation_mode": context.conversation_mode,
            "medical_topic": bool(context.conversation_mode == "therapy"),
            "user_audio_save_note": user_audio_save_note,
        }

        if transcript_text:
            append_transcript(transcript_text)
            append_conversation("user", transcript_text)
            append_session_conversation(session_id, "user", transcript_text)

        runtime.dialog_state = decide_next_state(
            runtime.dialog_state,
            {
                "user_text": transcript_text,
                "is_speech_detected": transcription.is_speech_detected,
                "is_recognized": transcription.is_recognized,
                "recognition_confidence": transcription.confidence,
                "silence_duration": silence_duration,
                "consecutive_failures": runtime.consecutive_failures,
                "elapsed_sec": context.elapsed_time,
                "turn_index": runtime.turn_count,
                "request_close": _to_bool(voice_meta.get("request_close"), False),
            },
        )

        if not auto_chat:
            return {
                "transcript": transcript_text,
                "transcription": asdict(transcription),
                "response": None,
                "state": serialize_state(runtime.dialog_state),
                "audio_base64": None,
                "audio_mime_type": None,
                "saved_audio_path": str(saved_path) if saved_path else None,
                "session_id": session_id,
                "meta": {
                    "session_slot": session_slot,
                    "session_slot_label": _get_session_label(session_slot),
                    "next_session_slot": next_session_slot,
                    "next_session_slot_label": _get_session_label(next_session_slot),
                    "conversation_mode": context.conversation_mode,
                    "medical_topic": bool(context.conversation_mode == "therapy"),
                    "silence_duration": silence_duration,
                    "recognition_failed": recognition_failed,
                    "stimulus_enabled": bool(runtime.current_stimulus),
                    "stimulus_count": len(runtime.used_stimuli),
                    "policy_id": incoming_meta.get("policy_id") or "mci_dummy",
                    "llm_model": policy.llm_model,
                    "stt_model": policy.stt_model,
                    "tts_voice": policy.tts_voice,
                    "user_audio_save_note": user_audio_save_note,
                },
            }

        model_result_payload = parse_json_object_form(model_result, field_name="model_result", default={}) or {}
        external_request_close = _to_bool(voice_meta.get("request_close"), False)

        turn_result = _execute_turn(
            session_id=session_id,
            context=context,
            runtime=runtime,
            policy=policy,
            user_text=transcript_text,
            model_result=model_result_payload,
            incoming_meta=voice_meta,
            request_close_override=external_request_close,
        )
        reply = _clean_text(str(turn_result.get("response") or ""))

        target_voice = _clean_text(tts_voice) or policy.tts_voice
        audio_bytes = synthesize_speech(
            reply,
            voice=target_voice,
            response_format=tts_format,
            model=policy.tts_model,
            instructions=policy.tts_style,
        )
        audio_mime_type = "audio/mpeg" if tts_format == "mp3" else "audio/wav"

        turn_result.update(
            {
                "transcript": transcript_text,
                "transcription": asdict(transcription),
                "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
                "audio_mime_type": audio_mime_type,
                "saved_audio_path": str(saved_path) if saved_path else None,
                "user_audio_save_note": user_audio_save_note,
            }
        )
        return turn_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()
        if temp_path and temp_path.exists():
            temp_path.unlink()
        if converted_user_wav_path and converted_user_wav_path.exists():
            converted_user_wav_path.unlink()

