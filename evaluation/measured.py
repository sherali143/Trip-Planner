"""
The one place measured results are read from.

Every number in the dissertation, the overview and the slides comes through
here. Nothing else reads the results files directly, so the three documents
cannot disagree with each other. A missing measurement raises rather than
returning a default.
"""

from __future__ import annotations

import functools
import json
import os
import subprocess
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "evaluation", "results")

COMPARISON_PATH = os.path.join(RESULTS_DIR, "comparison_results.json")
PROTOCOL_PATH = os.path.join(RESULTS_DIR, "protocol_conformance.json")
BUDGET_GATE_PATH = os.path.join(RESULTS_DIR, "budget_gate.json")
API_CALLS_PATH = os.path.join(RESULTS_DIR, "api_calls_per_arm.json")
API_QUOTA_PATH = os.path.join(RESULTS_DIR, "api_quota.json")

ARM_LABELS = {
    "A": "Single LLM",
    "B": "6 agents, naive",
    "C": "6 agents, tuned",
    "D": "3 agents, direct",
}
ARM_ORDER = ["A", "B", "C", "D"]


class MissingMeasurement(RuntimeError):
    """A result the build needs has not been measured. Never substitute a default."""


def _load(path: str, what: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise MissingMeasurement(
            f"{what} has not been measured: {os.path.relpath(path, ROOT)} does not "
            f"exist. Run the experiment that produces it before building."
        )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@functools.lru_cache(maxsize=None)
def results() -> Dict[str, Any]:
    """The four-arm architecture comparison."""
    return _load(COMPARISON_PATH, "The architecture comparison")


@functools.lru_cache(maxsize=None)
def api_calls_per_arm() -> Dict[str, Any]:
    """
    How many calls to each API each architecture makes for one trip.

    Measured by counting real calls through the recording layer with travel
    responses replayed, so the count cost no quota. B and C vary between runs
    because their agents decide when to call a tool; A and D do not.
    """
    return _load(API_CALLS_PATH, "Per-architecture API call counts")


@functools.lru_cache(maxsize=None)
def api_quota() -> Dict[str, Any]:
    """
    The last reading of how much monthly travel-API quota is left.

    Written by evaluation/check_quota.py, which has to make one live call per API
    because the balance is only reported in a response header. Carries the time it
    was taken, since it is a snapshot and falls with every live run.
    """
    return _load(API_QUOTA_PATH, "The API quota reading")


@functools.lru_cache(maxsize=None)
def protocol() -> Dict[str, Any]:
    """The A2A and MCP conformance audit."""
    return _load(PROTOCOL_PATH, "Protocol conformance")


@functools.lru_cache(maxsize=None)
def budget_gate() -> Dict[str, Any]:
    """The budget feasibility gate evaluation."""
    return _load(BUDGET_GATE_PATH, "The budget gate evaluation")


# ------------------------------------------------------------------ arms
def arm(code: str) -> Dict[str, Any]:
    arms = results().get("arms") or {}
    if code not in arms:
        raise MissingMeasurement(
            f"arm {code} is absent from the results file; measured arms: "
            f"{sorted(arms)}")
    return arms[code]


def arm_metric(code: str, key: str) -> float:
    row = arm(code)
    if key not in row:
        raise MissingMeasurement(f"arm {code} has no measured '{key}'")
    return row[key]


def detail(code: str, index: int = 0) -> Dict[str, Any]:
    """One scenario's full record for an arm, including the groundedness score."""
    rows = (results().get("details_by_arm") or {}).get(code) or []
    if len(rows) <= index:
        raise MissingMeasurement(
            f"arm {code} has {len(rows)} scenario record(s); index {index} requested")
    return rows[index]


def groundedness(code: str, index: int = 0) -> Dict[str, Any]:
    score = detail(code, index).get("groundedness") or {}
    if not score.get("scored"):
        raise MissingMeasurement(f"arm {code} scenario {index} has no groundedness score")
    return score


def llm_breakdown(code: str, index: int = 0) -> Dict[str, Any]:
    block = detail(code, index).get("llm") or {}
    if "prompt_tokens" not in block:
        raise MissingMeasurement(f"arm {code} has no recorded token breakdown")
    return block


def token_split(code: str) -> Dict[str, float]:
    """
    Mean prompt and completion tokens for an arm, across every recorded run.

    llm_breakdown() returns one run. Charting that while the results table quotes
    the mean made the token chart disagree with the table beside it by ten
    thousand tokens, which is exactly the drift the single-accessor rule exists to
    prevent.
    """
    rows = [r for r in ((results().get("details_by_arm") or {}).get(code) or [])
            if r.get("success") and (r.get("llm") or {}).get("prompt_tokens") is not None]
    if not rows:
        raise MissingMeasurement(f"arm {code} has no recorded token breakdown")
    n = len(rows)
    return {
        "n": n,
        "prompt_tokens": sum(r["llm"]["prompt_tokens"] for r in rows) / n,
        "completion_tokens": sum(r["llm"]["completion_tokens"] for r in rows) / n,
        "llm_time_s": sum(r["llm"].get("llm_time_s", 0) for r in rows) / n,
    }


def phase_timings(code: str = "D", index: int = 0) -> Dict[str, float]:
    """Measured per-phase wall-clock for an arm that records phases."""
    row = detail(code, index)
    phases = {k: v for k, v in row.items() if k.startswith("phase")}
    if not phases:
        raise MissingMeasurement(f"arm {code} records no phase timings")
    return phases


def improvement(pair: str) -> Dict[str, Any]:
    """A recorded pairwise gain, e.g. 'D_vs_C'."""
    gains = results().get("improvements") or {}
    if pair not in gains:
        raise MissingMeasurement(f"no recorded improvement for {pair}; have {sorted(gains)}")
    return gains[pair]


# ------------------------------------------------------------- provenance
def provenance() -> Dict[str, Any]:
    return results().get("provenance") or {}


def scenario_ids() -> List[str]:
    ids = results().get("scenario_ids") or []
    if not ids:
        raise MissingMeasurement("the results file names no scenarios")
    return ids


def coverage() -> Dict[str, Any]:
    """
    How much of the designed evaluation the result set actually covers.

    Quoted wherever a number from it appears, so a partial run can never be
    read as a complete one.
    """
    from evaluation.scenarios import SCENARIOS
    measured = scenario_ids()
    # Repeats are counted from the recorded rows, not assumed. This was hardcoded
    # to 1 while the harness could only do one run per scenario; leaving it that
    # way after repeats were added would have understated the evidence.
    rows = (results().get("details_by_arm") or {}).get("D") or []
    repeats = max(1, len(rows) // max(1, len(measured)))
    return {
        "scenarios_measured": len(measured),
        "scenarios_designed": len(SCENARIOS),
        "scenario_ids": measured,
        "coverage_pct": round(len(measured) / len(SCENARIOS) * 100, 1),
        "repeats_per_arm": repeats,
        "status": results().get("status", "unknown"),
        "api_mode": provenance().get("api_mode", "unknown"),
        "model": provenance().get("model", "unknown"),
        "is_complete": results().get("status") == "complete" and len(measured) == len(SCENARIOS),
        "has_repeats": repeats > 1,
    }


# ------------------------------------------------------- dispersion accessors
def spread(code: str, metric: str) -> Dict[str, Any]:
    """
    Mean, standard deviation and 95% interval for one metric on one arm.

    Raises rather than returning a bare mean when repeats were never recorded,
    because quoting an interval that does not exist is worse than saying so.
    """
    block = (arm(code).get("spread") or {}).get(metric)
    if not block:
        raise MissingMeasurement(
            f"arm {code} has no recorded spread for {metric!r}; the run predates "
            f"repeat support, or was made with --repeats 1")
    if block.get("n", 0) < 2:
        raise MissingMeasurement(
            f"arm {code} has {block.get('n')} observation(s) of {metric!r}, so it "
            f"has no measurable spread")
    return block


def intervals_overlap(code_a: str, code_b: str, metric: str) -> bool:
    """
    Do two arms' 95% intervals overlap on this metric?

    Used instead of a significance test because with five observations per arm a
    formal test adds precision the sample does not have. Non-overlapping
    intervals are a conservative, readable statement that a difference is larger
    than the run-to-run noise; overlapping intervals say the opposite, and both
    are reported.
    """
    a, b = spread(code_a, metric), spread(code_b, metric)
    return not (a["ci95_high"] < b["ci95_low"] or b["ci95_high"] < a["ci95_low"])


def model_name() -> str:
    """
    The model that produced the recorded numbers, as a reader would write it.

    Read from provenance rather than named in prose. Three documents had
    "Gemini 2.5 Flash" typed into them, which was true of the first round of
    measurements and false of the results that shipped: 2.5 Flash was withdrawn
    from new API keys mid-project and everything was re-measured on its
    replacement. A model name typed by hand goes stale exactly when the model
    changes, which is the one moment it matters.

    "gemini/gemini-3.6-flash" becomes "Gemini 3.6 Flash".
    """
    raw = provenance().get("model", "")
    if not raw:
        raise MissingMeasurement(
            "the results file records no model in its provenance block, so no "
            "document can state which model produced these numbers")
    name = raw.split("/")[-1]                      # drop the LiteLLM provider prefix
    parts = name.split("-")
    return " ".join(p.capitalize() if not p[0].isdigit() else p for p in parts)


# ------------------------------------------------------- protocol accessors
def protocol_check(check_id: str) -> Dict[str, Any]:
    for group in ("a2a_checks", "mcp_checks"):
        for check in protocol().get(group, []):
            if check["id"] == check_id:
                return check
    raise MissingMeasurement(f"no protocol check {check_id!r} in the audit results")


def protocol_summary() -> Dict[str, Any]:
    summary = protocol().get("summary") or {}
    if "total_checks" not in summary:
        raise MissingMeasurement("the protocol audit has no summary block")
    return summary


def mcp_schema_stats() -> Dict[str, Any]:
    observed = protocol_check("M2")["observed"]
    return {
        "clean": observed["clean"],
        "inspectable": observed["inspectable"],
        "undeclared_parameter_count": observed["undeclared_parameter_count"],
        "tools_total": len(observed["tools"]),
        "defective_tools": [t["tool"] for t in observed["tools"]
                            if t["undeclared_params"] or t["required_mismatch"]],
    }


# --------------------------------------------------- budget gate accessors
def gate_agreement() -> Dict[str, Any]:
    block = budget_gate().get("agreement") or {}
    if "cohens_kappa" not in block:
        raise MissingMeasurement("the budget gate results carry no agreement statistic")
    return block


def gate_misses() -> List[Dict[str, Any]]:
    """Scenarios where the gate's decision disagreed with the designed intent."""
    return [r for r in budget_gate().get("decision_table", []) if not r["agrees"]]


def gate_external_validity() -> Dict[str, Any]:
    block = budget_gate().get("external_validity") or {}
    if not block.get("comparable"):
        raise MissingMeasurement(
            f"the flight anchor was not externally validated: "
            f"{block.get('reason', 'unknown reason')}")
    return block


# ------------------------------------------------------------ repo evidence
@functools.lru_cache(maxsize=None)
def test_count() -> Dict[str, Any]:
    """
    The real test count, collected from pytest rather than remembered.

    Collection only — no test is executed here, so this is safe to call from a
    figure script. The build runs the suite properly and records the pass count.
    """
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", "-q", "--collect-only"],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MissingMeasurement(f"could not collect tests: {exc}") from exc
    import re
    match = re.search(r"(\d+) tests? collected", proc.stdout)
    if not match:
        match = re.search(r"(\d+)/(\d+) tests collected", proc.stdout)
    if not match:
        raise MissingMeasurement(
            "pytest did not report a collected test count; output tail: "
            + proc.stdout[-400:])
    return {"collected": int(match.group(1))}


@functools.lru_cache(maxsize=None)
def api_cache_stats() -> Dict[str, Any]:
    """What is actually recorded in .api_cache, by host."""
    cache_dir = os.path.join(ROOT, ".api_cache")
    if not os.path.isdir(cache_dir):
        raise MissingMeasurement(".api_cache does not exist")
    by_host: Dict[str, int] = {}
    total_bytes = 0
    for name in os.listdir(cache_dir):
        if not name.endswith(".json"):
            continue
        host = name.split("__")[0]
        by_host[host] = by_host.get(host, 0) + 1
        total_bytes += os.path.getsize(os.path.join(cache_dir, name))
    return {
        "entries": sum(by_host.values()),
        "by_host": by_host,
        "total_kb": round(total_bytes / 1024, 1),
    }


@functools.lru_cache(maxsize=None)
def flight_api_evidence() -> Dict[str, Any]:
    """
    The recorded flight responses, classified by which bug they demonstrate.

    The cache is a forensic record as well as a replay source. Two recordings
    used the snake_case date parameters the API silently ignores; one used the
    correct camelCase form; one is the poll that collects the completed search.
    Reading the classification from the files means Chapter 5 quotes the
    evidence rather than describing it from memory.
    """
    cache_dir = os.path.join(ROOT, ".api_cache")
    if not os.path.isdir(cache_dir):
        raise MissingMeasurement(".api_cache does not exist")

    groups: Dict[str, List[Dict[str, Any]]] = {
        "snake_case_params": [], "camel_case_params": [], "poll": []}
    for name in sorted(os.listdir(cache_dir)):
        if not name.startswith("fly-scraper") or not name.endswith(".json"):
            continue
        with open(os.path.join(cache_dir, name), encoding="utf-8") as fh:
            entry = json.load(fh)
        params = entry.get("params") or {}
        body = entry.get("body") or ""
        try:
            payload = json.loads(body).get("data") or {}
            itineraries = len(payload.get("itineraries") or [])
            status = (payload.get("context") or {}).get("status")
        except (json.JSONDecodeError, AttributeError):
            itineraries, status = 0, None
        row = {"bytes": len(body), "itineraries": itineraries, "status": status,
               "route": f"{params.get('originSkyId', '?')}-"
                        f"{params.get('destinationSkyId', '?')}"}
        if "sessionId" in params:
            groups["poll"].append(row)
        elif "outbound_date" in params:
            groups["snake_case_params"].append(row)
        elif "departureDate" in params:
            groups["camel_case_params"].append(row)

    def best(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        return max(rows, key=lambda r: r["itineraries"]) if rows else {}

    broken = groups["snake_case_params"]
    fixed = best(groups["camel_case_params"])
    poll = best(groups["poll"])
    if not broken or not fixed or not poll:
        raise MissingMeasurement(
            "the cache does not contain all three flight recording kinds "
            f"(snake_case={len(broken)}, camelCase="
            f"{len(groups['camel_case_params'])}, poll={len(groups['poll'])})")
    return {
        "broken_recordings": len(broken),
        "broken_max_itineraries": max(r["itineraries"] for r in broken),
        "broken_bytes": [r["bytes"] for r in broken],
        "fixed_bytes": fixed["bytes"],
        "fixed_itineraries": fixed["itineraries"],
        "fixed_status": fixed["status"],
        "poll_bytes": poll["bytes"],
        "poll_itineraries": poll["itineraries"],
        "poll_status": poll["status"],
    }


@functools.lru_cache(maxsize=None)
def code_stats() -> Dict[str, Any]:
    """Line and file counts per top-level area, for the appendix code map."""
    areas = {
        "trip_planner": "the application itself",
        "evaluation": "the four architectures and the experiments",
        "demos": "demonstration scripts",
        "testing": "test suite",
        "report": "report and figure generators",
    }
    out: Dict[str, Any] = {"areas": {}, "total_lines": 0, "total_files": 0}
    for area, description in areas.items():
        base = os.path.join(ROOT, area)
        if not os.path.isdir(base):
            continue
        files = 0
        lines = 0
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d not in {"__pycache__", ".pytest_cache"}]
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                files += 1
                with open(os.path.join(dirpath, filename), encoding="utf-8",
                          errors="replace") as fh:
                    lines += sum(1 for _ in fh)
        out["areas"][area] = {"description": description, "files": files, "lines": lines}
        out["total_files"] += files
        out["total_lines"] += lines
    return out


@functools.lru_cache(maxsize=None)
def git_stats() -> Dict[str, Any]:
    """Commit count and span, as evidence of how the work proceeded."""
    def _git(*args: str) -> Optional[str]:
        try:
            proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                                  text=True, timeout=30)
            return proc.stdout.strip() if proc.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    count = _git("rev-list", "--count", "HEAD")
    first = _git("log", "--reverse", "--format=%ad", "--date=short")
    last = _git("log", "-1", "--format=%ad", "--date=short")
    return {
        "commits": int(count) if count and count.isdigit() else None,
        "first_commit": first.split("\n")[0] if first else None,
        "last_commit": last or None,
    }
