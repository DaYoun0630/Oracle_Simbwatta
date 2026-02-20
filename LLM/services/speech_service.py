import os
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from openai import OpenAI

AudioErrorType = Literal["api_error", "no_sound", "unclear_speech", "low_confidence"]


@dataclass
class TranscriptionResult:
    text: str
    confidence: float  # 0.0 ~ 1.0
    is_speech_detected: bool  # Voice activity was detected from the input audio.
    is_recognized: bool  # Transcription produced non-empty text.
    error_type: AudioErrorType | None


def _build_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


def transcribe_audio(
    file_path: str,
    *,
    model: str = "gpt-4o-transcribe",
) -> TranscriptionResult:
    client = _build_client()
    is_speech_detected = _detect_audio_activity(file_path)

    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
            )

        text = (transcript.text or "").strip()
        is_speech = bool(text) or is_speech_detected
        is_recognized = bool(text)
        confidence = _estimate_confidence(text)
        error_type = _classify_error(text=text, is_speech=is_speech, confidence=confidence)
        return TranscriptionResult(
            text=text,
            confidence=confidence,
            is_speech_detected=is_speech,
            is_recognized=is_recognized,
            error_type=error_type,
        )
    except Exception:
        return TranscriptionResult(
            text="",
            confidence=0.0,
            is_speech_detected=is_speech_detected,
            is_recognized=False,
            error_type="api_error",
        )


def inspect_wav(path: str | Path) -> dict[str, int]:
    wav_path = Path(path)
    if not wav_path.exists():
        raise FileNotFoundError(f"WAV file not found: {wav_path}")

    try:
        with wave.open(str(wav_path), "rb") as wav_file:
            channels = int(wav_file.getnchannels())
            sample_rate = int(wav_file.getframerate())
            sample_width = int(wav_file.getsampwidth())
            return {
                "channels": channels,
                "sample_rate": sample_rate,
                "sample_width": sample_width,
            }
    except wave.Error as exc:
        raise ValueError(f"Invalid WAV format: {wav_path}") from exc


def ensure_wav_16k_mono_pcm16(
    input_path: str | Path,
    output_path: str | Path,
) -> Path:
    src = Path(input_path)
    dst = Path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        info = inspect_wav(src)
        if (
            info.get("channels") == 1
            and info.get("sample_rate") == 16000
            and info.get("sample_width") == 2
        ):
            if src.resolve() == dst.resolve():
                return dst
            shutil.copyfile(src, dst)
            return dst
    except Exception:
        # Non-standard/invalid WAV is converted via ffmpeg fallback below.
        pass

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-sample_fmt",
        "s16",
        str(dst),
    ]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("WAV conversion timeout (ffmpeg > 10s).") from exc
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg not found. Install ffmpeg for WAV conversion.") from exc

    if completed.returncode != 0 or not dst.exists():
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(f"WAV conversion failed: {stderr or 'ffmpeg error'}")
    return dst


def synthesize_speech(
    text: str,
    *,
    voice: str = "alloy",
    response_format: Literal["mp3", "wav"] = "mp3",
    model: str = "gpt-4o-mini-tts",
    instructions: str | None = None,
) -> bytes:
    if response_format not in ("mp3", "wav"):
        raise ValueError("response_format must be one of: mp3, wav")

    cleaned_text = (text or "").strip()
    if not cleaned_text:
        raise ValueError("text must not be empty.")

    payload: dict[str, object] = {
        "model": model,
        "voice": voice,
        "input": cleaned_text,
        "format": response_format,
    }
    if instructions:
        payload["instructions"] = instructions

    client = _build_client()
    try:
        response = client.audio.speech.create(**payload)
    except TypeError:
        # Older SDK/API path may not accept instructions field.
        payload.pop("instructions", None)
        response = client.audio.speech.create(**payload)
    return _extract_audio_bytes(response)


def _extract_audio_bytes(response: object) -> bytes:
    if isinstance(response, (bytes, bytearray)):
        return bytes(response)
    if hasattr(response, "read"):
        payload = response.read()
        if isinstance(payload, (bytes, bytearray)):
            return bytes(payload)
    if hasattr(response, "content"):
        payload = getattr(response, "content")
        if isinstance(payload, (bytes, bytearray)):
            return bytes(payload)
    raise RuntimeError("TTS response did not contain audio bytes.")


def _detect_audio_activity(file_path: str) -> bool:
    path = Path(file_path)
    if not path.exists():
        return False
    if path.stat().st_size <= 0:
        return False

    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wav_file:
                frame_count = wav_file.getnframes()
                if frame_count <= 0:
                    return False

                sample_width = wav_file.getsampwidth()
                frame_rate = max(1, wav_file.getframerate())
                # Analyze up to ~2 seconds for fast VAD-like detection.
                frames = wav_file.readframes(min(frame_count, frame_rate * 2))
                peak = _peak_amplitude(frames, sample_width)
                max_amp = _max_amplitude(sample_width)
                if max_amp <= 0:
                    return len(frames) > 0
                return (peak / max_amp) >= 0.01
        except Exception:
            # If WAV parsing fails, use a conservative size-based fallback.
            pass

    # For compressed formats (webm/mp3/etc.), use a coarse fallback signal.
    return path.stat().st_size > 2048


def _peak_amplitude(frames: bytes, sample_width: int) -> float:
    if not frames or sample_width <= 0:
        return 0.0

    if sample_width == 1:
        # 8-bit PCM is typically unsigned.
        return float(max(abs(byte - 128) for byte in frames))

    step = sample_width
    max_peak = 0
    for idx in range(0, len(frames) - step + 1, step):
        sample = int.from_bytes(frames[idx : idx + step], byteorder="little", signed=True)
        abs_sample = abs(sample)
        if abs_sample > max_peak:
            max_peak = abs_sample
    return float(max_peak)


def _max_amplitude(sample_width: int) -> float:
    if sample_width <= 0:
        return 0.0
    if sample_width == 1:
        return 127.0
    return float((1 << (8 * sample_width - 1)) - 1)


def _estimate_confidence(text: str) -> float:
    cleaned = "".join(text.split())
    if not cleaned:
        return 0.0
    if len(cleaned) < 2:
        return 0.2
    if len(cleaned) < 5:
        return 0.5
    return 0.9


def _classify_error(text: str, is_speech: bool, confidence: float) -> AudioErrorType | None:
    if not is_speech:
        return "no_sound"
    if not text:
        return "unclear_speech"
    if len("".join(text.split())) < 3 or confidence < 0.4:
        return "low_confidence"
    return None
