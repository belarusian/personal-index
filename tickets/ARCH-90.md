# ARCH-90: build_tree drops a package's own module when it also has children

Status: CLAIMED 2026-09-16
Component: personal_index/cycle_signals.py
Issue: #1469

## Symptom

`build_tree` (line 256) is documented to return a node whose `modules` field
holds "leaf module names". But a node that is BOTH a module (its own package
file, e.g. `pkg.sub/__init__.py`, has functions so it is recorded in
`node["modules"]`) AND has children (a subpackage, e.g. `pkg.sub.beta`) loses
its own module entry in the output: the node shows `stats.modules` counting it,
but has no `modules` key, so the module is invisible in the tree while still
counted in the aggregate stats.

## Evidence

`_node_to_dict` (line 205) only emits `result["modules"]` for leaf nodes:

    222    signal_modules: list[str] = []
    223    if not children:  # leaf node
    224        signal_modules.extend(node["modules"])
    ...
    236    if signal_modules:
    237        result["modules"] = signal_modules

When `children` is non-empty, `signal_modules` stays `[]`, so the node's own
module (present in `node["modules"]`) is dropped.

Repro (deterministic, no I/O):

    from personal_index import cycle_signals
    mods = [
      {"name":"pkg.sub","lines":10,"functions":1,"classes":0,"tests":0,
       "ruff_errors":0,"mypy_errors":0,"ruff_warnings":0},
      {"name":"pkg.sub.beta","lines":10,"functions":1,"classes":0,"tests":0,
       "ruff_errors":0,"mypy_errors":0,"ruff_warnings":0},
    ]
    t = cycle_signals.build_tree(mods)
    sub = t["children"]["pkg"]["children"]["sub"]
    # sub["stats"]["modules"] == 2  (counts pkg.sub AND pkg.sub.beta)
    # "modules" not in sub          (pkg.sub's own entry is dropped)
    # sub["children"]["beta"]["modules"] == ["pkg.sub.beta"]

Observed: `sub` has `stats.modules == 2` but no `modules` key; only
`pkg.sub.beta` is listed (under `children.beta.modules`). `pkg.sub` itself is
counted in stats yet absent from the tree's module listing.

## Why it matters

The tree is the LLM-facing scope summary (`format_for_auditor` / `--format
tree`). A package that has both an `__init__.py` with logic and submodules is
exactly the kind of node an auditor needs to see; its own module silently
disappears while the stats still count it, so the stats and the visible module
listing disagree.

## Proposed fix (implementer)

In `_node_to_dict`, emit the node's own modules whenever `node["modules"]` is
non-empty, independent of whether the node has children — i.e. remove the
`if not children:` gate on the `signal_modules` population (or, if the intent
is to keep non-leaf nodes compact, document that a package's own module is
deliberately omitted and reconcile `stats.modules` so it does not count the
omitted module). The minimal additive fix is to always extend
`signal_modules` from `node["modules"]` and emit `result["modules"]` when
non-empty, so a package node carries both its own module and its `children`.

## Acceptance criteria

1. For a module list containing a package that is both a module and a parent
   (e.g. `pkg.sub` + `pkg.sub.beta`), `build_tree` output for the `pkg.sub`
   node includes `pkg.sub` in its `modules` list AND keeps `children` with
   `pkg.sub.beta`.
2. `stats.modules` at every node equals the number of module entries visible
   under that node (own `modules` + descendants) — no counted-but-invisible
   module.
3. Leaf-node behavior is unchanged: a node with only modules (no children)
   still lists them in `modules`.
4. `format_tree` / `format_for_auditor` output for such a node now shows the
   package's own module.

## Pinning tests to add (tests/test_cycle_signals.py)

- `test_package_with_children_keeps_own_module`: build a tree from
  `pkg.sub` + `pkg.sub.beta`; assert the `pkg.sub` node has
  `"modules" == ["pkg.sub"]` and `children["beta"]["modules"] ==
  ["pkg.sub.beta"]`, and `stats["modules"] == 2`.
- `test_leaf_node_modules_unchanged`: build a tree from a single leaf module;
  assert its `modules` list is unchanged (guard path: no children).

## Docs update (same PR)

`docs/cycle-signals.md` (new spec page) documents the `build_tree` contract
and calls out this hole under the `build_tree` section; `docs/README.md` gains
the index entry.
