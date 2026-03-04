from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SessionMeta(BaseModel):
    session_id: Optional[str] = None
    profile_id: Optional[str] = None
    patient_id: Optional[int] = None
    session_mode: Optional[str] = None
    conversation_mode: Optional[str] = None
    conversation_phase: Optional[str] = None
    request_close: Optional[bool] = None
    session_event: Optional[str] = None
    stt_event: Optional[str] = None
    closing_reason: Optional[str] = None
    turn_index: Optional[int] = None
    elapsed_sec: Optional[float] = None
    remaining_sec: Optional[float] = None
    target_sec: Optional[int] = None
    hard_limit_sec: Optional[int] = None
    should_wrap_up: Optional[bool] = None
    source: Optional[str] = None


class ChatRequest(BaseModel):
    user_message: str
    model_result: Dict[str, Any] = Field(default_factory=dict)
    state: Optional[Dict[str, Any]] = None
    dialog_summary: Optional[str] = None
    meta: Optional[SessionMeta] = None


class StartRequest(BaseModel):
    model_result: Dict[str, Any] = Field(default_factory=dict)
    meta: Optional[SessionMeta] = None


class EndSessionRequest(BaseModel):
    session_id: str
    end_reason: str
    elapsed_sec: Optional[float] = None
    turn_count: Optional[int] = None
    session_mode: Optional[str] = None

