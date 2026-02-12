from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is optional at runtime
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:  # type: ignore[misc]
        return False


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")

# Optional external backend hooks.
external_run_llm = None
external_init_dialog_state = None
external_update_state = None
external_dialog_state_model = None

try:
    from .services.llm_service import run_llm as imported_run_llm
    from .states.dialog_state import DialogState as ImportedDialogState
    from .states.dialog_state import init_dialog_state as imported_init_dialog_state
    from .states.state_transition import update_state as imported_update_state

    external_run_llm = imported_run_llm
    external_init_dialog_state = imported_init_dialog_state
    external_update_state = imported_update_state
    external_dialog_state_model = ImportedDialogState
except Exception:
    try:
        from services.llm_service import run_llm as imported_run_llm
        from states.dialog_state import DialogState as ImportedDialogState
        from states.dialog_state import init_dialog_state as imported_init_dialog_state
        from states.state_transition import update_state as imported_update_state

        external_run_llm = imported_run_llm
        external_init_dialog_state = imported_init_dialog_state
        external_update_state = imported_update_state
        external_dialog_state_model = ImportedDialogState
    except Exception:
        pass


def fallback_init_dialog_state() -> dict[str, Any]:
    return {
        "dialog_state": "session_open",
        "training_type": "none",
        "training_level": 1,
        "training_step": 0,
        "fatigue_level": "low",
        "turn_index": 0,
        "elapsed_sec": 0,
        "last_user_utterance": "",
        "last_assistant_utterance": "",
    }


def fallback_update_state(state: dict[str, Any], user_message: str) -> dict[str, Any]:
    message = user_message.lower()
    state["last_user_utterance"] = user_message
    state["turn_index"] = int(state.get("turn_index", 0)) + 1

    if any(token in message for token in ("stop", "finish", "enough", "tired", "quit", "end")):
        state["dialog_state"] = "session_wrap"
        state["fatigue_level"] = "high"
        return state

    if state.get("dialog_state") == "session_open":
        if any(token in message for token in ("remember", "practice", "question", "memory", "train")):
            state["dialog_state"] = "cognitive_training"
            if state.get("training_type") in (None, "none"):
                state["training_type"] = "memory"
            state["training_step"] = 0
        elif state.get("turn_index", 0) >= 1:
            state["dialog_state"] = "cognitive_training"
        return state

    if state.get("dialog_state") == "cognitive_training":
        step = state.get("training_step", 0)
        state["training_step"] = int(step) + 1
        return state

    if state.get("dialog_state") == "recovery_dialog":
        if any(token in message for token in ("okay", "괜찮", "다시", "continue", "yes")):
            state["dialog_state"] = "cognitive_training"
        return state

    if state.get("dialog_state") == "session_wrap":
        return state

    return state


def state_to_payload(state: Any) -> dict[str, Any]:
    if state is None:
        return {}

    if hasattr(state, "model_dump"):
        dumped = state.model_dump()
        if isinstance(dumped, dict):
            return dumped

    if isinstance(state, dict):
        return dict(state)

    return {}


def build_state_from_payload(payload: dict[str, Any] | None) -> Any:
    if payload is None:
        if external_init_dialog_state:
            return external_init_dialog_state()
        return fallback_init_dialog_state()

    if external_dialog_state_model and hasattr(external_dialog_state_model, "model_validate"):
        try:
            return external_dialog_state_model.model_validate(payload)
        except Exception:
            return payload

    return payload


def update_dialog_state(state: Any, user_message: str) -> Any:
    if external_update_state:
        try:
            return external_update_state(state, user_message)
        except Exception:
            pass

    fallback_state = state_to_payload(state)
    return fallback_update_state(fallback_state, user_message)


class SessionMeta(BaseModel):
    session_id: str | None = None
    profile_id: str | None = None
    session_mode: str | None = None
    turn_index: int | None = None
    elapsed_sec: float | None = None
    remaining_sec: float | None = None
    target_sec: int | None = None
    hard_limit_sec: int | None = None
    should_wrap_up: bool | None = None
    source: str | None = None


