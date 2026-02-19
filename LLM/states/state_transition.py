try:
    from .dialog_state import DialogState, DialogStage, FatigueLevel
except ImportError:
    from states.dialog_state import DialogState, DialogStage, FatigueLevel


def decide_next_state(
    state: DialogState,
    signals: dict,
) -> DialogState:
    if not isinstance(signals, dict):
        signals = {}

    user_text = str(signals.get("user_text") or "").strip()
    is_speech_detected = _to_bool_default(signals.get("is_speech_detected"), default=True)
    is_recognized = _to_bool_default(signals.get("is_recognized"), default=True)
    recognition_confidence = _safe_float(signals.get("recognition_confidence"), 1.0)
    silence_duration = _safe_int(signals.get("silence_duration"), 0)
    consecutive_failures = _safe_int(signals.get("consecutive_failures"), 0)

    state.elapsed_sec = _safe_int(signals.get("elapsed_sec"), state.elapsed_sec)
    state.turn_index = _safe_int(signals.get("turn_index"), state.turn_index)

    request_close = _to_bool(signals.get("request_close"))
    if request_close:
        state.last_user_intent = "external_close_request"
        state.conversation_phase = "closing"
        state.dialog_state = DialogStage.SESSION_WRAP.value
        state.question_budget = 0
        return state

    if silence_duration > 0 and not user_text:
        state.last_user_intent = "needs_encouragement"
        state.strategy_mode = "supportive_mode"
        state.question_budget = 0
        return state

    recognition_failed = is_speech_detected and ((not is_recognized) or recognition_confidence < 0.4)
    if recognition_failed:
        state.last_user_intent = "recognition_failed"
        state.strategy_mode = "clarification_mode"
        state.question_budget = 0 if consecutive_failures >= 3 else 1
        return state

    if state.turn_index <= 2:
        state.conversation_phase = "warmup"
        state.dialog_state = DialogStage.SESSION_OPEN.value
    else:
        state.conversation_phase = "dialog"
        state.dialog_state = DialogStage.COGNITIVE_TRAINING.value

    if user_text:
        state.last_user_utterance = user_text
        state.has_user_turn = True
        # Keep step as internal marker only: first meaningful user turn moves to 1, no auto step game.
        if state.training_step == 0:
            state.training_step = 1

    is_question = _to_bool(signals.get("is_question"))
    is_suggestion = _to_bool(signals.get("is_suggestion"))
    is_meta_feedback = _to_bool(signals.get("is_meta_feedback"))
    is_negative_response = _to_bool(signals.get("is_negative_response"))

    if is_meta_feedback:
        state.strategy_mode = "repair_mode"
        state.question_budget = 0
        state.last_user_intent = "meta_feedback"
    elif is_question or is_suggestion:
        state.strategy_mode = "answer_mode"
        state.question_budget = 1
        state.last_user_intent = "question_or_suggestion"
    else:
        state.strategy_mode = "explore_mode"
        state.question_budget = 0 if is_negative_response else 1
        state.last_user_intent = "negative_response" if is_negative_response else "general"

    fatigue = _pick_level(signals.get("fatigue_level"), default=state.fatigue_level)
    engagement = _pick_level(signals.get("engagement_level"), default="normal")
    error = _pick_level(signals.get("error_level"), default="normal")

    if _contains_any(user_text, ("힘들", "지침", "피곤", "아파", "졸려", "tired", "exhausted")):
        fatigue = FatigueLevel.HIGH.value

    user_refused = bool(signals.get("user_refused_training", False)) or _contains_any(
        user_text,
        ("싫", "아니", "그만", "stop", "quit", "end it"),
    )

    state.fatigue_level = fatigue
    if user_refused:
        state.dialog_state = DialogStage.RECOVERY_DIALOG.value
        state.question_budget = 0
        return state

    if fatigue == FatigueLevel.HIGH.value:
        state.dialog_state = DialogStage.RECOVERY_DIALOG.value
        state.question_budget = 0
        return state

    if state.conversation_phase == "dialog":
        if fatigue == FatigueLevel.MEDIUM.value and (engagement == "low" or error == "high"):
            state.dialog_state = DialogStage.RECOVERY_DIALOG.value
            state.question_budget = 0
            return state
        state.dialog_state = DialogStage.COGNITIVE_TRAINING.value
        return state

    state.dialog_state = DialogStage.SESSION_OPEN.value
    return state


def _pick_level(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("low", "medium", "high"):
            return v
        if v in ("normal",):
            return "normal"
    return default


def _safe_int(value, default):
    try:
        if value is None:
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value, default):
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _contains_any(value: str, tokens: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in tokens)


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _to_bool_default(value: object, default: bool) -> bool:
    if value is None:
        return default
    return _to_bool(value)
