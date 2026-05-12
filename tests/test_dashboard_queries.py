"""TDD tests for dashboard.queries."""
from datetime import date
import pytest

from kisabella.dashboard.queries import top10, summary_metrics, get_store_options, get_date_bounds


def test_top10_products_by_profit_returns_brands_ordered_by_profit_net(warehouse_with_data):
    result = top10(warehouse_with_data, by="product", rank="profit")
    assert result["group_key"].to_list() == [100, 300, 200, 400]
    assert result["profit_net"].to_list() == pytest.approx([90.0, 65.0, 15.0, 5.5])


def test_top10_with_store_filter_excludes_other_stores(warehouse_with_data):
    # store=1 has rows 1, 2, 5, 6 (plus anomalous row 7 which must remain excluded).
    result = top10(warehouse_with_data, by="product", rank="profit", store_filter=[1])
    assert result["group_key"].to_list() == [100, 200, 400]
    assert result["profit_net"].to_list() == pytest.approx([90.0, 15.0, 0.5])


def test_top10_products_by_margin_orders_by_weighted_margin(warehouse_with_data):
    result = top10(warehouse_with_data, by="product", rank="margin")
    # Margins (excluding anomalous & cost_missing rows):
    #   300: 65/95   = 68.42%
    #   100: 90/190  = 47.37%
    #   200: 15/95   = 15.79%
    #   400: 5.5/104.5 = 5.26%
    assert result["group_key"].to_list() == [300, 100, 200, 400]
    assert result["margin_net_pct"].to_list() == pytest.approx(
        [68.4211, 47.3684, 15.7895, 5.2632], abs=1e-3
    )


def test_top10_vendors_by_profit_uses_vendor_dimension(warehouse_with_data):
    result = top10(warehouse_with_data, by="vendor", rank="profit")
    # vendor 10: products 100 (90) + 200 (15) = 105
    # vendor 20: products 300 (65) + 400 (5.5) = 70.5
    assert result["group_key"].to_list() == [10, 20]
    assert result["profit_net"].to_list() == pytest.approx([105.0, 70.5])


def test_summary_metrics_aggregates_active_revenue_and_counts_flags(warehouse_with_data):
    m = summary_metrics(warehouse_with_data)
    # Active rows (1-6, excluding anomalous row 7 and cost-missing row 8):
    #   revenue_net = 95+95+95+95+9.5+95 = 484.5
    #   profit_net  = 45+15+65+5+0.5+45 = 175.5
    assert m["total_revenue_net"] == pytest.approx(484.5)
    assert m["total_profit_net"] == pytest.approx(175.5)
    assert m["n_returns"] == 0
    assert m["n_anomalies"] == 1
    assert m["n_cost_missing"] == 1


def test_get_store_options_returns_id_and_city_for_each_store(warehouse_with_data):
    options = get_store_options(warehouse_with_data)
    assert options.columns == ["store_id", "city"]
    assert options.to_dicts() == [
        {"store_id": 1, "city": "A"},
        {"store_id": 2, "city": "B"},
    ]


def test_get_date_bounds_returns_min_and_max_dates_in_dim_date(warehouse_with_data):
    lo, hi = get_date_bounds(warehouse_with_data)
    assert lo == date(2016, 1, 1)
    assert hi == date(2016, 1, 3)
