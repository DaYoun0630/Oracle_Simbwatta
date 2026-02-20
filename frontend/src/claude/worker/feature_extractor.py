"""
Feature extraction pipeline for voice-based MCI assessment.

Extracts 1561 features from audio files:
- 768-dim audio embeddings (wav2vec2-base, mean pooling)
- 768-dim text embeddings (klue/bert-base, CLS token)
- ~25 linguistic features (Kiwi Korean NLP)
"""

import os
import logging
import numpy as np
import torch
import librosa

logger = logging.getLogger(__name__)

# Singleton model holders (loaded once per worker process)
_whisper_model = None
_wav2vec2_model = None
_wav2vec2_processor = None
_bert_model = None
_bert_tokenizer = None
_kiwi = None

SAMPLE_RATE = 16000


def _load_whisper():
    """Load faster-whisper model for Korean speech-to-text (INT8, CPU optimized)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info("Loading faster-whisper model: small (INT8, CPU)")
        _whisper_model = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8",
        )
    return _whisper_model


def _load_wav2vec2():
    """Load wav2vec2 model for audio embeddings."""
    global _wav2vec2_model, _wav2vec2_processor
    if _wav2vec2_model is None:
        from transformers import Wav2Vec2Model, Wav2Vec2Processor
        model_name = "facebook/wav2vec2-base"
        logger.info(f"Loading wav2vec2 model: {model_name}")
        _wav2vec2_processor = Wav2Vec2Processor.from_pretrained(model_name)
        _wav2vec2_model = Wav2Vec2Model.from_pretrained(model_name)
        _wav2vec2_model.eval()
    return _wav2vec2_model, _wav2vec2_processor


def _load_bert():
    """Load Korean BERT model for text embeddings."""
    global _bert_model, _bert_tokenizer
    if _bert_model is None:
        from transformers import BertModel, BertTokenizer
        model_name = "klue/bert-base"
        logger.info(f"Loading BERT model: {model_name}")
        _bert_tokenizer = BertTokenizer.from_pretrained(model_name)
        _bert_model = BertModel.from_pretrained(model_name)
        _bert_model.eval()
    return _bert_model, _bert_tokenizer


def _load_kiwi():
    """Load Kiwi Korean NLP tokenizer."""
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        logger.info("Loading Kiwi Korean NLP")
        _kiwi = Kiwi()
    return _kiwi


def load_audio(file_path: str) -> tuple[np.ndarray, int]:
    """Load audio file at 16kHz mono."""
    logger.info(f"Loading audio: {file_path}")
    audio, sr = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)
    # Normalize amplitude
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val
    return audio, sr


def transcribe(audio: np.ndarray, sr: int = SAMPLE_RATE) -> str:
    """Transcribe audio to Korean text using faster-whisper (INT8, ~4-6x faster)."""
    model = _load_whisper()

    segments, info = model.transcribe(
        audio,
        language="ko",
        task="transcribe",
        beam_size=5,
    )

    transcript = " ".join(seg.text.strip() for seg in segments)
    logger.info(f"Transcription complete: {len(transcript)} chars, lang={info.language}")
    return transcript.strip()


def extract_audio_embeddings(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Extract 768-dim audio embeddings using wav2vec2 (mean pooling)."""
    model, processor = _load_wav2vec2()

    inputs = processor(audio, sampling_rate=sr, return_tensors="pt", padding=True)

    with torch.no_grad():
        outputs = model(**inputs)

    # Mean pooling over time dimension -> 768-dim vector
    embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    logger.info(f"Audio embeddings shape: {embeddings.shape}")
    return embeddings  # (768,)


def extract_text_embeddings(transcript: str) -> np.ndarray:
    """Extract 768-dim text embeddings using klue/bert-base (CLS token)."""
    model, tokenizer = _load_bert()

    inputs = tokenizer(
        transcript,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True,
    )

    with torch.no_grad():
        outputs = model(**inputs)

    # CLS token embedding -> 768-dim vector
    cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()
    logger.info(f"Text embeddings shape: {cls_embedding.shape}")
    return cls_embedding  # (768,)


