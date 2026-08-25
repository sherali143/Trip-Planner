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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DOCS = {
    p: p.read_text(encoding="utf-8")
    for p in ROOT.rglob("*.md")
    if not any(x in p.as_posix() for x in (".venv", ".git", "node_modules"))
}
ALL_TEXT = "\n".join(DOCS.values())


def test_documentation_exists_for_every_package():
    """Each top-level folder explains itself."""
    for folder in ("trip_planner", "trip_planner/evaluation",
                   "trip_planner/demos", "trip_planner/tests", "submission"):
        assert (ROOT / folder / "README.md").exists(), f"{folder}/ has no README"


def test_the_dissertation_is_present():
    """
    The generated dissertation is the project's single written deliverable.

    It replaced a separate PROJECT_GUIDE.docx that restated the same measured
    results in a second document; keeping both meant two places for the same
    number to be wrong in.
    """
    report = ROOT / "submission" / "CMP7200_Dissertation.docx"
    assert report.exists(), (
        "submission/CMP7200_Dissertation.docx is missing — regenerate with "
        "python -m submission.build.build_dissertation"
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
            # Not project files: standard tooling invoked with -m.
            if cmd in ("pytest", "venv", "pip", "streamlit"):
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
    scenarios = (ROOT / "trip_planner/evaluation/scenarios.py").read_text(encoding="utf-8")
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
    results_path = ROOT / "trip_planner/evaluation/results/comparison_results.json"
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


def test_every_module_is_named_in_its_package_readme():
    """
    A new module must be added to the README of the folder it lives in.

    gemini_compat.py — the module that made the agent arms runnable again after
    Google withdrew the old model, and which now holds the single default model
    string — sat undocumented in trip_planner/README.md. Someone reading that
    README to understand the codebase would not have known the model problem had
    been solved at all.

    Only folders that keep a module table are checked, and only modules that are
    part of the explained surface: dunder files and the test suite are exempt.
    """
    packages = {
        "trip_planner": ["trip_planner", "trip_planner/core", "trip_planner/tools",
                         "trip_planner/comms", "trip_planner/server",
                         "trip_planner/ui"],
        "trip_planner/evaluation": ["trip_planner/evaluation"],
        "trip_planner/demos": ["trip_planner/demos"],
    }

    undocumented = []
    for package, folders in packages.items():
        readme_path = ROOT / package / "README.md"
        if not readme_path.exists():
            continue
        readme = readme_path.read_text(encoding="utf-8")
        for folder in folders:
            directory = ROOT / folder
            if not directory.is_dir():
                continue
            for module in sorted(directory.glob("*.py")):
                if module.name.startswith("__"):
                    continue
                # A README may name a module as a filename, as a path, or as the
                # dotted form used to run it ("python -m trip_planner.evaluation.exp_protocol").
                # All three tell the reader the module exists; only the absence of
                # all three is a documentation gap.
                dotted = f"{folder}/{module.stem}".replace("/", ".")
                forms = (module.name, f"{folder}/{module.name}", dotted)
                if not any(form in readme for form in forms):
                    undocumented.append(f"{folder}/{module.name} "
                                        f"(not in {package}/README.md)")
    assert not undocumented, (
        "modules missing from their package README: " + ", ".join(undocumented))


def test_the_test_count_in_docs_matches_what_pytest_collects():
    """
    A documented test count must match the suite.

    trip_planner/tests/README.md said "149 tests" long after the suite had grown past 170; a
    reader who runs the command sees a different number and reasonably wonders
    what else is out of date. The dissertation gets this right by running pytest
    at build time; a README cannot, so it is pinned here instead.

    Counted by asking pytest to COLLECT, not by parsing the files. An earlier
    version of this test walked the AST and multiplied out parametrize arguments,
    which worked until a parametrize list was computed at runtime
    (`sorted(AGENT_REGISTRY)`) — it counted that as one case instead of eight and
    then accused the README of being wrong by seven. Collection is the only source
    that agrees with what the reader will see.
    """
    import subprocess

    if os.environ.get("TRIP_PLANNER_COLLECTING"):
        pytest.skip("already inside a collection run")

    env = dict(os.environ, TRIP_PLANNER_COLLECTING="1")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only"],
        cwd=ROOT, capture_output=True, text=True, timeout=600, env=env)
    match = re.search(r"(\d+) tests? collected", proc.stdout)
    assert match, ("could not read a collection count from pytest:\n"
                   + proc.stdout[-800:])
    collected = int(match.group(1))

    quoted = {int(n) for n in re.findall(r"(\d+) tests", ALL_TEXT)}
    assert quoted, "no document states a test count"
    assert quoted == {collected}, (
        f"docs claim {sorted(quoted)} tests; pytest collects {collected}. "
        f"Update the README, or the number is the first thing a reader "
        f"finds wrong.")


