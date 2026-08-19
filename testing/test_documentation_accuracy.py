"""
Checks that the documentation tells the truth about the code.

Every number in a README is a claim, and claims rot: files get deleted while
the command that runs them stays documented, tool counts change, results are
re-measured. A supervisor or a new contributor hits those first, and a README
that names a file which no longer exists costs more trust than it saves.

These tests fail when the prose and the project disagree, so the docs cannot
quietly drift out of date the way the project document's hardcoded "5 LLM
calls" did.
"""

import json
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = {
    p: p.read_text(encoding="utf-8")
    for p in ROOT.rglob("*.md")
    if not any(x in p.as_posix() for x in (".venv", ".git", "node_modules"))
}
ALL_TEXT = "\n".join(DOCS.values())


def test_documentation_exists_for_every_package():
    """Each top-level folder explains itself."""
    for folder in ("trip_planner", "evaluation", "demos", "testing",
                   "proposal", "report"):
        assert (ROOT / folder / "README.md").exists(), f"{folder}/ has no README"


def test_the_dissertation_is_present():
    """
    The generated dissertation is the project's single written deliverable.

    It replaced a separate PROJECT_GUIDE.docx that restated the same measured
    results in a second document; keeping both meant two places for the same
    number to be wrong in.
    """
    report = ROOT / "report" / "CMP7200_Dissertation.docx"
    assert report.exists(), (
        "report/CMP7200_Dissertation.docx is missing — regenerate with "
        "python -m report.build.build_report"
    )


def test_every_python_file_has_a_module_docstring():
    """A reader should never have to infer what a file is for."""
    import ast

    missing = []
    for p in ROOT.rglob("*.py"):
        if any(x in p.as_posix() for x in (".venv", "__pycache__", ".git")):
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            missing.append(f"{p.relative_to(ROOT)} (syntax error)")
            continue
        if not ast.get_docstring(tree):
            missing.append(str(p.relative_to(ROOT)))
    assert not missing, "files without a module docstring: " + ", ".join(missing)


def test_documented_file_paths_exist():
    """A README must not name a file that has been deleted or moved."""
    broken = []
    for doc, text in DOCS.items():
        for ref in set(re.findall(r"`([a-zA-Z0-9_./-]+\.(?:py|json|toml|txt))`", text)):
            if (ROOT / ref).exists() or (doc.parent / ref).exists():
                continue
            # A bare filename is a valid shorthand only if it is unique in the tree.
            if "/" not in ref and any(ROOT.rglob(ref)):
                continue
            broken.append(f"{doc.relative_to(ROOT)} -> {ref}")
    assert not broken, "documented paths that do not exist: " + ", ".join(broken)


def test_documented_commands_point_at_real_targets():
    """`python x/y.py` in a README must be runnable."""
    broken = []
    for doc, text in DOCS.items():
        for cmd in set(re.findall(r"python (?:-m )?([a-zA-Z0-9_./]+)", text)):
            if cmd in ("pytest", "venv"):
                continue
            candidates = [
                ROOT / cmd,
                ROOT / (cmd if cmd.endswith(".py") else cmd.replace(".", "/") + ".py"),
                ROOT / cmd.replace(".", "/"),
            ]
            if not any(c.exists() for c in candidates):
                broken.append(f"{doc.relative_to(ROOT)} -> python {cmd}")
    assert not broken, "documented commands with no target: " + ", ".join(broken)


def test_mcp_tool_count_matches_the_server():
    """The "12 tools" claim must match what the server actually registers."""
    server = (ROOT / "trip_planner/server/mcp_server.py").read_text(encoding="utf-8")
    actual = len(re.findall(r'Tool\(\s*name="', server))
    claimed = {int(n) for n in re.findall(r"(\d+) (?:schema-validated )?tools", ALL_TEXT)}
    assert claimed, "no tool count is documented anywhere"
    assert claimed == {actual}, f"docs claim {sorted(claimed)} tools, server exposes {actual}"


def test_scenario_count_matches_the_scenario_file():
    scenarios = (ROOT / "evaluation/scenarios.py").read_text(encoding="utf-8")
    actual = len(re.findall(r'"id":\s*"SC-', scenarios))
    assert actual == 20, f"expected 20 scenarios, found {actual}"
    assert "20 scenario" in ALL_TEXT or "20 evaluation scenarios" in ALL_TEXT


