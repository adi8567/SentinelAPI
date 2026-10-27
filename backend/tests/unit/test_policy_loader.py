"""Unit tests for Policy-as-Code loader and serialization."""

import pytest
from backend.app.schemas.policy import PolicyAction, PolicyRule
from backend.app.services.policy.loader import PolicyLoader


SAMPLE_POLICY_YAML = """
version: "1.0"
policies:
  - policy_id: "test_block_sqli"
    name: "Block SQL Injection"
    description: "Drop all SQLi probes"
    is_enabled: true
    priority: 10
    conditions:
      min_risk_score: 75.0
      attack_types:
        - "sqli"
    action: "block"
    action_params:
      ban_duration_seconds: 1800
  - policy_id: "test_throttle_auth"
    name: "Throttle Auth"
    is_enabled: true
    priority: 50
    conditions:
      endpoint_pattern: "^/api/v1/auth"
    action: "throttle"
    action_params:
      rate_limit_rpm: 5
"""


def test_load_from_yaml_string():
    rules = PolicyLoader.load_from_yaml_string(SAMPLE_POLICY_YAML)
    assert len(rules) == 2
    # Verify priority sorting
    assert rules[0].policy_id == "test_block_sqli"
    assert rules[0].priority == 10
    assert rules[0].action == PolicyAction.BLOCK
    assert rules[0].conditions.min_risk_score == 75.0
    assert "sqli" in rules[0].conditions.attack_types
    assert rules[0].action_params.get("ban_duration_seconds") == 1800

    assert rules[1].policy_id == "test_throttle_auth"
    assert rules[1].priority == 50
    assert rules[1].action == PolicyAction.THROTTLE


def test_export_to_yaml_and_json():
    rules = PolicyLoader.load_from_yaml_string(SAMPLE_POLICY_YAML)
    yaml_out = PolicyLoader.export_to_yaml(rules)
    assert "test_block_sqli" in yaml_out
    assert "test_throttle_auth" in yaml_out

    json_out = PolicyLoader.export_to_json(rules)
    assert '"policy_id": "test_block_sqli"' in json_out


def test_duplicate_policy_id_overwritten():
    duplicate_yaml = """
    policies:
      - policy_id: "rule_1"
        name: "First Version"
        action: "allow"
        priority: 10
      - policy_id: "rule_1"
        name: "Second Version"
        action: "block"
        priority: 5
    """
    rules = PolicyLoader.load_from_yaml_string(duplicate_yaml)
    assert len(rules) == 1
    assert rules[0].name == "Second Version"
    assert rules[0].action == PolicyAction.BLOCK
