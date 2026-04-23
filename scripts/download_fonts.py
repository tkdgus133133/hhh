#!/usr/bin/env python3
"""Render 배포 시 한글 폰트 자동 다운로드.

buildCommand에서 호출:
  python scripts/download_fonts.py
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
PUBLIC_FONTS_DIR = ROOT / "public" / "fonts"

# 다운로드할 폰트 목록: (저장파일명, 다운로드 URL)
FONTS = [
    (
        "NanumGothic.ttf",
        "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf",
    ),
    (
        "NanumGothicBold.ttf",
        "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf",
    ),
]


def main() -> int:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_FONTS_DIR.mkdir(parents=True, exist_ok=True)
    success = True
    for filename, url in FONTS:
        targets = [FONTS_DIR / filename, PUBLIC_FONTS_DIR / filename]
        primary = targets[0]
        if primary.exists() and primary.stat().st_size > 10_000:
            print(f"[fonts] Already exists: {primary} ({primary.stat().st_size:,} bytes)")
        else:
            print(f"[fonts] Downloading {filename} from {url} ...")
            try:
                urllib.request.urlretrieve(url, str(primary))
                size = primary.stat().st_size
                print(f"[fonts] OK: {primary} ({size:,} bytes)")
                if size < 10_000:
                    print(f"[fonts] WARN: {filename} seems too small ({size} bytes), may be corrupt", file=sys.stderr)
                    success = False
            except Exception as exc:
                print(f"[fonts] WARN: {filename} download failed: {exc}", file=sys.stderr)
                success = False
                continue

        for target in targets[1:]:
            try:
                target.write_bytes(primary.read_bytes())
                print(f"[fonts] Synced: {target}")
            except Exception as exc:
                print(f"[fonts] WARN: sync failed for {target}: {exc}", file=sys.stderr)
                success = False
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
