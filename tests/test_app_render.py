"""HTML rendering escapes untrusted strings (ticker input, Finnhub company names)."""
import math
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="module")
def app():
    # Load app.py without running its routing (it calls st.stop() when no key is set).
    import importlib.util

    import streamlit as st
    import data
    spec = importlib.util.spec_from_file_location("app_under_test", ROOT / "app.py")
    mod = importlib.util.module_from_spec(spec)
    with mock.patch.object(data, "FINNHUB_API_KEY", ""), \
         mock.patch.object(st, "stop", side_effect=SystemExit), \
         mock.patch.object(st, "error"):
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass
    return mod


PAYLOAD = '<img src=x onerror="alert(1)">'


def test_stock_card_escapes_company_name(app):
    from data import Profile, Quote
    html = app.render_stock_card("AAPL", Quote("AAPL", 1, 1, 1, 0), Profile("AAPL", PAYLOAD, 1e9), {})
    assert "<img" not in html
    assert "&lt;img" in html


def test_search_result_escapes(app):
    from data import Profile
    r = {"symbol": PAYLOAD, "quote": None, "profile": Profile("X", PAYLOAD, 0),
         "period_changes": {}, "metrics": {}}
    html = app.render_search_result(r)
    assert "<img" not in html


def test_infinite_ratio_renders(app):
    assert "∞" in app._metric_cell(math.inf, "ratio")
    assert app.fmt_ratio(math.inf) == "∞"
