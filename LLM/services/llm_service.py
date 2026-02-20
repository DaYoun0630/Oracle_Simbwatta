import json
import os
import re
from difflib import SequenceMatcher
from typing import Any

from openai import OpenAI

try:
    from ..prompts.system_prompt import SYSTEM_PROMPT
except ImportError:
    from prompts.system_prompt import SYSTEM_PROMPT

try:
    from .llm_validator import build_soft_retry_hint
except Exception:
    def build_soft_retry_hint(_: str) -> str:
        return ""


EMERGENCY_FALLBACK_MESSAGE = "잠시 음성이 끊겼어요. 천천히 한 번만 더 말씀해 주세요."
EMERGENCY_CLOSING_MESSAGE = "오늘 대화는 여기서 마무리할게요. 다음에 이어서 도와드릴게요."
EMERGENCY_STT_NO_SPEECH_MESSAGE = "소리가 잘 들리지 않았어요. 한 번만 다시 말씀해 주세요."

MAX_RECENT_MESSAGES = 12
DEFAULT_MODEL_CANDIDATES = ("gpt-4o", "gpt-4o-mini")
STIMULUS_JSON_RETRY_LIMIT = 1

PROPOSAL_TOKENS = (
    "해볼까요",
    "시작해볼까요",
    "시작할까요",
    "준비되셨다면",
    "해볼게요",
)
REACTION_TOKENS = (
    "그랬군요",
    "좋아요",
    "맞아요",
    "말씀",
    "그렇군요",
    "잘하셨어요",
    "수고하셨어요",
)
SESSION_META_PATTERN = re.compile(
    r"(세션\s*(시작|종료|진행)|세션을\s*시작|세션이\s*시작|환영(해요|합니다)|반갑게\s*맞이|시작하게\s*되어)"
)
SWITCH_PERMISSION_PATTERN = re.compile(
    r"(다른|새로운)\s*주제[^.?!]*?(넘어가|전환|바꾸|이야기)[^.?!]*?(볼까요|할까요|갈까요|해볼까요|괜찮을까요|좋을까요)"
)
FOLLOWUP_PROMPT_PATTERN = re.compile(
    r"(말씀|이야기|말해|알려|들려|생각)[^.!?]*?(주세요|주실래요|해\s*주세요|해\s*주실래요|해주시겠어요|해\s*주시겠어요|해보실래요)"
)


def _build_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


def _clean_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _safe_int(value: Any, default: int) -> int:
    try:
        if value is None:
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _state_get(dialog_state: Any | None, key: str, default: Any = None) -> Any:
    if isinstance(dialog_state, dict):
        return dialog_state.get(key, default)
    if dialog_state is None:
        return default
    return getattr(dialog_state, key, default)


def _normalize_event_name(raw_value: Any) -> str:
    return _clean_text(str(raw_value or "")).lower().replace("-", "_")


def _normalize_messages(
    messages: list[dict[str, Any]] | None,
    *,
    last_k: int = MAX_RECENT_MESSAGES,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "").strip().lower()
        content = _clean_text(str(message.get("content") or ""))
        if role not in ("user", "assistant"):
            continue
        if not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized[-max(1, last_k):]


def _format_recent(messages: list[dict[str, str]]) -> str:
    if not messages:
        return "- (recent conversation is empty)"
    lines: list[str] = []
    for message in messages:
        label = "User" if message["role"] == "user" else "Assistant"
        lines.append(f"- {label}: {message['content']}")
    return "\n".join(lines)


def _format_profile(profile: dict[str, Any] | None) -> str:
    if not profile:
        return "- (profile is empty)"
    lines: list[str] = []
    for key, value in profile.items():
        if value is None:
            continue
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "- (profile is empty)"


