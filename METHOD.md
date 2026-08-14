# METHOD.md — how claims move through this repository

This repo makes claims about physical systems. Claims get tested. Tests
falsify claims. This file defines what happens next, so that the trail from
first guess to current claim stays readable years later.

The rule this document exists to enforce:

> **A falsified artifact is never deleted and never silently overwritten.
> It moves to `legacy/` and gets a ledger entry.**

Precedence carries. A claim that was tested and failed constrains what may
be claimed afterward — you do not get to re-assert it later without
addressing why it failed the first time. That constraint only works if the
failure is still on disk.

-----

## The loop

```
  hypothesize ──► run ──► result
                            │
              ┌─────────────┴─────────────┐
              │                           │
          survives                    falsified
              │                           │
     record as confirmed          edit the claim
     (with the test that          move the old artifact to legacy/
      would break it)             write the ledger entry
              │                           │
              └──────────► name the unknowns ◄──────┘
                                  │
                                rerun
```

Six steps, each with an obligation:

**1. Hypothesize.** State the claim so it can fail. "Wrong-order activation
is harmful" is not testable. "Wrong-order activation drives Φ above 1.0
within 120 months" is.

**2. Run.** Execute it — an ODE integration, an agent-based sweep, a field
measurement, a git archaeology pass. Record the exact invocation and the
numbers, not a summary of the numbers.

**3. Result.** Write down what actually came out, including when it is
boring, and including when it contradicts the reason you ran it.

**4. Falsified → edit the claim.** Change the claim in the file where it
lives — README, schema, module docstring. Do not leave the old wording
standing next to the new evidence. If the *artifact* is superseded rather
than the sentence, move the artifact to `legacy/`.

**5. Search for unknowns.** Every falsification must name at least one
unknown it opened. A falsification that opens no unknowns usually means the
test was weaker than it looked. This is the step most often skipped and the
one that pays.

**6. Rerun.** Test the revised claim, and test it harder than the first
time — a stronger schedule, a wider sweep, a parameter deliberately pushed
until the result breaks. A revised claim that has not been rerun is still
a hypothesis.

-----

## Verdict vocabulary

Every ledger entry carries exactly one verdict:

| verdict | meaning |
|---|---|
| `confirmed` | survived a test that could have broken it. Records the test. |
| `falsified` | the claim failed. Claim edited, artifact moved. |
| `revised` | partly true. The surviving part is narrower than the original. |
| `superseded` | not wrong, but replaced by something strictly better. |
| `orphaned` | depends on something not present. Cannot run here. |
| `untested` | asserted, never run. Named so it is not mistaken for evidence. |
| `irrecoverable` | falsified, but the prior artifact was lost before this rule existed. |

`untested` is not an insult. Most of this model is `untested`. The failure
mode is not having untested claims — it is untested claims that read like
confirmed ones.

-----

## `legacy/` — what it is and is not

`legacy/` is **evidence**, not an attic.

It holds artifacts that no longer run, no longer hold, or were replaced.
Each one is paired with a ledger entry saying what killed it and what part
of it survives. Files there are not maintained, not imported by live code,
and not deleted.

Read `legacy/README.md` for the current contents and
`legacy/ledger.json` for the machine-readable record.

**What does not go in `legacy/`:** incomplete work that was never tested
(that stays where it is, marked `untested` or `TODO`), and generated output
that can be reproduced by rerunning (that goes in `figures/`).

-----

## Adding an entry

Append to `legacy/ledger.json` under `entries`. Every field is required;
use `null` only where the schema permits it.

```json
{
  "id": "F-009",
  "date_opened": "2026-09-01",
  "date_resolved": "2026-09-03",
  "subject": "what the claim was about, in one line",
  "hypothesis": "the claim as originally stated, quoted if possible",
  "test": "exact command or procedure — reproducible by someone else",
  "result": "the numbers that came out",
  "verdict": "falsified",
  "claim_before": "the wording that was in the repo",
  "claim_after": "the wording that replaced it",
  "unknowns_opened": [
    "at least one — what this result made visible that was not visible before"
  ],
  "artifact": "legacy/some_file.py",
  "precedent_retained": "what part of the dead thing still binds future claims",
  "rerun": "the stronger test that was run against the revised claim, or null if pending"
}
```

Then:

1. Validate: `python3 validate.py` — checks that the entry parses, carries
   every required field, uses a verdict from the vocabulary, names at least
   one unknown, and points at an artifact that exists.
2. Edit the claim at its source — README, schema, or docstring.
3. If an artifact moved, use `git mv` so history follows it.
4. Reference the entry id from any code whose behavior depends on it.

That last point matters. `sim/network_sim.py` carries a comment pointing at
`F-004` on the one parameter that result is conditional on. A reader who
changes that parameter finds out immediately what it is load-bearing for.

-----

## Why this is not overhead

The repo already lost one of these. `audit/collapse_substrate_mapping.py`
was committed as "v2" with a docstring explaining that an earlier draft
framed a question wrongly and had to be rebuilt. The v1 was never committed.
The reasoning that produced the correction survives; the thing it corrected
does not. Nobody can now check whether the v2 diagnosis of v1 was fair, or
whether v1 contained anything worth keeping.

That is ledger entry `F-006`, verdict `irrecoverable`. It is the reason for
this file.

The same lesson applies to the rules themselves. `F-001` established that
schema files must use ASCII quotes only. The fix was applied by hand, one
smart apostrophe survived it, and because the file still *parsed*, nothing
noticed for five months. `validate.py` exists because a rule with no check
is a preference. Run it before committing:

```bash
python3 validate.py           # rules 1-6, fast
python3 validate.py --full    # also runs every audit module
```

-----

*CC0 1.0 Universal, same as the rest of the repository.*
