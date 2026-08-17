#!/usr/bin/env python3
"""
validate.py — check the repository's own rules against the repository.

Ledger F-001 established that schema files must be parseable JSON with ASCII
double quotes only. That was fixed by hand and one smart apostrophe survived
in system-model.json for five months, because a rule with no check is a
preference. This is the check.

Verifies:
  1. Every JSON file parses.
  2. No Unicode smart quotes in any JSON file.
  3. legacy/ledger.json entries carry every field METHOD.md requires.
  4. Every ledger verdict is in the documented vocabulary.
  5. Every artifact path referenced by a ledger entry exists.
  6. Every path in index.json's repository_map exists.
  7. Every audit/ module imports and runs; sim/transition.py runs in each of
     its stdlib-only modes and imports nothing outside the standard library
     at module level.

Usage:
  python3 validate.py           # rules 1-6 (fast)
  python3 validate.py --full    # also rule 7 (runs every audit module)

Exit code 0 if clean, 1 otherwise. Stdlib only.
License: CC0 1.0 Universal
"""

import ast
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SMART_QUOTES = {"‘", "’", "“", "”"}

REQUIRED_LEDGER_FIELDS = [
    "id", "date_opened", "date_resolved", "subject", "hypothesis", "test",
    "result", "verdict", "claim_before", "claim_after", "unknowns_opened",
    "artifact", "precedent_retained", "rerun",
]

failures = []


def fail(rule, msg):
    failures.append(f"[{rule}] {msg}")


def rel(p):
    return os.path.relpath(p, ROOT)


def json_files():
    paths = sorted(glob.glob(os.path.join(ROOT, "*.json")))
    paths += sorted(glob.glob(os.path.join(ROOT, "legacy", "*.json")))
    return paths


def check_json_parses():
    parsed = {}
    for path in json_files():
        try:
            with open(path, encoding="utf-8") as fh:
                parsed[path] = json.load(fh)
        except (ValueError, UnicodeDecodeError) as exc:
            fail("parse", f"{rel(path)}: {exc}")
    return parsed


def check_no_smart_quotes():
    for path in json_files():
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                found = sorted(SMART_QUOTES & set(line))
                if found:
                    fail("ascii", f"{rel(path)}:{lineno} contains {found} "
                                  f"-- use ASCII quotes (ledger F-001)")


def check_ledger(parsed):
    path = os.path.join(ROOT, "legacy", "ledger.json")
    ledger = parsed.get(path)
    if ledger is None:
        fail("ledger", "legacy/ledger.json missing or unparseable")
        return

    vocabulary = set(ledger.get("verdict_vocabulary", {}))
    if not vocabulary:
        fail("ledger", "verdict_vocabulary is empty")

    seen_ids = set()
    for entry in ledger.get("entries", []):
        eid = entry.get("id", "<no id>")

        if eid in seen_ids:
            fail("ledger", f"{eid}: duplicate entry id")
        seen_ids.add(eid)

        for field in REQUIRED_LEDGER_FIELDS:
            if field not in entry:
                fail("ledger", f"{eid}: missing required field '{field}' "
                               f"-- see METHOD.md")

        verdict = entry.get("verdict")
        if vocabulary and verdict not in vocabulary:
            fail("ledger", f"{eid}: verdict '{verdict}' not in vocabulary "
                           f"{sorted(vocabulary)}")

        unknowns = entry.get("unknowns_opened")
        if not isinstance(unknowns, list) or not unknowns:
            fail("ledger", f"{eid}: must name at least one unknown opened "
                           f"-- see METHOD.md step 5")

        artifact = entry.get("artifact")
        if artifact and not os.path.exists(os.path.join(ROOT, artifact)):
            fail("ledger", f"{eid}: artifact '{artifact}' does not exist. "
                           f"Falsified artifacts are moved, never deleted.")


def check_index_paths(parsed):
    path = os.path.join(ROOT, "index.json")
    index = parsed.get(path)
    if index is None:
        fail("index", "index.json missing or unparseable")
        return

    def walk(node):
        if isinstance(node, dict):
            target = node.get("path")
            if isinstance(target, str):
                if not os.path.exists(os.path.join(ROOT, target)):
                    fail("index", f"repository_map path '{target}' does not "
                                  f"exist (ledger F-007)")
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(index.get("repository_map", {}))


def _run(argv, rule, label):
    result = subprocess.run(argv, capture_output=True, timeout=180, cwd=ROOT)
    if result.returncode != 0:
        last = result.stderr.decode(errors="replace").strip().splitlines()
        detail = last[-1] if last else f"exit {result.returncode}"
        fail(rule, f"{label}: {detail}")


def check_audit_modules():
    modules = sorted(glob.glob(os.path.join(ROOT, "audit", "*.py")))
    if not modules:
        fail("audit", "no modules found in audit/")
    for module in modules:
        _run([sys.executable, module], "audit", rel(module))

    transition = os.path.join(ROOT, "sim", "transition.py")
    if not os.path.exists(transition):
        fail("transition", "sim/transition.py missing")
        return
    for mode in ("actors", "minimal", "substrate", "sensitivity",
                 "schedule", "all"):
        _run([sys.executable, transition, mode], "transition",
             f"sim/transition.py {mode}")
    check_transition_is_stdlib(transition)


# Third-party modules this repo uses. Anything here is fine inside sim/sim.py
# and sim/network_sim.py, and must not appear at module level in
# sim/transition.py, which is stdlib-only so a reader without numpy can use it.
THIRD_PARTY = {"numpy", "scipy", "matplotlib"}


def check_transition_is_stdlib(path):
    """
    Assert sim/transition.py imports nothing third-party at module level.

    Running the modes is not sufficient evidence: this machine has numpy
    installed, so a stray top-level import would run fine here and fail on
    the machine the claim is made for. Checking the import graph is the check
    that can actually fail. Function-level imports are allowed — the verify
    mode imports numpy inside the function and degrades gracefully without it.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)

    for node in tree.body:  # module level only, not nested in functions
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".")[0]]
        for name in names:
            if name in THIRD_PARTY:
                fail("transition",
                     f"{rel(path)}:{node.lineno} imports '{name}' at module "
                     f"level. This module is stdlib-only by design so it runs "
                     f"without an install step.")


def main():
    full = "--full" in sys.argv

    parsed = check_json_parses()
    check_no_smart_quotes()
    check_ledger(parsed)
    check_index_paths(parsed)
    if full:
        check_audit_modules()

    if failures:
        print(f"FAILED — {len(failures)} problem(s):\n")
        for line in failures:
            print("  " + line)
        return 1

    scope = "rules 1-7" if full else "rules 1-6 (use --full for audit modules)"
    print(f"OK — {scope} pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