def _parse_json_like(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    if not (
        (text.startswith("{") and text.endswith("}"))
        or (text.startswith("[") and text.endswith("]"))
    ):
        return value
    try:
        return json.loads(text)
    except Exception:
        return value


def _extract_first_json_object(raw_text: str) -> dict[str, Any] | None:
    text = _clean_text(raw_text)
    if not text:
        return None

    direct = _parse_json_like(text)
    if isinstance(direct, dict):
        return direct

    source = raw_text or ""
    length = len(source)
    start = 0
    while start < length:
        open_idx = source.find("{", start)
        if open_idx < 0:
            break

        depth = 0
        in_string = False
        escaped = False
        close_idx = -1

        for idx in range(open_idx, length):
            ch = source[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    close_idx = idx
                    break

        if close_idx >= 0:
            snippet = source[open_idx : close_idx + 1]
            try:
                candidate = json.loads(snippet)
            except Exception:
                start = open_idx + 1
                continue
            if isinstance(candidate, dict):
                return candidate
            start = open_idx + 1
            continue

        break

    return None


def _json_string(value: Any, default: Any) -> str:
    candidate = _parse_json_like(value)
    if candidate is None or candidate == "":
        candidate = default
    try:
        return json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return json.dumps(default, ensure_ascii=False, separators=(",", ":"))


def _limit_question_marks(text: str) -> str:
    seen = False
    chars: list[str] = []
    for ch in text:
        if ch == "?":
            if seen:
                chars.append(".")
                continue
            seen = True
        chars.append(ch)
    return "".join(chars)


def _split_sentences(text: str) -> list[str]:
    chunks = re.findall(r"[^.!?…]+[.!?…]?", text)
    parts = [chunk.strip() for chunk in chunks if chunk.strip()]
    if parts:
        return parts
    stripped = text.strip()
    return [stripped] if stripped else []


def _enforce_response_shape(text: str, *, max_sentences: int = 2) -> str:
    normalized = _clean_text(text)
    if not normalized:
        return ""

    limited_questions = _limit_question_marks(normalized)
    sentences = _split_sentences(limited_questions)
    if not sentences:
        return ""

    safe_limit = max(1, min(3, _safe_int(max_sentences, 2)))
    kept = sentences[:safe_limit]
    joined = " ".join(kept).strip()
    if joined and joined[-1] not in ".?!…":
        joined += "."
    return joined


def _has_reaction_phrase(text: str) -> bool:
    lowered = text.lower()
    if any(token in text for token in REACTION_TOKENS):
        return True
    return bool(
        re.search(
            r"(그렇군요|그랬군요|좋아요|맞아요|잘하셨어요|들었어요|말씀해주셔서)",
            lowered,
        )
    )


def _is_proposal_only(text: str) -> bool:
    normalized = _clean_text(text)
    if not normalized:
        return True

    has_proposal = any(token in normalized for token in PROPOSAL_TOKENS)
    if not has_proposal:
        return False
    if _has_reaction_phrase(normalized):
        return False

    non_proposal_content = re.sub(
        r"(해볼까요|시작해볼까요|시작할까요|준비되셨다면|해볼게요|부담 없이|가볍게)",
        "",
        normalized,
    ).strip()
    sentence_count = len(_split_sentences(normalized))

    if len(non_proposal_content) <= 8:
        return True
    return sentence_count <= 1


def _phrase_signature(text: str) -> str:
    normalized = re.sub(r"[^\w가-힣]+", "", _clean_text(text)).lower()
    return normalized[:80]


def _is_repeated_phrase(text: str, used_phrases: list[str]) -> bool:
    signature = _phrase_signature(text)
    if not signature:
        return False
    normalized_pool = {_phrase_signature(item) for item in used_phrases if item}
    return signature in normalized_pool


def _first_sentence(text: str) -> str:
    sentences = _split_sentences(_clean_text(text))
    if not sentences:
        return ""
    return _clean_text(sentences[0])


def _is_session_meta_opening(text: str) -> bool:
    normalized = _clean_text(text)
    if not normalized:
        return False
    return bool(SESSION_META_PATTERN.search(normalized))


def _is_switch_permission_question(text: str) -> bool:
    normalized = _clean_text(text)
    if not normalized:
        return False
    return bool(SWITCH_PERMISSION_PATTERN.search(normalized))


def _needs_followup_question(contract_next_move: str, closing_turn: bool) -> bool:
    if closing_turn:
        return False
    return contract_next_move in {"ask", "retry", "switch", "hint_up", "confirm_stt"}


def _has_followup_prompt(text: str) -> bool:
    normalized = _clean_text(text)
    if not normalized:
        return False
    if "?" in normalized:
        return True
    return bool(FOLLOWUP_PROMPT_PATTERN.search(normalized))


def _lead_sentence_signature(text: str) -> str:
    first_sentence = _first_sentence(text)
    if not first_sentence:
        return ""
    normalized = re.sub(r"[^\w가-힣]+", "", first_sentence).lower()
    return normalized[:80]


def _is_repeated_lead_sentence(text: str, used_phrases: list[str]) -> bool:
    signature = _lead_sentence_signature(text)
    if len(signature) < 6:
        return False

    for phrase in used_phrases[-5:]:
        prev_signature = _lead_sentence_signature(str(phrase))
        if len(prev_signature) < 6:
            continue
        ratio = SequenceMatcher(None, signature, prev_signature).ratio()
        if ratio >= 0.9:
            return True
    return False


def _remove_leading_unhelpful_sentence(
    text: str,
    *,
    conversation_phase: str,
    contract_next_move: str,
) -> str:
    normalized = _clean_text(text)
    if not normalized:
        return ""

    sentences = _split_sentences(normalized)
    if len(sentences) < 2:
        return normalized

    current_sentences = sentences
    changed = False

    if conversation_phase in {"opening", "warmup"}:
        filtered_meta = [segment for segment in current_sentences if not _is_session_meta_opening(segment)]
        if filtered_meta and len(filtered_meta) < len(current_sentences):
            current_sentences = filtered_meta
            changed = True

    if contract_next_move == "switch":
        filtered_switch = [segment for segment in current_sentences if not _is_switch_permission_question(segment)]
        if filtered_switch and len(filtered_switch) < len(current_sentences):
            current_sentences = filtered_switch
            changed = True

    if not changed:
        return normalized

    return _clean_text(" ".join(current_sentences))


def _build_retry_hint_for_response(
    text: str,
    *,
    used_phrases: list[str],
    user_input_incomplete: bool,
    contract_outcome: str,
    contract_next_move: str,
    conversation_phase: str,
    closing_turn: bool,
    include_soft_checks: bool = False,
) -> str:
    normalized = _clean_text(text)
    if not normalized:
        return "응답이 비었습니다. 짧은 반응 후 질문 1개를 포함해 주세요."

    if conversation_phase in {"opening", "warmup"} and _is_session_meta_opening(normalized):
        return "세션 진행 안내 표현 없이 자연스러운 인사와 질문으로 시작하세요."

    if contract_next_move == "switch" and _is_switch_permission_question(normalized):
        return "주제 전환 동의를 묻지 말고, 바로 새 질문 1개로 이어가세요."

    if _is_repeated_phrase(normalized, used_phrases):
        return "직전 발화와 겹치지 않게 표현을 바꿔 짧게 말하세요."

    if _is_repeated_lead_sentence(normalized, used_phrases):
        return "시작 문장 반복을 피하고 반응 표현을 바꿔 주세요."

    if _is_proposal_only(normalized):
        return "제안 문장으로 끝내지 말고 같은 턴에서 구체 질문까지 이어서 말하세요."

    if user_input_incomplete and not _has_followup_prompt(normalized):
        return "사용자 말이 미완성일 때는 추정 설명 대신 이어 말할 수 있는 질문 1개를 포함하세요."

    if contract_outcome == "no_response" and contract_next_move == "ask" and not _has_followup_prompt(normalized):
        return "무응답 상황에서는 짧은 체크인 뒤 질문 1개를 포함하세요."

    if _needs_followup_question(contract_next_move, closing_turn) and not _has_followup_prompt(normalized):
        return "설명만으로 끝내지 말고 같은 턴에서 바로 답할 수 있는 질문 1개를 포함하세요."

    if include_soft_checks:
        soft_hint = build_soft_retry_hint(normalized)
        if soft_hint:
            return soft_hint

    return ""


def _behavior_fallback_reply(
    *,
    request_close: bool,
    stt_event: str,
    conversation_phase: str,
    contract_outcome: str,
    contract_next_move: str,
) -> str:
    if request_close:
        return EMERGENCY_CLOSING_MESSAGE
    if stt_event == "no_speech":
        return EMERGENCY_STT_NO_SPEECH_MESSAGE

    if contract_next_move == "confirm_stt":
        return "잘 듣지 못했어요. 한 번만 천천히 다시 말씀해 주세요."
    if contract_outcome == "incomplete":
        return "말씀을 이어서 해 주셔도 괜찮아요. 끝까지 들려주실래요?"
    if contract_outcome == "no_response":
        return "괜찮아요. 준비되시면 한마디로 말씀해 주세요."
    if conversation_phase in {"opening", "warmup"}:
        return "안녕하세요. 오늘 기분은 어떠세요?"
    if contract_next_move in {"ask", "retry", "hint_up", "switch"}:
        return "좋아요. 이어서 한 가지 더 말씀해 주실래요?"
    return EMERGENCY_FALLBACK_MESSAGE


def _minimal_emergency_reply(*, request_close: bool, stt_event: str) -> str:
    if request_close:
        return EMERGENCY_CLOSING_MESSAGE
    if stt_event == "no_speech":
        return EMERGENCY_STT_NO_SPEECH_MESSAGE
    return EMERGENCY_FALLBACK_MESSAGE


def _resolve_model_candidates(meta_payload: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    preferred = _clean_text(str(meta_payload.get("llm_model") or ""))
    fallback = _clean_text(str(meta_payload.get("llm_fallback_model") or ""))
    if preferred:
        candidates.append(preferred)
    if fallback and fallback not in candidates:
        candidates.append(fallback)
    for model in DEFAULT_MODEL_CANDIDATES:
        if model not in candidates:
            candidates.append(model)
    return candidates


def _request_completion(
    *,
    messages: list[dict[str, str]],
    temperature: float,
    model_candidates: list[str],
) -> str:
    client = _build_client()
    for model in model_candidates:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            content = _clean_text(response.choices[0].message.content or "")
            if content:
                return content
        except Exception:
            continue
    return ""


def _sanitize_keywords(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        cleaned = _clean_text(str(item))
        if cleaned:
            result.append(cleaned)
    return result[:8]


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^\w가-힣]+", "", _clean_text(text)).lower()


def _infer_topic_seed(recent_messages: list[dict[str, Any]] | None, conversation_summary: str) -> str:
    for message in reversed(recent_messages or []):
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "").lower() != "user":
            continue
        content = _clean_text(str(message.get("content") or ""))
        if not content:
            continue
        tokens = re.findall(r"[가-힣A-Za-z]{2,}", content)
        if tokens:
            return tokens[0]

    summary_tokens = re.findall(r"[가-힣A-Za-z]{2,}", _clean_text(conversation_summary))
    if summary_tokens:
        return summary_tokens[0]
    return "최근 일상"


def _sanitize_stimulus(
    raw: dict[str, Any] | None,
    *,
    module: str,
    difficulty: int,
    topic_seed: str,
) -> dict[str, Any]:
    payload = raw if isinstance(raw, dict) else {}

    prompt = _clean_text(str(payload.get("prompt") or ""))
    if not prompt:
        prompt = f"{topic_seed}와 관련된 경험을 짧게 말해 주세요."

    target_keywords = _sanitize_keywords(payload.get("target_keywords"))
    if not target_keywords:
        target_keywords = [_clean_text(topic_seed)]

    related_keywords = _sanitize_keywords(payload.get("related_keywords"))
    superordinate_keywords = _sanitize_keywords(payload.get("superordinate_keywords"))
    phonological_cues = _sanitize_keywords(payload.get("phonological_cues"))
    region_focus = _sanitize_keywords(payload.get("region_focus"))
    task_family = _clean_text(str(payload.get("task_family") or ""))
    cognitive_domain = _clean_text(str(payload.get("cognitive_domain") or ""))
    if not phonological_cues:
        cues: list[str] = []
        for keyword in target_keywords:
            normalized = re.sub(r"\s+", "", keyword)
            if normalized:
                cues.append(normalized[:1])
        phonological_cues = cues[:3]

    return {
        "module": _clean_text(module) or "naming",
        "difficulty": max(1, min(5, _safe_int(payload.get("difficulty"), difficulty))),
        "prompt": prompt,
        "target_keywords": target_keywords[:5],
        "related_keywords": related_keywords[:5],
        "superordinate_keywords": superordinate_keywords[:5],
        "phonological_cues": phonological_cues[:5],
        "task_family": task_family,
        "cognitive_domain": cognitive_domain,
        "region_focus": region_focus[:4],
        "note": _clean_text(str(payload.get("note") or "")),
    }


def generate_stimulus(
    *,
    module: str,
    difficulty: int,
    used_stimuli: list[dict[str, Any]] | None = None,
    conversation_summary: str = "",
    recent_messages: list[dict[str, Any]] | None = None,
    user_profile: dict[str, Any] | None = None,
    training_profile: dict[str, Any] | None = None,
    time_context: dict[str, Any] | None = None,
    llm_model: str | None = None,
) -> dict[str, Any]:
    topic_seed = _infer_topic_seed(recent_messages, conversation_summary)
    used_digest = json.dumps((used_stimuli or [])[-10:], ensure_ascii=False)
    recent_digest = _format_recent(_normalize_messages(recent_messages, last_k=8))
    training_digest = _json_string(training_profile, default={})
    time_digest = _json_string(time_context, default={})

    prompt = f"""
너는 한국어 MCI 언어치료 세션용 자극 생성기다.
중복 없이 새 자극 1개를 JSON으로만 출력해라.

[Output JSON schema]
{{
  "prompt": "사용자에게 말할 과제 지시 1문장",
  "target_keywords": ["정답/핵심어"],
  "related_keywords": ["관련어"],
  "superordinate_keywords": ["상위범주어"],
  "phonological_cues": ["초성/첫음절 단서"],
  "task_family": "과제 유형 태그(예: recent_event_recall)",
  "cognitive_domain": "인지 기능 태그(예: episodic_memory)",
  "region_focus": ["관련 뇌영역 태그"],
  "difficulty": {max(1, min(5, difficulty))},
  "note": "치료자 참고 메모(짧게)"
}}

[Rules]
- module={module}
- difficulty={max(1, min(5, difficulty))}
- 이전 used_stimuli와 표현/정답이 겹치지 않게 생성
- 정답을 prompt에서 직접 공개하지 말 것
- 한 턴 한 과제 원칙
- 노인 친화 한국어
- training_profile의 active_regions/cognitive_targets/task_families를 우선 반영
- 최근 used_stimuli의 task_family 편중을 피하고 과제 유형을 순환
- 사용자 데이터와 model snapshot 기반으로 자연스러운 일상 맥락에서 유도

[Used Stimuli]
{used_digest}

[Training Profile]
{training_digest}

[Time Context]
{time_digest}

[Conversation Summary]
{conversation_summary or "(empty)"}

[Recent]
{recent_digest}

[User Profile]
{_format_profile(user_profile)}

[Topic Seed]
{topic_seed}
"""

    model_candidates = [llm_model] if _clean_text(str(llm_model or "")) else []
    for model in DEFAULT_MODEL_CANDIDATES:
        if model not in model_candidates:
            model_candidates.append(model)

    parsed: dict[str, Any] | None = None
    for attempt in range(STIMULUS_JSON_RETRY_LIMIT + 1):
        retry_suffix = ""
        if attempt > 0:
            retry_suffix = (
                "\n\n[Retry]\n"
                "직전 출력은 JSON 파싱에 실패했습니다. 설명 없이 JSON 객체 하나만 출력하세요."
            )
        raw = _request_completion(
            messages=[
                {"role": "system", "content": "JSON-only stimulus generator."},
                {"role": "user", "content": (prompt.strip() + retry_suffix).strip()},
            ],
            temperature=0.8,
            model_candidates=model_candidates,
        )
        parsed = _extract_first_json_object(raw)
        if isinstance(parsed, dict):
            break

    if not isinstance(parsed, dict):
        fallback_task_family = ""
        fallback_domain = ""
        fallback_regions: list[str] = []
        if isinstance(training_profile, dict):
            task_candidates = _sanitize_keywords(training_profile.get("task_families"))
            domain_candidates = _sanitize_keywords(training_profile.get("cognitive_targets"))
            region_candidates = _sanitize_keywords(training_profile.get("active_regions"))
            fallback_task_family = task_candidates[0] if task_candidates else ""
            fallback_domain = domain_candidates[0] if domain_candidates else ""
            fallback_regions = region_candidates[:2]
        parsed = {
            "prompt": f"{topic_seed}와 관련된 경험을 한 가지 말해 주세요.",
            "target_keywords": [topic_seed],
            "related_keywords": [],
            "superordinate_keywords": [],
            "phonological_cues": [_normalize_for_match(topic_seed)[:1]],
            "task_family": fallback_task_family,
            "cognitive_domain": fallback_domain,
            "region_focus": fallback_regions,
            "difficulty": max(1, min(5, difficulty)),
            "note": "fallback_due_to_json_parse_failure",
        }

    return _sanitize_stimulus(
        parsed,
        module=module,
        difficulty=difficulty,
        topic_seed=topic_seed,
    )


def _build_user_prompt(
    *,
    conversation_phase: str,
    fatigue_state: str,
    closing_turn: bool,
    turn_index: int,
    training_type: str,
    training_level: int,
    behavior_contract_json: str,
    stimulus_json: str,
    action_text: str,
    memory_summary: str,
    recent_block: str,
    user_text: str,
    used_phrases_json: str,
    time_context_json: str,
    user_time_reference: bool = False,
    user_input_incomplete: bool = False,
) -> str:
    sections: list[str] = [
        "[Session]",
        f"phase={conversation_phase}, fatigue={fatigue_state}, request_close={'true' if closing_turn else 'false'}, turn={turn_index}",
        f"training_type={training_type}, level={training_level}",
        "",
        "[TimeContext]",
        time_context_json,
        "",
        "[BehaviorContract]",
        behavior_contract_json,
        "",
        "[Stimulus]",
        stimulus_json,
    ]

    if action_text:
        sections.extend(["", "[Action]", action_text])

    sections.extend(
        [
            "",
            "[StyleGuard]",
            "- 세션 시작/환영 같은 시스템 메타 표현은 금지합니다.",
            "- 주제 전환 동의를 묻는 허가형 질문은 금지하고 바로 구체 질문으로 이어갑니다.",
            "- 직전 발화와 같은 시작 문구를 반복하지 않습니다.",
            "- 시간/시간대 관련 표현은 TimeContext의 한국시간 기준과 모순되지 않게 유지합니다.",
        ]
    )

    memory = _clean_text(memory_summary)
    if memory:
        sections.extend(["", "[Memory]", memory])

    if user_input_incomplete:
        sections.extend(
            [
                "",
                "[InputStatus]",
                "user_input_incomplete=true",
                "- 사용자의 말을 추정해 완성하지 말고, 이어 말할 수 있는 질문 1개로 연결하세요.",
            ]
        )

    if user_time_reference:
        sections.extend(
            [
                "",
                "[TimeHint]",
                "- 사용자가 시간/시간대를 언급했습니다.",
                "- 한국시간 기준 현재 시각을 짧게 확인하고 같은 턴에서 질문 1개를 이어가세요.",
            ]
        )

    sections.extend(
        [
            "",
            "[Recent]",
            recent_block,
            "",
            "[UsedPhrases]",
            used_phrases_json,
            "",
            "[User]",
            user_text or "(no speech input)",
            "",
            "요청: 행동계약을 지키는 한국어 응답 1~2문장만 출력하세요.",
        ]
    )
    return "\n".join(sections)


def run_llm_summary(
    *,
    existing_summary: str,
    recent_messages: list[dict[str, Any]] | None,
    user_profile: dict[str, Any] | None = None,
) -> str:
    normalized_recent = _normalize_messages(recent_messages)
    if not normalized_recent:
        return _clean_text(existing_summary)

    prompt = f"""
기존 요약과 최근 대화를 합쳐 4문장 이내의 짧은 요약으로 작성하세요.
평가/채점 표현은 쓰지 말고, 대화의 흐름과 핵심 내용만 정리하세요.

[User Profile]
{_format_profile(user_profile)}

[Existing Summary]
{existing_summary or '(none)'}

[Recent Conversation]
{_format_recent(normalized_recent)}
"""

    try:
        response = _build_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 대화 요약 도우미다."},
                {"role": "user", "content": prompt.strip()},
            ],
            temperature=0.2,
        )
        summary = _clean_text(response.choices[0].message.content or "")
        if summary:
            return summary
    except Exception:
        pass

    tail = " / ".join(f"{m['role']}: {m['content']}" for m in normalized_recent[-3:])
    if existing_summary:
        return _clean_text(f"{existing_summary} / {tail}")
    return _clean_text(tail)