def extract_linguistic_features(transcript: str) -> tuple[np.ndarray, dict]:
    """
    Extract linguistic features using Kiwi Korean NLP.

    Returns:
        features: numpy array of ~25 linguistic features
        detail: dict with human-readable feature breakdown
    """
    kiwi = _load_kiwi()

    tokens = kiwi.tokenize(transcript)

    # Basic counts
    total_tokens = len(tokens)
    unique_forms = len(set(t.form for t in tokens))

    # POS tag counts
    pos_counts = {}
    for t in tokens:
        tag = t.tag
        pos_counts[tag] = pos_counts.get(tag, 0) + 1

    # Filler words (음, 어, 그, 저, 뭐, 아)
    filler_words = {"음", "어", "그", "저", "뭐", "아", "에", "으음", "어어"}
    filler_count = sum(1 for t in tokens if t.form in filler_words)

    # Deictic words (그거, 저거, 이거, 그것, 저것, 이것)
    deictic_words = {"그거", "저거", "이거", "그것", "저것", "이것", "거기", "여기", "저기"}
    deictic_count = sum(1 for t in tokens if t.form in deictic_words)

    # POS category counts
    noun_tags = {"NNG", "NNP", "NNB", "NR", "NP"}
    verb_tags = {"VV", "VA", "VX", "VCP", "VCN"}
    adj_tags = {"VA"}
    adv_tags = {"MAG", "MAJ"}

    noun_count = sum(pos_counts.get(t, 0) for t in noun_tags)
    verb_count = sum(pos_counts.get(t, 0) for t in verb_tags)
    adj_count = sum(pos_counts.get(t, 0) for t in adj_tags)
    adv_count = sum(pos_counts.get(t, 0) for t in adv_tags)

    # Rates (avoid division by zero)
    safe_total = max(total_tokens, 1)
    filler_rate = filler_count / safe_total
    deictic_rate = deictic_count / safe_total
    noun_ratio = noun_count / safe_total
    verb_ratio = verb_count / safe_total
    adj_ratio = adj_count / safe_total
    adv_ratio = adv_count / safe_total
    lexical_diversity = unique_forms / safe_total

    # Sentence-level features
    sentences = kiwi.split_into_sents(transcript)
    num_sentences = len(sentences)
    avg_sentence_length = total_tokens / max(num_sentences, 1)

    # Build feature vector (25 features)
    feature_vector = np.array([
        total_tokens,
        unique_forms,
        num_sentences,
        avg_sentence_length,
        lexical_diversity,
        filler_count,
        filler_rate,
        deictic_count,
        deictic_rate,
        noun_count,
        noun_ratio,
        verb_count,
        verb_ratio,
        adj_count,
        adj_ratio,
        adv_count,
        adv_ratio,
        pos_counts.get("NNG", 0),   # Common nouns
        pos_counts.get("NNP", 0),   # Proper nouns
        pos_counts.get("VV", 0),    # Verbs
        pos_counts.get("VA", 0),    # Adjectives
        pos_counts.get("MAG", 0),   # Adverbs
        pos_counts.get("JKS", 0),   # Subject particles
        pos_counts.get("JKO", 0),   # Object particles
        pos_counts.get("EF", 0),    # Sentence-ending endings
    ], dtype=np.float32)

    detail = {
        "total_tokens": total_tokens,
        "unique_forms": unique_forms,
        "num_sentences": num_sentences,
        "avg_sentence_length": round(avg_sentence_length, 2),
        "lexical_diversity": round(lexical_diversity, 4),
        "filler_count": filler_count,
        "filler_rate": round(filler_rate, 4),
        "deictic_count": deictic_count,
        "deictic_rate": round(deictic_rate, 4),
        "noun_ratio": round(noun_ratio, 4),
        "verb_ratio": round(verb_ratio, 4),
        "adj_ratio": round(adj_ratio, 4),
        "adv_ratio": round(adv_ratio, 4),
    }

    logger.info(f"Linguistic features: {len(feature_vector)} dims")
    return feature_vector, detail


def extract_all_features(file_path: str) -> tuple[str, np.ndarray, dict]:
    """
    Full feature extraction pipeline.

    Args:
        file_path: Path to audio file (wav, mp3, etc.)

    Returns:
        transcript: Korean text transcription
        features: 1561-dim numpy array (768 + 768 + 25)
        linguistic_detail: dict with readable linguistic breakdown
    """
    logger.info(f"Starting full feature extraction for: {file_path}")

    # Step 1: Load audio
    audio, sr = load_audio(file_path)
    logger.info(f"Audio loaded: {len(audio)/sr:.1f}s duration")

    # Step 2: Transcribe with Whisper
    transcript = transcribe(audio, sr)

    # Step 3: Extract audio embeddings (wav2vec2)
    audio_emb = extract_audio_embeddings(audio, sr)  # (768,)

    # Step 4: Extract text embeddings (BERT)
    text_emb = extract_text_embeddings(transcript)  # (768,)

    # Step 5: Extract linguistic features (Kiwi)
    ling_features, ling_detail = extract_linguistic_features(transcript)  # (25,)

    # Step 6: Concatenate all features
    features = np.concatenate([audio_emb, text_emb, ling_features])
    logger.info(f"Combined features: {features.shape} (expected 1561)")

    return transcript, features, ling_detail
