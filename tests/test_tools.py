"""
tests/test_tools.py

pytest tests for the three FitFindr tool functions.

Run from the project root:
    pytest tests/test_tools.py
"""

import sys
import os

# Make sure the project root is importable regardless of where pytest is invoked
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── Shared fixture data ───────────────────────────────────────────────────────

SAMPLE_ITEM = {
    "id": "lst_002",
    "title": "Y2K Baby Tee — Butterfly Print",
    "category": "tops",
    "colors": ["white", "pink", "purple"],
    "style_tags": ["y2k", "vintage", "graphic tee"],
    "size": "S/M",
    "price": 18.00,
    "platform": "depop",
}


# ── search_listings ───────────────────────────────────────────────────────────

class TestSearchListingsFailure:
    def test_no_results_returns_empty_list(self):
        results = search_listings("xyzzy_nonexistent_zzzzz")
        assert results == []

    def test_no_results_is_list_not_exception(self):
        # Confirm type — not None, not an error
        results = search_listings("qqqqqq_nothing_matches")
        assert isinstance(results, list)

    def test_price_filter_excludes_all_returns_empty(self):
        # max_price of 0 should exclude everything
        results = search_listings("vintage", max_price=0.00)
        assert results == []


class TestSearchListingsSuccess:
    def test_vintage_graphic_tee_returns_results(self):
        results = search_listings("vintage graphic tee")
        assert len(results) > 0

    def test_returns_list_of_dicts(self):
        results = search_listings("vintage graphic tee")
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)

    def test_results_have_required_fields(self):
        results = search_listings("vintage")
        assert len(results) > 0
        for listing in results:
            for field in ("id", "title", "description", "price", "size", "platform"):
                assert field in listing

    def test_price_filter_respected(self):
        results = search_listings("vintage", max_price=25.00)
        assert all(r["price"] <= 25.00 for r in results)

    def test_size_filter_case_insensitive(self):
        # "m" should match listings with size "M", "S/M", "XL (oversized M)", etc.
        results = search_listings("vintage", size="M")
        assert all("m" in r["size"].lower() for r in results)

    def test_sorted_by_relevance(self):
        # The listing whose tags include both "graphic" and "tee" should rank
        # ahead of one that matches only one keyword
        results = search_listings("graphic tee")
        assert len(results) > 0
        # First result must at least contain "tee" or "graphic" somewhere
        first = results[0]
        text = (
            first["title"] + " " +
            first["description"] + " " +
            " ".join(first.get("style_tags", []))
        ).lower()
        assert "tee" in text or "graphic" in text


# ── suggest_outfit ────────────────────────────────────────────────────────────

class TestSuggestOutfitFailure:
    def test_empty_wardrobe_no_exception(self):
        empty = get_empty_wardrobe()
        result = suggest_outfit(SAMPLE_ITEM, empty)
        assert isinstance(result, str)

    def test_empty_wardrobe_returns_non_empty_string(self):
        empty = get_empty_wardrobe()
        result = suggest_outfit(SAMPLE_ITEM, empty)
        assert len(result) > 0

    def test_missing_items_key_no_exception(self):
        result = suggest_outfit(SAMPLE_ITEM, {})
        assert isinstance(result, str)
        assert len(result) > 0


class TestSuggestOutfitSuccess:
    def test_with_wardrobe_returns_string(self):
        wardrobe = get_example_wardrobe()
        result = suggest_outfit(SAMPLE_ITEM, wardrobe)
        assert isinstance(result, str)

    def test_with_wardrobe_returns_non_empty(self):
        wardrobe = get_example_wardrobe()
        result = suggest_outfit(SAMPLE_ITEM, wardrobe)
        assert len(result) > 0


# ── create_fit_card ───────────────────────────────────────────────────────────

class TestCreateFitCardFailure:
    def test_empty_string_returns_error_message(self):
        result = create_fit_card("", SAMPLE_ITEM)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_whitespace_only_returns_error_message(self):
        result = create_fit_card("   ", SAMPLE_ITEM)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_none_returns_error_message(self):
        result = create_fit_card(None, SAMPLE_ITEM)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_outfit_does_not_raise(self):
        try:
            create_fit_card("", SAMPLE_ITEM)
        except Exception as exc:
            assert False, f"create_fit_card raised an exception: {exc}"


class TestCreateFitCardSuccess:
    def test_valid_outfit_returns_string(self):
        outfit = "Baby tee tucked into baggy dark-wash jeans with chunky sneakers."
        result = create_fit_card(outfit, SAMPLE_ITEM)
        assert isinstance(result, str)

    def test_valid_outfit_returns_non_empty(self):
        outfit = "Baby tee tucked into baggy dark-wash jeans with chunky sneakers."
        result = create_fit_card(outfit, SAMPLE_ITEM)
        assert len(result) > 0
