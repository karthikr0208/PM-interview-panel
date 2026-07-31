"""Is the NVIDIA endpoint slow, queued, or broken? Streaming tells them apart.

A non-streaming call that times out is ambiguous. With streaming, time-to-first-byte
separates the cases: bytes arriving late means queueing, no bytes at all means the
request never started.

Run:  python scripts/probe_latency.py
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
TIMEOUT = 240


def stream_probe(label: str, extra: dict) -> None:
    body = {
        "model": env["NVIDIA_MODEL"],
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 16,
        "stream": True,
        **extra,
    }
    req = urllib.request.Request(
        f"{env['NVIDIA_BASE_URL']}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {env['NVIDIA_API_KEY']}",
                 "Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )

    print(f"\n{label}")
    started = time.perf_counter()
    first_byte: float | None = None
    chunks = 0
    text = ""

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            connected = time.perf_counter() - started
            print(f"  connected            {connected:6.1f}s   HTTP {resp.status}")
            for raw in resp:
                line = raw.decode(errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                if first_byte is None:
                    first_byte = time.perf_counter() - started
                    print(f"  first token          {first_byte:6.1f}s")
                chunks += 1
                try:
                    delta = json.loads(payload)["choices"][0].get("delta", {})
                    text += delta.get("content") or ""
                except Exception:  # noqa: BLE001
                    pass
        total = time.perf_counter() - started
        print(f"  complete             {total:6.1f}s   {chunks} chunks")
        print(f"  output               {text.strip()!r}")
    except urllib.error.HTTPError as exc:
        print(f"  HTTP {exc.code}: {exc.read()[:200].decode(errors='replace')}")
    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - started
        got = "some bytes" if first_byte else "NO bytes"
        print(f"  failed after {elapsed:.1f}s ({got}) — {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    print(f"model {env['NVIDIA_MODEL']}  timeout {TIMEOUT}s")
    stream_probe("thinking disabled", {"thinking": {"type": "disabled"}})
    stream_probe("thinking default", {})
