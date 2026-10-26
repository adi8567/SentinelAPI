"""Unit Tests for Path Normalization and Risk Scoring."""

import pytest
from backend.app.schemas.inventory import RiskLevel
from backend.app.services.inventory.path_normalizer import (
    evaluate_endpoint_risk,
    generate_endpoint_id,
    parameterize_path,
)


def test_parameterize_path_patterns():
    # Numeric ID
    assert parameterize_path("/api/v1/users/1001") == "/api/v1/users/{id}"
    assert parameterize_path("/api/v1/orders/55219") == "/api/v1/orders/{id}"

    # UUID
    assert parameterize_path("/api/v1/orders/c6af9ac6-7b61-11e6-9a41-97e8112f1af0") == "/api/v1/orders/{uuid}"

    # Prefixed ID
    assert parameterize_path("/api/v1/catalog/products/prod_99214") == "/api/v1/catalog/products/{id}"
    assert parameterize_path("/customers/cst_8819") == "/customers/{id}"
    assert parameterize_path("/api/v1/cart/items/item_8812") == "/api/v1/cart/items/{id}"

    # Filename
    assert parameterize_path("/billing/invoices/inv_4021.pdf") == "/billing/invoices/{file}"
    assert parameterize_path("/reports/export.csv") == "/reports/{file}"

    # Static paths untouched
    assert parameterize_path("/api/v1/auth/login") == "/api/v1/auth/login"
    assert parameterize_path("/api/v1/catalog/search") == "/api/v1/catalog/search"


def test_endpoint_risk_and_tagging():
    # Admin / Critical
    risk_admin, tags_admin = evaluate_endpoint_risk("GET", "/api/v1/admin/users")
    assert risk_admin == RiskLevel.CRITICAL
    assert "administrative" in tags_admin

    # Auth / High
    risk_auth, tags_auth = evaluate_endpoint_risk("POST", "/api/v1/auth/login")
    assert risk_auth == RiskLevel.HIGH
    assert "authentication" in tags_auth

    # Payment / Financial / High
    risk_pay, tags_pay = evaluate_endpoint_risk("POST", "/api/v1/payments/process")
    assert risk_pay == RiskLevel.HIGH
    assert "financial" in tags_pay

    # Export / Medium
    risk_exp, tags_exp = evaluate_endpoint_risk("GET", "/api/v1/reports/export")
    assert risk_exp == RiskLevel.MEDIUM
    assert "data-transfer" in tags_exp

    # Standard read / Low
    risk_std, tags_std = evaluate_endpoint_risk("GET", "/api/v1/catalog/products")
    assert risk_std == RiskLevel.LOW
    assert "standard-api" in tags_std


def test_endpoint_id_deterministic():
    id1 = generate_endpoint_id("GET", "/api/v1/users/{id}")
    id2 = generate_endpoint_id("GET", "/api/v1/users/{id}")
    id_post = generate_endpoint_id("POST", "/api/v1/users/{id}")

    assert id1 == id2
    assert id1 != id_post
    assert len(id1) == 16
