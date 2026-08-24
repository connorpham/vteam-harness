#!/usr/bin/env python3
"""checkpoint.py — save/load ticket checkpoint: which lanes completed, where to resume.

Why: when /dev crashes mid-work, the ticket state lives in the branch + ledger.
This checkpoint stores enough to skip re-doing earlier lanes and resume at the
next ready one. Format: JSON {completed_lanes, next_lane, code_sha, resumed_count}.

Checkpoint file location: {paths.evidence}/<TICKET>/.checkpoint (one JSON per ticket).
Lifecycle:
  1. lane finishes → gate calls checkpoint_save() with lane="qa"
  2. phiên crash → dev runs: vteam resume TICKET
  3. resume reads .checkpoint, prints "DEMO-1: ready for BA review (qa), skipping dor" (or similar)
  4. PM re-dispatches from that lane
Determinism: resume is idempotent (file content doesn't change on re-read).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def lane_order() -> list[str]:
    """The canonical lane sequence."""
    return ["plan", "docs", "dor", "dev", "review", "qa"]


def load_checkpoint(evidence_dir: Path, ticket: str) -> dict | None:
    """Load the checkpoint for a ticket, or None if missing."""
    f = evidence_dir / ticket / ".checkpoint"
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_checkpoint(evidence_dir: Path, ticket: str, lane: str, code_sha: str | None = None) -> str:
    """Save checkpoint: this ticket completed `lane`, ready for the next.
    Return the checkpoint file path for verification.
    Deterministic: same inputs → same output (no timestamp)."""
    order = lane_order()
    if lane not in order:
        raise ValueError(f"lane {lane!r} not in {order}")
    idx = order.index(lane)
    completed = order[: idx + 1]  # up to and including `lane`
    next_lane = order[idx + 1] if idx + 1 < len(order) else "done"

    if code_sha is None:
        try:
            code_sha = subprocess.run(["git", "rev-parse", "HEAD"],
                                      capture_output=True, text=True, timeout=5).stdout.strip()
            if not code_sha or len(code_sha) < 7:
                code_sha = None
        except Exception:
            code_sha = None

    checkpoint = {
        "ticket": ticket,
        "completed_lanes": completed,
        "next_lane": next_lane,
        "code_sha": code_sha,
    }
    checkpoint_file = evidence_dir / ticket / ".checkpoint"
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_file.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(checkpoint_file)


def checkpoint_message(checkpoint: dict) -> str:
    """Human-readable status from checkpoint dict."""
    ticket = checkpoint.get("ticket", "UNKNOWN")
    completed = " → ".join(checkpoint.get("completed_lanes", []))
    next_lane = checkpoint.get("next_lane", "done")
    sha_short = checkpoint.get("code_sha", "")[:7] if checkpoint.get("code_sha") else "—"
    return (f"{ticket}: completed [{completed}], ready for {next_lane} (code {sha_short}). "
            f"Run `vteam resume {ticket}` to continue from the next lane.")


def _selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        evd = Path(td)
        # save checkpoint: DEMO-1 finished "dev"
        cp_file = save_checkpoint(evd, "DEMO-1", "dev", "abc1234")
        assert (evd / "DEMO-1" / ".checkpoint").exists(), cp_file
        loaded = load_checkpoint(evd, "DEMO-1")
        assert loaded["completed_lanes"] == ["plan", "docs", "dor", "dev"], loaded
        assert loaded["next_lane"] == "review", loaded
        assert loaded["code_sha"] == "abc1234", loaded
        # idempotency: save again, content is same
        cp_file2 = save_checkpoint(evd, "DEMO-1", "dev", "abc1234")
        assert open(cp_file).read() == open(cp_file2).read(), "not idempotent"
        # message
        msg = checkpoint_message(loaded)
        assert "DEMO-1" in msg and "review" in msg, msg
        print("checkpoint selftest: OK (save + load + idempotency + message)")


if __name__ == "__main__":
    import argparse
    import sys
    from ctx import Ctx  # noqa: E402

    ap = argparse.ArgumentParser()
    ap.add_argument("--save", nargs=2, metavar=("TICKET", "LANE"), help="save checkpoint after lane")
    ap.add_argument("--query", metavar="TICKET", help="query checkpoint for a ticket")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
    elif args.save:
        ticket, lane = args.save
        c = Ctx()
        evd = c.path("evidence")
        cp_file = save_checkpoint(evd, ticket, lane)
        print(f"{ticket}: checkpoint saved to {cp_file}")
    elif args.query:
        c = Ctx()
        evd = c.path("evidence")
        cp = load_checkpoint(evd, args.query)
        if cp is None:
            print(f"No checkpoint for {args.query}", file=sys.stderr)
            sys.exit(1)
        print(checkpoint_message(cp))
    else:
        ap.print_help()
        sys.exit(1)
