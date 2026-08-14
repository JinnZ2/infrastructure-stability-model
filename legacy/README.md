# legacy/

Artifacts that no longer run, no longer hold, or were replaced.

**This is evidence, not an attic.** Nothing here is deleted. Nothing here is
maintained. Nothing here is imported by live code. Each item is paired with
an entry in [`ledger.json`](ledger.json) recording what killed it and what
part of it still binds future work.

Precedence carries: a claim that was tested and failed constrains what may
be claimed afterward. That only works if the failure is still on disk. See
[`../METHOD.md`](../METHOD.md) for the protocol.

-----

## Contents

### `audit_producers.py` — orphaned (ledger `F-005`)

Adapter shim that wrapped each audit module as a `ConstraintProducer`
emitting into a shared `AuditAccumulator`, with a `ReadinessGate` evaluating
the result.

**Why it is here:** it imports `audit_substrate` and `audit_vestibular`,
neither of which exists in this repository, and adapts a sensory-audit stack
(haptic, acoustic, olfactory, visual fouling, vestibular) that is also
absent. It raises `ModuleNotFoundError` on import. The 13 audit modules that
remain in `audit/` are independent and stdlib-only; there is no shared bus
for this file to adapt them to.

**What survives:** the architecture. Producers emitting typed
`ConstraintResult` and `LifecycleCost` records into a shared accumulator,
with a gate evaluating readiness against them, is still the right target for
this repo's audit modules. The interface shape in this file is the
specification. Only its imports are dead.

-----

## What does not go here

- **Incomplete work that was never tested** — stays where it lives, marked
  `untested` in the ledger or with a `TODO`. Being unfinished is not being
  falsified. (`audit/induced_incompetence_cascade.py`, ledger `F-008`.)
- **Generated output** — figures are reproducible by rerunning the sims;
  they live in `figures/` and are overwritten, not archived.
- **Claims** — a falsified *sentence* is corrected at its source and
  recorded in the ledger. Only falsified *artifacts* move here.

-----

## The entry that is missing

`collapse_substrate_mapping.py` v1 should be in this directory and is not.
It was rewritten in place as v2 and the original was never committed — the
correction survives, its subject does not, and nobody can now check whether
the v2 diagnosis was fair. That is ledger `F-006`, verdict `irrecoverable`,
and it is why this directory exists.
