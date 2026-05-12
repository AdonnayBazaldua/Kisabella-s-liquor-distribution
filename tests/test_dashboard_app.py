"""TDD smoke tests for the Streamlit dashboard via AppTest."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

SCRIPT = (Path(__file__).resolve().parent.parent / "src" / "kisabella" / "dashboard" / "app.py").as_posix()


def test_dashboard_renders_title_tabs_and_filter_widgets(warehouse_at_config_path):
    at = AppTest.from_file(SCRIPT, default_timeout=15).run()

    assert not at.exception, at.exception

    # Page title contains the brand
    assert any("Kisabella" in t.value or "Top 10" in t.value for t in at.title)

    # Sidebar exposes the filter widgets
    assert len(at.sidebar.multiselect) >= 1, "expected store multiselect in sidebar"
    assert len(at.sidebar.date_input) >= 1, "expected date_input in sidebar"

    # Main body has the two product/vendor tabs
    assert len(at.tabs) >= 2


def test_selecting_a_store_filter_narrows_the_top10_table(warehouse_at_config_path):
    at = AppTest.from_file(SCRIPT, default_timeout=15).run()

    # With no filters, fixture has 4 distinct brands in fact_sales (excluding the
    # anomalous and cost-missing rows). The first dataframe in the first tab is
    # "Top 10 products by Profit$".
    initial = at.tabs[0].dataframe[0].value
    assert initial.shape[0] == 4

    # Apply store=1 filter: only brands sold in store 1 survive (100, 200, 400).
    at.sidebar.multiselect[0].set_value([1]).run()
    assert not at.exception, at.exception
    filtered = at.tabs[0].dataframe[0].value
    assert filtered.shape[0] == 3
