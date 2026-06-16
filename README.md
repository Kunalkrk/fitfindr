# FitFindr

FitFindr is a Groq-powered thrift shopping assistant. A user describes what they are looking for; the agent searches a secondhand listings dataset, selects the best match, generates outfit ideas using the user's wardrobe, and produces a short social-media caption — all surfaced in a Gradio UI.

---

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root with your Groq API key (free at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Run the UI:

```bash
python app.py
```

Run the CLI demo (both happy and no-results paths):

```bash
python agent.py
```

Run tests:

```bash
pytest tests/test_tools.py -v
```

---

## Project Structure

```
fitfindr/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe (10 items)
├── utils/
│   └── data_loader.py         # load_listings(), get_example_wardrobe(), get_empty_wardrobe()
├── tools.py                   # The three agent tools
├── agent.py                   # Planning loop — run_agent()
├── app.py                     # Gradio UI — handle_query()
├── tests/
│   └── test_tools.py          # 20 pytest tests
└── planning.md                # Design notes and architecture diagram
```

---

## Tool Inventory

### Tool 1 — `search_listings`

**Purpose:** Finds secondhand listings that match the user's keywords, size, and budget. This is the entry point of every interaction. No LLM is involved — matching is done by keyword overlap scoring.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `description` | `str` | Keywords describing what the user wants (e.g. `"vintage graphic tee"`) |
| `size` | `str \| None` | Size to filter by; `None` skips size filtering. Case-insensitive substring match — `"M"` matches `"S/M"` and `"XL (oversized M)"` |
| `max_price` | `float \| None` | Maximum price inclusive; `None` skips price filtering |

**Output:** `list[dict]` — matching listing dicts sorted by relevance score (highest first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`.

**Scoring:** A listing's score is the count of keyword tokens (from `description`) that appear in its `title` + `description` + `style_tags` combined. Listings with a score of zero are dropped.

---

### Tool 2 — `suggest_outfit`

**Purpose:** Generates 1–2 complete outfit suggestions using the selected listing and the user's wardrobe. Uses the Groq LLM (`llama-3.3-70b-versatile`). Wardrobe items are referenced by name in the prompt so the LLM produces specific, actionable pairings.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `new_item` | `dict` | The selected listing dict from `search_listings` |
| `wardrobe` | `dict` | A wardrobe dict with an `"items"` key; may be empty |

**Output:** `str` — a non-empty outfit suggestion. If the wardrobe is empty, returns general styling advice rather than specific wardrobe pairings. If the LLM call fails, returns a hardcoded fallback built from the item's tags and colors.

---

### Tool 3 — `create_fit_card`

**Purpose:** Turns the outfit suggestion and item details into a 2–4 sentence Instagram/TikTok-style caption. Uses the Groq LLM at `temperature=0.9` so repeated runs produce different captions. Mentions the item name, price, and platform exactly once each.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `outfit` | `str` | The outfit suggestion string from `suggest_outfit` |
| `new_item` | `dict` | The selected listing dict (for title, price, platform) |

**Output:** `str` — a casual caption string. If `outfit` is empty, `None`, or whitespace-only, returns a descriptive error string immediately (no LLM call). If the LLM call fails, returns a simple fallback caption.

---

## Planning Loop

`run_agent(query, wardrobe)` is the single entry point. It runs the tools in a fixed sequence and writes every intermediate result to a session dict before advancing.

```
User query
    │
    ▼
Parse query (regex)
Extract: description, size, max_price
    │
    ▼
search_listings(description, size, max_price)
    │
    ├── [] (no results) ──► set session["error"], return early
    │
    └── results found
            │
            ▼
        session["selected_item"] = results[0]   ← top relevance score
            │
            ▼
        suggest_outfit(selected_item, wardrobe)
            │
            ▼
        session["outfit_suggestion"] = <LLM response>
            │
            ▼
        create_fit_card(outfit_suggestion, selected_item)
            │
            ▼
        session["fit_card"] = <LLM caption>
            │
            ▼
        return session
```

**Query parsing:** Regex extracts structured fields from the free-text query before passing them to `search_listings`:
- Size: `\bsize\s+([A-Za-z0-9/]+)` — captures tokens like `M`, `XL`, `S/M`
- Price ceiling: `\bunder\s+\$?(\d+(?:\.\d+)?)` — captures the numeric value
- Description: the query with size and price phrases stripped out

The branching rule is hard: `suggest_outfit` and `create_fit_card` are only called if `search_listings` returns at least one result. Nothing after the early return executes.

---

## State Management

The session dict is the sole source of truth for one interaction. It is created by `_new_session()` and mutated in place as each step completes:

```python
session = {
    "query":            str,          # original user query, never modified
    "parsed":           dict,         # {"description": str, "size": str|None, "max_price": float|None}
    "search_results":   list[dict],   # all results from search_listings; [] on no match
    "selected_item":    dict | None,  # results[0]; None if no results
    "wardrobe":         dict,         # passed in unchanged; never mutated
    "outfit_suggestion": str | None,  # suggest_outfit output; None if skipped
    "fit_card":         str | None,   # create_fit_card output; None if skipped
    "error":            str | None,   # set on early termination; None on success
}
```

Values flow strictly forward: `selected_item` → `suggest_outfit` → `outfit_suggestion` → `create_fit_card`. The exact same object stored in the session is passed into each subsequent tool call (verified with `is` identity checks during development).

`app.py` reads only from the returned session dict — it calls no tools directly and contains no agent logic.

---

## Error Handling

### `search_listings` — no matching results

When `search_listings` returns `[]`, `run_agent` sets `session["error"]` and returns immediately. `suggest_outfit` and `create_fit_card` are never called.

**Concrete example from testing:**

Query: `"designer ballgown size XXS under $5"`

```python
{
    "search_results":    [],
    "selected_item":     None,
    "outfit_suggestion": None,
    "fit_card":          None,
    "error": "No listings found matching 'designer ballgown size XXS under $5'. "
             "Try different keywords, a different size, or a higher price limit."
}
```

Verified with monkey-patched wrappers that `suggest_outfit` and `create_fit_card` call counters stayed at zero.

---

### `suggest_outfit` — empty wardrobe

When `wardrobe["items"]` is an empty list (or the `"items"` key is absent), the tool switches to a general styling prompt instead of a wardrobe-specific one.

**Concrete example from testing:**

```python
suggest_outfit(
    new_item={"title": "Y2K Baby Tee — Butterfly Print",
              "category": "tops", "colors": ["white", "pink"],
              "style_tags": ["y2k", "vintage", "graphic tee"]},
    wardrobe={"items": []}
)
```

Returned (non-empty, no exception):
> *"The Y2K Baby Tee pairs well with high-waisted wide-leg denim or a plaid mini skirt for a vintage-inspired look. Add chunky platform sneakers or Mary Janes to lean into the Y2K aesthetic, and layer with an open flannel or cropped cardigan for a complete outfit."*

If the Groq call itself fails (e.g. no API key), the `except Exception` block returns a hardcoded fallback:
> *"This Y2K Baby Tee — Butterfly Print has a y2k, vintage, graphic tee vibe in white, pink. It would pair well with neutral basics and clean footwear for an effortless look."*

---

### `create_fit_card` — empty or missing outfit string

The guard runs before any LLM call. If `outfit` is `None`, `""`, or whitespace-only, the function returns an error string immediately.

**Concrete examples from testing:**

```python
create_fit_card("", sample_item)
# → "No outfit suggestion available — cannot generate a fit card without an outfit."

create_fit_card("   ", sample_item)
# → "No outfit suggestion available — cannot generate a fit card without an outfit."

create_fit_card(None, sample_item)
# → "No outfit suggestion available — cannot generate a fit card without an outfit."
```

All three return a non-empty string and raise no exception (`test_empty_outfit_does_not_raise` confirms this explicitly).

If the Groq call fails on a valid outfit string, the fallback caption is assembled from the item's title, price, and platform inline.

---

## Test Results

20 tests, 0 failures.

```
tests/test_tools.py::TestSearchListingsFailure::test_no_results_returns_empty_list        PASSED
tests/test_tools.py::TestSearchListingsFailure::test_no_results_is_list_not_exception     PASSED
tests/test_tools.py::TestSearchListingsFailure::test_price_filter_excludes_all_returns_empty PASSED
tests/test_tools.py::TestSearchListingsSuccess::test_vintage_graphic_tee_returns_results  PASSED
tests/test_tools.py::TestSearchListingsSuccess::test_returns_list_of_dicts                PASSED
tests/test_tools.py::TestSearchListingsSuccess::test_results_have_required_fields         PASSED
tests/test_tools.py::TestSearchListingsSuccess::test_price_filter_respected               PASSED
tests/test_tools.py::TestSearchListingsSuccess::test_size_filter_case_insensitive         PASSED
tests/test_tools.py::TestSearchListingsSuccess::test_sorted_by_relevance                  PASSED
tests/test_tools.py::TestSuggestOutfitFailure::test_empty_wardrobe_no_exception           PASSED
tests/test_tools.py::TestSuggestOutfitFailure::test_empty_wardrobe_returns_non_empty_string PASSED
tests/test_tools.py::TestSuggestOutfitFailure::test_missing_items_key_no_exception        PASSED
tests/test_tools.py::TestSuggestOutfitSuccess::test_with_wardrobe_returns_string          PASSED
tests/test_tools.py::TestSuggestOutfitSuccess::test_with_wardrobe_returns_non_empty       PASSED
tests/test_tools.py::TestCreateFitCardFailure::test_empty_string_returns_error_message    PASSED
tests/test_tools.py::TestCreateFitCardFailure::test_whitespace_only_returns_error_message PASSED
tests/test_tools.py::TestCreateFitCardFailure::test_none_returns_error_message            PASSED
tests/test_tools.py::TestCreateFitCardFailure::test_empty_outfit_does_not_raise           PASSED
tests/test_tools.py::TestCreateFitCardSuccess::test_valid_outfit_returns_string           PASSED
tests/test_tools.py::TestCreateFitCardSuccess::test_valid_outfit_returns_non_empty        PASSED

20 passed in 6.92s
```

Tests pass without a live Groq API key because both `suggest_outfit` and `create_fit_card` catch all exceptions internally and return fallback strings.

---

## Spec Reflection

**What went as planned:**

The tool boundaries mapped cleanly to the spec. Each tool is self-contained and testable in isolation — no shared global state, no cross-tool imports. The session dict made it straightforward to verify state at every step and to prove (with identity checks) that the exact same objects flowed between tools.

The early-exit pattern for empty search results was the most important design decision. Because `suggest_outfit` and `create_fit_card` are only reached through a single linear path after a non-empty `results` list, there is no way to accidentally call them with `None` input. The no-results path was verified both by running the CLI test and by patching the tools to confirm their call counters stayed at zero.

**What required adjustment:**

The planning doc described `create_fit_card`'s input as just `outfit (str)`, but the implementation needs `new_item` too — to pull the title, price, and platform into the caption. The spec was updated accordingly during implementation.

Query parsing with regex covers the common patterns (`"size M"`, `"under $30"`) well for the mock dataset. For a production system, an LLM-based parser would handle a much wider range of phrasing (e.g. `"fits a medium"`, `"budget of thirty dollars"`), but regex was the right choice here for simplicity and zero API calls during the search step.

**Empty wardrobe path:** The spec said to handle empty wardrobes gracefully. The implementation satisfies this by switching to a different LLM prompt (general styling advice) rather than a static string, so the response is still contextually relevant to the specific item even when no wardrobe data is available.

---

## AI Usage

### Instance 1 — Implementing `search_listings`

**Input given:**
The Tool 1 section of `planning.md` (inputs: `description str`, `size str`, `max_price float`; output: `list[dict]`; failure: return `[]`), the field list from the `load_listings()` docstring in `data_loader.py` (`title`, `description`, `style_tags`, `size`, `price`, etc.), and the five TODO steps already present inside the stub in `tools.py`.

**What it produced:**
A keyword overlap scorer using Python set intersection. For each listing that passes the price and size filters, it counts how many of the user's query tokens appear in the listing's `title`, `description`, and `style_tags` combined. Listings with a score of zero are dropped; the rest are sorted descending by score and returned as a plain list of dicts.

**What was reviewed and left unchanged:**
The scoring logic treats all three fields equally — a match in `style_tags` counts the same as a match in `title`. A weighted approach (e.g. title matches worth 2×) would rank more precisely, but the unweighted version matched the spec ("score each remaining listing by keyword overlap") exactly and produced correct ordering for every test query run during development. No change was made.

**What was verified before keeping:**
Three manual spot-checks: `"vintage graphic tee"` returned items tagged `["graphic tee", "vintage"]` at the top; `"vintage"` with `max_price=25.00` returned only listings priced ≤ $25; `"xyzzy_nonexistent"` returned `[]`. All matched expected output.

---

### Instance 2 — Implementing `suggest_outfit` and discovering the `create_fit_card` signature gap

**Input given:**
The Tool 2 section of `planning.md` (inputs: `new_item dict`, `wardrobe dict`; output: non-empty str; failure: empty wardrobe handled gracefully), the wardrobe item schema from `wardrobe_schema.json` (each item has `name`, `category`, `colors`, `style_tags`, `notes`), and the four TODO steps in the stub.

**What it produced:**
A two-branch prompt strategy: if `wardrobe["items"]` is empty or the key is absent, a general styling prompt is sent asking what kinds of bottoms, shoes, and outerwear pair well with the item; if the wardrobe is populated, each item is formatted as a bullet line (`- name [category] — colors — tags (notes)`) and the prompt asks the LLM to reference pieces by name. Both branches call `llama-3.3-70b-versatile` and catch all exceptions with a hardcoded fallback string.

**What was changed before using it:**
While implementing `create_fit_card` immediately after, the planning doc listed its only input as `outfit (str)`. The caption prompt needs the item's title, price, and platform to satisfy the spec requirement ("mention the item name, price, and platform naturally, once each"). The signature was extended to `create_fit_card(outfit: str, new_item: dict)` before writing any code for that function, and the corresponding call in `run_agent` was updated to pass `session["selected_item"]` as the second argument. The planning doc's Tool 3 parameter list was the gap that triggered this correction.

**What was verified before keeping:**
Ran `suggest_outfit` with `get_example_wardrobe()` and confirmed the output referenced wardrobe pieces by name (e.g. "Baggy straight-leg jeans", "Black combat boots"). Ran again with `get_empty_wardrobe()` and confirmed a non-empty general styling string was returned instead of an exception or empty string. Both verified against the test suite (`TestSuggestOutfitFailure`, `TestSuggestOutfitSuccess`).

---

### Instance 3 — Implementing `run_agent` and choosing regex over LLM for query parsing

**Input given:**
The Planning Loop section of `planning.md` (call `search_listings` → if no results stop → select top result → `suggest_outfit` → `create_fit_card` → return), the State Management section (the seven session keys and which tool writes each one), and the architecture diagram showing the branching paths for empty results and empty wardrobe.

**What it produced:**
A linear planning loop that initialises a session dict, parses the query with two regex patterns, runs the tools in sequence, and hard-stops after `search_listings` if results are empty. The specific patterns: `\bsize\s+([A-Za-z0-9/]+)` for size tokens and `\bunder\s+\$?(\d+(?:\.\d+)?)` for price ceilings. Both patterns are stripped from the query string; the remainder becomes the `description` argument.

**What was overridden:**
The planning doc noted the parser could use "regex, string splitting, or ask the LLM." The AI proposed regex and documented this as a deliberate tradeoff: LLM parsing handles a wider range of phrasing (`"fits a medium"`, `"thirty dollars max"`) but costs an API call on every search before any results are returned. For the mock dataset — where all example queries follow predictable patterns like `"size M"` and `"under $30"` — regex covers all real cases with zero latency and zero API cost. The LLM option was considered and rejected in favour of regex for this scope. If the dataset or query patterns were expanded to production use, the parser would be the first component to replace.

**What was verified before keeping:**
Ran both CLI paths in `agent.py`. The happy path (`"looking for a vintage graphic tee under $30"`) correctly parsed `description="looking for a vintage graphic tee"`, `size=None`, `max_price=30.0` and returned a full session. The no-results path (`"designer ballgown size XXS under $5"`) parsed `description="designer ballgown"`, `size="XXS"`, `max_price=5.0`, returned `search_results=[]`, and left `selected_item`, `outfit_suggestion`, and `fit_card` all as `None` — confirmed by printing the full session dict.
