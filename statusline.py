#!/usr/bin/env python3
"""Claude Code statusline — context usage indicator with compaction guidance.

Displays current context token usage as a progress bar with stage-based
guidance on when to run /compact. Unlike generic token-percentage statuslines,
this shows actionable advice tied to compaction timing.
"""
import json
import sys
import os

# Model context window limits (tokens).
# Models with "[1m]" suffix use the 1M long-context beta.
MODEL_LIMITS = {
    "claude-opus-4-6[1m]": 1_000_000,
    "claude-sonnet-4-6[1m]": 1_000_000,
    "claude-opus-4-6": 200_000,
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5": 200_000,
}
DEFAULT_LIMIT = 200_000


def get_last_usage(transcript_path):
    """Return the latest assistant-turn context size from the transcript JSONL.

    Computes input_tokens + cache_read_input_tokens + cache_creation_input_tokens
    from the most recent assistant message that has a usage field.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return 0
    last_tokens = 0
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = obj.get("message", {})
                usage = msg.get("usage") if isinstance(msg, dict) else None
                if usage:
                    tokens = (
                        usage.get("input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                        + usage.get("cache_creation_input_tokens", 0)
                    )
                    if tokens:
                        last_tokens = tokens
    except Exception:
        pass
    return last_tokens


def bar(pct, width=10):
    filled = int(pct * width / 100)
    return "█" * filled + "░" * (width - filled)


def stage(pct):
    """Return (ansi_color, label) for the given usage percentage."""
    if pct < 50:
        return "\033[32m", "OK"
    if pct < 70:
        return "\033[36m", "compact at next break"
    if pct < 80:
        return "\033[33m", "⚠ consider /compact"
    if pct < 85:
        return "\033[33m", "⚠ compact soon"
    return "\033[31m", "🔴 /compact now"


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        data = {}

    model_id = (data.get("model", {}) or {}).get("id", "")
    transcript = data.get("transcript_path", "")
    cwd = data.get("workspace", {}).get("current_dir") or data.get("cwd", "")

    limit = MODEL_LIMITS.get(model_id, DEFAULT_LIMIT)
    tokens = get_last_usage(transcript)
    pct = (tokens / limit * 100) if limit else 0

    color, tag = stage(pct)
    RESET = "\033[0m"
    DIM = "\033[90m"

    cwd_short = os.path.basename(cwd) if cwd else ""
    model_short = model_id.replace("claude-", "").replace("[1m]", "·1M")

    line = (
        f"{color}[{bar(pct)}] {tokens:>7,}/{limit:,} ({pct:5.1f}%) {tag}{RESET}"
        f"  {DIM}{model_short} · {cwd_short}{RESET}"
    )
    print(line)


if __name__ == "__main__":
    main()