class ChatRequest(BaseModel):
    user_message: str
    model_result: dict[str, Any]
    state: dict[str, Any] | None = None
    dialog_summary: str | None = None
    meta: SessionMeta | None = None


class StartRequest(BaseModel):
    model_result: dict[str, Any]
    meta: SessionMeta | None = None


class EndSessionRequest(BaseModel):
    session_id: str
    end_reason: str
    elapsed_sec: float | None = None
    turn_count: int | None = None
    session_mode: str | None = None


def build_fallback_reply(
    user_text: str,
    state_payload: dict[str, Any],
    model_result: dict[str, Any],
    meta: SessionMeta | None,
) -> str:
    if meta and meta.should_wrap_up:
        return (
            "오늘 대화 감사해요. 지금까지 이야기한 내용을 잘 기억해 둘게요. "
            "필요하면 다음에 이어서 편하게 말해 주세요."
        )

    dialog_mode = str(state_payload.get("dialog_state", "session_open"))
    stage = str(model_result.get("stage", "unknown"))

    if dialog_mode == "cognitive_training":
        return (
            "좋아요. 방금 말씀하신 내용을 기억하고 있어요. "
            "다음 내용을 이어서 천천히 말해 주세요."
        )

    if dialog_mode == "recovery_dialog":
        return (
            "괜찮아요. 잠깐 쉬었다가 다시 해도 됩니다. "
            "원하시면 지금까지 이야기한 기억을 이어서 정리해 볼게요."
        )

    if dialog_mode == "session_wrap":
        return (
            "오늘 대화 내용을 기억해 두겠습니다. "
            "수고 많으셨고 다음에 다시 이어서 이야기해요."
        )

    return (
        f"말씀해 주신 내용을 기억하겠습니다. 현재 단계는 {stage}로 보고 있어요. "
        "조금 더 이야기해 주시면 이전 내용과 연결해서 도와드릴게요."
    )

def run_dialog_reply(
    user_text: str,
    dialog_state: Any,
    model_result: dict[str, Any],
    meta: SessionMeta | None,
    memory_context: str | None = None,
) -> str:
    if external_run_llm:
        try:
            guidance_lines = [
                "[System Guidance]",
                "- Reply in Korean with a warm but concise tone.",
                "- Use known memory and recent context before asking follow-up questions.",
                "- Do not repeatedly ask for facts the user already provided.",
                "- If user sounds frustrated, acknowledge briefly and move forward.",
                "- Keep memory updated in real time from this turn.",
            ]
            if memory_context:
                guidance_lines.append("")
                guidance_lines.append("[Memory Context]")
                guidance_lines.append(memory_context)
            guidance_lines.append("")
            guidance_lines.append("[Current User Message]")
            guidance_lines.append(user_text)

            guided_user_text = "\n".join(guidance_lines)
            return external_run_llm(
                user_text=guided_user_text,
                dialog_state=dialog_state,
                model_result=model_result,
                meta=to_meta_payload(meta),
            )
        except Exception:
            pass

    return build_fallback_reply(
        user_text=user_text,
        state_payload=state_to_payload(dialog_state),
        model_result=model_result,
        meta=meta,
    )
LOG_DIR = BASE_DIR / "runtime_logs"
LOG_FILE = LOG_DIR / "voice_session_events.jsonl"
LOG_LOCK = Lock()


def append_log(event: str, session_id: str, payload: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "session_id": session_id,
        **payload,
    }

    with LOG_LOCK:
        with LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def to_meta_payload(meta: SessionMeta | None) -> dict[str, Any]:
    if not meta:
        return {}
    return meta.model_dump(exclude_none=True)


MEMORY_FILE = LOG_DIR / "voice_memory_store.json"
MEMORY_LOCK = Lock()
MAX_PROFILE_MEMORY_ITEMS = 40
MAX_PROFILE_RECENT_MESSAGES = 120
MAX_SESSION_MEMORY_TURNS = 80


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_message(text: str) -> str:
    return " ".join((text or "").split()).strip()


