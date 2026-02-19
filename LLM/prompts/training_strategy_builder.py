import json
from typing import Any


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _to_intensity(modifier: dict[str, Any]) -> str:
    hint_level = _clean_text(modifier.get("hint_level")).lower()
    pace = _clean_text(modifier.get("training_pace")).lower()
    if hint_level in ("high", "strong") or pace == "slow":
        return "mid"
    return "low"


def _build_hint(strategy: dict[str, Any], modifier: dict[str, Any], user_utterance: str) -> str:
    goal = _clean_text(strategy.get("goal"))
    category = _clean_text(strategy.get("category"))
    if category and user_utterance:
        return f"사용자 발화와 연결해 {category} 맥락에서 짧은 단서 1개만 제시하세요."
    if goal and user_utterance:
        return f"사용자 마지막 말에 반응한 뒤, {goal}와 연결된 가벼운 확장 1개만 제시하세요."
    if goal:
        return f"이번 턴은 {goal}와 관련된 부담 없는 미니 개입 1개만 넣으세요."
    return "사용자 발화에 먼저 반응하고, 같은 주제에서 아주 짧은 개입 1개만 넣으세요."


def _build_avoid(strategy: dict[str, Any]) -> str:
    avoid = _clean_text(strategy.get("avoid"))
    if avoid:
        return avoid
    return "범주를 갑자기 바꾸거나, 과제 안내 템플릿을 반복하지 마세요."


def build_training_behavior(
    strategy_json: str,
    modifier_json: str,
    user_utterance: str = "",
) -> str:
    """
    Returns a compact turn-level intervention card:
    {"name": str, "hint": str, "avoid": str, "intensity": "low|mid"}
    """
    try:
        strategy = json.loads(strategy_json) if strategy_json else {}
    except Exception:
        strategy = {}

    try:
        modifier = json.loads(modifier_json) if modifier_json else {}
    except Exception:
        modifier = {}

    name = _clean_text(strategy.get("name") or strategy.get("module") or strategy.get("goal") or "general")
    payload = {
        "name": name,
        "hint": _build_hint(strategy, modifier, _clean_text(user_utterance)),
        "avoid": _build_avoid(strategy),
        "intensity": _to_intensity(modifier),
    }
    return json.dumps(payload, ensure_ascii=False)