def test_run_bat_menu_is_internally_consistent_and_matches_the_docs():
    """
    Every menu option run.bat offers must dispatch somewhere, and the docs must
    not name an option that does not exist.

    Inserting one option into the middle of the menu shifts every number after it.
    That happened when the project-overview option was added: run.bat was updated,
    and three documents went on telling the reader that the live-trip option was
    number 10 when it had become 11. A reader following those instructions runs
    the wrong thing.
    """
    run_bat = (ROOT / "run.bat").read_text(encoding="utf-8", errors="replace")

    dispatch = dict(re.findall(r'if "%choice%"=="(\d+)"\s+goto\s+(\w+)', run_bat))
    assert dispatch, "run.bat has no menu dispatch table"

    labels = set(re.findall(r"^:(\w+)", run_bat, re.M))
    dangling = {n: t for n, t in dispatch.items() if t not in labels}
    assert not dangling, f"menu options dispatching to missing labels: {dangling}"

    numbers = sorted(int(n) for n in dispatch)
    assert numbers == list(range(1, len(numbers) + 1)),         f"menu options are not a contiguous run from 1: {numbers}"

    highest = numbers[-1]
    prompt = re.search(r"Enter a number \(1-(\d+)\)", run_bat)
    assert prompt, "run.bat does not prompt for a numbered choice"
    assert int(prompt.group(1)) == highest, (
        f"run.bat prompts for 1-{prompt.group(1)} but dispatches up to {highest}")

    # No document may point at an option the menu does not have.
    quoted = {int(n) for n in re.findall(r"option[s]? (\d+)", ALL_TEXT)}
    quoted |= {int(n) for n in re.findall(r"options (\d+) to \d+", ALL_TEXT)}
    quoted |= {int(n) for n in re.findall(r"options \d+ to (\d+)", ALL_TEXT)}
    beyond = sorted(n for n in quoted if n > highest)
    assert not beyond, (
        f"docs name menu option(s) {beyond}, but run.bat only goes up to {highest}")


def test_no_module_defaults_to_the_withdrawn_model():
    """
    No code may fall back to a model Google has withdrawn.

    Seven modules defaulted to "gemini/gemini-2.5-flash". Google withdrew it from
    new API keys, so anyone who ran the project without a .env got a 404 from
    every arm and no indication why. The default now lives once, in
    gemini_compat.py, and that module is the only place allowed to name the dead
    model — it has to, in order to explain what changed.
    """
    from trip_planner.core.gemini_compat import (DEFAULT_MODEL, WITHDRAWN_MODEL,
                                                 model_string)
    assert DEFAULT_MODEL != WITHDRAWN_MODEL, \
        "the default model is the one that was withdrawn"

    offenders = []
    for path in ROOT.rglob("*.py"):
        if any(part in {".venv", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.name in {"gemini_compat.py", pathlib.Path(__file__).name}:
            continue
        if WITHDRAWN_MODEL in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, (
        f"these modules still name the withdrawn model {WITHDRAWN_MODEL!r}: "
        f"{offenders}. Call model_string() instead.")

    # And the fallback must be live even with no environment set.
    saved = os.environ.pop("GEMINI_MODEL", None)
    try:
        assert model_string() == DEFAULT_MODEL
    finally:
        if saved is not None:
            os.environ["GEMINI_MODEL"] = saved


def test_the_model_named_in_docs_is_the_model_that_produced_the_results():
    """
    The documents must name the model the recorded numbers actually came from.

    Three documents said "Gemini 2.5 Flash", which was true of the first round of
    measurements and false of the results that shipped. The report and the project
    overview now interpolate measured.model_name(); the READMEs are hand-written,
    so this is what stops them drifting back.
    """
    from trip_planner.evaluation import measured
    try:
        name = measured.model_name()
    except Exception:                       # noqa: BLE001 - no results recorded yet
        pytest.skip("no model recorded in the results provenance")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert name in readme, (
        f"README.md does not name {name!r}, the model recorded in the results "
        f"provenance block")


def test_conformance_defect_counts_in_docs_match_the_audit():
    """
    The defect counts the READMEs quote must match the conformance results.

    The dissertation interpolates these from the results file, so it cannot drift.
    The READMEs are written by hand, and one of them did drift: it claimed four
    tool schemas disagreed with their implementations when the audit found three.
    A reader who spots that stops trusting every other number in the document.
    """
    results_path = ROOT / "trip_planner/evaluation/results/protocol_conformance.json"
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


# ---------------------------------------------------------------------------
# Repository hygiene: no code that nothing uses
# ---------------------------------------------------------------------------
#
# These were hand-run scans, repeated every time the question "is there dead code
# left?" came up. A scan you have to remember to run is a scan that stops being
# run, so they are tests.
#
# What they caught between them: a test function defined twice in the same file,
# so the first had never executed once; a `parallel_mode` constructor argument
# that nothing passed and nothing read, advertising parallel searching this class
# has not done since the pivot; an `agent_card` attribute assigned and never used;
# and `suggest_budget`, a formatter duplicating CostEstimate.explain that no
# caller, demo, experiment or document referred to.

def _production_files():
    """Everything that ships or is run, excluding the test suite itself."""
    files = [ROOT / "run_cli.py", ROOT / "run_web.py"]
    for package in ("trip_planner", "submission"):
        files += [p for p in (ROOT / package).rglob("*.py")
                  # The test suite lives under trip_planner/ now, and it is not
                  # production code: sweeping it in flags every test function as
                  # unreferenced, because pytest finds them by name.
                  if "__pycache__" not in p.parts and "tests" not in p.parts]
    return files


def _test_files():
    return [p for p in (ROOT / "trip_planner" / "tests").rglob("*.py")
            if "__pycache__" not in p.parts]


def _read_all(paths):
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                     for p in paths)


def _searchable_text():
    """Every place a name could legitimately be referred to from."""
    parts = []
    for pattern in ("*.py", "*.md", "*.bat", "*.toml"):
        for path in ROOT.rglob(pattern):
            if any(x in path.parts for x in (".venv", ".git", "__pycache__")):
                continue
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def _defined_names(path):
    """(name, lineno) for every function and class defined in one file."""
    import ast

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    return [(n.name, n.lineno) for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef))
            and not n.name.startswith("__")]