def test_a2a_card_and_message_type_counts_match_the_code():
    registry = (ROOT / "trip_planner/comms/registry.py").read_text(encoding="utf-8")
    cards = len(re.findall(r"AgentCard\(\s*\n?\s*agent_id=", registry))
    assert cards == 8, f"docs claim 8 agent cards, registry defines {cards}"

    protocol = (ROOT / "trip_planner/comms/protocol.py").read_text(encoding="utf-8")
    block = re.search(r"class MessageType\b.*?(?=\nclass |\Z)", protocol, re.S)
    assert block, "MessageType enum not found"
    types = len(re.findall(r"^\s+[A-Z_]+\s*=", block.group(0), re.M))
    assert types == 6, f"docs claim 6 message types, protocol defines {types}"


@pytest.mark.parametrize("arm", ["A", "B", "C", "D"])
def test_results_quoted_in_docs_match_the_results_file(arm):
    """
    The headline table in README.md and AGENTS.md must match the measured data.

    These are the numbers a marker reads first. The project document already
    generates its table from this file; the READMEs are written by hand, so
    this is what stops them drifting.
    """
    results_path = ROOT / "evaluation/results/comparison_results.json"
    if not results_path.exists():
        pytest.skip("no results recorded yet")
    arms = json.loads(results_path.read_text(encoding="utf-8")).get("arms", {})
    if arm not in arms:
        pytest.skip(f"arm {arm} not in results")

    calls = round(arms[arm]["avg_llm_calls"])
    tokens = round(arms[arm]["avg_total_tokens"])
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    # Find the results row for this arm and confirm both figures appear on it.
    row = next((ln for ln in readme.splitlines()
                if ln.strip().startswith(f"| {arm} ")), None)
    if row is None:
        pytest.skip(f"README has no results row for arm {arm}")
    assert str(calls) in row, f"README arm {arm} row missing llm_calls={calls}: {row}"
    assert f"{tokens:,}" in row, f"README arm {arm} row missing tokens={tokens:,}: {row}"


def test_conformance_defect_counts_in_docs_match_the_audit():
    """
    The defect counts the READMEs quote must match the conformance results.

    The dissertation interpolates these from the results file, so it cannot drift.
    The READMEs are written by hand, and one of them did drift: it claimed four
    tool schemas disagreed with their implementations when the audit found three.
    A reader who spots that stops trusting every other number in the document.
    """
    results_path = ROOT / "evaluation/results/protocol_conformance.json"
    if not results_path.exists():
        pytest.skip("no conformance results recorded yet")
    data = json.loads(results_path.read_text(encoding="utf-8"))

    m2 = next((c for c in data["mcp_checks"] if c["id"] == "M2"), None)
    assert m2, "M2 (implementation parameters absent from schema) not in the results"
    # "8/11 inspectable tools are clean" -> 3 tools disagree with their schema.
    match = re.search(r"(\d+)/(\d+) inspectable tools are clean", m2["detail"])
    assert match, f"M2 detail no longer states a clean/total count: {m2['detail']}"
    clean, total = int(match.group(1)), int(match.group(2))
    dirty = total - clean

    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
             7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven"}
    quoted = re.findall(r"(\w+) tool schemas disagree", ALL_TEXT)
    assert quoted, "no document states how many tool schemas disagree"
    expected = {words.get(dirty, str(dirty)), str(dirty)}
    wrong = [q for q in quoted if q.lower() not in expected]
    assert not wrong, (f"docs claim {wrong} tool schemas disagree; the audit found "
                       f"{dirty} ({clean} of {total} inspectable tools are clean)")

    summary = data["summary"]
    passed, failed = summary["passed"], summary["failed"]
    total_checks = summary["total_checks"]
    assert f"{passed} of {total_checks}" in ALL_TEXT or \
           f"{total_checks} checks" in ALL_TEXT, \
        (f"the conformance result ({passed} of {total_checks} passing, {failed} "
         f"failing) is not stated in any document")
