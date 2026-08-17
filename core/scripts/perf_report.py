#!/usr/bin/env python3
"""perf_report.py — team performance from the ledger: who did what, on which
model, was the routing sane, and where the tokens went.

Reads {paths.pm}/log.md (the same table log_check guards — this tool is the
READER that makes the accounting convention pay off) and prints a markdown
report block for the desk report / the 14-day framework review.

Sections:
  1. Summary        — items, done/blocked/failed, total tokens, period
  2. By lane        — who did what: items, outcomes, token totals/medians
  3. Model routing sanity — tier usage + FLAGS where the ledger contradicts
     model-routing.md: `frontier` without owner-approved escalation ·
     `utility` on a DEV row (utility is a subagent brain) · a done DEV row
     with no tier recorded (rule: record the model so routing is tuned by data)
  4. Outliers       — rows > 2× the median token cost (review-round eaters)
  5. Monthly trend  — tokens and items per month
  6. Rough cost band — tokens × the tier's price range from
     model-routing.data.yaml (labelled an ESTIMATE: tok≈ mixes input+output)

Usage:
  perf_report.py [--month YYYY-MM] [--since YYYY-MM-DD]
  perf_report.py --selftest
Exit is always 0 unless the ledger is unreadable — this is a report, not a
gate; the flags it prints are the desk report's job to surface.
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

TIERS = ("frontier", "workhorse", "standard", "utility")
ROW_TIER = re.compile(r"\((frontier|workhorse|standard|utility)\)")
# Ledgers written before vteam name models directly — map them so history reads.
LEGACY_TIER = {"fable": "frontier", "opus": "workhorse", "sonnet": "standard", "haiku": "utility"}
LEGACY_RE = re.compile(r"\b(fable|opus|sonnet|haiku)\b", re.I)
ROW_TOK = re.compile(r"tok\s*≈\s*(\d+(?:\.\d+)?)\s*k")
DATE_PAT = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def parse_ledger(text: str) -> list[dict]:
    rows, in_table = [], False
    for line in text.splitlines():
        if re.match(r"^\|\s*Date\s*\|", line, re.I):
            in_table = True
            continue
        if not in_table or not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        day, lane, item, result, link = cells
        m = DATE_PAT.match(day)
        if not m:
            continue
        outcome = ("done" if result.startswith("done")
                   else "blocked" if result.startswith("blocked")
                   else "failed" if result.startswith("failed") else "other")
        tier, tier_src = (ROW_TIER.search(result) or [None, None])[1], "explicit"
        if tier is None:
            lm = LEGACY_RE.search(result) or LEGACY_RE.search(item)
            tier, tier_src = (LEGACY_TIER[lm.group(1).lower()], "legacy") if lm else (None, None)
        tokm = ROW_TOK.search(result)
        rows.append({
            "date": date(int(m.group(1)), int(m.group(2)), int(m.group(3))),
            "lane": lane.upper(), "item": item, "outcome": outcome,
            "tier": tier, "tier_src": tier_src,
            "tok": float(tokm.group(1)) if tokm else None,
            "link": link,
        })
    return rows


def flags_for(rows: list[dict], adopted: date | None = None) -> list[str]:
    """Accounting flags apply only from `adopted` onward — pre-adoption rows are
    grandfathered history nobody can retro-fix (same law as log_check)."""
    out = []
    grandfathered = 0
    for r in rows:
        if adopted and r["date"] < adopted:
            grandfathered += 1
            continue
        where = f"{r['item']} ({r['date'].isoformat()}, {r['lane']})"
        if r["tier"] == "frontier":
            out.append(f"🚩 {where}: ran on `frontier` — allowed only after the same work "
                       f"failed twice AND the owner approved the spend (check the decision queue)")
        if r["tier"] == "utility" and r["lane"] == "DEV":
            out.append(f"🚩 {where}: DEV work on `utility` — utility is a lookup-subagent "
                       f"brain, never a working brain (model-routing §3)")
        if r["lane"] == "DEV" and r["outcome"] == "done" and r["tier"] is None:
            out.append(f"🚩 {where}: done DEV row with NO tier recorded — routing can only "
                       f"be tuned by data if the ledger names the model (model-routing §4.3)")
        if r["outcome"] == "done" and r["tok"] is None:
            out.append(f"🚩 {where}: done with no `tok ≈` — spend invisible to every report")
    if grandfathered:
        out.append(f"ℹ️  {grandfathered} rows predate project.adopted — counted in the "
                   f"stats, exempt from accounting flags (grandfathered)")
    toks = [r["tok"] for r in rows if r["tok"]]
    if len(toks) >= 4:
        med = statistics.median(toks)
        for r in rows:
            if r["tok"] and r["tok"] > 2 * med:
                out.append(f"⚠️  {r['item']}: {r['tok']:.0f}k tokens — >2× the median "
                           f"({med:.0f}k); usually extra review rounds — worth a look")
    return out


def fmt_tok(v: float | None) -> str:
    return f"{v:.0f}k" if v is not None else "—"


def build_report(rows: list[dict], prices: dict | None, period: str,
                 adopted: date | None = None) -> str:
    L: list[str] = [f"## Team performance — {period}", ""]
    if not rows:
        return "\n".join(L + ["(no ledger rows in this period)"])
    done = [r for r in rows if r["outcome"] == "done"]
    toks = [r["tok"] for r in rows if r["tok"]]
    L.append(f"**{len(rows)} items** · {len(done)} done · "
             f"{sum(1 for r in rows if r['outcome'] == 'blocked')} blocked · "
             f"{sum(1 for r in rows if r['outcome'] == 'failed')} failed · "
             f"**Σ {sum(toks):.0f}k tokens** on {len(toks)} accounted rows")
    L += ["", "### Who did what (by lane)", "",
          "| Lane | Items | Done | Blocked/Failed | Σ tok | Median tok |", "|---|---|---|---|---|---|"]
    for lane in sorted({r["lane"] for r in rows}):
        lr = [r for r in rows if r["lane"] == lane]
        lt = [r["tok"] for r in lr if r["tok"]]
        L.append(f"| {lane} | {len(lr)} | {sum(1 for r in lr if r['outcome'] == 'done')} "
                 f"| {sum(1 for r in lr if r['outcome'] in ('blocked', 'failed'))} "
                 f"| {fmt_tok(sum(lt) if lt else None)} "
                 f"| {fmt_tok(statistics.median(lt) if lt else None)} |")
    L += ["", "### Model usage", "", "| Tier | Rows | Σ tok |", "|---|---|---|"]
    for tier in TIERS + (None,):
        tr = [r for r in rows if r["tier"] == tier]
        if not tr:
            continue
        tt = [r["tok"] for r in tr if r["tok"]]
        legacy = sum(1 for r in tr if r.get("tier_src") == "legacy")
        note = f" ({legacy} via legacy model names)" if legacy else ""
        L.append(f"| {tier or '(unrecorded)'} | {len(tr)}{note} | {fmt_tok(sum(tt) if tt else None)} |")
    fl = flags_for(rows, adopted)
    L += ["", "### Routing & accounting flags", ""]
    L += [f"- {f}" for f in fl] if fl else ["- none — routing and accounting look sane ✅"]
    L += ["", "### Monthly trend", "", "| Month | Items | Σ tok |", "|---|---|---|"]
    for month in sorted({r["date"].strftime("%Y-%m") for r in rows}):
        mr = [r for r in rows if r["date"].strftime("%Y-%m") == month]
        mt = [r["tok"] for r in mr if r["tok"]]
        L.append(f"| {month} | {len(mr)} | {fmt_tok(sum(mt) if mt else None)} |")
    if prices:
        L += ["", "### Rough cost band (ESTIMATE — `tok ≈` mixes input+output)", "",
              "| Tier | Σ tok | $ low (all-input) | $ high (all-output) |", "|---|---|---|---|"]
        total_lo = total_hi = 0.0
        for tier in TIERS:
            tt = [r["tok"] for r in rows if r["tier"] == tier and r["tok"]]
            p = prices.get(tier)
            if not tt or not p:
                continue
            ktok = sum(tt)
            lo = ktok / 1000 * float(p["input_per_mtok"])
            hi = ktok / 1000 * float(p["output_per_mtok"])
            total_lo += lo
            total_hi += hi
            L.append(f"| {tier} | {ktok:.0f}k | ${lo:.2f} | ${hi:.2f} |")
        unrec = [r["tok"] for r in rows if r["tier"] is None and r["tok"]]
        if unrec:
            L.append(f"| (unrecorded tier) | {sum(unrec):.0f}k | ? | ? |")
        L.append(f"| **total (recorded tiers)** | | **${total_lo:.2f}** | **${total_hi:.2f}** |")
    return "\n".join(L)


def load_prices(root: Path) -> dict | None:
    from ctx import parse_config
    for cand in (root / "docs" / "team" / "model-routing.data.yaml",
                 Path(__file__).resolve().parent.parent / "doctrine" / "model-routing.data.yaml"):
        if cand.is_file():
            return parse_config(cand.read_text(encoding="utf-8")).get("tiers", {})
    return None


def main() -> int:
    from ctx import Ctx
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="YYYY-MM")
    ap.add_argument("--since", help="YYYY-MM-DD")
    args = ap.parse_args()
    c = Ctx()
    ledger = c.path("pm") / "log.md"
    if not ledger.is_file():
        print(f"perf_report: {ledger} not found")
        return 1
    rows = parse_ledger(ledger.read_text(encoding="utf-8"))
    period = "all time"
    if args.month:
        rows = [r for r in rows if r["date"].strftime("%Y-%m") == args.month]
        period = args.month
    if args.since:
        rows = [r for r in rows if r["date"] >= date.fromisoformat(args.since)]
        period = f"since {args.since}"
    adopted = None
    ad = c.cfg("project.adopted", None)
    if ad:
        adopted = date.fromisoformat(str(ad))
    print(build_report(rows, load_prices(c.root), period, adopted))
    return 0


def _selftest():
    head = "| Date | Lane | Item | Result | Link |\n|---|---|---|---|---|\n"
    fixture = head + "\n".join([
        "| 2026-01-05 | DEV | P-1 | done (workhorse) · tok ≈ 90k | PR #1 |",
        "| 2026-01-06 | QA | P-1 | done · tok ≈ 30k | P-1 |",
        "| 2026-01-07 | DEV | P-2 | done (utility) · tok ≈ 40k | PR #2 |",
        "| 2026-01-08 | DEV | P-3 | done (frontier) · tok ≈ 300k | PR #3 |",
        "| 2026-01-09 | DEV | P-4 | done · tok ≈ 50k | PR #4 |",
        "| 2026-01-10 | BA | auth | blocked: Q2 open | Q2 |",
        "| 2026-02-02 | DEV | P-5 | done (standard) | PR #5 |",
    ])
    rows = parse_ledger(fixture)
    assert len(rows) == 7, len(rows)
    assert rows[0]["tier"] == "workhorse" and rows[0]["tok"] == 90.0
    legacy = parse_ledger(head + "| 2026-01-05 | DEV | P-9 (opus — main loop) | done · tok ≈ 80k | PR #9 |\n")
    assert legacy[0]["tier"] == "workhorse" and legacy[0]["tier_src"] == "legacy"
    assert not flags_for(legacy), "legacy-named tier row must not be flagged tierless"
    gf = flags_for(rows, adopted=date(2026, 3, 1))
    assert any("grandfathered" in f for f in gf), gf
    assert not any(f.startswith("🚩") for f in gf), f"pre-adoption rows must carry no 🚩: {gf}"
    fl = flags_for(rows)
    assert any("frontier" in f for f in fl), "frontier row must be flagged"
    assert any("utility" in f for f in fl), "DEV-on-utility must be flagged"
    assert any("NO tier recorded" in f for f in fl), "tierless done DEV row must be flagged"
    assert any("no `tok ≈`" in f for f in fl), "done row without tok must be flagged"
    assert any(">2× the median" in f for f in fl), "300k outlier must be flagged"
    prices = {"workhorse": {"input_per_mtok": 5, "output_per_mtok": 25}}
    rpt = build_report(rows, prices, "test")
    assert "| DEV | 5 |" in rpt and "| workhorse | 1 |" in rpt, rpt
    assert "2026-01" in rpt and "2026-02" in rpt
    assert "$0.45" in rpt and "$2.25" in rpt, "cost band 90k×$5/$25 per Mtok"
    clean = parse_ledger(head + "| 2026-01-05 | DEV | P-1 | done (workhorse) · tok ≈ 90k | PR #1 |\n")
    assert not flags_for(clean), "clean row must produce no flags"
    print("perf_report selftest: OK (parse + 5 flag classes + cost band + clean path)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