def clip_message(text: str, limit: int = 140) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def dedupe_keep_recent(values: list[str], max_items: int) -> list[str]:
    seen: set[str] = set()
    result_reversed: list[str] = []

    for item in reversed(values):
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result_reversed.append(item)
        if len(result_reversed) >= max_items:
            break

    result_reversed.reverse()
    return result_reversed


def sanitize_memory_id(raw: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "_"
        for char in raw.strip()
    )
    return cleaned[:120] or "anonymous"


def default_memory_store() -> dict[str, Any]:
    return {"profiles": {}, "sessions": {}}


def as_clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = normalize_message(item)
        if normalized:
            result.append(normalized)
    return result


def load_memory_store_unlocked() -> dict[str, Any]:
    if not MEMORY_FILE.exists():
        return default_memory_store()

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except Exception:
        return default_memory_store()

    if not isinstance(loaded, dict):
        return default_memory_store()

    profiles = loaded.get("profiles")
    sessions = loaded.get("sessions")
    if not isinstance(profiles, dict):
        profiles = {}
    if not isinstance(sessions, dict):
        sessions = {}

    return {
        "profiles": profiles,
        "sessions": sessions,
    }


def save_memory_store_unlocked(store: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = MEMORY_FILE.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(store, file, ensure_ascii=False, indent=2)
    temp_path.replace(MEMORY_FILE)


def resolve_profile_id(meta: SessionMeta | None, session_id: str) -> str:
    raw_profile_id = ""
    if meta and meta.profile_id:
        raw_profile_id = str(meta.profile_id).strip()
    if not raw_profile_id:
        raw_profile_id = f"anon_{session_id}"
    return sanitize_memory_id(raw_profile_id)


def ensure_profile_unlocked(store: dict[str, Any], profile_id: str) -> dict[str, Any]:
    profiles = store.setdefault("profiles", {})
    profile = profiles.get(profile_id)
    if not isinstance(profile, dict):
        profile = {}

    profile["profile_id"] = profile_id
    profile["updated_at"] = now_iso()
    profile["memory_items"] = as_clean_string_list(profile.get("memory_items"))
    profile["recent_user_messages"] = as_clean_string_list(profile.get("recent_user_messages"))
    profiles[profile_id] = profile
    return profile


def ensure_session_unlocked(
    store: dict[str, Any],
    session_id: str,
    profile_id: str,
) -> dict[str, Any]:
    sessions = store.setdefault("sessions", {})
    session = sessions.get(session_id)
    if not isinstance(session, dict):
        session = {}

    session["session_id"] = session_id
    session["profile_id"] = profile_id
    session["updated_at"] = now_iso()

    turns = session.get("turns")
    if not isinstance(turns, list):
        turns = []
    session["turns"] = turns

    sessions[session_id] = session
    return session


def build_memory_context_unlocked(profile: dict[str, Any], session: dict[str, Any]) -> str:
    lines: list[str] = []

    memory_items = as_clean_string_list(profile.get("memory_items"))
    if memory_items:
        lines.append("Long-term user memory:")
        for item in memory_items[-8:]:
            lines.append(f"- {clip_message(item)}")

    recent_messages = as_clean_string_list(profile.get("recent_user_messages"))
    if recent_messages:
        lines.append("Recent user statements:")
        for item in recent_messages[-8:]:
            lines.append(f"- {clip_message(item)}")

    turns = session.get("turns")
    if isinstance(turns, list) and turns:
        lines.append("Recent session turns:")
        for turn in turns[-6:]:
            if not isinstance(turn, dict):
                continue
            role = str(turn.get("role") or "user").lower()
            label = "User" if role == "user" else "Assistant"
            message = normalize_message(str(turn.get("message") or ""))
            if not message:
                continue
            lines.append(f"- {label}: {clip_message(message)}")

    return "\n".join(lines).strip()


def ensure_memory_session(profile_id: str, session_id: str) -> str:
    with MEMORY_LOCK:
        store = load_memory_store_unlocked()
        profile = ensure_profile_unlocked(store, profile_id)
        session = ensure_session_unlocked(store, session_id, profile_id)
        context = build_memory_context_unlocked(profile, session)
        save_memory_store_unlocked(store)
        return context


def remember_turn_and_get_context(
    session_id: str,
    profile_id: str,
    role: str,
    message: str,
) -> str:
    normalized = normalize_message(message)
    if not normalized:
        return ""

    with MEMORY_LOCK:
        store = load_memory_store_unlocked()
        profile = ensure_profile_unlocked(store, profile_id)
        session = ensure_session_unlocked(store, session_id, profile_id)

        turns = session.get("turns")
        if not isinstance(turns, list):
            turns = []
        turns.append(
            {
                "timestamp": now_iso(),
                "role": role,
                "message": normalized,
            }
        )
        session["turns"] = turns[-MAX_SESSION_MEMORY_TURNS:]
        session["updated_at"] = now_iso()

        if role == "user":
            recent_user_messages = as_clean_string_list(profile.get("recent_user_messages"))
            recent_user_messages.append(normalized)
            profile["recent_user_messages"] = dedupe_keep_recent(
                recent_user_messages,
                MAX_PROFILE_RECENT_MESSAGES,
            )

            if len(normalized) >= 4:
                memory_items = as_clean_string_list(profile.get("memory_items"))
                memory_items.append(normalized)
                profile["memory_items"] = dedupe_keep_recent(
                    memory_items,
                    MAX_PROFILE_MEMORY_ITEMS,
                )

        profile["updated_at"] = now_iso()
        context = build_memory_context_unlocked(profile, session)
        save_memory_store_unlocked(store)
        return context


def finalize_memory_session(session_id: str, end_reason: str) -> None:
    with MEMORY_LOCK:
        store = load_memory_store_unlocked()
        sessions = store.setdefault("sessions", {})
        session = sessions.get(session_id)
        if not isinstance(session, dict):
            return
        session["updated_at"] = now_iso()
        session["ended_at"] = now_iso()
        session["end_reason"] = end_reason
        save_memory_store_unlocked(store)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "LLM chatbot server is running"}


