"""Post-approval provider preflight for Aperture.

Run ONLY after Rohan's explicit approval of the specific Gemini key for this
project. Verifies, using the environment (never prints or stores the key):

  1. The configured GEMINI_MODEL exists on this key's project and supports
     generateContent.
  2. One minimal generateContent call succeeds (proves quota is available at
     that moment; a 429 means free quota is busy/exhausted, no paid fallback).

Usage:
  GEMINI_API_KEY=... GEMINI_MODEL=gemini-3.5-flash-lite \
      python scripts/preflight_provider.py
"""
import json
import os
import sys

import httpx

KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
BASE = "https://generativelanguage.googleapis.com/v1beta"


def main() -> int:
    if not KEY:
        print("GEMINI_API_KEY is not set; aborting (no credential use without approval).")
        return 2
    headers = {"x-goog-api-key": KEY}
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE}/models/{MODEL}", headers=headers)
        if r.status_code != 200:
            print(f"model check failed: HTTP {r.status_code}: {r.text[:300]}")
            return 1
        info = r.json()
        methods = info.get("supportedGenerationMethods", [])
        print(f"model {MODEL} found; methods={methods}")
        if "generateContent" not in methods:
            print("model does not support generateContent; choose another GEMINI_MODEL")
            return 1

        probe = client.post(
            f"{BASE}/models/{MODEL}:generateContent",
            headers=headers,
            json={
                "contents": [{"role": "user", "parts": [{"text": "Reply with the single word: ok"}]}],
                "generationConfig": {"maxOutputTokens": 8, "temperature": 0},
            },
        )
        if probe.status_code == 429:
            print("quota busy or exhausted (HTTP 429). Free tier only; retry later, no paid fallback.")
            return 3
        if probe.status_code != 200:
            print(f"generation probe failed: HTTP {probe.status_code}: {probe.text[:300]}")
            return 1
        text = "".join(
            p.get("text", "")
            for p in probe.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
        )
        print(f"generation probe succeeded; reply={text.strip()!r}")
        print("Preflight OK: model available and a live free-tier call succeeded at this time.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
