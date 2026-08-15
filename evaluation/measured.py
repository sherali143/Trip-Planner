"""
The single place anything reads a measured result from.

Why this exists
---------------
Every number in the report, in every figure, and in the project document has to
come from a file written by a measurement run. Nothing may be typed by hand,
because hand-typed figures rot silently: an earlier version of the project
document claimed "5 LLM calls", "~230 seconds" and "85% faster", and all three
were wrong once the calls were actually instrumented.

Having exactly one loader matters as much as having none hardcoded. When three
scripts each parse the results JSON their own way, they drift, and then a figure
disagrees with the table beside it. So: figures, the report chapters, the
project document and the appendices all come through here.

Accessors raise `MissingMeasurement` rather than returning a plausible default.
A missing measurement must stop the build, not quietly become a zero that reads
like a real result.

    from evaluation.measured import results, arm, protocol, budget_gate
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
    return {
        "scenarios_measured": len(measured),
        "scenarios_designed": len(SCENARIOS),
        "scenario_ids": measured,
        "coverage_pct": round(len(measured) / len(SCENARIOS) * 100, 1),
        "repeats_per_arm": 1,
        "status": results().get("status", "unknown"),
        "api_mode": provenance().get("api_mode", "unknown"),
        "model": provenance().get("model", "unknown"),
        "is_complete": results().get("status") == "complete" and len(measured) == len(SCENARIOS),
    }


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