# Kept deliberately, and each is argued in the dissertation rather than quietly
# left behind. Section 7.2 states that the shipped path records A2A messages and
# never dequeues, so "the delivery machinery, the executor class and the
# message-processing loop are all unreachable in production". Deleting these would
# make that sentence false, and would remove the surface the conformance audit
# measures. They are unused by the product on purpose, and that is the finding.
UNUSED_ON_PURPOSE = {
    "from_json",        # the deserialising half of the A2A wire format
    "to_dict",          # an agent card rendered as primitives
    "send_to_agent",    # AgentExecutor's convenience wrapper
}


def test_no_function_or_class_is_referenced_nowhere():
    """
    Anything defined and never named again is either dead or misspelt.

    Documents and run.bat count as references: a script's only caller may be a
    documented command rather than other code.
    """
    text = _searchable_text()
    orphans = []
    for path in _production_files():
        for name, line in _defined_names(path):
            if len(re.findall(r"\b" + re.escape(name) + r"\b", text)) <= 1:
                orphans.append(f"{path.relative_to(ROOT)}:{line} {name}")
    assert not orphans, "defined and never referenced: " + ", ".join(orphans)


def test_nothing_new_is_used_only_by_its_own_tests():
    """
    A function whose only caller is its test is not covered — it is unused, with
    a test for company. The three exceptions are listed above with their reason.
    """
    prod_text = _read_all(_production_files())
    test_text = _read_all(_test_files())

    unexpected = []
    for path in _production_files():
        for name, line in _defined_names(path):
            if name in UNUSED_ON_PURPOSE:
                continue
            word = r"\b" + re.escape(name) + r"\b"
            if (len(re.findall(word, prod_text)) <= 1
                    and re.search(word, test_text)):
                unexpected.append(f"{path.relative_to(ROOT)}:{line} {name}")
    assert not unexpected, (
        "used only by tests — delete it, or add it to UNUSED_ON_PURPOSE with a "
        "reason: " + ", ".join(unexpected))


def test_no_function_body_is_duplicated():
    """
    Copies drift. test_run_bat_menu_is_internally_consistent_and_matches_the_docs
    was pasted twice into this very file, and Python bound the second, so the
    first had never run.

    Compares normalised syntax trees with docstrings stripped, so two functions
    doing the same thing under different names are caught too.
    """
    import ast
    import hashlib
    from collections import defaultdict

    bodies = defaultdict(list)
    for path in list(_production_files()) + _test_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = list(node.body)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(getattr(body[0], "value", None), ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body = body[1:]
            if len(body) < 4:            # too short to be a meaningful clone
                continue
            key = hashlib.sha1(
                "".join(ast.dump(n) for n in body).encode()).hexdigest()
            bodies[key].append(f"{path.relative_to(ROOT)}:{node.lineno} "
                               f"{node.name}")
    clones = [group for group in bodies.values() if len(group) > 1]
    assert not clones, "identical function bodies: " + "; ".join(
        " == ".join(group) for group in clones)


def test_no_attribute_is_assigned_and_never_read():
    """
    `self.parallel_mode = parallel_mode` was the whole of that field's life. It
    read as a supported option — parallel API searches — that no caller could
    switch on and no code consulted.
    """
    import ast

    text = _read_all(list(_production_files()) + _test_files())
    orphans = set()
    for path in _production_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for node in ast.walk(cls):
                if (isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "self"
                        and isinstance(node.ctx, ast.Store)):
                    if len(re.findall(r"\.\b" + re.escape(node.attr) + r"\b",
                                      text)) <= 1:
                        orphans.add(f"{path.relative_to(ROOT)}:"
                                    f"{cls.name}.{node.attr}")
    assert not orphans, "assigned but never read: " + ", ".join(sorted(orphans))