def run_llm(
    user_text: str,
    dialog_state: Any | None,
    model_result: dict[str, Any] | None,
    meta: dict[str, Any] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    recent_turns: list[dict[str, Any]] | None = None,
    summary: str = "",
    last_questions: list[str] | None = None,
    conversation_summary: str | None = None,
    recent_messages: list[dict[str, Any]] | None = None,
    user_profile: dict[str, Any] | None = None,
    focus_hint: str = "",
    emotional_tone: str = "neutral",
    feedback_level: str = "neutral",
    request_close: bool = False,
    silence_duration: int = 0,
    recognition_failed: bool = False,
    consecutive_failures: int = 0,
) -> str:
    _ = (model_result, summary, last_questions, user_profile, focus_hint, emotional_tone, feedback_level)
    _ = (silence_duration, recognition_failed, consecutive_failures)

    meta_payload = meta or {}
    model_candidates = _resolve_model_candidates(meta_payload)
    effective_recent = recent_messages or conversation_history or recent_turns or []
    normalized_recent = _normalize_messages(effective_recent, last_k=MAX_RECENT_MESSAGES)
    stt_event = _normalize_event_name(meta_payload.get("stt_event"))

    closing_turn = _to_bool(meta_payload.get("request_close"), request_close)
    turn_index = _safe_int(
        meta_payload.get("turn_index"),
        _safe_int(_state_get(dialog_state, "turn_index", 0), 0),
    )

    conversation_phase = _clean_text(str(meta_payload.get("conversation_phase") or "training")).lower()
    fatigue_state = _clean_text(
        str(
            meta_payload.get("fatigue_state")
            or meta_payload.get("fatigue_level")
            or _state_get(dialog_state, "fatigue_state")
            or _state_get(dialog_state, "fatigue_level")
            or "normal"
        )
    ).lower()

    training_type = _clean_text(
        str(
            meta_payload.get("training_type")
            or _state_get(dialog_state, "training_type", "semantic_naming")
            or "semantic_naming"
        )
    ).lower()
    training_level = _safe_int(
        meta_payload.get("training_level"),
        _safe_int(_state_get(dialog_state, "training_level", 1), 1),
    )

    behavior_contract = _parse_json_like(meta_payload.get("behavior_contract")) or {}
    constraints: dict[str, Any] = {}
    if isinstance(behavior_contract, dict):
        candidate = behavior_contract.get("constraints")
        if isinstance(candidate, dict):
            constraints = candidate
    max_sentences = max(1, min(3, _safe_int(constraints.get("max_sentences"), 2)))
    contract_outcome = _clean_text(str((behavior_contract or {}).get("outcome") or "")).lower()
    contract_next_move = _clean_text(str((behavior_contract or {}).get("next_move") or "")).lower()
    user_input_incomplete = _to_bool(meta_payload.get("user_input_incomplete"), default=False)
    if not user_input_incomplete and contract_outcome == "incomplete":
        user_input_incomplete = True

    stimulus_value: dict[str, Any] = {}
    if isinstance(behavior_contract, dict):
        candidate = behavior_contract.get("stimulus")
        if isinstance(candidate, dict):
            stimulus_value = candidate
    if not stimulus_value:
        candidate = _parse_json_like(meta_payload.get("stimulus"))
        if isinstance(candidate, dict):
            stimulus_value = candidate
    stimulus_json = _json_string(stimulus_value, default={})

    action_text = _clean_text(str(meta_payload.get("action_text") or ""))
    if not action_text and isinstance(behavior_contract, dict):
        action_text = _clean_text(str(behavior_contract.get("notes") or ""))
    user_time_reference = _to_bool(meta_payload.get("user_time_reference"), default=False)
    time_context = _parse_json_like(meta_payload.get("time_context"))
    if not isinstance(time_context, dict):
        time_context = {
            "timezone": _clean_text(str(meta_payload.get("timezone") or "Asia/Seoul")),
            "now_kst_iso": _clean_text(str(meta_payload.get("now_kst_iso") or "")),
            "date_kst": _clean_text(str(meta_payload.get("date_kst") or "")),
            "time_kst": _clean_text(str(meta_payload.get("time_kst") or "")),
            "session_slot_kst": _clean_text(str(meta_payload.get("session_slot") or "")),
        }
    time_context_json = _json_string(time_context, default={"timezone": "Asia/Seoul"})

    memory_summary = _clean_text(
        str(
            meta_payload.get("memory_summary")
            or _state_get(dialog_state, "memory_summary")
            or conversation_summary
            or ""
        )
    )

    recent_block = _format_recent(normalized_recent)
    user_text_cleaned = _clean_text(user_text)

    used_phrases = _parse_json_like(meta_payload.get("used_phrases"))
    if not isinstance(used_phrases, list):
        used_phrases = []
    used_phrases_json = _json_string(used_phrases[-10:], default=[])
    behavior_contract_json = _json_string(behavior_contract, default={})

    user_prompt = _build_user_prompt(
        conversation_phase=conversation_phase,
        fatigue_state=fatigue_state,
        closing_turn=closing_turn,
        turn_index=turn_index,
        training_type=training_type,
        training_level=training_level,
        behavior_contract_json=behavior_contract_json,
        stimulus_json=stimulus_json,
        action_text=action_text,
        memory_summary=memory_summary,
        recent_block=recent_block,
        user_text=user_text_cleaned,
        used_phrases_json=used_phrases_json,
        time_context_json=time_context_json,
        user_time_reference=user_time_reference,
        user_input_incomplete=user_input_incomplete,
    )

    base_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt.strip()},
    ]

    first_raw = _request_completion(
        messages=base_messages,
        temperature=0.55,
        model_candidates=model_candidates,
    )
    used_phrase_texts = [str(item) for item in used_phrases]
    if first_raw:
        first_shaped = _enforce_response_shape(first_raw, max_sentences=max_sentences)
        hard_retry_hint = _build_retry_hint_for_response(
            first_shaped,
            used_phrases=used_phrase_texts,
            user_input_incomplete=user_input_incomplete,
            contract_outcome=contract_outcome,
            contract_next_move=contract_next_move,
            conversation_phase=conversation_phase,
            closing_turn=closing_turn,
            include_soft_checks=False,
        ) if first_shaped else ""
        soft_retry_hint = build_soft_retry_hint(first_shaped) if first_shaped and not hard_retry_hint else ""
        retry_hint = hard_retry_hint or soft_retry_hint
        needs_retry = bool(retry_hint)

        if first_shaped and needs_retry and not closing_turn:
            retry_messages = [
                {
                    "role": "system",
                    "content": (
                        SYSTEM_PROMPT
                        + "\n추가 지시: "
                        + (
                            retry_hint
                            or "제안만 하지 말고, 사용자 마지막 말에 반응한 뒤 같은 주제로 짧게 이어가세요."
                        )
                    ),
                },
                {"role": "user", "content": user_prompt.strip()},
            ]
            retry_raw = _request_completion(
                messages=retry_messages,
                temperature=0.55,
                model_candidates=model_candidates,
            )
            retry_shaped = _enforce_response_shape(retry_raw, max_sentences=max_sentences) if retry_raw else ""
            retry_shaped = _remove_leading_unhelpful_sentence(
                retry_shaped,
                conversation_phase=conversation_phase,
                contract_next_move=contract_next_move,
            )
            retry_violation = _build_retry_hint_for_response(
                retry_shaped,
                used_phrases=used_phrase_texts,
                user_input_incomplete=user_input_incomplete,
                contract_outcome=contract_outcome,
                contract_next_move=contract_next_move,
                conversation_phase=conversation_phase,
                closing_turn=closing_turn,
                include_soft_checks=False,
            ) if retry_shaped else "retry_empty"
            if retry_shaped and not retry_violation:
                return retry_shaped

        if first_shaped:
            cleaned_first = _remove_leading_unhelpful_sentence(
                first_shaped,
                conversation_phase=conversation_phase,
                contract_next_move=contract_next_move,
            )
            first_violation = _build_retry_hint_for_response(
                cleaned_first,
                used_phrases=used_phrase_texts,
                user_input_incomplete=user_input_incomplete,
                contract_outcome=contract_outcome,
                contract_next_move=contract_next_move,
                conversation_phase=conversation_phase,
                closing_turn=closing_turn,
                include_soft_checks=False,
            ) if cleaned_first else "first_empty"
            if cleaned_first and not first_violation:
                return cleaned_first

    return _behavior_fallback_reply(
        request_close=closing_turn,
        stt_event=stt_event,
        conversation_phase=conversation_phase,
        contract_outcome=contract_outcome,
        contract_next_move=contract_next_move,
    )
