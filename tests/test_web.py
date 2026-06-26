"""Smoke-тесты Flask routes."""
from __future__ import annotations

import pytest

from src.web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_overview_ok(client):
    r = client.get("/")
    assert r.status_code == 200


def test_product_ok(client):
    r = client.get("/product")
    assert r.status_code == 200


def test_order_ok(client):
    r = client.get("/order")
    assert r.status_code == 200


def test_chart_api_404(client):
    r = client.get("/api/product/nonexistent/chart-data?chart=season")
    assert r.status_code == 404


def test_metrics_api_ok(client):
    r = client.get("/api/product/dlsc002/metrics?years=2024&years=2025")
    assert r.status_code == 200
    data = r.get_json()
    assert "weekly_consumption" in data
