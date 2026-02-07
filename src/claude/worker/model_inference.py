"""
Model inference for voice-based MCI assessment.

Loads the trained RandomForestClassifier and SimpleImputer,
applies feature imputation, and returns prediction results.
"""

import os
import pickle
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Singleton model holders
_model = None
_imputer = None

MODEL_DIR = os.getenv("MODEL_DIR", "/models/audio_processed")
THRESHOLD = 0.48
MODEL_VERSION = "RandomForest_v1_audio"


def load_models():
    """Load trained model and imputer from disk (singleton)."""
    global _model, _imputer

    if _model is None:
        model_path = os.path.join(MODEL_DIR, "trained_model.pkl")
        imputer_path = os.path.join(MODEL_DIR, "trained_model_imputer.pkl")

        logger.info(f"Loading model from: {model_path}")
        with open(model_path, "rb") as f:
            _model = pickle.load(f)

        logger.info(f"Loading imputer from: {imputer_path}")
        with open(imputer_path, "rb") as f:
            _imputer = pickle.load(f)

        logger.info(
            f"Models loaded: {type(_model).__name__}, "
            f"n_features={_model.n_features_in_}, threshold={THRESHOLD}"
        )

    return _model, _imputer


def predict(features: np.ndarray) -> dict:
    """
    Run MCI prediction on extracted features.

    Args:
        features: 1561-dim feature vector from feature_extractor

    Returns:
        dict with prediction results:
            - label: "MCI" or "Control"
            - mci_probability: float 0-1
            - cognitive_score: float 0-100 (higher = healthier)
            - flag: "normal" / "warning" / "critical"
            - flag_reasons: list of explanation strings
            - model_version: version identifier
    """
    model, imputer = load_models()

    # Reshape for sklearn (1 sample, N features)
    features_2d = features.reshape(1, -1)

    # Apply imputation (handle any NaN/missing values)
    features_imputed = imputer.transform(features_2d)

    # Get prediction probabilities
    probas = model.predict_proba(features_imputed)[0]

    # Class 1 = MCI probability
    mci_probability = float(probas[1])

    # Binary prediction with custom threshold
    label = "MCI" if mci_probability >= THRESHOLD else "Control"

    # Cognitive score: 0-100 (higher = healthier)
    cognitive_score = round((1.0 - mci_probability) * 100, 2)

    # Flag determination
    if mci_probability < 0.35:
        flag = "normal"
    elif mci_probability < 0.65:
        flag = "warning"
    else:
        flag = "critical"

    # Generate flag reasons
    flag_reasons = _generate_flag_reasons(mci_probability, label, flag)

    logger.info(
        f"Prediction: {label} (prob={mci_probability:.3f}, "
        f"score={cognitive_score}, flag={flag})"
    )

    return {
        "label": label,
        "mci_probability": round(mci_probability, 4),
        "cognitive_score": cognitive_score,
        "flag": flag,
        "flag_reasons": flag_reasons,
        "model_version": MODEL_VERSION,
    }


def _generate_flag_reasons(mci_probability: float, label: str, flag: str) -> list[str]:
    """Generate human-readable reasons for the assessment flag."""
    reasons = []

    if flag == "critical":
        reasons.append(f"MCI 확률이 매우 높습니다 ({mci_probability:.1%})")
        reasons.append("전문의 상담을 권장합니다")
    elif flag == "warning":
        reasons.append(f"MCI 가능성이 감지되었습니다 ({mci_probability:.1%})")
        reasons.append("추가 검사를 고려해 주세요")
    else:
        reasons.append("인지 기능이 정상 범위입니다")

    return reasons
