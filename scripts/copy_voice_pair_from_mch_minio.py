#!/usr/bin/env python3
"""
Copy one voice pair (.wav + .txt) from m_ch MinIO into final MinIO.

This script copies real object bytes via S3 API. It does NOT read MinIO's internal
filesystem metadata layout.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from minio import Minio


def parse_bucket_key(raw: str, default_bucket: str) -> tuple[str, str]:
    value = (raw or "").strip().replace("s3://", "")
    if not value:
        raise ValueError("Object path is empty")
    if "/" not in value:
        return default_bucket, value
    first, rest = value.split("/", 1)
    known = {
        "voice-recordings",
        "voice-transcript",
        "processed",
        "mri-scans",
        "exports",
        "mri-preprocessed",
        "mri-xai",
    }
    if first in known:
        return first, rest
    return default_bucket, value


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def stream_copy(
    src: Minio,
    dst: Minio,
    src_bucket: str,
    src_key: str,
    dst_bucket: str,
    dst_key: str,
    content_type: str,
) -> int:
    stat = src.stat_object(src_bucket, src_key)
    size = int(getattr(stat, "size", 0) or 0)
    if size <= 0:
        raise RuntimeError(f"Source object is empty: {src_bucket}/{src_key}")

    ensure_bucket(dst, dst_bucket)

    response = None
    try:
        response = src.get_object(src_bucket, src_key)
        dst.put_object(
            dst_bucket,
            dst_key,
            response,
            length=size,
            content_type=content_type,
        )
    finally:
        if response is not None:
            response.close()
            response.release_conn()

    return size


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy voice wav/txt pair from m_ch MinIO to final MinIO")
    parser.add_argument("--audio-key", required=True, help="Audio object key in m_ch MinIO")
    parser.add_argument(
        "--transcript-key",
        default=None,
        help="Transcript object key in m_ch MinIO (default: audio key with .txt)",
    )

    parser.add_argument("--src-endpoint", default="localhost:9003")
    parser.add_argument("--src-access-key", default="minioadmin")
    parser.add_argument("--src-secret-key", default="minioadmin123")
    parser.add_argument("--src-audio-bucket", default="voice-recordings")
    parser.add_argument("--src-transcript-bucket", default="voice-transcript")

    parser.add_argument("--dst-endpoint", default="localhost:9000")
    parser.add_argument("--dst-access-key", default="minioadmin")
    parser.add_argument("--dst-secret-key", default="change_me1")
    parser.add_argument("--dst-audio-bucket", default="voice-recordings")
    parser.add_argument("--dst-transcript-bucket", default="voice-transcript")

    args = parser.parse_args()

    src_client = Minio(
        endpoint=args.src_endpoint,
        access_key=args.src_access_key,
        secret_key=args.src_secret_key,
        secure=False,
    )
    dst_client = Minio(
        endpoint=args.dst_endpoint,
        access_key=args.dst_access_key,
        secret_key=args.dst_secret_key,
        secure=False,
    )

    src_audio_bucket, src_audio_key = parse_bucket_key(args.audio_key, args.src_audio_bucket)

    if args.transcript_key:
        src_transcript_bucket, src_transcript_key = parse_bucket_key(args.transcript_key, args.src_transcript_bucket)
    else:
        stem = str(Path(src_audio_key).with_suffix(""))
        src_transcript_bucket, src_transcript_key = args.src_transcript_bucket, f"{stem}.txt"

    # Keep destination key exactly the same unless source bucket prefix was provided.
    _, dst_audio_key = parse_bucket_key(args.audio_key, args.dst_audio_bucket)
    if args.transcript_key:
        _, dst_transcript_key = parse_bucket_key(args.transcript_key, args.dst_transcript_bucket)
    else:
        dst_transcript_key = str(Path(dst_audio_key).with_suffix("")) + ".txt"

    audio_size = stream_copy(
        src=src_client,
        dst=dst_client,
        src_bucket=src_audio_bucket,
        src_key=src_audio_key,
        dst_bucket=args.dst_audio_bucket,
        dst_key=dst_audio_key,
        content_type="audio/wav",
    )
    txt_size = stream_copy(
        src=src_client,
        dst=dst_client,
        src_bucket=src_transcript_bucket,
        src_key=src_transcript_key,
        dst_bucket=args.dst_transcript_bucket,
        dst_key=dst_transcript_key,
        content_type="text/plain; charset=utf-8",
    )

    print("Copied objects:")
    print(f"  audio: {src_audio_bucket}/{src_audio_key} -> {args.dst_audio_bucket}/{dst_audio_key} ({audio_size} bytes)")
    print(
        "  transcript: "
        f"{src_transcript_bucket}/{src_transcript_key} -> "
        f"{args.dst_transcript_bucket}/{dst_transcript_key} ({txt_size} bytes)"
    )
    print("Now call /api/patient/recordings/from-minio with these destination keys.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
