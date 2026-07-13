# Repo Map: upgrading from hand-rolled PageRank to `networkx`

## Why this doc exists

`repo_map.py`'s PageRank (`repo_map._pagerank`) is currently a small,
hand-rolled implementation (~50 lines), not `networkx`. This was a
deliberate choice, not an oversight -- documented here per explicit
instruction so the reasoning and upgrade path are preserved rather than
silently forgotten.

## What was actually verified (not assumed)

A proposal for this feature claimed `networkx` was "already installed via
some dependency." That claim was checked directly against this project's
real environment and found to be **misleading**:

- `networkx` IS present in this sandbox (confirmed: `pip show networkx`
  succeeds, version 3.6.1).
- But it is **not** a real dependency of anything in `requirements.txt`.
  Checked every package this project actually requires
  (`litellm`, `python-dotenv`, `playwright`, `ddgs`, `requests`,
  `pylspclient`, `python-lsp-server`, `mcp`, `mcp-server-fetch`,
  `GitPython`, `chromadb`, `tree-sitter`, `tree-sitter-python`,
  `tree-sitter-javascript`) -- none of them require `networkx` or
  `scikit-image` (`networkx`'s actual origin here).
- `scikit-image` itself is present in this sandbox for reasons entirely
  unrelated to this project (likely a base-image default), and pulls in
  `networkx` as its own transitive dependency.

This is a materially different situation from `PyYAML` (used by
`skills.py`/`rules.py`), which genuinely IS a real transitive dependency
of `chromadb` (a project requirement) -- confirmed separately when
building those modules. Relying on `networkx` today would mean relying on
an accident of this particular sandbox image, not a guarantee that holds
in a clean environment, a different sandbox, or a real deployment.

## The decision

Build a small, hand-rolled PageRank now (zero new dependency risk),
verified NUMERICALLY correct against `networkx`'s own real output
(`nx.pagerank()`, using `networkx` as ground truth for verification only,
not as a runtime dependency) -- matched to 5-6 decimal places across
multiple test graphs, including the edge case of an isolated node with no
edges at all. See `test/repo_map_test.py`'s
`test_pagerank_matches_networkx_on_normal_graph` and
`test_pagerank_matches_networkx_with_isolated_node` for the exact
verification.

This matches this project's established build-cheap-first,
measure-then-escalate practice (see README.md's "Batching nudge" section
for the precedent: build the smaller thing, escalate only if a real
measurement shows it's insufficient).

## When to actually upgrade to `networkx`

The hand-rolled implementation is a plain Python dict-based power
iteration -- O(iterations × edges) per call, no sparse matrix
optimization. It's been verified correct and is fast enough for this
project's own current size (74 real `.py`/`.js` files, cold scan ~0.35s,
warm/cached scan ~0.006s, full `get_repo_map()` pipeline ~0.03s -- all
measured directly, not estimated).

Upgrade to `networkx` when EITHER of these becomes true, based on a real
measurement (not a guess):

1. **Codebase size**: if a target codebase's file count grows into the
   thousands (well beyond this project's current 74), the O(n) per-
   iteration Python loop may become the actual bottleneck. Measure first
   (`time python3 -c "import repo_map; repo_map.get_repo_map()"` against
   the real target codebase) before assuming this is a problem -- Aider's
   own repo map (the algorithm this module is modeled on) reports
   sub-second performance on codebases with thousands of files using a
   similarly simple approach, so this threshold may be higher than it
   first appears.
2. **Algorithm sophistication**: if repo_map.py ever needs graph
   algorithms beyond plain PageRank (e.g. personalized PageRank with
   per-node reset probabilities, weighted edges reflecting reference
   COUNTS rather than a flat 0/1 edge per import, or community detection
   to group related files) -- `networkx` has these built-in and
   well-tested; hand-rolling each one is a worse trade than it is for
   plain PageRank alone.

## How to actually upgrade (when the time comes)

1. Add `networkx>=3.0` to `requirements.txt` as a REAL, declared
   dependency (not relying on sandbox coincidence).
2. Replace `repo_map._pagerank(nodes, edges, ...)`'s body with:
   ```python
   import networkx as nx
   g = nx.DiGraph()
   g.add_nodes_from(nodes)  # include isolated nodes explicitly -- same
                            # requirement the hand-rolled version has,
                            # confirmed this session that edges alone
                            # can't reveal an isolated file
   g.add_edges_from(edges)
   return nx.pagerank(g, alpha=alpha, max_iter=max_iter, tol=tol)
   ```
3. Re-run `test/repo_map_test.py`'s existing PageRank tests unchanged --
   they compare against real `nx.pagerank()` output already, so they
   should continue passing with `networkx` doing the actual computation
   instead of just being the verification ground truth.
4. Keep the hand-rolled `_pagerank` function in the codebase (renamed
   `_pagerank_pure_python` or similar) as a fallback for environments
   where `networkx` genuinely isn't installed, following this project's
   own established `try/except` + `_AVAILABLE` flag pattern used for
   every other optional dependency (PyYAML, chromadb, tree-sitter, etc.)
   -- don't hard-require `networkx` if the pure-Python version still
   works correctly for smaller codebases.
