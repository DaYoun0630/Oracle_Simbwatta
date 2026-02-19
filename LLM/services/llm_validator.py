import re
from typing import Any, Dict, List


def has_reaction_sentence(text: str) -> bool:
    normalized = " ".join((text or "").split()).strip()
    if not normalized:
        return False
    return bool(
        re.search(
            r"(그렇군요|그랬군요|좋아요|맞아요|말씀|들으니|수고하셨어요|잘하셨어요)",
            normalized,
        )
    )


def is_proposal_only_response(text: str) -> bool:
    normalized = " ".join((text or "").split()).strip()
    if not normalized:
        return True

    has_proposal = bool(re.search(r"(해볼까요|시작해볼까요|시작할까요|준비되셨다면)", normalized))
    if not has_proposal:
        return False

    # Allow proposal if it also contains natural reaction/acknowledgement.
    if has_reaction_sentence(normalized):
        return False

    # Proposal only when it is mostly invitation with no concrete follow-up.
    bare = re.sub(r"(해볼까요|시작해볼까요|시작할까요|준비되셨다면|가볍게|부담 없이)", "", normalized)
    bare = bare.strip(" .!?")
    return len(bare) < 10


def build_soft_retry_hint(final_text: str) -> str:
    if is_proposal_only_response(final_text):
        return "제안만 하지 말고, 사용자 마지막 말에 공감 반응 후 같은 주제로 한 번 이어가세요."
    if not has_reaction_sentence(final_text):
        return "응답 첫 문장에서 사용자 말에 대한 반응을 먼저 넣어주세요."
    return ""


def validate_llm_json_response(
    llm_json: Dict[str, Any],
    session_context: Dict[str, Any],
) -> List[str]:
    violations: List[str] = []

    final_text = str(llm_json.get("final_text", ""))
    facts_used = llm_json.get("facts_used", [])

    if not final_text:
        violations.append("final_text_empty")

    banned_patterns = [
        r"채점",
        r"점수",
        r"오답",
        r"정답을 공개",
        r"진단입니다",
        r"치매입니다",
    ]
    for pat in banned_patterns:
        if re.search(pat, final_text):
            violations.append(f"banned_phrase:{pat}")
            break

    memory_claim_patterns = [
        r"지난번",
        r"저번에",
        r"기억하시죠",
        r"아까 말했죠",
    ]

    if any(re.search(p, final_text) for p in memory_claim_patterns):
        allowed_memory = str(session_context.get("recent_session_summary", "")) + " " + str(
            json_path_get(session_context, ["therapy_profile", "preferred_topics"], "")
        )
        if not allowed_memory.strip():
            violations.append("possible_fabricated_memory")

    # Naturalness flags are warnings for soft retry, not hard failure.
    if is_proposal_only_response(final_text):
        violations.append("soft_retry:proposal_only")
    elif not has_reaction_sentence(final_text):
        violations.append("soft_retry:missing_reaction")

    if not isinstance(facts_used, list):
        violations.append("facts_used_not_list")
        return violations

    for key in facts_used:
        if not isinstance(key, str):
            violations.append("facts_used_non_string_key")
            continue
        if not context_key_exists(session_context, key):
            violations.append(f"facts_used_key_not_in_context:{key}")

    return violations


def context_key_exists(context: Dict[str, Any], dotted_key: str) -> bool:
    parts = dotted_key.split(".")
    cur: Any = context
    for p in parts:
        if not isinstance(cur, dict):
            return False
        if p not in cur:
            return False
        cur = cur[p]
    return True


def json_path_get(context: Dict[str, Any], path: List[str], default: Any) -> Any:
    cur: Any = context
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur
