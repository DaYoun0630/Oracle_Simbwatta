#!/usr/bin/env python3
"""Generate synthetic MRI + voice + transcript artifacts for demo use.

This does NOT touch DB/MinIO. It only writes to data/synthetic/.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import random
import wave

import numpy as np
import nibabel as nib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"

rng = np.random.default_rng(20260304)
random.seed(20260304)

NUM_PATIENTS = 5
SR = 16000
DUR_SEC = 6

KOREAN_NAMES = [
    "김하늘", "이준호", "박서연", "최민재", "정유진",
]


def make_brain_like_volume(shape=(160, 192, 160)):
    z, y, x = np.indices(shape)
    cx, cy, cz = np.array(shape) / 2
    rx, ry, rz = shape[0] * 0.35, shape[1] * 0.35, shape[2] * 0.40
    mask = ((x - cx) ** 2) / (rx ** 2) + ((y - cy) ** 2) / (ry ** 2) + ((z - cz) ** 2) / (rz ** 2) <= 1

    vol = rng.normal(0, 0.05, size=shape)
    tissue = 0.3 + 0.7 * np.exp(-(((x - cx) ** 2) + ((y - cy) ** 2) + ((z - cz) ** 2)) / (2 * (min(shape) * 0.18) ** 2))
    vol += tissue
    vol *= mask

    for _ in range(3):
        sx, sy, sz = rng.integers(0, shape[0]), rng.integers(0, shape[1]), rng.integers(0, shape[2])
        rr = rng.integers(6, 12)
        blob = (x - sx) ** 2 + (y - sy) ** 2 + (z - sz) ** 2 <= rr ** 2
        vol[blob] += rng.uniform(0.1, 0.3)

    vol = (vol - vol.min()) / (vol.max() - vol.min() + 1e-8)
    return vol.astype(np.float32)


def write_wav(path: Path, freq=180.0):
    t = np.arange(0, DUR_SEC, 1 / SR)
    env = 0.5 * (1 - np.cos(2 * math.pi * np.minimum(t / DUR_SEC, 1)))
    sig = 0.25 * np.sin(2 * math.pi * freq * t) + 0.05 * rng.normal(0, 1, size=t.shape)
    sig = (sig * env).astype(np.float32)

    pcm = np.clip(sig, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    patients = []

    for i in range(1, NUM_PATIENTS + 1):
        pid = f"SYN_20260304_{i:03d}"
        name = KOREAN_NAMES[(i - 1) % len(KOREAN_NAMES)]
        pdir = OUT / pid
        pdir.mkdir(parents=True, exist_ok=True)

        vol = make_brain_like_volume()
        img = nib.Nifti1Image(vol, affine=np.eye(4))
        mri_path = pdir / f"{pid}_synthetic_t1.nii.gz"
        nib.save(img, str(mri_path))

        wav_path = pdir / f"{pid}_session.wav"
        write_wav(wav_path, freq=160 + i * 15)

        transcript = f"{name}님의 합성 음성 세션입니다. 이것은 테스트용 데이터입니다."
        txt_path = pdir / f"{pid}_session.txt"
        txt_path.write_text(transcript, encoding="utf-8")

        manifest = {
            "patient_id": pid,
            "name": name,
            "mri": mri_path.name,
            "voice": wav_path.name,
            "transcript": txt_path.name,
            "synthetic": True,
        }
        (pdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        patients.append(manifest)

    (OUT / "patients.json").write_text(json.dumps(patients, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Synthetic dataset created at: {OUT}")


if __name__ == "__main__":
    main()
