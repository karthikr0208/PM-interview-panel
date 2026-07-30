"""Is the queue specific to GLM 5.2, or account-wide?

Discriminating experiment. If another model answers in seconds, the ~230s wait is
GLM-5.2 demand, not an account-level throttle — and the fix is a different model.
If everything queues, the fix is a different provider or off-peak scheduling.

Run:  python scripts/probe_models.py
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
KEY = env["NVIDIA_API_KEY"]
BASE = env["NVIDIA_BASE_URL"]
TIMEOUT = 75  # a model that cannot answer a 3-token prompt in 75s is unusable here

CANDIDATES = [
    "z-ai/glm-5.2",
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-8b-instruct",
    "qwen/qwen2.5-7b-instruct",
    "mistralai/mistral-small-24b-instruct",
    "nvidia/llama-3.3-nemotron-super-49b-v1",
]


def list_models() -> list[str]:
    req = urllib.request.Request(f"{BASE}/models",
                                 headers={"Authorization": f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return sorted(m["id"] for m in json.load(resp).get("data", []))
    except Exception as exc:  # noqa: BLE001
        print(f"  could not list models: {type(exc).__name__}: {exc}")
        return []


def timed_call(model: str) -> None:
    body = {"model": model,
            "messages": [{"role": "user", "content": "Reply with one word: ok"}],
            "max_tokens": 8}
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.load(resp)
        elapsed = time.perf_counter() - started
        out = data["choices"][0]["message"].get("content", "")[:24].replace("\n", " ")
        verdict = "USABLE" if elapsed < 15 else "slow"
        print(f"  {model:44} {elapsed:6.1f}s  {verdict:7} {out!r}")
    except urllib.error.HTTPError as exc:
        print(f"  {model:44} HTTP {exc.code}  {exc.read()[:60].decode(errors='replace')}")
    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - started
        print(f"  {model:44} {elapsed:6.1f}s  QUEUED/TIMEOUT")


if __name__ == "__main__":
    print("available models on this account:")
    available = list_models()
    print(f"  {len(available)} listed\n")

    targets = [m for m in CANDIDATES if not available or m in available]
    missing = [m for m in CANDIDATES if available and m not in available]
    for m in missing:
        print(f"  {m:44} not in catalog, skipping")

    print(f"\ntiming (timeout {TIMEOUT}s):")
    for model in targets:
        timed_call(model)