@app.post("/chat")
async def chat(req: ChatRequest) -> dict[str, Any]:
    try:
        meta = req.meta
        session_id = (meta.session_id if meta and meta.session_id else None) or (
            f"session_{uuid.uuid4().hex[:12]}"
        )
        profile_id = resolve_profile_id(meta, session_id)

        dialog_state = build_state_from_payload(req.state)
        dialog_state = update_dialog_state(dialog_state, req.user_message)
        state_payload = state_to_payload(dialog_state)
        state_payload["profile_id"] = profile_id
        memory_context = remember_turn_and_get_context(
            session_id=session_id,
            profile_id=profile_id,
            role="user",
            message=req.user_message,
        )

        append_log(
            event="turn",
            session_id=session_id,
            payload={
                "role": "user",
                "message": req.user_message,
                "profile_id": profile_id,
                "state": state_payload,
                "meta": to_meta_payload(meta),
            },
        )

        reply = run_dialog_reply(
            user_text=req.user_message,
            dialog_state=dialog_state,
            model_result=req.model_result,
            meta=meta,
            memory_context=memory_context,
        )
        remember_turn_and_get_context(
            session_id=session_id,
            profile_id=profile_id,
            role="assistant",
            message=reply,
        )

        append_log(
            event="turn",
            session_id=session_id,
            payload={
                "role": "assistant",
                "message": reply,
                "profile_id": profile_id,
                "state": state_payload,
                "meta": to_meta_payload(meta),
            },
        )

        dialog_summary = (
            "wrap_up_mode" if meta and meta.should_wrap_up else None
        )

        return {
            "response": reply,
            "state": state_payload,
            "dialog_summary": dialog_summary,
            "session_id": session_id,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/start")
async def start_chat(req: StartRequest) -> dict[str, Any]:
    try:
        meta = req.meta
        session_id = (meta.session_id if meta and meta.session_id else None) or (
            f"session_{uuid.uuid4().hex[:12]}"
        )
        profile_id = resolve_profile_id(meta, session_id)
        memory_context = ensure_memory_session(profile_id, session_id)

        dialog_state = build_state_from_payload(None)
        state_payload = state_to_payload(dialog_state)
        state_payload["profile_id"] = profile_id

        opening_user_prompt = (
            "??덈??뤾쉭?? 筌ｌ뮇荑??筌띾Ŋ???뤿???우뮇媛??щ빍?? "
            "??삳뮎 ??롳펷 餓?疫꿸퀣堉??롫뮉 ????揶쎛筌왖??筌욁룓苡???곷튊疫꿸퀬鍮?雅뚯눘苑??"
        )
        reply = run_dialog_reply(
            user_text=opening_user_prompt,
            dialog_state=dialog_state,
            model_result=req.model_result,
            meta=meta,
            memory_context=memory_context,
        )
        remember_turn_and_get_context(
            session_id=session_id,
            profile_id=profile_id,
            role="assistant",
            message=reply,
        )

        append_log(
            event="session_start",
            session_id=session_id,
            payload={
                "profile_id": profile_id,
                "state": state_payload,
                "meta": to_meta_payload(meta),
            },
        )

        append_log(
            event="turn",
            session_id=session_id,
            payload={
                "role": "assistant",
                "message": reply,
                "profile_id": profile_id,
                "state": state_payload,
                "meta": to_meta_payload(meta),
            },
        )

        return {
            "response": reply,
            "state": state_payload,
            "dialog_summary": None,
            "session_id": session_id,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/session/end")
async def end_session(req: EndSessionRequest) -> dict[str, Any]:
    try:
        finalize_memory_session(req.session_id, req.end_reason)
        append_log(
            event="session_end",
            session_id=req.session_id,
            payload={
                "end_reason": req.end_reason,
                "elapsed_sec": req.elapsed_sec,
                "turn_count": req.turn_count,
                "session_mode": req.session_mode,
            },
        )

        return {
            "status": "ok",
            "session_id": req.session_id,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/session/log/{session_id}")
def get_session_log(session_id: str, limit: int = 200) -> dict[str, Any]:
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")

    if not LOG_FILE.exists():
        return {"session_id": session_id, "events": []}

    events: list[dict[str, Any]] = []

    with LOG_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            if data.get("session_id") != session_id:
                continue

            events.append(data)

    return {
        "session_id": session_id,
        "events": events[-limit:],
    }


@app.get("/memory/profile/{profile_id}")
def get_profile_memory(profile_id: str, limit: int = 20) -> dict[str, Any]:
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")

    safe_profile_id = sanitize_memory_id(profile_id)

    with MEMORY_LOCK:
        store = load_memory_store_unlocked()
        profiles = store.get("profiles") if isinstance(store, dict) else {}
        sessions = store.get("sessions") if isinstance(store, dict) else {}
        if not isinstance(profiles, dict):
            profiles = {}
        if not isinstance(sessions, dict):
            sessions = {}

        profile = profiles.get(safe_profile_id) if isinstance(profiles.get(safe_profile_id), dict) else {}
        memory_items = as_clean_string_list(profile.get("memory_items"))[-limit:]
        recent_user_messages = as_clean_string_list(profile.get("recent_user_messages"))[-limit:]

        related_sessions: list[dict[str, Any]] = []
        for session_id, session_data in sessions.items():
            if not isinstance(session_data, dict):
                continue
            if session_data.get("profile_id") != safe_profile_id:
                continue
            related_sessions.append(
                {
                    "session_id": session_id,
                    "updated_at": session_data.get("updated_at"),
                    "ended_at": session_data.get("ended_at"),
                    "end_reason": session_data.get("end_reason"),
                }
            )

    related_sessions.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)

    return {
        "profile_id": safe_profile_id,
        "memory_items": memory_items,
        "recent_user_messages": recent_user_messages,
        "sessions": related_sessions[:limit],
    }


