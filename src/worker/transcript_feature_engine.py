"""
Transcript-first feature extraction engine.

This adapts the core logic from transcripts_pre_lightweight_accurate.py
to produce session-level features without requiring pandas.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Callable, Dict, Iterable, List, Optional, Tuple

SPACE_RE = re.compile(r"\s+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
TOKEN_CLEAN_RE = re.compile(r"[^0-9A-Za-z가-힣]")

DEICTIC_WORDS = {
    "그거",
    "이거",
    "저거",
    "이것",
    "그것",
    "저것",
    "여기",
    "거기",
    "저기",
}
DEICTIC_WORDS_STRICT = DEICTIC_WORDS - {"저기"}

FILLER_WORDS = {"음", "어", "저기", "그러니까", "인제", "뭐", "아", "오"}

PRONOUNS = {
    "나",
    "내",
    "저",
    "제",
    "우리",
    "저희",
    "너",
    "네",
    "너희",
    "당신",
    "자기",
    "본인",
    "그",
    "그녀",
    "그들",
    "이것",
    "그것",
    "저것",
    "얘",
    "걔",
    "쟤",
}

ADVERBS = {
    "정말",
    "진짜",
    "매우",
    "너무",
    "아주",
    "더",
    "잘",
    "빨리",
    "천천히",
    "가끔",
    "자주",
    "다시",
    "거의",
    "먼저",
    "계속",
    "또",
    "함께",
    "같이",
    "이제",
}

CASE_SUFFIXES = (
    "이",
    "가",
    "을",
    "를",
    "에",
    "에서",
    "에게",
    "한테",
    "로",
    "으로",
    "와",
    "과",
    "의",
)

VERB_ENDINGS = (
    "합니다",
    "했다",
    "했어요",
    "해요",
    "한다",
    "된다",
    "됐다",
    "았다",
    "었다",
    "겠다",
    "였다",
    "이다",
    "다",
    "요",
)

ADJ_STEMS = (
    "좋",
    "싫",
    "예쁘",
    "아프",
    "즐겁",
    "행복",
    "슬프",
    "힘들",
    "어렵",
    "쉽",
    "귀찮",
    "바쁘",
    "크",
    "작",
    "많",
    "적",
    "길",
    "짧",
    "빠르",
    "느리",
    "같",
    "다르",
)

SUBORDINATE_ENDINGS_ENHANCED = (
    "면서",
    "지만",
    "니까",
    "므로",
    "기에",
    "어서",
    "아서",
    "면",
    "거든",
    "는데",
    "ㄴ데",
    "더니",
    "다가",
    "도록",
)

QUOTE_PATTERN = re.compile(r"(다고|라고|냐고|자고)\s*(말|생각|듣|보|느끼)")
NOMINAL_PATTERNS = (
    re.compile(r"(기|음|ㅁ)\s*(를|을|가|이|도|만|은|는)"),
    re.compile(r"것\s*(을|를|이|가)"),
)

KIWI_PUNCT_TAGS = {"SF", "SP", "SS", "SE", "SO", "SW"}
KIWI_NOUN_TAGS = {"NNG", "NNP", "NNB", "NR", "NP"}
KIWI_VERB_TAGS = {"VV", "VX", "VCP", "VCN"}
KIWI_ADJ_TAGS = {"VA"}
KIWI_ADV_TAGS = {"MAG", "MAJ"}
KIWI_PRON_TAGS = {"NP"}
KIWI_CASE_TAGS = {"JKS", "JKO", "JKG", "JKB", "JKC", "JX"}
KIWI_FILLER_TAGS = {"IC"}
MorphAnalyzeFn = Callable[[str], List[Tuple[str, str]]]


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", " ")
    text = SPACE_RE.sub(" ", text).strip()
    return unicodedata.normalize("NFC", text)


def _count_eojeol(text: str) -> int:
    return len([tok for tok in text.split(" ") if tok.strip()])


def _clean_token(token: str) -> str:
    return TOKEN_CLEAN_RE.sub("", token)


def _tokenize(text: str) -> List[str]:
    return [t for t in (_clean_token(x) for x in text.split(" ")) if t]


def _split_utterances(text: str) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []

    parts = []
    for piece in SENTENCE_SPLIT_RE.split(text):
        p = piece.strip()
        if p:
            parts.append(p)
    return parts if parts else [text]


def _endswith_any(token: str, suffixes: Iterable[str]) -> bool:
    return any(len(token) > len(suffix) and token.endswith(suffix) for suffix in suffixes)


def _is_adv(token: str) -> bool:
    return token in ADVERBS or (token.endswith("히") and len(token) > 1)


def _is_adj(token: str) -> bool:
    if any(stem in token for stem in ADJ_STEMS):
        return True
    return token.endswith(("스럽다", "같다", "답다"))


def _is_verb(token: str) -> bool:
    if _is_adj(token):
        return False
    return token.endswith(VERB_ENDINGS)


def _count_case_marked_high_precision(tokens: List[str]) -> int:
    count = 0
    for tok in tokens:
        if len(tok) < 2:
            continue
        if _endswith_any(tok, CASE_SUFFIXES):
            count += 1
    return count


def _count_deictic_high_precision(tokens: List[str]) -> int:
    return sum(1 for t in tokens if t in DEICTIC_WORDS_STRICT)


class EnhancedSubordinateDetector:
    def __init__(self):
        self.ending_set = set(SUBORDINATE_ENDINGS_ENHANCED)

    def detect_from_tokens(self, tokens: List[str]) -> int:
        count = 0
        for tok in tokens:
            if _endswith_any(tok, tuple(self.ending_set)):
                count += 1
        return count

    def detect_from_text(self, text: str) -> int:
        count = 0
        if QUOTE_PATTERN.search(text):
            count += 1
        for patt in NOMINAL_PATTERNS:
            count += len(patt.findall(text))
        return count

    def detect_from_morphs(self, morphs: List[Tuple[str, str]]) -> int:
        count = 0
        for form, tag in morphs:
            if tag == "EC":
                count += 1
                continue
            if _endswith_any(form, tuple(self.ending_set)):
                count += 1
        return count


def build_morph_analyzer(choice: str) -> Tuple[str, Optional[MorphAnalyzeFn]]:
    if choice == "none":
        return "none", None

    if choice in ("auto", "kiwi"):
        try:
            from kiwipiepy import Kiwi  # type: ignore

            kiwi = Kiwi()

            def analyze_kiwi(text: str) -> List[Tuple[str, str]]:
                out: List[Tuple[str, str]] = []
                for token in kiwi.tokenize(text):
                    out.append((token.form, token.tag))
                return out

            return "kiwi", analyze_kiwi
        except Exception:
            if choice == "kiwi":
                raise
    return "none", None


def _weighted_utterances(text: str, duration_ms: int) -> List[Tuple[str, int, int]]:
    utt_texts = _split_utterances(text)
    if not utt_texts:
        return []

    weights = [max(1, _count_eojeol(u)) for u in utt_texts]
    total = sum(weights)

    rows: List[Tuple[str, int, int]] = []
    cursor = 0
    for i, utt in enumerate(utt_texts):
        if i == len(utt_texts) - 1:
            start_ms = cursor
            end_ms = duration_ms
        else:
            chunk = int(round(duration_ms * (weights[i] / total)))
            start_ms = cursor
            end_ms = min(duration_ms, cursor + max(1, chunk))
        cursor = end_ms
        rows.append((utt, start_ms, end_ms))
    return rows


def _safe_mean(values: List[Optional[float]]) -> Optional[float]:
    nums = [v for v in values if isinstance(v, (int, float))]
    return (sum(nums) / len(nums)) if nums else None


def extract_session_features(
    transcript_text: str,
    duration_ms: int,
    speaker_id: str = "test",
    speaker: str = "PAR",
    mode: str = "lightweight_accurate",
    morph_analyzer_choice: str = "none",
    summary_agg_mode: str = "sum",
    feature_profile: str = "sum_rate",
    drop_unstable_features: bool = False,
) -> Dict[str, object]:
    use_high_precision = mode == "lightweight_accurate"
    text = normalize_text(transcript_text)
    if not text:
        return {
            "speaker_id": speaker_id,
            "speaker": speaker,
            "text": "",
            "dur_ms": duration_ms,
            "eojeol": 0,
            "token_total_mor": 0,
            "pos_noun": 0,
            "pos_verb": 0,
            "pos_adj": 0,
            "pos_adv": 0,
            "pos_pron": 0,
            "deictic_cnt": 0,
            "filler_cnt": 0,
            "particle_cnt_text_proxy": 0,
            "case_marked_cnt_mor_proxy": 0,
            "subordinate_rel_rate": 0.0,
            "deictic_rate": 0.0,
            "filler_rate": 0.0,
            "particle_rate_text_proxy": 0.0,
            "n_par_utts": 0,
        }

    _, morph_analyze = build_morph_analyzer(morph_analyzer_choice)
    detector = EnhancedSubordinateDetector()
    utter_rows = _weighted_utterances(text, duration_ms)
    if not utter_rows:
        return {
            "speaker_id": speaker_id,
            "speaker": speaker,
            "text": text,
            "dur_ms": duration_ms,
            "n_par_utts": 0,
        }

    rows: List[Dict[str, Optional[float]]] = []
    for utt_text, start_ms, end_ms in utter_rows:
        eojeol = _count_eojeol(utt_text)
        dur = max(0, end_ms - start_ms)
        tokens = _tokenize(utt_text)
        morphs = morph_analyze(utt_text) if morph_analyze is not None else []
        morphs_clean = [(_clean_token(f), t) for f, t in morphs if _clean_token(f)]

        if morphs_clean:
            token_total = sum(1 for _, tag in morphs_clean if tag not in KIWI_PUNCT_TAGS)
            pos_noun = sum(1 for _, tag in morphs_clean if tag in KIWI_NOUN_TAGS)
            pos_verb = sum(1 for _, tag in morphs_clean if tag in KIWI_VERB_TAGS)
            pos_adj = sum(1 for _, tag in morphs_clean if tag in KIWI_ADJ_TAGS)
            pos_adv = sum(1 for _, tag in morphs_clean if tag in KIWI_ADV_TAGS)
            pos_pron = sum(1 for _, tag in morphs_clean if tag in KIWI_PRON_TAGS)
            deictic_vocab = DEICTIC_WORDS_STRICT if use_high_precision else DEICTIC_WORDS
            deictic_cnt = sum(
                1 for tok, tag in morphs_clean if tag in KIWI_PRON_TAGS and tok in deictic_vocab
            )
            filler_cnt = sum(
                1 for tok, tag in morphs_clean if tag in KIWI_FILLER_TAGS or tok in FILLER_WORDS
            )
            case_marked_cnt = sum(1 for _, tag in morphs_clean if tag in KIWI_CASE_TAGS)
            rel_total = token_total
            sub_cnt = detector.detect_from_morphs(morphs_clean)
            if use_high_precision:
                sub_cnt = max(sub_cnt, detector.detect_from_text(utt_text))
        else:
            token_total = len(tokens)
            pos_pron = sum(1 for t in tokens if t in PRONOUNS)
            pos_adv = sum(1 for t in tokens if _is_adv(t))
            pos_adj = sum(1 for t in tokens if _is_adj(t))
            pos_verb = sum(1 for t in tokens if _is_verb(t))
            non_noun = pos_verb + pos_adj + pos_adv + pos_pron + sum(1 for t in tokens if t in FILLER_WORDS)
            pos_noun = max(0, token_total - non_noun)
            deictic_cnt = (
                _count_deictic_high_precision(tokens)
                if use_high_precision
                else sum(1 for t in tokens if t in DEICTIC_WORDS)
            )
            filler_cnt = sum(1 for t in tokens if t in FILLER_WORDS)
            case_marked_cnt = (
                _count_case_marked_high_precision(tokens)
                if use_high_precision
                else sum(1 for t in tokens if _endswith_any(t, CASE_SUFFIXES))
            )
            rel_total = len(tokens)
            sub_cnt = detector.detect_from_tokens(tokens)
            if use_high_precision:
                sub_cnt = max(sub_cnt, detector.detect_from_text(utt_text))

        particle_patterns = [
            r"(은|는)\b",
            r"(이|가)\b",
            r"(을|를)\b",
            r"(에|에서)\b",
            r"(으로|로)\b",
            r"(와|과)\b",
            r"(도|만|까지|부터)\b",
        ]
        particle_cnt = sum(len(re.findall(p, utt_text)) for p in particle_patterns)

        subordinate_rel_rate = (sub_cnt / rel_total) if rel_total else None
        deictic_rate = (deictic_cnt / token_total) if token_total else None
        filler_rate = (filler_cnt / token_total) if token_total else None
        particle_rate = (particle_cnt / eojeol) if eojeol else None

        rows.append(
            {
                "dur_ms": float(dur),
                "eojeol": float(eojeol),
                "token_total_mor": float(token_total),
                "pos_noun": float(pos_noun),
                "pos_verb": float(pos_verb),
                "pos_adj": float(pos_adj),
                "pos_adv": float(pos_adv),
                "pos_pron": float(pos_pron),
                "deictic_cnt": float(deictic_cnt),
                "filler_cnt": float(filler_cnt),
                "particle_cnt_text_proxy": float(particle_cnt),
                "case_marked_cnt_mor_proxy": None if drop_unstable_features else float(case_marked_cnt),
                "subordinate_rel_rate": None if drop_unstable_features else subordinate_rel_rate,
                "deictic_rate": deictic_rate,
                "filler_rate": filler_rate,
                "particle_rate_text_proxy": particle_rate,
            }
        )

    if summary_agg_mode not in {"sum", "mean"}:
        raise ValueError(f"Unsupported summary_agg_mode: {summary_agg_mode}")
    if feature_profile not in {"sum_only", "rate_only", "sum_rate"}:
        raise ValueError(f"Unsupported feature_profile: {feature_profile}")

    def _sum(key: str) -> float:
        return sum((r.get(key) or 0.0) for r in rows)

    eojeol_sum = _sum("eojeol")
    token_sum = _sum("token_total_mor")
    deictic_sum = _sum("deictic_cnt")
    filler_sum = _sum("filler_cnt")
    particle_sum = _sum("particle_cnt_text_proxy")
    case_sum = _sum("case_marked_cnt_mor_proxy") if not drop_unstable_features else None

    subordinate_mean = _safe_mean([r.get("subordinate_rel_rate") for r in rows])
    deictic_rate_sum_based = (deictic_sum / token_sum) if token_sum else 0.0
    filler_rate_sum_based = (filler_sum / token_sum) if token_sum else 0.0
    particle_rate_sum_based = (particle_sum / eojeol_sum) if eojeol_sum else 0.0

    if summary_agg_mode == "mean":
        base = {
            "dur_ms": _safe_mean([r.get("dur_ms") for r in rows]) or 0.0,
            "eojeol": _safe_mean([r.get("eojeol") for r in rows]) or 0.0,
            "token_total_mor": _safe_mean([r.get("token_total_mor") for r in rows]) or 0.0,
            "pos_noun": _safe_mean([r.get("pos_noun") for r in rows]) or 0.0,
            "pos_verb": _safe_mean([r.get("pos_verb") for r in rows]) or 0.0,
            "pos_adj": _safe_mean([r.get("pos_adj") for r in rows]) or 0.0,
            "pos_adv": _safe_mean([r.get("pos_adv") for r in rows]) or 0.0,
            "pos_pron": _safe_mean([r.get("pos_pron") for r in rows]) or 0.0,
            "deictic_cnt": _safe_mean([r.get("deictic_cnt") for r in rows]) or 0.0,
            "filler_cnt": _safe_mean([r.get("filler_cnt") for r in rows]) or 0.0,
            "particle_cnt_text_proxy": _safe_mean([r.get("particle_cnt_text_proxy") for r in rows]) or 0.0,
            "case_marked_cnt_mor_proxy": _safe_mean([r.get("case_marked_cnt_mor_proxy") for r in rows]) or 0.0,
            "subordinate_rel_rate": subordinate_mean or 0.0,
            "deictic_rate": _safe_mean([r.get("deictic_rate") for r in rows]) or 0.0,
            "filler_rate": _safe_mean([r.get("filler_rate") for r in rows]) or 0.0,
            "particle_rate_text_proxy": _safe_mean([r.get("particle_rate_text_proxy") for r in rows]) or 0.0,
        }
    else:
        sum_block = {
            "dur_ms": _sum("dur_ms"),
            "eojeol": eojeol_sum,
            "token_total_mor": token_sum,
            "pos_noun": _sum("pos_noun"),
            "pos_verb": _sum("pos_verb"),
            "pos_adj": _sum("pos_adj"),
            "pos_adv": _sum("pos_adv"),
            "pos_pron": _sum("pos_pron"),
            "deictic_cnt": deictic_sum,
            "filler_cnt": filler_sum,
            "particle_cnt_text_proxy": particle_sum,
            "case_marked_cnt_mor_proxy": case_sum if case_sum is not None else 0.0,
        }
        rate_block = {
            "subordinate_rel_rate": subordinate_mean or 0.0,
            "deictic_rate": deictic_rate_sum_based,
            "filler_rate": filler_rate_sum_based,
            "particle_rate_text_proxy": particle_rate_sum_based,
        }

        if feature_profile == "sum_only":
            base = sum_block
        elif feature_profile == "rate_only":
            base = rate_block
        else:
            base = {**sum_block, **rate_block}

    return {
        "speaker_id": speaker_id,
        "speaker": speaker,
        "text": text,
        "n_par_utts": float(len(rows)),
        **base,
    }
