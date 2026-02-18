"""
Lightweight transcript-first feature extraction for voice assessment.

This worker path does not run Whisper STT or large embedding models.
It expects transcript text from upstream API/chatbot and extracts
session-level linguistic features aligned with the lightweight bundle.
"""

from __future__ import annotations

import logging
import os
import wave
from typing import Any, Dict, Optional, Tuple

from .transcript_feature_engine import extract_session_features, normalize_text

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


TRANSCRIPT_EXTRACTOR_MODE = os.getenv("VOICE_FEATURE_MODE", "lightweight_accurate")
TRANSCRIPT_MORPH_ANALYZER = os.getenv("TRANSCRIPT_MORPH_ANALYZER", "auto")
TRANSCRIPT_FEATURE_PROFILE = os.getenv("TRANSCRIPT_FEATURE_PROFILE", "sum_rate")
TRANSCRIPT_SUMMARY_AGG_MODE = os.getenv("TRANSCRIPT_SUMMARY_AGG_MODE", "sum")
TRANSCRIPT_DROP_UNSTABLE_FEATURES = _env_bool("TRANSCRIPT_DROP_UNSTABLE_FEATURES", False)


def _get_duration_ms(file_path: str) -> int:
    """Read WAV duration in milliseconds."""
    try:
        with wave.open(file_path, "rb") as wf:
            frames = wf.getnframes()
            sample_rate = wf.getframerate()
            if sample_rate <= 0:
                raise ValueError("Invalid sample rate")
            return int(round((frames * 1000.0) / sample_rate))
    except Exception as e:
        raise RuntimeError(f"Failed to read WAV duration: {e}")


def _build_linguistic_detail(feature_row: Dict[str, Any]) -> Dict[str, Any]:
    """Build a concise and stable detail payload for DB storage/debugging."""
    keys = [
        "dur_ms",
        "n_par_utts",
        "eojeol",
        "token_total_mor",
        "pos_noun",
        "pos_verb",
        "pos_adj",
        "pos_adv",
        "pos_pron",
        "deictic_cnt",
        "filler_cnt",
        "particle_cnt_text_proxy",
        "case_marked_cnt_mor_proxy",
        "subordinate_rel_rate",
        "deictic_rate",
        "filler_rate",
        "particle_rate_text_proxy",
    ]
    return {k: feature_row.get(k) for k in keys if k in feature_row}


def transcribe(*_args, **_kwargs) -> str:
    """STT is intentionally disabled in this transcript-first pipeline."""
    raise RuntimeError("Whisper STT is disabled. Provide transcript text from upstream.")


def extract_all_features(
    file_path: str,
    transcript: Optional[str] = None,
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Transcript-first feature extraction.

    Args:
        file_path: Path to WAV file (used for duration only).
        transcript: Required transcript text from upstream STT/LLM flow.

    Returns:
        transcript: normalized transcript text
        features: lightweight feature row dictionary
        linguistic_detail: concise extracted feature details
    """
    if transcript is None or not str(transcript).strip():
        raise RuntimeError("Transcript is required for lightweight post-STT pipeline")

    text = normalize_text(str(transcript))
    if not text:
        raise RuntimeError("Transcript is empty after normalization")

    duration_ms = _get_duration_ms(file_path)

    feature_row = extract_session_features(
        transcript_text=text,
        duration_ms=duration_ms,
        speaker_id="worker",
        speaker="PAR",
        mode=TRANSCRIPT_EXTRACTOR_MODE,
        morph_analyzer_choice=TRANSCRIPT_MORPH_ANALYZER,
        summary_agg_mode=TRANSCRIPT_SUMMARY_AGG_MODE,
        feature_profile=TRANSCRIPT_FEATURE_PROFILE,
        drop_unstable_features=TRANSCRIPT_DROP_UNSTABLE_FEATURES,
    )

    detail = _build_linguistic_detail(feature_row)
    logger.info(
        "Lightweight features extracted: n_keys=%s, duration_ms=%s, morph=%s",
        len(feature_row),
        duration_ms,
        TRANSCRIPT_MORPH_ANALYZER,
    )

    return text, feature_row, detail


def extract_features_after_stt(file_path: str, transcript: str):
    """Public helper used by Celery task path."""
    return extract_all_features(file_path=file_path, transcript=transcript)
