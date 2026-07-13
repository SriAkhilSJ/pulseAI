# RAG Upgrade Path: from the cheap option to the best option

## What's running right now (the cheap option)

`rag_indexer.py` uses **ChromaDB's default embedding function**: a small
ONNX-exported `all-MiniLM-L6-v2` model (~79MB, downloaded once to
`~/.cache/chroma/onnx_models/` on first use), run via `onnxruntime` (a
regular ChromaDB dependency — no extra install, no GPU).

This was a deliberate choice, not a default nobody thought about — the
originally-proposed stack (`sentence-transformers`) pulls in `torch`, whose
Linux wheel alone is **507MB**. Downloading it in this sandbox filled the
entire 996MB `/tmp` tmpfs and failed with `OSError: No space left on
device` — confirmed directly, not assumed. The cheap option was the only
one that actually worked here.

**What you get with the cheap option:**
- Zero API cost, fully offline after the one-time ~79MB download.
- Fast indexing (no GPU needed, runs fine on CPU).
- Good-enough semantic search — verified live (see `test/rag_indexer_test.py`
  and `test/rag_live_test_run.log`) that it correctly matches queries like
  *"external cryptocurrency price lookup"* to the actual Bitcoin-price Flask
  endpoint, with zero literal keyword overlap between the query and the code.
- 384-dimensional embeddings (MiniLM's native output size).

**What you're giving up:**
- MiniLM is a small, general-purpose sentence embedding model — not
  code-specific, not tuned to understand identifiers, call graphs, or
  language-specific structure the way a code-trained embedding model is.
- No batching/GPU acceleration — fine for a single project's codebase, will
  get slow indexing tens of thousands of files.
- Lower ceiling on retrieval quality for large, complex, multi-language
  codebases where subtle semantic distinctions matter (e.g. distinguishing
  "database connection pooling" from "database connection retry logic").

## When to upgrade

You don't need to upgrade for this project's current size (a few dozen
files). Consider it when:
- The codebase you're indexing grows past a few thousand files and search
  quality/recall starts feeling noticeably worse.
- You're regularly searching across multiple large repos/languages at once.
- You have a machine (or are willing to pay for cloud inference) with a GPU,
  or are fine paying a small per-embedding API cost.

## Option A — Better local model, still free, still no GPU required

Swap ChromaDB's default embedding function for a stronger *sentence*
embedding model that still runs on CPU via `onnxruntime` or a light
`sentence-transformers` install, but sized reasonably (not `torch`'s full
500MB+ footprint if you can avoid it):

```python
from chromadb.utils import embedding_functions

# BGE-small / GTE-small class models: better MTEB benchmark scores than
# MiniLM, still small enough to run on CPU (~130-260MB depending on model).
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-small-en-v1.5"  # or "thenlper/gte-small"
)
coll = client.get_or_create_collection("codebase", embedding_function=ef)
```

**Trade-off:** this DOES require `sentence-transformers` (and therefore
`torch`) — check available disk/`/tmp` space before installing in a
constrained environment like this sandbox. On a normal machine with a few
GB free, this is a straightforward, meaningfully-better upgrade with no
API cost.

## Option B — A code-specific embedding model (better semantic quality for code)

General sentence embedding models (MiniLM, BGE, GTE) are trained on natural
language, not code. A model actually trained to understand code structure
will retrieve better for programming-concept queries specifically:

- `jinaai/jina-embeddings-v2-base-code` (open, runs via `sentence-transformers`)
- `Salesforce/codet5p-110m-embedding` (smaller, code-specific)
- `microsoft/codebert-base` (older but still solid, code+docstring pairs)

Same integration pattern as Option A — swap the `embedding_function=` passed
to `get_or_create_collection`. Re-index everything after switching models
(embeddings from different models are NOT compatible/comparable with each
other — you cannot mix old MiniLM vectors with new model vectors in the
same collection; delete `.agent_rag_index/` and run `rag_index_directory`
again from scratch).

## Option C — Hosted embedding API (best quality, has a cost, needs internet)

For the best available retrieval quality with zero local compute cost:

- **OpenAI** `text-embedding-3-small` / `text-embedding-3-large` — cheap
  per-token, very strong general + code retrieval quality, but costs money
  and requires an OpenAI API key + network access.
- **Voyage AI** `voyage-code-2` — purpose-built for code retrieval,
  currently one of the strongest code-embedding models available, paid API.
- **Cohere** `embed-english-v3.0` — good general quality, has a free tier
  with rate limits, still needs network + a Cohere key.

```python
from chromadb.utils import embedding_functions

ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="...",  # store in .env like every other key in this project,
                     # never hardcoded, never committed -- see .env.example
    model_name="text-embedding-3-small",
)
coll = client.get_or_create_collection("codebase", embedding_function=ef)
```

**Trade-off:** ongoing per-embedding cost (small, but not zero — a few
cents per 1M tokens for OpenAI's small model, more for Voyage's code
model), requires network access and a valid API key, and re-introduces the
same "real API key pasted in chat, rotate it after" pattern already
established for Groq/Gemini/Cerebras/OpenRouter/Tavily in this project —
follow the same `.env`-only, never-committed, rotate-after-use discipline.

## How to actually switch, step by step

1. **Pick one option above** based on your constraints (disk/GPU/budget/
   internet access).
2. **Install whatever it needs** (`pip install sentence-transformers` for
   A/B, nothing extra for C beyond `chromadb` itself since it already
   bundles `OpenAIEmbeddingFunction`/etc.).
3. **Edit `rag_indexer.py`'s `_get_collection()` function** — it currently
   does:
   ```python
   def _get_collection():
       client = chromadb.PersistentClient(path=str(_get_index_dir()))
       return client.get_or_create_collection("codebase")
   ```
   Change it to pass your chosen `embedding_function=` explicitly:
   ```python
   def _get_collection():
       from chromadb.utils import embedding_functions
       ef = embedding_functions.SentenceTransformerEmbeddingFunction(
           model_name="BAAI/bge-small-en-v1.5"
       )
       client = chromadb.PersistentClient(path=str(_get_index_dir()))
       return client.get_or_create_collection("codebase", embedding_function=ef)
   ```
4. **Delete the old index and rebuild it** — embeddings from different
   models are not interchangeable:
   ```
   rm -rf .agent_rag_index/
   ```
   then call `rag_index_directory('.')` again (via the agent, or directly:
   `python3 -c "import rag_indexer; print(rag_indexer.index_directory('.'))"`).
5. **Re-run `test/rag_indexer_test.py`** to confirm the new embedder still
   passes the same correctness checks (decorator-attachment, no-content-lost,
   sensitive-file exclusion, and the two live semantic-search assertions) —
   don't just trust that a "better" model works without re-verifying.
6. If you switch to a hosted API (Option C), **update `.env.example`** with
   the new key's placeholder + signup link, following the exact pattern
   already used for the 5 existing keys in this project, and add the real
   key only to `.env` (git-ignored) — never commit it, never paste it
   anywhere it will be logged.

## What does NOT need to change when you upgrade

Everything else in `rag_indexer.py` — chunking (`chunk_file`,
`_chunk_by_boundaries`, the decorator-attachment fix), the sensitive-path
guardrail (`is_sensitive_path` check before indexing anything), the
`index_file`/`index_directory`/`search`/`index_stats` functions, and the
agent-facing tool specs — is embedding-model-agnostic. Only
`_get_collection()`'s embedding function needs to change; nothing about how
chunks are produced or how tools are exposed to the agent depends on which
model turns text into vectors.
