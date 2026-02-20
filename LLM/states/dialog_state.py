from dataclasses import dataclass
from enum import Enum


class DialogStage(str, Enum):
    EMOTIONAL_STABILIZATION = "emotional_stabilization"
    SESSION_OPEN = "session_open"
    COGNITIVE_TRAINING = "cognitive_training"
    ADAPTIVE_ADJUSTMENT = "adaptive_adjustment"
    RECOVERY_DIALOG = "recovery_dialog"
    SESSION_WRAP = "session_wrap"


class FatigueLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class DialogState:
    conversation_phase: str = "opening"
    dialog_state: str = DialogStage.SESSION_OPEN.value
    strategy_mode: str = "explore_mode"
    question_budget: int = 1
    training_type: str = "none"
    training_level: int = 1
    training_step: int = 0
    fatigue_level: str = FatigueLevel.LOW.value

    session_type: str = "unknown"
    session_goal: str = ""
    turn_index: int = 0
    elapsed_sec: int = 0
    last_user_utterance: str = ""
    last_assistant_utterance: str = ""
    last_user_intent: str = "unknown"

    # Short rolling memory used as prompt hint (1~2 sentences).
    memory_summary: str = ""

    # True once at least one meaningful user utterance was observed.
    has_user_turn: bool = False
